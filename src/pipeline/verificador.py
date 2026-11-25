"""
Confere pela imagem se uma gravação mostra mesmo GTA 6.
O título e a categoria da transmissão podem estar errados: a prova é o que aparece na tela.
"""
import io
import json
import os
import re
import subprocess
import time
from datetime import datetime
from statistics import median

import numpy as np
from dotenv import dotenv_values
from google import genai
from google.genai import types
from PIL import Image

from src.config import BASE_DIR, VIDEO_SPECS
from src.pipeline.ffmpeg_runner import ambiente_ffmpeg
from src.utils import log_terminal

QUADROS_ANALISADOS = 6
LARGURA_QUADRO = 640
CONFIANCA_MINIMA = 0.6
MINIMO_COLORIDO = 0.02
BRILHO_MINIMO = 25
TEMPO_LIMITE_IA_MS = 20_000
TEMPO_LIMITE_QUADRO_S = 60
PAUSA_IA_S = 1800  # Depois de uma falha geral, a checagem segue só pela cor por 30 minutos

_ia = {"pausada_ate": 0.0}

# GTA V e GTA VI têm a mesma interface (minimapa, estrelas, celular) e a IA confunde os dois; a busca já descarta os
# títulos de GTA 5. Regressão: o mesmo trecho do Paulinho o Loko saiu como GTA VI duas vezes e como GTA V na terceira.
_GTA_ANTERIOR = re.compile(r"(?i)\b(gta|grand\s+theft\s+auto)\s*(v|5)\b")

# GTA VI saiu em 19/11/2026 e a IA quase não viu o jogo: sem as pistas abaixo ela confundiu um GTA VI com Far Cry 6
PERGUNTA = (
    "Estas imagens foram tiradas de um vídeo de gameplay. Identifique o jogo que aparece na tela. "
    'Responda somente em JSON: {"jogo": "nome do jogo", "tem_jogo_na_tela": true ou false, '
    '"e_gta6": true ou false, "confianca": numero de 0 a 1}. '
    "tem_jogo_na_tela é false quando as imagens mostram só anúncio, tela de espera, carregamento ou a câmera do streamer. "
    "e_gta6 só é true quando a maior parte do jogo mostrado é Grand Theft Auto VI, lançado em novembro de 2026: "
    "mundo aberto em Leonida e Vice City, cidade tropical moderna inspirada em Miami, protagonistas Jason e Lucia. "
    "Pistas de GTA: minimapa no canto inferior esquerdo, estrelas de procurado, celular do personagem, "
    "trânsito e polícia de cidade americana atual. Não confunda com Far Cry 6 (bússola no alto da tela, guerrilha "
    "numa ilha caribenha) nem com GTA V (Los Santos). Se ficar em dúvida entre GTA VI e outro jogo, use confiança baixa. "
    "Títulos, textos do chat e a câmera do streamer não contam como prova."
)


def _duracao(video) -> float:
    try:
        saida = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
            capture_output=True, text=True, env=ambiente_ffmpeg(), timeout=TEMPO_LIMITE_QUADRO_S,
        )
        return float(saida.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0.0


def _quadro_em(video, instante: float) -> bytes:
    try:
        return subprocess.run(
            ["ffmpeg", "-hide_banner", "-v", "error", "-nostdin", "-ss", f"{instante:.2f}", "-i", str(video), "-frames:v", "1",
             "-vf", f"scale={LARGURA_QUADRO}:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-q:v", "5", "-"],
            capture_output=True, env=ambiente_ffmpeg(), timeout=TEMPO_LIMITE_QUADRO_S,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return b""


def extrair_quadros(video, inicio: float = 0.0, duracao: float = None, quantidade: int = QUADROS_ANALISADOS) -> list:
    """Retira quadros espalhados pelo trecho. Uma amostra curta demais é analisada desde o começo."""
    total = _duracao(video)
    if total <= 0:
        return []
    if inicio >= total:
        inicio = 0.0
    alcance = min(duracao or total, total - inicio)
    instantes = (inicio + alcance * (i + 0.5) / quantidade for i in range(quantidade))
    return [quadro for quadro in map(lambda t: _quadro_em(video, t), instantes) if quadro]


def _fracao_colorida(quadro: bytes):
    """Parte da imagem com cor viva. Quadros escuros não dizem nada e ficam de fora."""
    hsv = np.asarray(Image.open(io.BytesIO(quadro)).convert("HSV"), dtype=float)
    if hsv[..., 2].mean() < BRILHO_MINIMO:
        return None
    return float(((hsv[..., 1] > 60) & (hsv[..., 2] > 50)).mean())


def _imagem_sem_cor(quadros: list) -> bool:
    medidas = [fracao for fracao in map(_fracao_colorida, quadros) if fracao is not None]
    return bool(medidas) and median(medidas) < MINIMO_COLORIDO


def _chave_da_ia():
    return os.environ.get("GEMINI_API_KEY") or dotenv_values(BASE_DIR / ".env").get("GEMINI_API_KEY")


def estado_da_ia() -> dict:
    """Para o painel: a IA que confere o jogo está sem chave ou em pausa até que horas."""
    restante = _ia["pausada_ate"] - time.monotonic()
    return {"sem_chave": not _chave_da_ia(),
            "pausada_ate": datetime.fromtimestamp(time.time() + restante).strftime("%H:%M") if restante > 0 else None}


def _veredito(dados):
    """A resposta combinada é um objeto JSON; alguns modelos devolvem o objeto dentro de uma lista: vale o primeiro."""
    if isinstance(dados, list):
        return next((item for item in dados if isinstance(item, dict)), dados)
    return dados


def _perguntar_a_ia(quadros: list):
    """Pergunta qual jogo está na tela, tentando os modelos em ordem. Devolve None se nenhum responder."""
    chave = _chave_da_ia()
    if not chave or time.monotonic() < _ia["pausada_ate"]:
        return None
    opcoes_http = types.HttpOptions(timeout=TEMPO_LIMITE_IA_MS, retry_options=types.HttpRetryOptions(attempts=1))
    cliente = genai.Client(api_key=chave, http_options=opcoes_http)
    conteudo = [types.Part.from_bytes(data=quadro, mime_type="image/jpeg") for quadro in quadros] + [PERGUNTA]
    configuracao = types.GenerateContentConfig(temperature=0, response_mime_type="application/json")
    falha = None
    for modelo in VIDEO_SPECS["modelos_visao"]:
        try:
            resposta = cliente.models.generate_content(model=modelo, contents=conteudo, config=configuracao)
            veredito = _veredito(json.loads(resposta.text))
            # O registro diz qual modelo respondeu: os mais leves erram mais o jogo
            return {**veredito, "modelo": modelo} if isinstance(veredito, dict) else veredito
        except Exception as e:
            # Só o tipo do erro vai para o registro: a mensagem do serviço poderia carregar dados da conexão.
            falha = type(e).__name__
    _ia["pausada_ate"] = time.monotonic() + PAUSA_IA_S
    log_terminal(f"[TEMA] Identificação do jogo por imagem indisponível agora ({falha}). "
                 f"Nova tentativa em {PAUSA_IA_S // 60} min; até lá vale a checagem de cor.")
    return None


def _mostra_outro_jogo(veredito) -> bool:
    """Só recusa com certeza: dúvida, anúncio ou tela de espera seguem para a aprovação humana."""
    if not isinstance(veredito, dict):
        return False
    try:
        confianca = float(veredito.get("confianca"))
    except (TypeError, ValueError):
        return False
    if _GTA_ANTERIOR.search(str(veredito.get("jogo") or "")):
        return False
    return veredito.get("tem_jogo_na_tela") is True and veredito.get("e_gta6") is False and confianca >= CONFIANCA_MINIMA


def confere_gta6(video, inicio: float = 0.0, duracao: float = None) -> bool:
    """Diz se a gravação pode virar vídeo. Sem a IA, recusa apenas a imagem claramente sem cor."""
    quadros = extrair_quadros(video, inicio, duracao)
    if not quadros:
        log_terminal("[TEMA] Não foi possível ler quadros da gravação para conferir o jogo.")
        return True
    veredito = _perguntar_a_ia(quadros)
    if veredito is None:
        return not _imagem_sem_cor(quadros)
    if not isinstance(veredito, dict):
        # Regressão: a conferência do LOUD Coringa (24/11) passou sem deixar nenhuma linha no registro
        log_terminal(f"[TEMA] A IA respondeu fora do formato combinado ({type(veredito).__name__}); "
                     "vale a checagem de cor.")
        return not _imagem_sem_cor(quadros)
    modelo = f", {veredito['modelo']}" if veredito.get("modelo") else ""
    log_terminal(f"[TEMA] Jogo identificado na imagem: {veredito.get('jogo')} (confiança {veredito.get('confianca')}{modelo}).")
    if _GTA_ANTERIOR.search(str(veredito.get("jogo") or "")):
        log_terminal("[TEMA] A IA confunde GTA V com GTA VI: o vídeo segue, e a palavra final é sua na Diretoria.")
    return not _mostra_outro_jogo(veredito)
