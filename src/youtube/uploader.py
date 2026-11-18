"""
Módulo de Upload e Agendamento no YouTube (API v3).
"""
from pathlib import Path
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from src.youtube.auth import obter_credenciais

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
    creds = obter_credenciais(canal_id)
    if not creds:
        return False, "Credenciais do canal não autorizadas ou ausentes", None

    try:
        youtube = build("youtube", "v3", credentials=creds)
        publish_at = formatar_data_publicacao(data_agenda, hora_agenda)

        tags = ["GTA RP", "GTA 6", "GTA VI", "Viela Vice", "GTA RP Brasil", "Shorts", "Clipes GTA"]
        desc_completa = (descricao or "").strip()
        if "Viela Vice" not in desc_completa:
            desc_completa += "\n\nInscreva-se no canal Viela Vice para os melhores momentos de GTA RP e GTA 6!"

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

        resp = None
        while resp is None:
            _, resp = req.next_chunk()

        vid_id = resp.get("id")
        return True, f"Agendado no canal com sucesso para {publish_at}", vid_id

    except Exception as e:
        return False, f"Erro YouTube API: {str(e)}", None
