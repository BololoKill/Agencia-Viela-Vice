"""
Módulo de Transcrição Whisper e Geração de Legendas.
"""
import subprocess
from pathlib import Path
import whisper
from src.utils import censor_text

def extrair_audio_wav(video_path: Path, output_wav: Path) -> Path:
    """Extrai faixa de áudio em PCM mono 16kHz otimizada para o Whisper."""
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        str(output_wav), "-y"
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_wav

def transcrever_audio(audio_wav: Path, model_name: str = "base") -> list:
    """
    Transcreve áudio com Whisper em português brasileiro.
    Retorna lista de segmentos com timestamp e texto.
    """
    model = whisper.load_model(model_name)
    resultado = model.transcribe(str(audio_wav), language="pt", task="transcribe")
    return resultado.get("segments", [])

def fatiar_em_chunks(segments: list, duracao_alvo: float = 65.0, max_chunks: int = 3) -> list:
    """
    Divide a transcrição em blocos contínuos de aproximadamente 60s a 75s.
    Retorna lista de tuplas: (start_time, end_time, segmentos_do_chunk).
    """
    if not segments:
        return []

    chunks = []
    chunk_atual = []
    chunk_start = segments[0]["start"]

    for seg in segments:
        chunk_atual.append(seg)
        duracao_corrente = seg["end"] - chunk_start
        if duracao_corrente >= duracao_alvo:
            chunks.append((chunk_start, seg["end"], list(chunk_atual)))
            chunk_atual = []
            if len(chunks) >= max_chunks:
                break
            chunk_start = seg["start"]

    if chunk_atual and len(chunks) < max_chunks:
        chunks.append((chunk_start, segments[-1]["end"], chunk_atual))

    return chunks

def gerar_arquivo_srt(segmentos: list, offset_base: float, srt_output: Path) -> Path:
    """Gera arquivo SRT limpo e com profanidades censuradas."""
    with open(srt_output, "w", encoding="utf-8") as f:
        idx = 1
        for s in segmentos:
            st = max(0.0, s["start"] - offset_base)
            en = max(st + 0.2, s["end"] - offset_base)
            t1 = f"{int(st//3600):02d}:{int((st%3600)//60):02d}:{int(st%60):02d},{int((st%1)*1000):03d}"
            t2 = f"{int(en//3600):02d}:{int((en%3600)//60):02d}:{int(en%60):02d},{int((en%1)*1000):03d}"
            texto = censor_text(s.get("text", "").strip())
            if texto:
                f.write(f"{idx}\n{t1} --> {t2}\n{texto}\n\n")
                idx += 1
    return srt_output
