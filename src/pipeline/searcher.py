"""
Módulo de Varredura e Busca de Conteúdo.
Prioridade: lives de GTA 6 na Twitch, lives de GTA 6 no YouTube, vídeos novos de GTA 6 e, como reserva, GTA RP.
"""
import random
import re
from datetime import datetime, timedelta
from urllib.parse import quote_plus
import yt_dlp
from src.config import CANAIS_TWITCH, STREAMERS_BR, DESCOBERTOS_PATH, HISTORICO_FILE
from src.pipeline.estado import classificar_erro, em_quarentena
from src.utils import load_json_safe, log_terminal

CATEGORIAS_BLOQUEIO = ("rate_limit", "bloqueio_youtube")
FILTRO_LIVE = "EgJAAQ%253D%253D"
FILTRO_RECENTES = "CAISAhAB"
DIAS_RECENTES = 7
DURACAO_MINIMA_S = 180
DURACAO_MAXIMA_S = 7200
RESULTADOS_POR_BUSCA = 12
STREAMERS_POR_CICLO = 4
MAX_FALHAS_TWITCH = 3
AVISOS_CANAL_INDISPONIVEL = ("not currently live", "does not exist")

CONSULTAS_LIVE_GTA6 = ["GTA 6 ao vivo", "GTA VI ao vivo Brasil", "jogando GTA 6 ao vivo"]
CONSULTAS_NOVOS_GTA6 = ["GTA 6 gameplay português", "jogando GTA 6", "GTA 6 novidades Brasil"]

_REGEX_GTA6 = re.compile(r"\bgta\s*-?\s*(?:6|vi)\b|\bgrand theft auto\s*(?:6|vi)\b", re.I)
_REGEX_GTA5 = re.compile(r"\bgta\s*-?\s*(?:5|v)\b", re.I)
_REGEX_FORA_DO_TEMA = re.compile(
    r"contagem|countdown|enhanced|\bmods?\b|\bfake\b|conceito|concept|pr[eé][\s-]*gta|antes d[oe] gta"
    r"|free\s*fire|fortnite|minecraft|roblox|valorant|counter[\s-]*strike|\bcs2\b|league of legends|\blol\b",
    re.I
)
_REGEX_PORTUGUES = re.compile(
    r"\b(?:ao vivo|jogando|jogo|brasil|br|pt-?br|portugu[eê]s|novidades|novo|nova|primeira|agora|aqui|você|vazou)\b"
    r"|[ãõçáéíóúâêô]", re.I
)
_REGEX_TEMA_TWITCH = re.compile(
    r"\bgta\s*-?\s*(?:6|vi)\b|\bgrand theft auto\s*(?:6|vi)\b|\bvice\s*city\b|\bleonida\b", re.I
)
_REGEX_REPRISE = re.compile(r"\brerun\b|\breprise\b", re.I)


class _SemMensagens:
    """Evita que cada canal offline apareça como erro no console."""

    def debug(self, _mensagem):
        pass

    warning = error = debug


def carregar_historico():
    """Carrega IDs de vídeos já baixados ou processados para evitar duplicidade."""
    if not HISTORICO_FILE.exists():
        return set()
    try:
        with open(HISTORICO_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except Exception:
        return set()


def registrar_historico(identificador: str):
    """Salva ID do vídeo no arquivo histórico."""
    try:
        with open(HISTORICO_FILE, "a", encoding="utf-8") as f:
            f.write(f"{identificador}\n")
    except Exception:
        pass


def titulo_e_gta6(titulo: str) -> bool:
    """Reconhece as grafias de GTA 6 e descarta títulos sobre GTA 5."""
    texto = str(titulo)
    return bool(_REGEX_GTA6.search(texto)) and not _REGEX_GTA5.search(texto)


def _no_tema(titulo: str) -> bool:
    return titulo_e_gta6(titulo) and not _REGEX_FORA_DO_TEMA.search(str(titulo))


def _titulo_aproveitavel(titulo: str) -> bool:
    return _no_tema(titulo) and bool(_REGEX_PORTUGUES.search(str(titulo)))


def titulo_twitch_no_tema(titulo) -> bool:
    """Na Twitch o título nem sempre cita o jogo pelo nome: 'Vice City' também vale."""
    texto = str(titulo or "")
    return (bool(_REGEX_TEMA_TWITCH.search(texto)) and not _REGEX_REPRISE.search(texto)
            and not _REGEX_GTA5.search(texto) and not _REGEX_FORA_DO_TEMA.search(texto))


def _url_busca(consulta: str, filtro: str) -> str:
    return f"https://www.youtube.com/results?search_query={quote_plus(consulta)}&sp={filtro}"


def _url_video(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def _listar(url: str) -> list:
    """Consulta uma página de resultados sem baixar os vídeos."""
    opcoes = {
        "extract_flat": True, "skip_download": True, "quiet": True,
        "no_warnings": True, "playlistend": RESULTADOS_POR_BUSCA,
    }
    with yt_dlp.YoutubeDL(opcoes) as ydl:
        resultado = ydl.extract_info(url, download=False)
    return [e for e in (resultado or {}).get("entries", []) if e]


def _detalhar(url: str) -> dict:
    """Confirma data e duração reais de um vídeo candidato."""
    with yt_dlp.YoutubeDL({"skip_download": True, "quiet": True, "no_warnings": True}) as ydl:
        return ydl.extract_info(url, download=False) or {}


def _e_recente(upload_date) -> bool:
    try:
        return datetime.strptime(str(upload_date), "%Y%m%d") >= datetime.now() - timedelta(days=DIAS_RECENTES)
    except ValueError:
        return False


def _disponivel(entry: dict, historico: set) -> bool:
    vid_id = entry.get("id")
    return bool(vid_id) and vid_id not in historico and _url_video(vid_id) not in historico and not em_quarentena(vid_id)


def _montar(entry: dict, streamer, origem: str, duracao=None, ao_vivo: bool = False) -> dict:
    return {
        "id": entry["id"],
        "url": _url_video(entry["id"]),
        "title": entry.get("title", ""),
        "streamer": streamer or entry.get("channel") or entry.get("uploader") or "GTA 6",
        "duration": duracao,
        "origem": origem,
        "ao_vivo": ao_vivo,
    }


class _Consultas:
    """Executa buscas tolerando falhas isoladas e interrompendo em bloqueios do YouTube."""

    def __init__(self):
        self.ok = 0
        self.ultimo_erro = None

    def listar(self, url: str, rotulo: str) -> list:
        try:
            entradas = _listar(url)
        except Exception as e:
            info = classificar_erro(e)
            log_terminal(f"[BUSCA] Falha ao consultar {rotulo}: {info['mensagem']}")
            if info["categoria"] in CATEGORIAS_BLOQUEIO:
                raise
            self.ultimo_erro = e
            return []
        self.ok += 1
        return entradas


def _consultar_canal_twitch(canal: str):
    """Devolve os dados da transmissão ou None quando o canal não está ao vivo."""
    opcoes = {"skip_download": True, "quiet": True, "no_warnings": True, "socket_timeout": 20, "logger": _SemMensagens()}
    try:
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            return ydl.extract_info(f"https://www.twitch.tv/{canal}", download=False)
    except Exception as e:
        if any(aviso in str(e) for aviso in AVISOS_CANAL_INDISPONIVEL):
            return None
        raise


def _buscar_live_twitch(historico: set):
    """Procura, em todos os canais cadastrados, uma transmissão de GTA 6 ainda não aproveitada."""
    canais = list(CANAIS_TWITCH)
    random.shuffle(canais)
    falhas = 0
    for canal in canais:
        try:
            live = _consultar_canal_twitch(canal)
        except Exception as e:
            falhas += 1
            log_terminal(f"[BUSCA] Twitch indisponível para {canal}: {classificar_erro(e)['mensagem']}")
            if falhas >= MAX_FALHAS_TWITCH:
                return None
            continue
        if not live or not titulo_twitch_no_tema(live.get("description")):
            continue
        video_id = f"twitch_{live['id']}"
        if video_id in historico or em_quarentena(video_id):
            continue
        return {
            "id": video_id,
            "url": f"https://www.twitch.tv/{canal}",
            "title": live.get("description", ""),
            "streamer": live.get("uploader") or canal,
            "duration": None,
            "origem": "live_twitch",
            "ao_vivo": True,
        }
    return None


def _buscar_live_gta6(consultas: _Consultas, historico: set):
    for consulta in CONSULTAS_LIVE_GTA6:
        for entry in consultas.listar(_url_busca(consulta, FILTRO_LIVE), consulta):
            if entry.get("live_status") == "is_live" and _disponivel(entry, historico) \
                    and _titulo_aproveitavel(entry.get("title", "")):
                return _montar(entry, None, "live_gta6", ao_vivo=True)
    return None


def _validar_video_novo(entry: dict, streamer):
    if entry.get("live_status") in ("is_live", "is_upcoming"):
        return None
    try:
        detalhe = _detalhar(_url_video(entry["id"]))
    except Exception as e:
        if classificar_erro(e)["categoria"] in CATEGORIAS_BLOQUEIO:
            raise
        return None
    duracao = detalhe.get("duration") or 0
    if detalhe.get("live_status") in ("is_live", "is_upcoming") or not _e_recente(detalhe.get("upload_date")):
        return None
    if not DURACAO_MINIMA_S <= duracao <= DURACAO_MAXIMA_S:
        return None
    return _montar(entry, streamer, "novo_gta6", duracao=duracao)


def _buscar_novo_gta6(consultas: _Consultas, historico: set, streamers: list):
    buscas = [(consulta, None) for consulta in CONSULTAS_NOVOS_GTA6]
    buscas += [(f"{nome} GTA 6", nome) for nome in streamers[:STREAMERS_POR_CICLO]]

    for consulta, streamer in buscas:
        for entry in consultas.listar(_url_busca(consulta, FILTRO_RECENTES), consulta):
            titulo = entry.get("title", "")
            valido = _no_tema(titulo) if streamer else _titulo_aproveitavel(titulo)
            if not valido or not _disponivel(entry, historico):
                continue
            video = _validar_video_novo(entry, streamer)
            if video:
                return video
    return None


def _buscar_gta_rp(consultas: _Consultas, historico: set, streamers: list):
    for streamer in streamers:
        for entry in consultas.listar(f"ytsearch3:{streamer} GTA RP", streamer):
            duracao = entry.get("duration") or 0
            if _disponivel(entry, historico) and DURACAO_MINIMA_S <= duracao <= DURACAO_MAXIMA_S:
                return _montar(entry, streamer, "gta_rp", duracao=duracao)
    return None


def buscar_melhor_live():
    """
    Seleciona o próximo conteúdo seguindo a prioridade de GTA 6.
    Bloqueios do YouTube são propagados para não serem confundidos com "nada novo".
    """
    historico = carregar_historico()
    descobertos = load_json_safe(DESCOBERTOS_PATH, [])
    streamers = list(set(STREAMERS_BR + descobertos))
    random.shuffle(streamers)

    video = _buscar_live_twitch(historico)
    if video:
        return video

    consultas = _Consultas()
    video = (
        _buscar_live_gta6(consultas, historico)
        or _buscar_novo_gta6(consultas, historico, streamers)
        or _buscar_gta_rp(consultas, historico, streamers)
    )
    if video:
        return video
    if consultas.ultimo_erro is not None and consultas.ok == 0:
        raise consultas.ultimo_erro
    return None
