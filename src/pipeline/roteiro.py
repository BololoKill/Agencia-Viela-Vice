"""
Roteirista do canal dark: escreve título, gancho e narração a partir do que foi falado no vídeo viral.
A narração própria é o que transforma o corte em conteúdo original do canal.
Não existe mais o formato antigo: sem roteiro válido o vídeo não é feito, e com a IA fora do ar a produção espera.
"""
import json
import math
import re
import time
from datetime import datetime

from google.genai import types

from src.config import VIDEO_SPECS
from src.pipeline import edicao, verificador
from src.utils import censor_text, log_terminal

TEMPO_LIMITE_MS = 30_000
PAUSA_FALHA_S = 300
RODADAS_IA = 2  # Quedas de segundos (503) são comuns: uma nova rodada antes de pausar
ESPERA_ENTRE_RODADAS_S = 20
ESPERA_MAXIMA_ROTEIRO_S = 1800  # Com a gravação pronta, vale esperar até 30 min a IA voltar
TENTATIVAS_ROTEIRO = 3  # Resposta fora do combinado (tamanho, quantidade de capítulos) é pedida de novo
VALIDADE_CONFERENCIA_S = 900  # A IA respondeu nos últimos 15 min: não precisa conferir antes de gravar
LIMITE_TRANSCRICAO = 4000
PERSONA = (
    "Você é o narrador do Viela Vice, um canal brasileiro sem rosto sobre GTA 6. "
    "Fala como um amigo contando a história: ágil, divertido, com gírias leves, sem palavrões. "
    "Nunca invente fatos que não estejam na transcrição e nunca fale do streamer de forma negativa."
)

_ia = {"pausada_ate": 0.0}


class SemRoteiro(RuntimeError):
    """A IA não entregou narração própria para o vídeo, então ele não é feito."""


class IaDeRoteiroFora(SemRoteiro):
    """A IA de roteiro está fora do ar (ou sem chave): nenhum vídeo pode ser narrado agora."""


def _palavras(texto) -> int:
    return len(str(texto or "").split())


def _limpar(texto: str) -> str:
    texto = re.sub(r"\s+", " ", censor_text(str(texto or ""))).strip()
    return texto.strip('"“”')


def ia_em_pausa() -> bool:
    """A IA falhou há pouco e descansa alguns minutos antes de ser chamada de novo."""
    return time.monotonic() < _ia["pausada_ate"]


def _perguntar(prompt: str, rodadas: int = RODADAS_IA):
    """Pede um JSON à IA, tentando os modelos em ordem. Devolve None se nenhum responder."""
    chave = verificador._chave_da_ia()
    _ia["sem_chave"] = not chave
    if not chave or ia_em_pausa():
        return None
    cliente = verificador.genai.Client(
        api_key=chave, http_options=types.HttpOptions(timeout=TEMPO_LIMITE_MS, retry_options=types.HttpRetryOptions(attempts=1)))
    configuracao = types.GenerateContentConfig(temperature=0.9, response_mime_type="application/json")
    falha = None
    for rodada in range(rodadas):
        if rodada:
            time.sleep(ESPERA_ENTRE_RODADAS_S)
        for modelo in VIDEO_SPECS["modelos_texto"]:
            try:
                resposta = cliente.models.generate_content(model=modelo, contents=[PERSONA, prompt], config=configuracao)
                dados = json.loads(resposta.text)
                _ia["respondeu_em"] = time.monotonic()
                return dados
            except Exception as e:
                falha = type(e).__name__
    _ia["pausada_ate"] = time.monotonic() + PAUSA_FALHA_S
    log_terminal(f"[ROTEIRO] IA de roteiro indisponível agora ({falha}). Nenhum vídeo sai sem narração própria: "
                 f"a produção espera e tenta de novo em {PAUSA_FALHA_S // 60} min.")
    return None


def ia_respondendo() -> bool:
    """Antes de gravar, confere se a IA de roteiro responde: sem ela nenhum vídeo pode ser narrado."""
    if ia_em_pausa():
        return False
    if time.monotonic() - _ia.get("respondeu_em", -math.inf) < VALIDADE_CONFERENCIA_S:
        return True
    return isinstance(_perguntar('Confirme que você está disponível. Responda só em JSON: {"ok": true}', rodadas=1), dict)


def estado_da_ia() -> dict:
    """Para o painel: a IA de roteiro está sem chave ou em pausa até que horas."""
    restante = _ia["pausada_ate"] - time.monotonic()
    return {"sem_chave": bool(_ia.get("sem_chave")),
            "pausada_ate": datetime.fromtimestamp(time.time() + restante).strftime("%H:%M") if restante > 0 else None}


def situacao_da_ia() -> str:
    """Explica no painel por que a produção está esperando."""
    if _ia.get("sem_chave"):
        return "Sem a chave da IA de roteiro (GEMINI_API_KEY): sem narração própria nenhum vídeo é feito."
    return "IA de roteiro fora do ar: o próximo vídeo viral só é baixado quando ela voltar, para todo vídeo ter narração própria."


def com_roteiro(gerar, *args, avisar=None):
    """
    Insiste no roteiro do vídeo, porque o canal dark não publica sem narração própria.
    Resposta fora do combinado é pedida de novo; com a IA em pausa, espera ela voltar.
    Devolve None quando a IA responde, mas não acerta o roteiro deste vídeo.
    Levanta IaDeRoteiroFora quando falta a chave ou a IA não volta a tempo.
    """
    inicio = time.monotonic()
    tentativas = 0
    while True:
        roteiro = gerar(*args)
        if roteiro:
            return roteiro
        if _ia.get("sem_chave"):
            raise IaDeRoteiroFora("Sem a chave da IA de roteiro (GEMINI_API_KEY): nenhum vídeo pode ser narrado.")
        espera = _ia["pausada_ate"] - time.monotonic()
        if espera <= 0:
            tentativas += 1
            if tentativas >= TENTATIVAS_ROTEIRO:
                return None
            continue
        if time.monotonic() - inicio + espera > ESPERA_MAXIMA_ROTEIRO_S:
            raise IaDeRoteiroFora(f"A IA de roteiro ficou fora do ar por mais de {ESPERA_MAXIMA_ROTEIRO_S // 60} min; "
                                  "nenhum vídeo sai sem narração própria.")
        if avisar:
            avisar(math.ceil(espera / 60))
        time.sleep(espera)


def _transcricao(segmentos: list) -> str:
    return " ".join(str(s.get("text", "")).strip() for s in segmentos)[:LIMITE_TRANSCRICAO]


def roteiro_short(segmentos: list, streamer: str):
    """Título, gancho da tela e narração de abertura de um Short. None quando a IA falha ou erra o combinado."""
    prompt = (
        f"Transcrição do momento mais intenso de um vídeo viral de {streamer} jogando GTA 6:\n\"{_transcricao(segmentos)}\"\n\n"
        "Crie o roteiro de um YouTube Short. Responda só em JSON:\n"
        '{"titulo": "título curioso de até 60 caracteres, sem hashtag", '
        '"gancho": "texto da tela com 3 a 5 palavras e no máximo 30 caracteres", '
        '"narracao": "1 ou 2 frases de 12 a 28 palavras que prendem a atenção e preparam o que vem, sem contar o final"}'
    )
    dados = _perguntar(prompt)
    if not isinstance(dados, dict):
        return None
    titulo, gancho, narracao = (_limpar(dados.get(c)) for c in ("titulo", "gancho", "narracao"))
    if not (10 <= _palavras(narracao) <= 34 and 3 <= len(titulo) <= 80):
        return None
    # O gancho precisa caber inteiro nas 2 linhas do topo do Short; se não couber, entra o gancho automático
    gancho = gancho.upper()
    cabe = 2 <= _palavras(gancho) <= 7 and " ".join(edicao.quebrar_linhas(gancho)) == " ".join(gancho.split())
    return {"titulo": titulo.replace("#", "")[:80], "gancho": gancho if cabe else None, "narracao": narracao}


def _narracao_do_longo(dados, quantidade: int):
    """Confere o roteiro do vídeo longo: título, abertura e exatamente uma narração por capítulo."""
    if not isinstance(dados, dict) or not isinstance(dados.get("capitulos"), list):
        return None
    titulo, abertura = _limpar(dados.get("titulo")), _limpar(dados.get("abertura"))
    narracoes = [_limpar(t) for t in dados["capitulos"]]
    if len(narracoes) != quantidade or not (10 <= _palavras(abertura) <= 36) or not (3 <= len(titulo) <= 90):
        return None
    if any(not (5 <= _palavras(t) <= 28) for t in narracoes):
        return None
    return {"titulo": titulo.replace("#", "")[:90], "abertura": abertura, "capitulos": narracoes}


def roteiro_compilacao(trechos: list):
    """
    Narração do Top da semana: um trecho de cada vídeo viral, em contagem regressiva.
    "trechos" traz (criador, transcrição) na ordem do vídeo. None quando a IA falha ou erra o combinado.
    """
    quantidade = len(trechos)
    blocos = "\n".join(
        f"{quantidade - i}º lugar, vídeo de {criador}: \"{_transcricao([{'text': texto or '(sem fala)'}])[:900]}\""
        for i, (criador, texto) in enumerate(trechos))
    prompt = (
        f"Trechos dos {quantidade} vídeos de GTA 6 mais vistos da semana no YouTube, em contagem regressiva "
        f"(o primeiro é o {quantidade}º lugar e o último é o 1º):\n{blocos}\n\n"
        "Escreva a narração do vídeo Top da semana. Responda só em JSON:\n"
        '{"titulo": "título chamativo de até 70 caracteres, sem hashtag", '
        '"abertura": "1 ou 2 frases de 12 a 30 palavras apresentando o top da semana", '
        f'"capitulos": [lista com exatamente {quantidade} frases, uma por trecho, de 8 a 22 palavras cada, '
        "dizendo a posição, citando o criador pelo nome e preparando o momento]}"
    )
    return _narracao_do_longo(_perguntar(prompt), quantidade)
