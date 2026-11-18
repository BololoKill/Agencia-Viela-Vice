"""
Controle da cota de envios por canal.
O YouTube é a fonte da verdade: cada ciclo vai das 05:00 às 05:00 e nunca reinicia antes disso.
Sem confirmação da cota, nenhum envio é liberado.
"""
import threading
import time
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from src.config import CANAIS_VIELA_VICE, COTAS_FILE, COTA_DIARIA_CANAL, HORA_REINICIO_COTA
from src.utils import load_json_safe, log_terminal, save_json_safe
from src.youtube.auth import obter_credenciais

INTERVALO_SINCRONIZACAO_S = 3600
MAXIMO_PAGINAS = 3
MAXIMO_ANTERIORES = 200

_trava = threading.RLock()
_reservas = {}


class CotaEsgotada(RuntimeError):
    """O canal já atingiu o limite de envios do ciclo."""


class CotaNaoVerificada(RuntimeError):
    """Não foi possível confirmar no YouTube quantos envios o canal já fez."""


def inicio_ciclo_cota(agora: datetime = None) -> datetime:
    """Retorna o início do ciclo atual, sempre às 05:00."""
    agora = agora or datetime.now()
    inicio = agora.replace(hour=HORA_REINICIO_COTA, minute=0, second=0, microsecond=0)
    return inicio if agora >= inicio else inicio - timedelta(days=1)


def consultar_envios_youtube(canal_id: str, inicio: datetime) -> list:
    """Lista os vídeos enviados ao canal desde o início do ciclo. Consulta somente leitura."""
    creds = obter_credenciais(canal_id)
    if not creds:
        raise CotaNaoVerificada(f"Canal {canal_id} sem autorização para consulta.")

    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    canais = youtube.channels().list(part="contentDetails", mine=True).execute().get("items", [])
    if not canais:
        raise CotaNaoVerificada(f"Canal {canal_id} não encontrado no YouTube.")
    uploads = canais[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    limite = inicio.astimezone(timezone.utc)

    videos = []
    pagina = None
    for _ in range(MAXIMO_PAGINAS):
        resposta = youtube.playlistItems().list(
            part="snippet", playlistId=uploads, maxResults=50, pageToken=pagina
        ).execute()
        itens = resposta.get("items", [])
        recentes = [
            item["snippet"]["resourceId"]["videoId"] for item in itens
            if datetime.fromisoformat(item["snippet"]["publishedAt"].replace("Z", "+00:00")) >= limite
        ]
        videos.extend(recentes)
        pagina = resposta.get("nextPageToken")
        if not pagina or len(recentes) < len(itens):
            break
    return videos


def _acumular_anteriores(dados: dict) -> dict:
    """Guarda os vídeos de ciclos passados: agendados mudam de data ao serem publicados."""
    anteriores = dados.get("anteriores") if isinstance(dados.get("anteriores"), dict) else {}
    acumulado = {canal: list(videos) for canal, videos in anteriores.items() if isinstance(videos, list)}
    for canal_id, registro in dados.get("canais", {}).items():
        if isinstance(registro, dict) and isinstance(registro.get("videos"), list):
            acumulado[canal_id] = (acumulado.get(canal_id, []) + registro["videos"])[-MAXIMO_ANTERIORES:]
    return acumulado


def _carregar(agora: datetime = None) -> dict:
    ciclo = inicio_ciclo_cota(agora).isoformat()
    dados = load_json_safe(COTAS_FILE, {})
    valido = isinstance(dados, dict) and isinstance(dados.get("canais"), dict)
    if valido and dados.get("ciclo") == ciclo:
        return dados
    return {
        "ciclo": ciclo, "api_esgotada": False, "canais": {},
        "anteriores": _acumular_anteriores(dados) if valido else {},
    }


def _canal(dados: dict, canal_id: str) -> dict:
    registro = dados["canais"].get(canal_id)
    if not isinstance(registro, dict) or not isinstance(registro.get("videos"), list):
        registro = {"videos": [], "verificado_em": None}
        dados["canais"][canal_id] = registro
    return registro


def sincronizar_canal(canal_id: str, agora: datetime = None) -> int:
    """Atualiza o canal com os envios do YouTube. Vídeos apagados continuam contando no ciclo."""
    videos = consultar_envios_youtube(canal_id, inicio_ciclo_cota(agora))
    with _trava:
        dados = _carregar(agora)
        registro = _canal(dados, canal_id)
        ja_contados = set((dados.get("anteriores") or {}).get(canal_id, []))
        registro["videos"] = sorted(set(registro["videos"]) | (set(videos) - ja_contados))
        registro["verificado_em"] = (agora or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
        save_json_safe(COTAS_FILE, dados)
        return len(registro["videos"])


def sincronizar_todos() -> dict:
    """Atualiza todos os canais. Falhas ficam visíveis no painel como não verificadas."""
    resultado = {}
    for canal_id in CANAIS_VIELA_VICE:
        try:
            resultado[canal_id] = sincronizar_canal(canal_id)
        except Exception as e:
            resultado[canal_id] = None
            log_terminal(f"[AVISO] Cota do canal {canal_id} não verificada: {e}")
    return resultado


def resumo(agora: datetime = None) -> dict:
    """Entrega ao painel as estrelas de cada canal no ciclo atual."""
    with _trava:
        dados = _carregar(agora)
        api_esgotada = bool(dados.get("api_esgotada"))
        saida = {}
        for canal_id in CANAIS_VIELA_VICE:
            registro = dados["canais"].get(canal_id) if isinstance(dados["canais"].get(canal_id), dict) else {}
            usados = len(set(registro.get("videos") or []))
            saida[canal_id] = {
                "usados": usados,
                "limite": COTA_DIARIA_CANAL,
                "bloqueado": api_esgotada or usados >= COTA_DIARIA_CANAL,
                "verificado": bool(registro.get("verificado_em")),
                "verificado_em": registro.get("verificado_em"),
            }
        return saida


def reservar_envio(canal_id: str):
    """Confirma a cota no YouTube e reserva uma vaga antes de iniciar o envio."""
    try:
        sincronizar_canal(canal_id)
    except Exception as e:
        raise CotaNaoVerificada(f"Não foi possível confirmar a cota no YouTube: {e}") from e

    with _trava:
        dados = _carregar()
        usados = len(set(_canal(dados, canal_id)["videos"]))
        if dados.get("api_esgotada"):
            raise CotaEsgotada("Cota da API do YouTube esgotada. Novos envios liberam às 05:00.")
        if usados + _reservas.get(canal_id, 0) >= COTA_DIARIA_CANAL:
            raise CotaEsgotada(f"Canal com {usados}/{COTA_DIARIA_CANAL} estrelas. Novos envios liberam às 05:00.")
        _reservas[canal_id] = _reservas.get(canal_id, 0) + 1


def concluir_envio(canal_id: str, video_id: str = None):
    """Libera a reserva e registra imediatamente o vídeo enviado."""
    with _trava:
        _reservas[canal_id] = max(0, _reservas.get(canal_id, 0) - 1)
        if video_id:
            dados = _carregar()
            registro = _canal(dados, canal_id)
            registro["videos"] = sorted(set(registro["videos"]) | {video_id})
            save_json_safe(COTAS_FILE, dados)


def marcar_api_esgotada():
    """Quando o próprio YouTube recusa por cota, todos os envios param até as 05:00."""
    with _trava:
        dados = _carregar()
        dados["api_esgotada"] = True
        save_json_safe(COTAS_FILE, dados)
    log_terminal("[AVISO] YouTube informou cota esgotada. Envios bloqueados até as 05:00.")


def _monitorar():
    ultimo_ciclo = None
    ultima_sincronizacao = 0.0
    while True:
        ciclo = inicio_ciclo_cota()
        if ciclo != ultimo_ciclo or time.monotonic() - ultima_sincronizacao >= INTERVALO_SINCRONIZACAO_S:
            sincronizar_todos()
            ultimo_ciclo = ciclo
            ultima_sincronizacao = time.monotonic()
        time.sleep(30)


def iniciar_monitor_cotas():
    """Mantém as estrelas atualizadas, inclusive com vídeos enviados fora do painel."""
    threading.Thread(target=_monitorar, daemon=True, name="monitor-cotas").start()
