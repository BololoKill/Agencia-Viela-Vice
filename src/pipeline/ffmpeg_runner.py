"""
Execução padronizada do FFmpeg: fontes configuradas, filtros escapados e erros legíveis.
"""
import functools
import os
import re
import subprocess
from pathlib import Path
from src.config import BASE_DIR, FONT_PATH

TIMEOUT_PADRAO_S = 1800
AMOSTRAS_POR_PACOTE_AAC = 1024
MAX_PACOTES_AMONTOADOS = 1
MAX_DIFERENCA_AUDIO_VIDEO_S = 0.1
MARGEM_COMERCIAL_S = 0.5
DURACAO_MAXIMA_COMERCIAL_S = 360.0
FOLGA_FIM_GRAVACAO_S = 4.0
TIMEOUT_QUADROS_CHAVE_S = 300
FONTE_WINDOWS = Path(r"C:\Windows\Fonts\arial.ttf")
FONTE_TITULO = Path(r"C:\Windows\Fonts\ariblk.ttf")
PASTA_FONTES = Path(r"C:\Windows\Fonts")
ESTILO_LEGENDA = "FontName=Arial,FontSize=18,PrimaryColour=&H0000FFFF,BorderStyle=4"
CRASHES_NATIVOS = {
    0xC0000005: "crash nativo do FFmpeg (0xC0000005, violação de acesso)",
    0xC0000409: "crash nativo do FFmpeg (0xC0000409, estouro de pilha)",
}


class FFmpegError(RuntimeError):
    """Falha de uma etapa de edição, com o motivo real informado pelo FFmpeg."""

    def __init__(self, etapa: str, codigo, detalhe: str):
        self.etapa = etapa
        self.codigo = codigo
        self.detalhe = detalhe
        super().__init__(f"FFmpeg falhou na etapa '{etapa}': {detalhe}")


def ambiente_ffmpeg() -> dict:
    """Aponta o FFmpeg para a configuração de fontes do projeto."""
    return dict(os.environ, FONTCONFIG_FILE=str(BASE_DIR / "fonts.conf"))


def escapar_caminho_filtro(caminho) -> str:
    """Escapa um caminho do Windows para uso entre aspas simples em filtros do FFmpeg."""
    texto = str(Path(caminho).resolve()).replace("\\", "/")
    return texto.replace(":", "\\:").replace("'", "'\\\\\\''")


def limpar_texto_filtro(texto: str) -> str:
    """Remove caracteres com significado especial no filtro drawtext."""
    return re.sub(r"[^\w @!?.,()\-]", "", str(texto)).strip()


def _caminho_fonte(preferida: Path = None) -> Path:
    if preferida is not None and preferida.exists():
        return preferida
    return FONT_PATH if FONT_PATH.exists() else FONTE_WINDOWS


def filtro_legendas(legenda_path) -> str:
    """Monta o filtro de legendas queimadas. Arquivos .ass já trazem o próprio estilo."""
    caminho = escapar_caminho_filtro(legenda_path)
    if Path(legenda_path).suffix.lower() == ".ass":
        return f"subtitles=filename='{caminho}':fontsdir='{escapar_caminho_filtro(PASTA_FONTES)}'"
    return f"subtitles=filename='{caminho}':force_style='{ESTILO_LEGENDA}'"


def filtro_texto(texto: str, opcoes: str, fonte: Path = None) -> str:
    """Monta um drawtext sempre com arquivo de fonte explícito."""
    arquivo = escapar_caminho_filtro(_caminho_fonte(fonte))
    return f"drawtext=fontfile='{arquivo}':text='{limpar_texto_filtro(texto)}':{opcoes}"


def _resumir_stderr(stderr: bytes) -> str:
    linhas = [
        linha.strip() for linha in stderr.decode("utf-8", "replace").splitlines()
        if linha.strip() and not linha.lstrip().startswith(("frame=", "size="))
    ]
    return " | ".join(linhas[-4:])[-500:] or "sem detalhes do FFmpeg"


def executar_ffmpeg(args: list, etapa: str, timeout: int = TIMEOUT_PADRAO_S) -> str:
    """Executa o FFmpeg, devolve o relatório e transforma falhas em FFmpegError com a causa real."""
    comando = ["ffmpeg", "-hide_banner", "-nostdin", *[str(a) for a in args]]
    try:
        resultado = subprocess.run(
            comando, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            env=ambiente_ffmpeg(), timeout=timeout,
        )
    except FileNotFoundError:
        raise FFmpegError(etapa, "ausente", "FFmpeg não encontrado no PATH do Windows.") from None
    except subprocess.TimeoutExpired:
        raise FFmpegError(etapa, "timeout", f"tempo limite de {timeout}s excedido.") from None

    if resultado.returncode != 0:
        codigo = resultado.returncode & 0xFFFFFFFF
        detalhe = _resumir_stderr(resultado.stderr or b"")
        if codigo in CRASHES_NATIVOS:
            detalhe = f"{CRASHES_NATIVOS[codigo]} | {detalhe}"
        raise FFmpegError(etapa, codigo, detalhe)
    return (resultado.stderr or b"").decode("utf-8", "replace")


@functools.lru_cache(maxsize=1)
def quick_sync_disponivel() -> bool:
    """Confere com uma codificação real se a placa Intel consegue gerar H.264."""
    try:
        executar_ffmpeg(["-f", "lavfi", "-i", "color=c=black:s=640x360:r=30:d=0.2", "-c:v", "h264_qsv", "-f", "null", "-"],
                        etapa="quick_sync", timeout=30)
        return True
    except FFmpegError:
        return False


def _sondar(video, fluxo: str, campos: str) -> list:
    saida = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", fluxo, "-show_entries", campos, "-of", "csv=p=0", str(video)],
        text=True, env=ambiente_ffmpeg(),
    )
    return [linha.strip().strip(",") for linha in saida.splitlines() if linha.strip().strip(",")]


def medir_linha_do_tempo(video) -> dict:
    """Mede quanto som e imagem o arquivo realmente carrega e se há áudio amontoado no mesmo instante."""
    taxa = int(_sondar(video, "a:0", "stream=sample_rate")[0])
    tempos_audio = [float(p) for p in _sondar(video, "a:0", "packet=pts_time")]
    quadros = len(_sondar(video, "v:0", "packet=pts_time"))
    fps_texto = _sondar(video, "v:0", "stream=avg_frame_rate")[0].split("/")
    fps = float(fps_texto[0]) / float(fps_texto[1])
    amontoados = sum(1 for a, b in zip(tempos_audio, tempos_audio[1:]) if b - a < 0.001)
    return {
        "audio_s": len(tempos_audio) * AMOSTRAS_POR_PACOTE_AAC / taxa,
        "video_s": quadros / fps,
        "pacotes_amontoados": amontoados,
    }


def garantir_sincronia(video) -> None:
    """Recusa o vídeo em que a fala poderia sair da imagem durante a reprodução."""
    medida = medir_linha_do_tempo(video)
    diferenca = abs(medida["audio_s"] - medida["video_s"])
    if medida["pacotes_amontoados"] > MAX_PACOTES_AMONTOADOS or diferenca > MAX_DIFERENCA_AUDIO_VIDEO_S:
        raise FFmpegError(
            "sincronia", "dessincronia",
            f"áudio com {medida['audio_s']:.2f}s, imagem com {medida['video_s']:.2f}s e "
            f"{medida['pacotes_amontoados']} pacotes de som amontoados.",
        )


def _quadros_chave(video) -> list:
    """Lista (instante, resolução) dos quadros-chave, sem precisar decodificar a gravação inteira."""
    saida = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-skip_frame", "nokey",
         "-show_entries", "frame=pts_time,width,height", "-of", "csv=p=0", str(video)],
        text=True, stderr=subprocess.DEVNULL, env=ambiente_ffmpeg(), timeout=TIMEOUT_QUADROS_CHAVE_S,
    )
    chaves = []
    for linha in saida.splitlines():
        campos = linha.strip().strip(",").split(",")
        if len(campos) >= 3 and campos[0] not in ("", "N/A"):
            chaves.append((float(campos[0]), (campos[1], campos[2])))
    return chaves


def detectar_intervalos_comerciais(video) -> list:
    """
    A Twitch exibe os comerciais em resolução diferente da live: trechos curtos fora da resolução
    predominante não podem virar vídeo. Uma falha aqui não impede a edição.
    """
    try:
        chaves = _quadros_chave(video)
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
    blocos = []
    origem = chaves[0][0] if chaves else 0.0  # A edição conta o tempo a partir do início do arquivo
    for instante, resolucao in ((tempo - origem, tamanho) for tempo, tamanho in chaves):
        if blocos:
            blocos[-1][2] = instante
        if not blocos or blocos[-1][0] != resolucao:
            blocos.append([resolucao, instante, instante])
    if not blocos:
        return []
    blocos[-1][2] += FOLGA_FIM_GRAVACAO_S

    tempo_por_resolucao = {}
    for resolucao, inicio, fim in blocos:
        tempo_por_resolucao[resolucao] = tempo_por_resolucao.get(resolucao, 0.0) + fim - inicio
    predominante = max(tempo_por_resolucao, key=tempo_por_resolucao.get)
    return [
        (max(0.0, inicio - MARGEM_COMERCIAL_S), fim + MARGEM_COMERCIAL_S)
        for resolucao, inicio, fim in blocos
        if resolucao != predominante and fim - inicio <= DURACAO_MAXIMA_COMERCIAL_S
    ]


def detectar_telas_pretas(video, inicio: float = 0.0, duracao: float = None) -> list:
    """Localiza telas pretas no trecho analisado. Uma falha aqui não impede a edição."""
    args = ["-ss", str(inicio), "-i", str(video)]
    if duracao:
        args += ["-t", str(duracao)]
    args += ["-vf", "fps=5,scale=320:-2,blackdetect=d=0.5:pic_th=0.92", "-an", "-f", "null", "-"]
    try:
        relatorio = executar_ffmpeg(args, etapa="telas_pretas")
    except FFmpegError:
        return []
    return [
        (inicio + float(ini), inicio + float(fim))
        for ini, fim in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", relatorio)
    ]
