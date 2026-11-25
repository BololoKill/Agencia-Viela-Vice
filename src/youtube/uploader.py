"""
Módulo de Upload e Agendamento no YouTube (API v3).
"""
import socket
import ssl
import time
from pathlib import Path
from datetime import datetime, timedelta

import google_auth_httplib2
import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from src.youtube.auth import CredencialYouTubeError, obter_credenciais
from src.utils import log_terminal

TEMPO_LIMITE_PARTE_S = 300  # Uma parte de 4 MB numa conexão ocupada pode levar minutos
TENTATIVAS_POR_PARTE = 6
STATUS_PASSAGEIROS = {500, 502, 503, 504}
ERROS_DE_REDE = (TimeoutError, socket.timeout, ssl.SSLError, ConnectionError, httplib2.HttpLib2Error)


def _cliente_youtube(creds):
    conexao = httplib2.Http(timeout=TEMPO_LIMITE_PARTE_S)
    # O YouTube responde 308 entre as partes de um envio: não é redirecionamento (igual à conexão padrão da biblioteca)
    conexao.redirect_codes = conexao.redirect_codes - {308}
    http = google_auth_httplib2.AuthorizedHttp(creds, http=conexao)
    return build("youtube", "v3", http=http, cache_discovery=False)


def _enviar_em_partes(pedido, nome: str):
    """Envia parte por parte. Uma falha passageira repete só a parte que falhou, sem perder o que já subiu."""
    resposta = None
    falhas = 0
    while resposta is None:
        try:
            _, resposta = pedido.next_chunk()
            falhas = 0
        except HttpError as e:
            if e.resp.status not in STATUS_PASSAGEIROS or falhas >= TENTATIVAS_POR_PARTE:
                raise
            falhas += 1
            log_terminal(f"[ENVIO] YouTube instável ({e.resp.status}) em {nome}; tentando a parte de novo ({falhas}/{TENTATIVAS_POR_PARTE}).")
            time.sleep(min(60, 2 ** falhas))
        except ERROS_DE_REDE as e:
            if falhas >= TENTATIVAS_POR_PARTE:
                raise
            falhas += 1
            log_terminal(f"[ENVIO] Conexão falhou em {nome} ({type(e).__name__}); tentando a parte de novo ({falhas}/{TENTATIVAS_POR_PARTE}).")
            time.sleep(min(60, 2 ** falhas))
    return resposta


def formatar_data_publicacao(data_str: str, hora_str: str) -> str:
    """Calcula timestamp ISO-8601 respeitando o mínimo de 15 minutos de antecedência exigido pelo YouTube."""
    dt = datetime.strptime(f"{data_str} {hora_str}", "%Y-%m-%d %H:%M")
    minimo = datetime.now() + timedelta(minutes=15)
    while dt <= minimo:
        dt += timedelta(days=1)
    return dt.strftime("%Y-%m-%dT%H:%M:00-03:00")

def enviar_video_agendado(
    video_path: Path,
    titulo: str,
    descricao: str,
    data_agenda: str,
    hora_agenda: str,
    canal_id: str = "1"
) -> tuple:
    """
    Realiza o envio de vídeo agendado para o YouTube.
    Retorna (sucesso: bool, mensagem: str, video_id: str ou None).
    """
    try:
        creds = obter_credenciais(canal_id)
        if not creds:
            return False, "Credenciais do canal não autorizadas ou ausentes", None

        youtube = _cliente_youtube(creds)
        publish_at = formatar_data_publicacao(data_agenda, hora_agenda)

        tags = ["GTA 6", "GTA VI", "Viela Vice", "GTA 6 Brasil", "GTA 6 narrado", "Vice City"]
        if "#shorts" in titulo.lower():
            tags.append("Shorts")
        desc_completa = (descricao or "").strip()
        if "Viela Vice" not in desc_completa:
            desc_completa += "\n\nInscreva-se no canal Viela Vice para mais histórias de GTA 6!"

        body = {
            "snippet": {
                "title": titulo[:98],
                "description": desc_completa[:4900],
                "tags": tags,
                "categoryId": "20"
            },
            "status": {
                "privacyStatus": "private",
                "publishAt": publish_at,
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(str(video_path), chunksize=4*1024*1024, resumable=True, mimetype="video/mp4")
        req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

        resp = _enviar_em_partes(req, Path(video_path).name)

        vid_id = resp.get("id")
        return True, f"Agendado no canal com sucesso para {publish_at}", vid_id

    except CredencialYouTubeError as e:
        return False, str(e), None
    except Exception as e:
        return False, f"Erro YouTube API: {str(e)}", None
