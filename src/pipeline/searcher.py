"""
Módulo de Varredura e Busca de Lives de GTA RP.
Responsável por rastrear vídeos novos de streamers brasileiros usando yt-dlp.
"""
import random
from pathlib import Path
import yt_dlp
from src.config import STREAMERS_BR, DESCOBERTOS_PATH, HISTORICO_FILE
from src.utils import load_json_safe

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

def buscar_melhor_live():
    """
    Rastreia lives e vídeos de GTA RP dos criadores cadastrados e descobertos.
    Retorna dicionário com dados do vídeo ou None.
    """
    historico = carregar_historico()
    descobertos = load_json_safe(DESCOBERTOS_PATH, [])
    streamers = list(set(STREAMERS_BR + descobertos))
    random.shuffle(streamers)

    ydl_opts = {
        "extract_flat": True,
        "skip_download": True,
        "quiet": True,
        "no_warnings": True
    }

    for streamer in streamers:
        query = f"ytsearch3:{streamer} GTA RP"
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                resultado = ydl.extract_info(query, download=False)
                if not resultado or "entries" not in resultado:
                    continue

                for entry in resultado["entries"]:
                    if not entry:
                        continue
                    vid_id = entry.get("id")
                    vid_url = entry.get("url") or f"https://www.youtube.com/watch?v={vid_id}"
                    vid_title = entry.get("title", "")
                    duracao = entry.get("duration", 0)

                    if vid_id not in historico and vid_url not in historico:
                        # Seleciona vídeos de 3 minutos a 2 horas (lives ou compilações)
                        if duracao and 180 <= duracao <= 7200:
                            return {
                                "id": vid_id,
                                "url": vid_url,
                                "title": vid_title,
                                "streamer": streamer,
                                "duration": duracao
                            }
        except Exception as e:
            print(f"[BUSCA] Erro temporário ao consultar {streamer}: {e}")
            continue

    return None
