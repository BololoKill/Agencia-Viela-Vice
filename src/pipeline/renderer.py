"""
Módulo de Renderização e Edição de Vídeos via FFmpeg Direto.
ATENÇÃO: MoviePy é estritamente proibido pelas diretrizes do projeto.
Todos os efeitos visuais, legendas e mixagem são processados diretamente via comandos FFmpeg.
"""
import os
import re
import time
import asyncio
import subprocess
from pathlib import Path
import edge_tts
from src.config import EXPORT_DIR, VIDEO_BRUTO_DIR, CTA_AUDIO, VIDEO_SPECS

async def gerar_audio_tts(texto: str, output_path: Path, voz: str = "pt-BR-AntonioNeural", rate: str = "+0%"):
    """Gera narração via Edge-TTS sem sobrepor o áudio do streamer."""
    communicate = edge_tts.Communicate(texto, voz, rate=rate)
    await communicate.save(str(output_path))

def criar_narração_intro(streamer: str, output_audio: Path) -> Path:
    """Cria introdução narrada dinâmica para o corte."""
    texto = f"Olha o que aconteceu na live de {streamer.replace('_', ' ')}! Veja só!"
    asyncio.run(gerar_audio_tts(texto, output_audio))
    return output_audio

def garantir_audio_cta(cta_path: Path = CTA_AUDIO):
    """Garante que o áudio de CTA padrão exista na pasta de exportação."""
    if not cta_path.exists():
        cta_path.parent.mkdir(parents=True, exist_ok=True)
        asyncio.run(gerar_audio_tts(
            "Se você curtiu o vídeo, já deixa o like e se inscreva no canal!",
            cta_path,
            rate="+15%"
        ))

def obter_duracao_audio(audio_path: Path) -> float:
    """Mede duração exata do arquivo de áudio via FFprobe."""
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

def renderizar_short(
    video_original: Path,
    start_sec: float,
    duracao_corte: float,
    srt_path: Path,
    streamer: str,
    output_final: Path
) -> Path:
    """
    Pipeline completo de renderização do Short em 9:16 (1080x1920) em H.264 / yuv420p:
    1. Corte do trecho bruto com folga de início
    2. Queima de legendas com estilo moderno e watermark
    3. Geração de introdução com zoom leve no primeiro quadro e narração TTS
    4. Concatenação da introdução com o corte principal
    5. Inclusão de banner e áudio de CTA nos últimos 4 segundos com atenuação do áudio do jogo
    """
    garantir_audio_cta()
    temp_dir = VIDEO_BRUTO_DIR
    temp_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)

    clip_bruto = temp_dir / f"clip_{ts}.mp4"
    clip_com_legendas = temp_dir / f"proc_{ts}.mp4"
    intro_img = temp_dir / f"intro_{ts}.png"
    intro_audio = temp_dir / f"intro_{ts}.mp3"
    intro_video = temp_dir / f"intro_vid_{ts}.mp4"
    norm_clip = temp_dir / f"norm_{ts}.mp4"
    concat_list = temp_dir / f"concat_{ts}.txt"
    concat_out = temp_dir / f"concat_out_{ts}.mp4"

    # 1. Cortar trecho do vídeo original
    start_offset = max(0, start_sec - 0.5)
    subprocess.run([
        "ffmpeg", "-ss", str(start_offset),
        "-i", str(video_original),
        "-t", str(duracao_corte + 1.0),
        "-c:v", VIDEO_SPECS["codec_v"],
        "-pix_fmt", VIDEO_SPECS["pix_fmt"],
        "-crf", VIDEO_SPECS["crf"],
        "-preset", VIDEO_SPECS["preset"],
        "-c:a", VIDEO_SPECS["codec_a"],
        "-b:a", VIDEO_SPECS["bitrate_a"],
        str(clip_bruto), "-y"
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 2. Formatar caminho do SRT para o filtro do FFmpeg no Windows
    abs_srt = str(srt_path.resolve())
    if ":" in abs_srt:
        drive, tail = os.path.splitdrive(abs_srt)
        srt_escaped = drive.replace(":", "\\\\:") + tail.replace("\\", "/")
    else:
        srt_escaped = abs_srt.replace("\\", "/")

    vf_subs = f"subtitles=\"{srt_escaped}\":force_style='FontName=Arial,FontSize=18,PrimaryColour=&H0000FFFF,BorderStyle=4'"
    vf_watermark = "drawtext=text='@VielaVice':fontcolor=white@0.65:fontsize=32:x=w-text_w-40:y=h-120"

    # 3. Escalonar e cortar para 1080x1920 (Vertical 9:16)
    subprocess.run([
        "ffmpeg", "-i", str(clip_bruto),
        "-vf", f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{vf_subs},{vf_watermark}",
        "-c:v", VIDEO_SPECS["codec_v"],
        "-pix_fmt", VIDEO_SPECS["pix_fmt"],
        "-preset", VIDEO_SPECS["preset"],
        "-crf", VIDEO_SPECS["crf"],
        "-c:a", VIDEO_SPECS["codec_a"],
        "-b:a", VIDEO_SPECS["bitrate_a"],
        str(clip_com_legendas), "-y"
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 4. Criar intro narrada
    criar_narração_intro(streamer, intro_audio)
    intro_dur = obter_duracao_audio(intro_audio)

    # Extrair primeiro frame
    subprocess.run([
        "ffmpeg", "-ss", "0", "-i", str(clip_com_legendas),
        "-vframes", "1", str(intro_img), "-y"
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    streamer_label = streamer.upper().replace("'", "")
    # Vídeo da vinheta com zoom suave e nome do streamer
    subprocess.run([
        "ffmpeg",
        "-loop", "1", "-i", str(intro_img),
        "-i", str(intro_audio),
        "-filter_complex", (
            f"[0:v]zoompan=z='min(zoom+0.0015,1.15)':d={int(intro_dur*30)}:s=1080x1920[v_zoom];"
            f"[v_zoom]drawtext=text='{streamer_label}':fontcolor=white:fontsize=60:box=1:boxcolor=black@0.8:boxborderw=16:x=(w-text_w)/2:y=200[v_text]"
        ),
        "-map", "[v_text]",
        "-map", "1:a",
        "-t", str(intro_dur),
        "-r", str(VIDEO_SPECS["fps"]),
        "-c:v", VIDEO_SPECS["codec_v"],
        "-pix_fmt", VIDEO_SPECS["pix_fmt"],
        "-preset", VIDEO_SPECS["preset"],
        "-crf", VIDEO_SPECS["crf"],
        "-c:a", VIDEO_SPECS["codec_a"],
        "-ar", "44100", "-ac", "2", "-b:a", VIDEO_SPECS["bitrate_a"],
        str(intro_video), "-y"
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Padronizar o clipe principal para concatenação limpa
    subprocess.run([
        "ffmpeg", "-i", str(clip_com_legendas),
        "-r", str(VIDEO_SPECS["fps"]),
        "-c:v", VIDEO_SPECS["codec_v"],
        "-pix_fmt", VIDEO_SPECS["pix_fmt"],
        "-preset", VIDEO_SPECS["preset"],
        "-crf", VIDEO_SPECS["crf"],
        "-c:a", VIDEO_SPECS["codec_a"],
        "-ar", "44100", "-ac", "2", "-b:a", VIDEO_SPECS["bitrate_a"],
        str(norm_clip), "-y"
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Concatenação da intro com o vídeo principal
    with open(concat_list, "w", encoding="utf-8") as cf:
        cf.write(f"file '{str(intro_video.resolve())}'\n")
        cf.write(f"file '{str(norm_clip.resolve())}'\n")

    subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(concat_out), "-y"
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 5. Adicionar CTA final nos últimos 4 segundos
    dur_total = intro_dur + duracao_corte
    cta_start = max(1.0, dur_total - 4.0)
    delay_ms = int(cta_start * 1000)

    final_video_filter = (
        f"drawtext=text='CURTA E SE INSCREVA NO VIELA VICE!':"
        f"fontcolor=white:fontsize=50:box=1:boxcolor=red@0.85:boxborderw=16:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{cta_start:.2f},{dur_total:.2f})'"
    )

    output_final.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg",
        "-i", str(concat_out),
        "-i", str(CTA_AUDIO),
        "-filter_complex", (
            f"[0:v]{final_video_filter}[v_final];"
            f"[0:a]volume=enable='between(t,{cta_start:.2f},{dur_total:.2f})':volume=0.15[a_game];"
            f"[1:a]adelay={delay_ms}|{delay_ms}[a_cta];"
            f"[a_game][a_cta]amix=inputs=2:duration=first[a_out]"
        ),
        "-map", "[v_final]",
        "-map", "[a_out]",
        "-c:v", VIDEO_SPECS["codec_v"],
        "-pix_fmt", VIDEO_SPECS["pix_fmt"],
        "-preset", VIDEO_SPECS["preset"],
        "-crf", VIDEO_SPECS["crf"],
        "-c:a", VIDEO_SPECS["codec_a"],
        "-b:a", VIDEO_SPECS["bitrate_a"],
        "-movflags", "+faststart",
        str(output_final), "-y"
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Limpeza dos arquivos intermediários deste corte
    for f in [clip_bruto, clip_com_legendas, intro_img, intro_audio, intro_video, norm_clip, concat_list, concat_out]:
        try:
            if f.exists():
                f.unlink()
        except Exception:
            pass

    return output_final
