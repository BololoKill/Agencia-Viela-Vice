"""
Módulo de Busca de Conteúdo.
O canal dark não grava mais lives: a matéria-prima são os vídeos de GTA 6 em português mais vistos
da semana no YouTube, no máximo um por criador. Com a semana toda aproveitada, entram os mais vistos do mês.
"""
import random
import re
import time
from urllib.parse import quote_plus
import yt_dlp
from src.config import STREAMERS_BR, DESCOBERTOS_PATH, HISTORICO_FILE
from src.pipeline.estado import classificar_erro, em_quarentena
from src.utils import load_json_safe, log_terminal

CATEGORIAS_BLOQUEIO = ("rate_limit", "bloqueio_youtube")
# Resultados ordenados por visualizações, só vídeos: publicados nesta semana e, na reserva, neste mês
FILTRO_MAIS_VISTOS_SEMANA = "CAMSBAgDEAE%253D"
FILTRO_MAIS_VISTOS_MES = "CAMSBAgEEAE%253D"
DURACAO_MINIMA_S = 480  # Em vídeos curtos, o Short e o trecho do Top seriam boa parte do vídeo de outro criador
VISUALIZACOES_MINIMAS = 100_000  # Abaixo disso não é viral: a busca do mês chegou a trazer um vídeo com 797
RESULTADOS_POR_BUSCA = 20
STREAMERS_POR_CICLO = 4
PAUSA_YOUTUBE_S = 7200
CANAL_PROPRIO = "viela vice"
AINDA_NO_AR = ("is_live", "is_upcoming", "post_live")

_fontes = {"youtube_pausado_ate": 0.0}

CONSULTAS_VIRAIS = ["GTA 6", "GTA 6 gameplay português", "GTA 6 brasil", "GTA VI português"]

_REGEX_GTA6 = re.compile(r"\bgta\s*-?\s*(?:6|vi)\b|\bgrand theft auto\s*(?:6|vi)\b", re.I)
_REGEX_GTA5 = re.compile(r"\bgta\s*-?\s*(?:5|v)\b", re.I)
_REGEX_FORA_DO_TEMA = re.compile(
    r"contagem|countdown|enhanced|\bmods?\b|\bfake\b|conceito|concept|pr[eé][\s-]*gta|antes d[oe] gta"
    r"|free\s*fire|fortnite|minecraft|roblox|valorant|counter[\s-]*strike|\bcs2\b|league of legends|\blol\b"
    # Reportagem de TV não é gameplay e a emissora derruba vídeo com trecho dela (apareceu o Fantástico de 22/11)
    r"|fant[aá]stico|reportagem|jornal nacional|\bglobo\b|record\s*tv|\bsbt\b|\bband\b",
    re.I
)
# Sinal de português no título. Na busca de 24/11 todo viral brasileiro tinha um, e os gringos
# (IShowSpeed, CarryMinati, Windah, CoryxKenshin) nenhum: sem ele, o vídeo nem é baixado.
_REGEX_PORTUGUES = re.compile(
    r"\b(?:ao vivo|jogando|jogo|brasil|brazil|br|pt-?br|portugu[eê]s|portuguese|novidades|novo|nova|primeira|primeiro"
    r"|agora|aqui|você|vazou|bem vindo|parte|dia|in[ií]cio|zerando|mundo|melhor|olha|muito|esse|essa|isso|n[aã]o"
    r"|meu|minha|pela|pelo)\b"
    r"|[ãõçáéíóúâêô]", re.I
)


def carregar_historico():
    """Carrega IDs de vídeos já aproveitados para evitar duplicidade."""
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


def pausar_youtube(segundos: int = PAUSA_YOUTUBE_S):
    """Respeita um bloqueio do YouTube: a busca descansa e só volta quando a pausa acabar."""
    _fontes["youtube_pausado_ate"] = time.monotonic() + segundos


def titulo_e_gta6(titulo: str) -> bool:
    """Reconhece as grafias de GTA 6 e descarta títulos sobre GTA 5."""
    texto = str(titulo)
    return bool(_REGEX_GTA6.search(texto)) and not _REGEX_GTA5.search(texto)


def _no_tema(titulo: str) -> bool:
    return titulo_e_gta6(titulo) and not _REGEX_FORA_DO_TEMA.search(str(titulo))


def _titulo_aproveitavel(titulo: str) -> bool:
    """Título de GTA 6 com sinal de português. O áudio ainda é conferido depois do download."""
    texto = str(titulo)
    return _no_tema(texto) and bool(_REGEX_PORTUGUES.search(texto))


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
    """Confirma duração e canal de um vídeo candidato."""
    with yt_dlp.YoutubeDL({"skip_download": True, "quiet": True, "no_warnings": True}) as ydl:
        return ydl.extract_info(url, download=False) or {}


def _disponivel(entry: dict, historico: set) -> bool:
    vid_id = entry.get("id")
    return bool(vid_id) and vid_id not in historico and _url_video(vid_id) not in historico and not em_quarentena(vid_id)


def _nome_do_canal(*fontes) -> str:
    """Nome do criador para a narração e o crédito, na primeira fonte que o trouxer."""
    for fonte in fontes:
        for campo in ("channel", "uploader", "creator"):
            if (fonte or {}).get(campo):
                return str(fonte[campo]).strip()
    return ""


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


def _candidato(entry: dict, historico: set) -> bool:
    """Vídeo de GTA 6 em português, já publicado, ainda não aproveitado e de outro canal."""
    if entry.get("live_status") in AINDA_NO_AR or not _titulo_aproveitavel(entry.get("title", "")):
        return False
    if not _disponivel(entry, historico) or CANAL_PROPRIO in _nome_do_canal(entry).lower():
        return False
    if (entry.get("view_count") or 0) < VISUALIZACOES_MINIMAS:
        return False
    duracao = entry.get("duration")
    return duracao is None or duracao >= DURACAO_MINIMA_S


def _validar(entry: dict):
    """Completa duração e canal quando a busca não os traz. Devolve None para live, Short ou vídeo inacessível."""
    detalhe = {}
    if not entry.get("duration") or not _nome_do_canal(entry):
        try:
            detalhe = _detalhar(_url_video(entry["id"]))
        except Exception as e:
            if classificar_erro(e)["categoria"] in CATEGORIAS_BLOQUEIO:
                raise
            return None
        if detalhe.get("live_status") in AINDA_NO_AR:
            return None
    duracao = entry.get("duration") or detalhe.get("duration") or 0
    if duracao < DURACAO_MINIMA_S:
        return None
    return {
        "id": entry["id"],
        "url": _url_video(entry["id"]),
        "title": entry.get("title", ""),
        "streamer": _nome_do_canal(entry, detalhe) or "GTA 6",
        "duration": duracao,
        "visualizacoes": entry.get("view_count") or detalhe.get("view_count") or 0,
        "origem": "viral",
        "ao_vivo": False,
    }


def buscar_videos_virais(quantidade: int, ignorar=()) -> list:
    """
    Os vídeos de GTA 6 em português mais vistos da semana, do mais visto para o menos visto,
    no máximo um por criador. Se a semana não completar a quantidade, entram os mais vistos do mês.
    Com o YouTube em pausa por bloqueio anti-robô, nada é buscado até a pausa acabar.
    "ignorar" recebe os vídeos que já foram tentados neste ciclo.
    """
    if time.monotonic() < _fontes["youtube_pausado_ate"]:
        return []
    historico = carregar_historico() | set(ignorar)
    descobertos = load_json_safe(DESCOBERTOS_PATH, [])
    streamers = list(set(STREAMERS_BR + (descobertos if isinstance(descobertos, list) else [])))
    random.shuffle(streamers)
    buscas = CONSULTAS_VIRAIS + [f"{nome} GTA 6" for nome in streamers[:STREAMERS_POR_CICLO]]

    consultas = _Consultas()
    escolhidos, canais = [], set()
    for filtro in (FILTRO_MAIS_VISTOS_SEMANA, FILTRO_MAIS_VISTOS_MES):
        candidatos = {}
        for consulta in buscas:
            for entry in consultas.listar(_url_busca(consulta, filtro), consulta):
                if entry.get("id") not in candidatos and _candidato(entry, historico):
                    candidatos[entry["id"]] = entry
        for entry in sorted(candidatos.values(), key=lambda e: e.get("view_count") or 0, reverse=True):
            if entry["id"] in {v["id"] for v in escolhidos}:
                continue
            video = _validar(entry)
            if not video or video["streamer"].lower() in canais:
                continue
            escolhidos.append(video)
            canais.add(video["streamer"].lower())
            if len(escolhidos) >= quantidade:
                return escolhidos
    if not escolhidos and consultas.ultimo_erro is not None and consultas.ok == 0:
        raise consultas.ultimo_erro
    return escolhidos
