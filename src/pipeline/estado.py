"""
Estado operacional da produção: trava de ciclo único, saúde, pausa, quarentena e diagnóstico de erros.
"""
import errno
import json
import os
import threading
import time
from datetime import datetime
import psutil
from src.config import STATUS_VIGIA_FILE, TRAVA_CICLO_FILE, FALHAS_FILE, CONTROLE_PRODUCAO_FILE
from src.pipeline.ffmpeg_runner import FFmpegError
from src.utils import load_json_safe, save_json_safe

LIMITE_TRAVADO_S = 180
LIMITE_ROBO_PARADO_S = 120
MAX_TENTATIVAS_VIDEO = 3

_trava_local = threading.Lock()
_trava_status = threading.Lock()
_trava_falhas = threading.Lock()

MENSAGENS_SAUDE = {
    "ocioso": "Robô Vigia ativo, aguardando a próxima varredura.",
    "pausado": "Produção pausada pelo painel.",
    "parado": "Robô Vigia desligado. Use a opção 1 do launcher para ligar a produção.",
    "travado": "A produção parou de responder. Reinicie o sistema pelo launcher.",
}


def classificar_erro(erro: Exception) -> dict:
    """Identifica a origem da falha e por quanto tempo a produção deve aguardar."""
    texto = str(erro).lower()

    def resultado(categoria, mensagem, transitorio, espera_s):
        return {
            "categoria": categoria,
            "mensagem": mensagem,
            "transitorio": transitorio,
            "espera_s": espera_s,
            "em": datetime.now().strftime("%H:%M:%S"),
        }

    if isinstance(erro, FFmpegError):
        return resultado("render", f"Falha no editor: {erro}", False, 60)
    if "429" in texto or "too many requests" in texto:
        return resultado("rate_limit", "YouTube limitou as requisições (HTTP 429).", True, 900)
    if "not a bot" in texto or "sign in to confirm" in texto:
        return resultado("bloqueio_youtube", "YouTube pediu confirmação anti-robô no download.", True, 1800)
    if "quota" in texto:
        return resultado("cota_api", "Cota diária da API do YouTube esgotada.", True, 3600)
    if (isinstance(erro, OSError) and erro.errno == errno.ENOSPC) or "no space left" in texto:
        return resultado("disco", "Espaço em disco insuficiente para produzir.", True, 600)
    termos_rede = ("getaddrinfo", "timed out", "connection", "network", "unreachable", "temporary failure")
    if isinstance(erro, (ConnectionError, TimeoutError)) or any(t in texto for t in termos_rede):
        return resultado("rede", "Falha de conexão com a internet.", True, 120)
    return resultado("desconhecido", f"Erro inesperado: {str(erro)[:300]}", False, 60)


def _dono_vivo(dados) -> bool:
    """Confirma que o processo dono da trava ainda existe, evitando PID reaproveitado."""
    try:
        pid = int(dados["pid"])
        if pid == os.getpid():
            return False
        return abs(psutil.Process(pid).create_time() - float(dados["criado_em"])) < 2
    except (KeyError, TypeError, ValueError, psutil.Error):
        return False


def _trava_recente() -> bool:
    """Uma trava ilegível criada há instantes ainda pode estar sendo gravada."""
    try:
        return time.time() - TRAVA_CICLO_FILE.stat().st_mtime < 5
    except OSError:
        return False


class TravaCiclo:
    """Garante um único ciclo de produção entre threads e processos."""

    def __init__(self):
        self._ativa = False

    def adquirir(self) -> bool:
        if not _trava_local.acquire(blocking=False):
            return False
        try:
            if self._criar_arquivo():
                self._ativa = True
                return True
        except OSError:
            pass
        _trava_local.release()
        return False

    def _criar_arquivo(self) -> bool:
        for _ in range(2):
            try:
                descritor = os.open(TRAVA_CICLO_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                dados = load_json_safe(TRAVA_CICLO_FILE, None)
                if _dono_vivo(dados) or (dados is None and _trava_recente()):
                    return False
                TRAVA_CICLO_FILE.unlink(missing_ok=True)
                continue
            with os.fdopen(descritor, "w", encoding="utf-8") as f:
                json.dump({"pid": os.getpid(), "criado_em": psutil.Process().create_time()}, f)
            return True
        return False

    def liberar(self):
        if not self._ativa:
            return
        self._ativa = False
        try:
            TRAVA_CICLO_FILE.unlink(missing_ok=True)
        except OSError:
            pass
        _trava_local.release()


def ciclo_em_andamento() -> bool:
    """Indica se existe um ciclo ativo neste ou em outro processo."""
    if _trava_local.locked():
        return True
    return _dono_vivo(load_json_safe(TRAVA_CICLO_FILE, None))


def _ler_status_bruto() -> dict:
    dados = load_json_safe(STATUS_VIGIA_FILE, {})
    return dados if isinstance(dados, dict) else {}


def publicar_status(**campos):
    """Atualiza o status preservando os campos anteriores e renovando o batimento."""
    with _trava_status:
        dados = _ler_status_bruto()
        dados.update(campos)
        dados["heartbeat"] = time.time()
        dados["atualizado_em"] = datetime.now().strftime("%H:%M:%S")
        save_json_safe(STATUS_VIGIA_FILE, dados)


def producao_ativa() -> bool:
    dados = load_json_safe(CONTROLE_PRODUCAO_FILE, {})
    return not (isinstance(dados, dict) and dados.get("ativo") is False)


def definir_producao_ativa(ativo: bool):
    save_json_safe(CONTROLE_PRODUCAO_FILE, {"ativo": bool(ativo)})


def ler_status() -> dict:
    """Entrega ao painel a situação real da produção."""
    dados = _ler_status_bruto()
    try:
        idade = max(0.0, time.time() - float(dados.get("heartbeat", 0)))
    except (TypeError, ValueError):
        idade = float("inf")
    ativo = producao_ativa()
    erro = dados.get("erro") if isinstance(dados.get("erro"), dict) else None
    etapa = dados.get("etapa") or ""

    if ciclo_em_andamento():
        saude = "travado" if idade > LIMITE_TRAVADO_S else "produzindo"
    elif idade > LIMITE_ROBO_PARADO_S:
        saude = "parado"
    elif not ativo:
        saude = "pausado"
    elif erro:
        saude = "erro"
    else:
        saude = "ocioso"

    if saude == "produzindo":
        mensagem = etapa or "Produção em andamento."
    elif saude == "erro":
        mensagem = erro.get("mensagem") or "A última tentativa de produção falhou."
    else:
        mensagem = MENSAGENS_SAUDE[saude]

    return {
        "saude": saude,
        "mensagem": mensagem,
        "etapa": etapa,
        "progresso": dados.get("progresso", 0),
        "streamer": dados.get("streamer", ""),
        "ativo": ativo,
        "erro": erro,
        "atualizado_em": dados.get("atualizado_em", ""),
        "proxima_tentativa_em": dados.get("proxima_tentativa_em"),
    }


def registrar_falha(video_id: str, info: dict) -> int:
    """Contabiliza falhas definitivas de um vídeo e retorna o total de tentativas."""
    with _trava_falhas:
        falhas = load_json_safe(FALHAS_FILE, {})
        falhas = falhas if isinstance(falhas, dict) else {}
        registro = falhas.get(video_id) if isinstance(falhas.get(video_id), dict) else {}
        tentativas = int(registro.get("tentativas", 0)) + 1
        falhas[video_id] = {
            "tentativas": tentativas,
            "categoria": info.get("categoria"),
            "mensagem": info.get("mensagem"),
            "em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_json_safe(FALHAS_FILE, falhas)
        return tentativas


def em_quarentena(video_id: str) -> bool:
    """Vídeos que falharam repetidamente deixam de consumir horas de processamento."""
    falhas = load_json_safe(FALHAS_FILE, {})
    registro = falhas.get(video_id) if isinstance(falhas, dict) else None
    return isinstance(registro, dict) and int(registro.get("tentativas", 0)) >= MAX_TENTATIVAS_VIDEO
