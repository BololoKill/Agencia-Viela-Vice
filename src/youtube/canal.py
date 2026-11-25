"""
Números reais do canal no YouTube para o painel: inscritos, visualizações e vídeos publicados.
A consulta é só de leitura, custa 1 unidade da cota da API e roda em segundo plano no máximo uma vez por hora:
o painel nunca espera o YouTube responder.
"""
import threading
import time
from datetime import datetime

from googleapiclient.discovery import build

from src.utils import log_terminal
from src.youtube.auth import obter_credenciais

INTERVALO_S = 3600

_cache = {"dados": {}, "consultado_em": None, "consultando": False}
_trava = threading.Lock()


def _consultar(canal_id: str = "1") -> dict:
    creds = obter_credenciais(canal_id)
    if not creds:
        return {}
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    itens = youtube.channels().list(part="statistics,snippet", mine=True).execute().get("items", [])
    if not itens:
        return {}
    numeros = itens[0].get("statistics", {})
    return {
        "nome": itens[0].get("snippet", {}).get("title", ""),
        "inscritos": int(numeros.get("subscriberCount", 0)),
        "visualizacoes": int(numeros.get("viewCount", 0)),
        "videos": int(numeros.get("videoCount", 0)),
        "atualizado_em": datetime.now().strftime("%H:%M"),
    }


def _atualizar():
    try:
        dados = _consultar()
    except Exception as e:
        log_terminal(f"[CANAL] Números do canal indisponíveis agora ({type(e).__name__}); nova consulta em 1 hora.")
        dados = None
    with _trava:
        if dados is not None:
            _cache["dados"] = dados
        _cache["consultado_em"] = time.monotonic()
        _cache["consultando"] = False


def estatisticas_do_canal() -> dict:
    """Devolve na hora os últimos números conhecidos; se tiverem mais de 1 hora, atualiza em segundo plano."""
    with _trava:
        vencido = _cache["consultado_em"] is None or time.monotonic() - _cache["consultado_em"] >= INTERVALO_S
        if vencido and not _cache["consultando"]:
            _cache["consultando"] = True
            threading.Thread(target=_atualizar, daemon=True, name="numeros-do-canal").start()
        return dict(_cache["dados"])
