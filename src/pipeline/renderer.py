"""
Módulo de Renderização e Edição de Vídeos via FFmpeg Direto.
ATENÇÃO: MoviePy é estritamente proibido pelas diretrizes do projeto.
Todos os efeitos visuais, legendas e mixagem são processados diretamente via comandos FFmpeg.
"""
import math
import os
import time
import asyncio
import subprocess
from pathlib import Path
import edge_tts
from src.config import VIDEO_BRUTO_DIR, CTA_AUDIO, VIDEO_SPECS, MARCA_PATH, WHOOSH_PATH
from src.pipeline import edicao
from src.utils import log_terminal
from src.pipeline.ffmpeg_runner import (
    FFmpegError, FONTE_TITULO, executar_ffmpeg, filtro_legendas, filtro_texto, garantir_sincronia,
    quick_sync_disponivel
)

TENTATIVAS_TTS = 3
PRESET_INTERMEDIARIO = "ultrafast"
CRF_INTERMEDIARIO = "14"
PRESET_FINAL = VIDEO_SPECS["preset"]
CRF_FINAL = VIDEO_SPECS["crf"]
ALTURA_GAMEPLAY = 810
TOPO_GAMEPLAY = (1920 - ALTURA_GAMEPLAY) // 2
DURACAO_MINIMA_CTA = 4.0
DURACAO_MINIMA_CONTEUDO = 10.0
TAXA_AUDIO = 44100
FORMATO_AUDIO = f"aformat=sample_fmts=fltp:sample_rates={TAXA_AUDIO}:channel_layouts=stereo"
NORMALIZAR_VOZ = f"loudnorm=I=-14:TP=-1.5:LRA=11,aresample={TAXA_AUDIO},aformat=channel_layouts=stereo"
FADE_CORTE_S = 0.006
QUALIDADE_QUICK_SYNC = "12"
LARGURA_LONGO = 1280
ALTURA_LONGO = 720
MARCA_LONGO = 96


async def gerar_audio_tts(texto: str, output_path: Path, voz: str = "pt-BR-AntonioNeural", rate: str = "+0%"):
    """Gera narração via Edge-TTS sem sobrepor o áudio do streamer."""
    communicate = edge_tts.Communicate(texto, voz, rate=rate)
    await communicate.save(str(output_path))


def _gerar_tts_com_retentativa(texto: str, destino: Path, rate: str = "+0%") -> Path:
    """O serviço de voz é online: instabilidades curtas não devem perder o corte."""
    ultimo_erro = None
    for tentativa in range(TENTATIVAS_TTS):
        try:
            asyncio.run(gerar_audio_tts(texto, destino, rate=rate))
            return destino
        except Exception as e:
            ultimo_erro = e
            time.sleep(2 * (tentativa + 1))
    raise ConnectionError(f"Narração indisponível no edge-tts: {ultimo_erro}")


def criar_narração_intro(streamer: str, output_audio: Path) -> Path:
    """Cria introdução narrada curta para o corte."""
    texto = f"Olha o que rolou na live de {edicao.nome_falado(streamer)}!"
    return _gerar_tts_com_retentativa(texto, output_audio, rate="+20%")


def garantir_audio_cta(cta_path: Path = None):
    """Garante que o áudio de CTA padrão exista na pasta de exportação."""
    alvo = cta_path or CTA_AUDIO
    if not alvo.exists():
        alvo.parent.mkdir(parents=True, exist_ok=True)
        _gerar_tts_com_retentativa("Se você curtiu o vídeo, já deixa o like e se inscreva no canal!", alvo, rate="+15%")


def obter_duracao_audio(audio_path: Path) -> float:
    """Mede duração exata do arquivo de mídia via FFprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 4.0


def _saida_intermediaria() -> list:
    return [
        "-r", str(VIDEO_SPECS["fps"]),
        "-c:v", VIDEO_SPECS["codec_v"], "-pix_fmt", VIDEO_SPECS["pix_fmt"],
        "-preset", PRESET_INTERMEDIARIO, "-crf", CRF_INTERMEDIARIO,
        "-c:a", VIDEO_SPECS["codec_a"], "-ar", "44100", "-ac", "2", "-b:a", VIDEO_SPECS["bitrate_a"],
    ]


def _amostras(quadros: int) -> int:
    """Quantidade de amostras de áudio que cabe exatamente em uma quantidade de quadros."""
    return int(round(quadros * TAXA_AUDIO / VIDEO_SPECS["fps"]))


def _quadros_dos_trechos(trechos: list, base: float) -> list:
    fps = VIDEO_SPECS["fps"]
    return [(int(round((ini - base) * fps)), int(round((fim - base) * fps))) for ini, fim in trechos]


def _expressao_quadros(quadros: list) -> str:
    return "+".join(f"between(n,{ini},{fim - 1})" for ini, fim in quadros)


def _expressao_zoom(quadros: list) -> str:
    """Alterna a aproximação a cada corte seco para dar ritmo ao vídeo."""
    termos = []
    acumulado = 0
    for indice, (ini, fim) in enumerate(quadros):
        if indice % 2 == 1:
            termos.append(f"between(on,{acumulado},{acumulado + fim - ini - 1})")
        acumulado += fim - ini
    return f"1+0.08*({'+'.join(termos[:40])})" if termos else "1"


def _filtro_layout(zoom: str) -> str:
    """Fundo desfocado com o gameplay nítido no centro, a partir das entradas [b0] e [f0]."""
    fps = VIDEO_SPECS["fps"]
    return (
        "[b0]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=10:2,"
        "scale=1080:1920,eq=brightness=-0.18:saturation=1.2[fundo];"
        "[f0]crop='min(iw,ih*4/3)':'min(ih,iw*3/4)',scale=1440:1080:flags=lanczos,"
        f"zoompan=z='{zoom}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d=1:"
        f"s=1080x{ALTURA_GAMEPLAY}:fps={fps},unsharp=5:5:0.5[frente];"
        f"[fundo][frente]overlay=0:{TOPO_GAMEPLAY},setsar=1,format=yuv420p"
    )


def _filtros_titulo(gancho: str, limite: float = None) -> list:
    quando = f":enable='lt(t,{limite:.2f})'" if limite is not None else ""
    return [
        filtro_texto(
            linha,
            f"fontcolor=white:fontsize=62:box=1:boxcolor=black@0.78:boxborderw=18:"
            f"x=(w-text_w)/2:y={200 + indice * 112}{quando}",
            fonte=FONTE_TITULO,
        )
        for indice, linha in enumerate(edicao.quebrar_linhas(gancho))
    ]


def _filtro_audio_cortes(quadros: list, rotulo: str = "a") -> str:
    """Corta o som nas mesmas fronteiras da imagem, amostra por amostra, sem estalos na emenda."""
    fps = VIDEO_SPECS["fps"]
    total = _amostras(sum(fim - ini for ini, fim in quadros))
    ramos = "".join(f"[r{i}]" for i in range(len(quadros)))
    partes = [f"[0:a]aresample={TAXA_AUDIO}:async=1:first_pts=0,{FORMATO_AUDIO},asplit={len(quadros)}{ramos};"]
    for i, (ini, fim) in enumerate(quadros):
        saida_fade = max(0.0, (fim - ini) / fps - FADE_CORTE_S)
        partes.append(
            f"[r{i}]atrim=start_sample={_amostras(ini)}:end_sample={_amostras(fim)},asetpts=PTS-STARTPTS,"
            f"afade=t=in:d={FADE_CORTE_S}:curve=tri,afade=t=out:st={saida_fade:.4f}:d={FADE_CORTE_S}:curve=tri[c{i}];"
        )
    entradas = "".join(f"[c{i}]" for i in range(len(quadros)))
    partes.append(
        f"{entradas}concat=n={len(quadros)}:v=0:a=1,{NORMALIZAR_VOZ},"
        f"apad=whole_len={total},atrim=end_sample={total},asetpts=N/SR/TB[{rotulo}]"
    )
    return "".join(partes)


def _renderizar_conteudo(video_original: Path, base: float, duracao_fonte: float, quadros: list,
                         legenda: Path, gancho: str, limite: float, saida: Path):
    """Monta o layout vertical com imagem, som e legendas presos à mesma grade de quadros."""
    fps = VIDEO_SPECS["fps"]
    filtros = ",".join([*_filtros_titulo(gancho, limite), filtro_legendas(legenda)])
    executar_ffmpeg([
        "-ss", f"{base:.3f}", "-t", f"{duracao_fonte:.3f}", "-i", str(video_original),
        "-filter_complex", (
            f"[0:v]fps={fps}:start_time=0,select='{_expressao_quadros(quadros)}',setpts=N/{fps}/TB,split=2[b0][f0];"
            f"{_filtro_layout(_expressao_zoom(quadros))},{filtros}[v];"
            f"{_filtro_audio_cortes(quadros)}"
        ),
        "-map", "[v]", "-map", "[a]", "-frames:v", str(sum(fim - ini for ini, fim in quadros)),
        *_saida_intermediaria(),
        str(saida), "-y"
    ], etapa="legendas")


def _renderizar_intro(video_original: Path, inicio_imagem, quadro: Path, narracao: Path, quadros: int,
                      streamer: str, gancho: str, saida: Path):
    """Abre com o jogo em movimento e o título na tela, sem sobrepor a voz do streamer."""
    fps = VIDEO_SPECS["fps"]
    duracao = quadros / fps
    total = _amostras(quadros)
    etiqueta = filtro_texto(
        edicao.nome_falado(streamer).upper(),
        "fontcolor=black:fontsize=50:box=1:boxcolor=0xFACC15:boxborderw=16:x=(w-text_w)/2:y=450",
        fonte=FONTE_TITULO,
    )
    if inicio_imagem is None:
        entradas = ["-loop", "1", "-i", str(quadro)]
        imagem = (
            f"[0:v]zoompan=z='min(1+0.0012*on,1.1)':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':"
            f"d={quadros}:s=1080x1920:fps={fps},eq=brightness=-0.08,setsar=1,{etiqueta},format=yuv420p[v];"
        )
    else:
        entradas = ["-ss", f"{inicio_imagem:.3f}", "-t", f"{duracao + 0.5:.3f}", "-i", str(video_original)]
        textos = ",".join([*_filtros_titulo(gancho), etiqueta])
        imagem = (
            f"[0:v]fps={fps}:start_time=0,trim=end_frame={quadros},setpts=N/{fps}/TB,split=2[b0][f0];"
            f"{_filtro_layout('min(1+0.0012*on,1.1)')},{textos}[v];"
        )
    entradas += ["-i", str(narracao)]
    voz = f"[1:a]{NORMALIZAR_VOZ},apad=whole_len={total},atrim=end_sample={total}"
    if WHOOSH_PATH.exists():
        entradas += ["-i", str(WHOOSH_PATH)]
        atraso = _amostras(max(0, quadros - int(0.35 * fps)))
        audio = (
            f"{voz}[voz];[2:a]aresample={TAXA_AUDIO},aformat=channel_layouts=stereo,volume=0.7,adelay={atraso}S:all=1[efeito];"
            f"[voz][efeito]amix=inputs=2:duration=first:normalize=0,{FORMATO_AUDIO}[a]"
        )
    else:
        audio = f"{voz},{FORMATO_AUDIO}[a]"

    executar_ffmpeg([
        *entradas,
        "-filter_complex", f"{imagem}{audio}",
        "-map", "[v]", "-map", "[a]", "-frames:v", str(quadros),
        *_saida_intermediaria(),
        str(saida), "-y"
    ], etapa="vinheta")


def _codificador_final(acelerado: bool) -> list:
    """Na placa Intel, a qualidade 12 equivale à do processador e leva cerca de metade do tempo."""
    if acelerado:
        return ["-c:v", "h264_qsv", "-preset", "veryslow", "-global_quality", QUALIDADE_QUICK_SYNC, "-pix_fmt", "nv12"]
    return ["-c:v", VIDEO_SPECS["codec_v"], "-pix_fmt", VIDEO_SPECS["pix_fmt"], "-preset", PRESET_FINAL, "-crf", CRF_FINAL]


def _codificar(entrada_e_filtros: list, saida_final: list, etapa: str):
    """Usa a placa Intel quando possível e refaz no processador se ela falhar."""
    acelerado = quick_sync_disponivel()
    try:
        executar_ffmpeg([*entrada_e_filtros, *_codificador_final(acelerado), *saida_final], etapa=etapa)
    except FFmpegError as erro:
        if not acelerado:
            raise
        log_terminal(f"[EDITOR] Placa Intel falhou, refazendo no processador: {erro.detalhe}")
        executar_ffmpeg([*entrada_e_filtros, *_codificador_final(False), *saida_final], etapa=etapa)


def _renderizar_final(intro: Path, conteudo: Path, quadros_total: int, saida: Path):
    """Une abertura e conteúdo em uma só linha do tempo, com a marca e a chamada final narrada."""
    fps = VIDEO_SPECS["fps"]
    duracao_cta = max(DURACAO_MINIMA_CTA, obter_duracao_audio(CTA_AUDIO) + 0.3)
    quadro_cta = max(fps, quadros_total - int(math.ceil(duracao_cta * fps)))
    inicio_cta = quadro_cta / fps
    total_amostras = _amostras(quadros_total)
    y_marca = TOPO_GAMEPLAY + 24
    arroba = filtro_texto(
        "@VielaVice",
        f"fontcolor=white:fontsize=30:borderw=3:bordercolor=black:x=w-text_w-28:y={y_marca + 134}",
        fonte=FONTE_TITULO,
    )
    faixas = ",".join(
        filtro_texto(
            texto,
            "fontcolor=white:fontsize=58:box=1:boxcolor=0xDC2626:boxborderw=20:"
            f"x=(w-text_w)/2:y={y}:enable='gte(t,{inicio_cta:.3f})'",
            fonte=FONTE_TITULO,
        )
        for texto, y in (("CURTA E SE INSCREVA", 230), ("NO VIELA VICE!", 350))
    )
    entrada_e_filtros = [
        "-i", str(intro),
        "-i", str(conteudo),
        "-i", str(CTA_AUDIO),
        "-loop", "1", "-i", str(MARCA_PATH),
        "-filter_complex", (
            "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[video][audio];"
            "[3:v]scale=128:128,format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
            "a='255*lte(hypot(X-W/2,Y-H/2),W/2)'[logo];"
            f"[video][logo]overlay=x=W-w-30:y={y_marca}:format=auto:shortest=1,{arroba},{faixas},format=yuv420p[v];"
            f"[audio]volume=volume=0.10:enable='gte(t,{inicio_cta:.3f})',{FORMATO_AUDIO}[jogo];"
            f"[2:a]aresample={TAXA_AUDIO},{FORMATO_AUDIO},volume=6dB,adelay={_amostras(quadro_cta)}S:all=1[voz_cta];"
            "[jogo][voz_cta]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.9:latency=1,"
            f"apad=whole_len={total_amostras},atrim=end_sample={total_amostras}[a]"
        ),
        "-map", "[v]", "-map", "[a]", "-frames:v", str(quadros_total),
        "-r", str(fps),
    ]
    saida_final = ["-c:a", VIDEO_SPECS["codec_a"], "-b:a", VIDEO_SPECS["bitrate_a"], "-movflags", "+faststart", str(saida), "-y"]
    _codificar(entrada_e_filtros, saida_final, etapa="final")


def _inicio_da_abertura(trechos: list, duracao: float, bloqueios) -> float:
    """Usa o jogo logo antes do corte na abertura, desde que exista e não seja tela preta."""
    inicio = trechos[0][0] - duracao - 0.1
    if inicio < 0 or any(inicio < b_fim and trechos[0][0] > b_ini for b_ini, b_fim in bloqueios):
        return None
    return inicio


def criar_narracao_longo(streamer: str, parte: int, output_audio: Path) -> Path:
    """Cria a abertura narrada do vídeo longo."""
    texto = f"Os melhores momentos da live de {edicao.nome_falado(streamer)}, parte {parte}!"
    return _gerar_tts_com_retentativa(texto, output_audio, rate="+10%")


def _textos_do_longo(streamer: str, parte: int, fim_intro: float, inicio_cta: float) -> str:
    y_marca = 24 + MARCA_LONGO + 6
    textos = [
        filtro_texto("@VielaVice", f"fontcolor=white:fontsize=22:borderw=2:bordercolor=black:x=w-text_w-20:y={y_marca}", fonte=FONTE_TITULO),
        filtro_texto("MELHORES MOMENTOS", f"fontcolor=white:fontsize=64:box=1:boxcolor=black@0.78:boxborderw=18:x=(w-text_w)/2:y=250:enable='lt(t,{fim_intro:.3f})'", fonte=FONTE_TITULO),
        filtro_texto(f"{edicao.nome_falado(streamer).upper()} - PARTE {parte}", f"fontcolor=black:fontsize=42:box=1:boxcolor=0xFACC15:boxborderw=14:x=(w-text_w)/2:y=370:enable='lt(t,{fim_intro:.3f})'", fonte=FONTE_TITULO),
        filtro_texto("CURTA E SE INSCREVA NO VIELA VICE!", f"fontcolor=white:fontsize=44:box=1:boxcolor=0xDC2626:boxborderw=16:x=(w-text_w)/2:y=600:enable='gte(t,{inicio_cta:.3f})'", fonte=FONTE_TITULO),
    ]
    return ",".join(textos)


def renderizar_longo(
    video_original: Path,
    inicio: float,
    duracao: float,
    streamer: str,
    parte: int,
    output_final: Path,
    bloqueios=()
) -> Path:
    """
    Produz um vídeo longo horizontal, em uma única passada para manter fala e imagem juntas.
    A abertura é narrada com o som do jogo mudo e o final traz a chamada para o canal.
    """
    garantir_audio_cta()
    fps = VIDEO_SPECS["fps"]
    temp_dir = VIDEO_BRUTO_DIR
    temp_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    narracao = temp_dir / f"longo_intro_{ts}.mp3"
    final_tmp = temp_dir / f"longo_{ts}.mp4"

    try:
        trechos = edicao.alinhar_trechos_aos_quadros(edicao.trechos_sem_bloqueios(inicio, duracao, bloqueios), fps)
        if not trechos:
            raise FFmpegError("edicao", "sem_imagem", "trecho do vídeo longo sem imagem aproveitável.")
        base = max(0.0, math.floor(trechos[0][0] * fps) / fps)
        quadros = _quadros_dos_trechos(trechos, base)
        quadros_total = sum(fim - ini for ini, fim in quadros)
        total_amostras = _amostras(quadros_total)

        criar_narracao_longo(streamer, parte, narracao)
        fim_intro = math.ceil((obter_duracao_audio(narracao) + 0.25) * fps) / fps
        duracao_cta = max(DURACAO_MINIMA_CTA, obter_duracao_audio(CTA_AUDIO) + 0.3)
        quadro_cta = max(fps, quadros_total - int(math.ceil(duracao_cta * fps)))
        inicio_cta = quadro_cta / fps

        entrada_e_filtros = [
            "-ss", f"{base:.3f}", "-t", f"{quadros[-1][1] / fps + 0.5:.3f}", "-i", str(video_original),
            "-i", str(narracao),
            "-i", str(CTA_AUDIO),
            "-loop", "1", "-i", str(MARCA_PATH),
            "-filter_complex", (
                f"[0:v]fps={fps}:start_time=0,select='{_expressao_quadros(quadros)}',setpts=N/{fps}/TB,"
                f"scale={LARGURA_LONGO}:{ALTURA_LONGO}:force_original_aspect_ratio=decrease,"
                f"pad={LARGURA_LONGO}:{ALTURA_LONGO}:(ow-iw)/2:(oh-ih)/2,setsar=1,eq=contrast=1.06:saturation=1.15[base];"
                f"[3:v]scale={MARCA_LONGO}:{MARCA_LONGO},format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
                "a='255*lte(hypot(X-W/2,Y-H/2),W/2)'[logo];"
                f"[base][logo]overlay=x=W-w-24:y=24:format=auto:shortest=1,"
                f"{_textos_do_longo(streamer, parte, fim_intro, inicio_cta)},format=yuv420p[v];"
                f"{_filtro_audio_cortes(quadros, rotulo='original')};"
                f"[original]volume=volume=0:enable='lt(t,{fim_intro:.3f})',"
                f"volume=volume=0.10:enable='gte(t,{inicio_cta:.3f})',{FORMATO_AUDIO}[jogo];"
                f"[1:a]{NORMALIZAR_VOZ},{FORMATO_AUDIO}[voz];"
                f"[2:a]aresample={TAXA_AUDIO},{FORMATO_AUDIO},volume=6dB,adelay={_amostras(quadro_cta)}S:all=1[voz_cta];"
                "[jogo][voz][voz_cta]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.9:latency=1,"
                f"apad=whole_len={total_amostras},atrim=end_sample={total_amostras}[a]"
            ),
            "-map", "[v]", "-map", "[a]", "-frames:v", str(quadros_total),
            "-r", str(fps),
        ]
        saida = ["-c:a", VIDEO_SPECS["codec_a"], "-b:a", VIDEO_SPECS["bitrate_a"], "-movflags", "+faststart", str(final_tmp), "-y"]
        _codificar(entrada_e_filtros, saida, etapa="longo")
        garantir_sincronia(final_tmp)
        output_final.parent.mkdir(parents=True, exist_ok=True)
        os.replace(final_tmp, output_final)
        return output_final
    finally:
        for arquivo in (narracao, final_tmp):
            try:
                arquivo.unlink(missing_ok=True)
            except OSError:
                pass


def renderizar_short(
    video_original: Path,
    segmentos: list,
    streamer: str,
    output_final: Path,
    gancho: str = None,
    bloqueios=()
) -> Path:
    """
    Produz o Short completo em 1080x1920:
    1. Remove pausas longas e telas pretas do trecho escolhido
    2. Monta fundo desfocado, gameplay nítido, título-gancho e legendas de até 3 palavras
    3. Abre com narração curta sobre o jogo em movimento
    4. Aplica a marca do canal e encerra com a chamada narrada
    5. Confere a sincronia entre fala e imagem antes de liberar o arquivo

    O arquivo só aparece na pasta de exportação depois de totalmente pronto.
    """
    garantir_audio_cta()
    temp_dir = VIDEO_BRUTO_DIR
    temp_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)

    legenda = temp_dir / f"legenda_{ts}.ass"
    conteudo = temp_dir / f"conteudo_{ts}.mp4"
    quadro = temp_dir / f"intro_{ts}.png"
    narracao = temp_dir / f"intro_{ts}.mp3"
    intro = temp_dir / f"intro_vid_{ts}.mp4"
    final_tmp = temp_dir / f"final_{ts}.mp4"
    intermediarios = [legenda, conteudo, quadro, narracao, intro, final_tmp]

    try:
        palavras = edicao.palavras_dos_segmentos(segmentos)
        fps = VIDEO_SPECS["fps"]
        trechos = edicao.alinhar_trechos_aos_quadros(edicao.calcular_trechos_uteis(
            palavras, bloqueios=bloqueios, duracao_max=VIDEO_SPECS["duracao_conteudo_s"]), fps)
        duracao_conteudo = edicao.duracao_trechos(trechos)
        if duracao_conteudo < DURACAO_MINIMA_CONTEUDO:
            raise FFmpegError("edicao", "sem_fala", "trecho sem fala suficiente para um Short.")

        base = max(0.0, math.floor((trechos[0][0] - 0.5) * fps) / fps)
        quadros = _quadros_dos_trechos(trechos, base)
        duracao_fonte = quadros[-1][1] / fps + 0.5

        criar_narração_intro(streamer, narracao)
        quadros_intro = int(math.ceil((obter_duracao_audio(narracao) + 0.25) * fps))
        duracao_cta = max(DURACAO_MINIMA_CTA, obter_duracao_audio(CTA_AUDIO) + 0.3)
        limite = max(1.0, duracao_conteudo - duracao_cta)

        grupos = edicao.agrupar_legendas(palavras, trechos, limite=limite)
        edicao.gerar_ass(grupos, legenda)
        titulo = gancho or edicao.gerar_gancho(segmentos, streamer)
        _renderizar_conteudo(video_original, base, duracao_fonte, quadros, legenda, titulo, limite, conteudo)

        inicio_abertura = _inicio_da_abertura(trechos, quadros_intro / fps, bloqueios)
        if inicio_abertura is None:
            executar_ffmpeg(["-i", str(conteudo), "-frames:v", "1", "-update", "1", str(quadro), "-y"], etapa="frame_intro")
        _renderizar_intro(video_original, inicio_abertura, quadro, narracao, quadros_intro, streamer, titulo, intro)

        quadros_total = quadros_intro + sum(fim - ini for ini, fim in quadros)
        _renderizar_final(intro, conteudo, quadros_total, final_tmp)
        garantir_sincronia(final_tmp)
        output_final.parent.mkdir(parents=True, exist_ok=True)
        os.replace(final_tmp, output_final)
        return output_final
    finally:
        for arquivo in intermediarios:
            try:
                arquivo.unlink(missing_ok=True)
            except OSError:
                pass
