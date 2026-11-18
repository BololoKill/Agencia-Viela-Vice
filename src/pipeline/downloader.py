"""
Módulo de Download de Vídeos Brutos via yt-dlp.
"""
from pathlib import Path
import yt_dlp
from src.config import VIDEO_BRUTO_DIR, VIDEO_SPECS

EXTENSOES_PARCIAIS = {".part", ".ytdl", ".temp"}


def baixar_video(url: str, destino_dir: Path = None, ao_vivo: bool = False, duracao_captura: int = None) -> Path:
    """
    Baixa o vídeo em até 720p. Lives no ar são gravadas por tempo limitado.
    Erros do YouTube são propagados com o motivo original para diagnóstico no painel.
    """
    destino_dir = destino_dir or VIDEO_BRUTO_DIR
    destino_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(destino_dir / "live_bruta.%(ext)s")

    ydl_opts = {
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 3,
        "fragment_retries": 5,
        "socket_timeout": 30,
    }
    if ao_vivo:
        segundos = duracao_captura or VIDEO_SPECS["captura_live_s"]
        ydl_opts.update({
            "merge_output_format": "mp4",
            "external_downloader": {"default": "ffmpeg"},
            "external_downloader_args": {"ffmpeg_i": ["-t", str(segundos)]},
        })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if not info:
            raise RuntimeError("Download falhou ou o vídeo está indisponível.")
        arquivo_baixado = Path(ydl.prepare_filename(info))
        if arquivo_baixado.exists():
            return arquivo_baixado

    # Caso a extensão tenha sido convertida na junção de áudio e vídeo (ex: mkv)
    possiveis = [p for p in destino_dir.glob("live_bruta.*") if p.suffix not in EXTENSOES_PARCIAIS]
    if possiveis:
        return possiveis[0]
    raise FileNotFoundError("Arquivo de vídeo baixado não foi localizado.")
