"""
Módulo de Download de Vídeos Brutos via yt-dlp.
De um vídeo publicado baixa só o trecho que será analisado: a internet é lenta e os virais chegam a ter horas.
Um vigia acompanha o download: se ele parar de crescer ou passar muito do tempo, o FFmpeg é encerrado.
"""
import json
import subprocess
import threading
import time
from pathlib import Path

import psutil
import yt_dlp
from yt_dlp.utils import download_range_func
from src.config import VIDEO_BRUTO_DIR
from src.pipeline.ffmpeg_runner import executar_ffmpeg
from src.utils import log_terminal

EXTENSOES_PARCIAIS = {".part", ".ytdl", ".temp"}
INTERVALO_VIGIA_S = 15
SEM_PROGRESSO_S = 180  # Download parado por 3 min: o YouTube não está mandando dados
FOLGA_TEMPO_TOTAL = 2.5  # Internet lenta baixa mais devagar que a duração do trecho, mas nunca 2,5 vezes
FOLGA_EXTRA_S = 300
TENTATIVAS_TRECHO = 2
COBERTURA_MINIMA = 0.97  # A imagem e o som precisam cobrir o trecho inteiro (sobra só o arredondamento do fim)
FORMATO_IMAGEM_TRECHO = "bestvideo[height<=720]/best[height<=720]/best"
FORMATO_SOM_TRECHO = "bestaudio/best"
# Quando o YouTube encerra a conexão antes do fim, o FFmpeg pede o resto a partir do ponto onde parou,
# em vez de entregar a parte cortada como se o vídeo tivesse acabado ali.
RECONEXAO_FFMPEG = ["-reconnect", "1", "-reconnect_on_network_error", "1", "-reconnect_delay_max", "30"]
OPCOES_DOWNLOAD = {
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "noprogress": True,
    "retries": 3,
    "fragment_retries": 5,
    "socket_timeout": 30,
}


class GravacaoTravada(RuntimeError):
    """O download parou de receber dados ou passou muito do tempo: o FFmpeg foi encerrado."""


class DownloadIncompleto(RuntimeError):
    """O trecho do vídeo chegou cortado ou quebrado mesmo depois de baixado de novo."""


def _tamanho_gravado(pasta: Path) -> int:
    total = 0
    for arquivo in pasta.glob("live_bruta*"):
        try:
            if arquivo.is_file():
                total += arquivo.stat().st_size
        except OSError:
            pass
    return total


def _encerrar_ffmpeg(alvo: str) -> int:
    """Encerra o FFmpeg deste processo que grava no arquivo indicado. As outras gravações continuam."""
    encerrados = 0
    for filho in psutil.Process().children(recursive=True):
        try:
            if "ffmpeg" in filho.name().lower() and any(alvo in parte for parte in filho.cmdline()):
                filho.kill()
                encerrados += 1
        except psutil.Error:
            continue
    return encerrados


class _Vigia(threading.Thread):
    """Acompanha o tamanho do download e encerra o FFmpeg se ele parar de crescer ou passar muito do tempo."""

    def __init__(self, pasta: Path, limite_total_s: float):
        super().__init__(daemon=True, name="vigia-gravacao")
        self.pasta = pasta
        self.alvo = str(pasta / "live_bruta.")
        self.limite_total_s = limite_total_s
        self.parar = threading.Event()
        self.motivo = None

    def run(self):
        inicio = ultimo_progresso = time.monotonic()
        ultimo_tamanho = -1
        while not self.parar.wait(INTERVALO_VIGIA_S):
            agora = time.monotonic()
            tamanho = _tamanho_gravado(self.pasta)
            if tamanho > ultimo_tamanho:
                ultimo_tamanho, ultimo_progresso = tamanho, agora
            if agora - ultimo_progresso >= SEM_PROGRESSO_S:
                self.motivo = f"o YouTube ficou {max(1, round((agora - ultimo_progresso) / 60))} min sem mandar dados"
            elif agora - inicio >= self.limite_total_s:
                self.motivo = f"o download passou de {max(1, round(self.limite_total_s / 60))} min"
            if self.motivo:
                _encerrar_ffmpeg(self.alvo)
                return


def _duracoes(caminho: Path) -> dict:
    """Duração da imagem e do som do arquivo, como o FFmpeg enxerga. Vazio se ele não abrir."""
    try:
        sonda = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration:format=duration", "-of", "json",
             str(caminho)], capture_output=True, text=True, timeout=60)
        if sonda.returncode != 0:
            return {}
        dados = json.loads(sonda.stdout or "{}")
        total = float((dados.get("format") or {}).get("duration") or 0)
        return {s.get("codec_type"): float(s.get("duration") or total) for s in dados.get("streams", [])}
    except (OSError, ValueError, subprocess.SubprocessError):
        return {}


def _arquivo_completo(caminho: Path) -> bool:
    """
    O arquivo abre, tem imagem e som, e o som vai até o fim da imagem.
    Regressão: o trecho do Skorpion Gamer veio com 6 min de imagem e só 1min32 de som.
    """
    duracoes = _duracoes(caminho)
    imagem, som = duracoes.get("video", 0.0), duracoes.get("audio", 0.0)
    return imagem > 0 and som >= imagem * COBERTURA_MINIMA


def baixar_video(url: str, destino_dir: Path = None, trecho: tuple = None) -> Path:
    """
    Baixa o vídeo em até 720p. "trecho" (início, duração) baixa só essa parte; o arquivo começa em zero.
    A imagem ou o som que chega cortado é baixado de novo uma vez.
    Erros do YouTube são propagados com o motivo original para diagnóstico no painel.
    """
    if not trecho:
        return _baixar(url, destino_dir)
    arquivo = _baixar_trecho(url, destino_dir or VIDEO_BRUTO_DIR, *(float(t) for t in trecho))
    if _arquivo_completo(arquivo):
        return arquivo
    arquivo.unlink(missing_ok=True)
    raise DownloadIncompleto("O trecho do vídeo não abriu depois de juntar a imagem e o som; ele fica para o próximo ciclo.")


def _baixar_trecho(url: str, destino_dir: Path, inicio: float, duracao: float) -> Path:
    """
    Baixa a imagem e o som do trecho separados, um depois do outro, e junta os dois no fim.
    Regressão: descendo juntos, a conexão do som ficava esperando a da imagem e o YouTube a encerrava
    no meio (alanzoka: 360 s de imagem e 149 s de som; Skorpion Gamer: 360 s e 92 s).
    """
    destino_dir.mkdir(parents=True, exist_ok=True)
    partes = {}
    try:
        for rotulo, formato in (("imagem", FORMATO_IMAGEM_TRECHO), ("som", FORMATO_SOM_TRECHO)):
            partes[rotulo] = _baixar_parte(url, destino_dir, rotulo, formato, inicio, duracao)
        saida = destino_dir / "live_bruta.mp4"
        executar_ffmpeg(["-i", str(partes["imagem"]), "-i", str(partes["som"]), "-map", "0:v:0", "-map", "1:a:0",
                         "-c", "copy", "-movflags", "+faststart", str(saida), "-y"], etapa="juntar_trecho")
        return saida
    finally:
        for parte in partes.values():
            parte.unlink(missing_ok=True)


def _baixar_parte(url: str, destino_dir: Path, rotulo: str, formato: str, inicio: float, duracao: float) -> Path:
    """
    Baixa a imagem ou o som do trecho e confere se a parte cobre o trecho inteiro.
    A parte que chega cortada ou quebrada é baixada de novo sozinha: na internet lenta o som desce em segundos
    e a imagem leva minutos. Regressão: o som cortado fazia a imagem de 6 min ser baixada de novo junto.
    """
    faixa, nome = ("video", "A imagem") if rotulo == "imagem" else ("audio", "O som")
    medida = 0.0
    for tentativa in range(1, TENTATIVAS_TRECHO + 1):
        try:
            parte = _descer(url, destino_dir, rotulo, formato, inicio, duracao)
        except yt_dlp.utils.DownloadError as e:
            # Regressão: o FFmpeg caiu no meio do trecho do alanzoka com um código de saída sem sentido (25/11).
            # Bloqueio anti-robô, limite de requisições e vídeo indisponível sobem como estão, para o ciclo tratar.
            if "ffmpeg exited with code" not in str(e):
                raise
            if tentativa == TENTATIVAS_TRECHO:
                raise DownloadIncompleto(f"{nome} do trecho parou no meio do download duas vezes; "
                                         "o vídeo fica para o próximo ciclo.") from e
            log_terminal(f"[AVISO] {nome} do trecho parou no meio do download (o FFmpeg caiu): baixando de novo.")
            continue
        medida = _duracoes(parte).get(faixa, 0.0)
        if medida >= duracao * COBERTURA_MINIMA:
            return parte
        parte.unlink(missing_ok=True)
        if tentativa < TENTATIVAS_TRECHO:
            log_terminal(f"[AVISO] {nome} do trecho chegou com {medida:.0f} de {duracao:.0f} s: baixando de novo.")
    raise DownloadIncompleto(f"{nome} do trecho chegou com {medida:.0f} de {duracao:.0f} s duas vezes; "
                             "o vídeo fica para o próximo ciclo.")


def _descer(url: str, destino_dir: Path, rotulo: str, formato: str, inicio: float, duracao: float) -> Path:
    """Uma descida do yt-dlp com o vigia ao lado: uma conexão parada não trava o ciclo."""
    opcoes = {
        **OPCOES_DOWNLOAD, "format": formato, "outtmpl": str(destino_dir / f"live_bruta.{rotulo}.%(ext)s"),
        "download_ranges": download_range_func(None, [(inicio, inicio + duracao)]),
        "external_downloader_args": {"ffmpeg_i": list(RECONEXAO_FFMPEG)},
    }
    vigia = _Vigia(destino_dir, duracao * FOLGA_TEMPO_TOTAL * 2 + FOLGA_EXTRA_S)
    vigia.start()
    try:
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            info = ydl.extract_info(url, download=True)
            if vigia.motivo:
                raise GravacaoTravada(f"Download encerrado: {vigia.motivo}.")
            if not info:
                raise RuntimeError("Download falhou ou o vídeo está indisponível.")
            return Path(ydl.prepare_filename(info))
    except GravacaoTravada:
        raise
    except Exception as e:
        if vigia.motivo:
            raise GravacaoTravada(f"Download encerrado: {vigia.motivo}.") from e
        raise
    finally:
        vigia.parar.set()


def _baixar(url: str, destino_dir: Path) -> Path:
    """Baixa o vídeo inteiro (só para vídeos mais curtos que o trecho analisado)."""
    destino_dir = destino_dir or VIDEO_BRUTO_DIR
    destino_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(destino_dir / "live_bruta.%(ext)s")

    ydl_opts = {**OPCOES_DOWNLOAD, "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best", "outtmpl": outtmpl}
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
