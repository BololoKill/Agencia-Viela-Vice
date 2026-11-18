"""
Módulo de Download de Vídeos Brutos via yt-dlp.
"""
from pathlib import Path
import yt_dlp
from src.config import VIDEO_BRUTO_DIR

def baixar_video(url: str, destino_dir: Path = VIDEO_BRUTO_DIR) -> Path:
    """
    Baixa o vídeo na resolução ideal (até 720p) para otimização de velocidade e espaço em disco.
    Retorna o Path do arquivo baixado.
    """
    destino_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(destino_dir / "live_bruta.%(ext)s")

    ydl_opts = {
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if not info:
            raise RuntimeError("Download falhou ou o vídeo está indisponível.")
        arquivo_baixado = Path(ydl.prepare_filename(info))
        if not arquivo_baixado.exists():
            # Caso a extensão tenha sido convertida (ex: mkv)
            possiveis = list(destino_dir.glob("live_bruta.*"))
            if possiveis:
                return possiveis[0]
            raise FileNotFoundError("Arquivo de vídeo baixado não foi localizado.")
        return arquivo_baixado
