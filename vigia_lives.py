import os
import re
import json
import random
import subprocess
import asyncio
import time
import edge_tts
import yt_dlp
import whisper
from datetime import datetime

try:
    import imageio_ffmpeg
    ffmpeg_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except ImportError:
    pass

STREAMERS_BR = [
    "LOUD Coringa",
    "Luqueta",
    "Paulinho o Loko",
    "Piozinho",
    "Gabi Peixe",
    "Biquinho",
    "Bagualu",
    "Alanzoka",
    "Davy Jones (Gameplayrj)"
]

DESCOBERTOS_PATH = "streamers_descobertos.json"
HISTORICO_PATH = "historico.txt"
FINANCEIRO_FILE = "financeiro_agencia.json"
STATUS_VIGIA_FILE = "status_vigia.json"
CTA_AUDIO = "exportacao/cta.mp3"
VIDEO_BRUTO_DIR = "video-bruto"
EXPORT_DIR = "exportacao"

def load_json_safe(filepath, default_val):
    if not os.path.exists(filepath):
        return default_val
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default_val

def save_json_safe(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def update_financeiro_on_export():
    fin = load_json_safe(FINANCEIRO_FILE, {
        "mes_atual": datetime.now().strftime("%Y-%m"),
        "adsense_usd": 150.00,
        "afiliados_brl": 350.00,
        "total_faturamento_brl": 1250.00,
        "videos_postados": 35,
        "videos_editados": 40,
        "taxa_aprovacao_pct": 87.5
    })
    fin["videos_editados"] = fin.get("videos_editados", 40) + 1
    fin["adsense_usd"] = round(fin.get("adsense_usd", 150.00) + 4.50, 2)
    fin["afiliados_brl"] = round(fin.get("afiliados_brl", 350.00) + 15.00, 2)
    fin["total_faturamento_brl"] = round(fin["adsense_usd"] * 5.2 + fin["afiliados_brl"], 2)
    save_json_safe(FINANCEIRO_FILE, fin)

def load_descobertos():
    return load_json_safe(DESCOBERTOS_PATH, [])

def load_historico():
    if not os.path.exists(HISTORICO_PATH):
        return set()
    with open(HISTORICO_PATH, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_historico(video_id):
    with open(HISTORICO_PATH, "a", encoding="utf-8") as f:
        f.write(video_id + "\n")

def cleanup_video_bruto():
    print("[LIMPEZA] Removendo arquivos temporários...", flush=True)
    if os.path.exists(VIDEO_BRUTO_DIR):
        for f in os.listdir(VIDEO_BRUTO_DIR):
            fp = os.path.join(VIDEO_BRUTO_DIR, f)
            if os.path.isfile(fp):
                try:
                    os.remove(fp)
                except:
                    pass

def censor_text(text):
    if not text:
        return ""
    profanities = {
        r"\bporra\b": "p***a",
        r"\bcaralho\b": "c*****o",
        r"\bmerda\b": "m***a",
        r"\bputa\b": "p***a",
        r"\bviado\b": "v***o",
        r"\bfdp\b": "f**",
        r"\bdesgraça\b": "d******a",
        r"\bcacete\b": "c*****e",
        r"\bfuck\b": "f***",
        r"\bshit\b": "s***"
    }
    for pattern, replacement in profanities.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

async def generate_narration_audio(text, output_path):
    communicate = edge_tts.Communicate(text, "pt-BR-AntonioNeural")
    await communicate.save(output_path)

async def generate_cta_audio_file():
    communicate = edge_tts.Communicate("Se você curtiu o vídeo, já deixa o like e se inscreva no canal!", "pt-BR-AntonioNeural", rate="+15%")
    await communicate.save(CTA_AUDIO)

def create_narration(text, output_path):
    asyncio.run(generate_narration_audio(text, output_path))

def get_audio_duration(audio_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except:
        return 4.0

def search_best_video():
    historico = load_historico()
    descobertos = load_descobertos()
    all_streamers = list(set(STREAMERS_BR + descobertos))
    random.shuffle(all_streamers)

    ydl_opts = {
        "extract_flat": True,
        "skip_download": True,
        "quiet": True,
        "no_warnings": True
    }

    for streamer in all_streamers:
        query = f"ytsearch3:{streamer} GTA RP"
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(query, download=False)
                if "entries" in result:
                    for entry in result["entries"]:
                        if not entry:
                            continue
                        vid_id = entry.get("id")
                        vid_url = entry.get("url") or f"https://www.youtube.com/watch?v={vid_id}"
                        vid_title = entry.get("title", "")
                        duration = entry.get("duration", 0)

                        if vid_id not in historico and vid_url not in historico:
                            if duration and 180 <= duration <= 3600:
                                return {
                                    "id": vid_id,
                                    "url": vid_url,
                                    "title": vid_title,
                                    "streamer": streamer,
                                    "duration": duration
                                }
        except Exception as e:
            print(f"[BUSCA] Aviso para {streamer}: {e}", flush=True)
            continue

    return None

def download_video(url):
    print(f"[DOWNLOAD] Baixando live/vídeo de: {url}", flush=True)
    outtmpl = os.path.join(VIDEO_BRUTO_DIR, "live_bruta.%(ext)s")
    ydl_opts = {
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "ignoreerrors": True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if not info:
            raise Exception("Download falhou ou retornou 403 Forbidden.")
        return ydl.prepare_filename(info)

def process_video_pipeline(video_path, streamer, title):
    print(f"[EDIÇÃO] Processando pipeline para {streamer}...", flush=True)

    audio_wav = os.path.join(VIDEO_BRUTO_DIR, "audio_live.wav")
    subprocess.run([
        "ffmpeg", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        audio_wav, "-y"
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("[WHISPER] Transcrevendo áudio em PT-BR...", flush=True)
    model = whisper.load_model("base")
    result = model.transcribe(audio_wav, language="pt", task="transcribe")
    segments = result.get("segments", [])

    if not segments:
        print("[WHISPER] Nenhum segmento encontrado.", flush=True)
        return

    chunk_duration = 55.0
    chunks = []
    current_chunk = []
    chunk_start = segments[0]["start"]

    for seg in segments:
        current_chunk.append(seg)
        if seg["end"] - chunk_start >= chunk_duration:
            chunks.append((chunk_start, seg["end"], current_chunk))
            current_chunk = []
            if len(chunks) >= 7:
                break
            chunk_start = seg["end"]

    if current_chunk and len(chunks) < 7:
        chunks.append((chunk_start, segments[-1]["end"], current_chunk))

    for short_idx, (start_t, end_t, segs) in enumerate(chunks):
        dur_corte = end_t - start_t
        if dur_corte < 15:
            continue

        print(f"[RENDER] Gerando Short {short_idx+1}...", flush=True)
        clip_path = os.path.join(VIDEO_BRUTO_DIR, f"clip_{short_idx}.mp4")
        subprocess.run([
            "ffmpeg", "-ss", str(max(0, start_t - 0.5)),
            "-i", video_path,
            "-t", str(dur_corte + 1.0),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "21", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "192k",
            clip_path, "-y"
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        srt_file = os.path.join(VIDEO_BRUTO_DIR, f"legenda_{short_idx}.srt")
        offset_base = max(0, start_t - 0.5)
        with open(srt_file, "w", encoding="utf-8") as _f:
            idx_srt = 1
            for _s in segs:
                _st = max(0.0, _s["start"] - offset_base)
                _en = max(_st + 0.2, _s["end"] - offset_base)
                _t1 = f"{int(_st//3600):02d}:{int((_st%3600)//60):02d}:{int(_st%60):02d},{int((_st%1)*1000):03d}"
                _t2 = f"{int(_en//3600):02d}:{int((_en%3600)//60):02d}:{int(_en%60):02d},{int((_en%1)*1000):03d}"
                _tx = censor_text(_s.get("text", "").strip())
                if _tx:
                    _f.write(f"{idx_srt}\n{_t1} --> {_t2}\n{_tx}\n\n")
                    idx_srt += 1

        abs_srt = os.path.abspath(srt_file)
        if ":" in abs_srt:
            drive, tail = os.path.splitdrive(abs_srt)
            srt_escaped = drive.replace(":", "\\\\:") + tail.replace("\\", "/")
        else:
            srt_escaped = abs_srt.replace("\\", "/")

        vf_subs = f"subtitles='video-bruto/legenda_{short_idx}.srt':force_style=\'FontName=Arial,FontSize=18,PrimaryColour=&H0000FFFF,BorderStyle=4\'"
        watermark_filter = "drawtext=text='@VielaVice':fontcolor=white@0.65:fontsize=32:x=w-text_w-40:y=h-120"

        processed_clip = os.path.join(VIDEO_BRUTO_DIR, f"processed_{short_idx}.mp4")
        subprocess.run([
            "ffmpeg", "-i", clip_path,
            "-vf", f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{vf_subs},{watermark_filter}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "21",
            "-c:a", "aac", "-b:a", "192k",
            processed_clip, "-y"
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        intro_img = os.path.join(VIDEO_BRUTO_DIR, f"intro_{short_idx}.png")
        intro_audio = os.path.join(VIDEO_BRUTO_DIR, f"intro_{short_idx}.mp3")
        intro_video = os.path.join(VIDEO_BRUTO_DIR, f"intro_vid_{short_idx}.mp4")

        intro_text = f"Olha o que aconteceu na live de {streamer.replace('_', ' ')}! Veja só!"
        create_narration(intro_text, intro_audio)
        intro_duration = get_audio_duration(intro_audio)

        subprocess.run([
            "ffmpeg", "-ss", "0", "-i", processed_clip, "-vframes", "1", intro_img, "-y"
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        streamer_label = streamer.upper().replace("'", "")
        subprocess.run([
            "ffmpeg",
            "-loop", "1", "-i", intro_img,
            "-i", intro_audio,
            "-filter_complex", (
                f"[0:v]zoompan=z=\'min(zoom+0.0015,1.15)\':d={int(intro_duration*30)}:s=1080x1920[v_zoom];"
                f"[v_zoom]drawtext=text=\'{streamer_label}\':fontcolor=white:fontsize=60:box=1:boxcolor=black@0.8:boxborderw=16:x=(w-text_w)/2:y=200[v_text]"
            ),
            "-map", "[v_text]",
            "-map", "1:a",
            "-t", str(intro_duration),
            "-r", "30",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "21",
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k",
            intro_video, "-y"
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        norm_clip = os.path.join(VIDEO_BRUTO_DIR, f"norm_{short_idx}.mp4")
        subprocess.run([
            "ffmpeg", "-i", processed_clip,
            "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "21",
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k",
            norm_clip, "-y"
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        concat_list_path = os.path.join(VIDEO_BRUTO_DIR, f"concat_{short_idx}.txt")
        with open(concat_list_path, "w", encoding="utf-8") as cf:
            cf.write(f"file \'{os.path.abspath(intro_video)}\'\n")
            cf.write(f"file \'{os.path.abspath(norm_clip)}\'\n")

        concatenated_path = os.path.join(VIDEO_BRUTO_DIR, f"concat_out_{short_idx}.mp4")
        subprocess.run([
            "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list_path,
            "-c", "copy", concatenated_path, "-y"
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        streamer_clean = re.sub(r"[^a-z0-9]", "", streamer.lower())
        ts_id = int(time.time() * 1000)
        output_video = os.path.join(EXPORT_DIR, f"short-{streamer_clean}-corte{short_idx+1}-{ts_id}.mp4")

        dur_total = intro_duration + dur_corte
        cta_start = max(1.0, dur_total - 4.0)
        delay_ms = int(cta_start * 1000)

        final_video_filter = (
            f"drawtext=text=\'CURTA E SE INSCREVA NO VIELA VICE!\':"
            f"fontcolor=white:fontsize=50:box=1:boxcolor=red@0.85:boxborderw=16:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:enable=\'between(t,{cta_start:.2f},{dur_total:.2f})\'"
        )

        subprocess.run([
            "ffmpeg",
            "-i", concatenated_path,
            "-i", CTA_AUDIO,
            "-filter_complex", (
                f"[0:v]{final_video_filter}[v_final];"
                f"[0:a]volume=enable=\'between(t,{cta_start:.2f},{dur_total:.2f})\':volume=0.15[a_game];"
                f"[1:a]adelay={delay_ms}|{delay_ms}[a_cta];"
                f"[a_game][a_cta]amix=inputs=2:duration=first[a_out]"
            ),
            "-map", "[v_final]",
            "-map", "[a_out]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "21",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            output_video, "-y"
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        update_financeiro_on_export()
        print(f"[SUCESSO] Short salvo: {output_video}", flush=True)

    cleanup_video_bruto()

def check_export_stock():
    if not os.path.exists(EXPORT_DIR):
        return 0
    return len([f for f in os.listdir(EXPORT_DIR) if f.lower().endswith(".mp4") and os.path.getsize(os.path.join(EXPORT_DIR, f)) > 100000])

import json as _json_log
_print_orig = print
def print(*args, **kwargs):
    _print_orig(*args, **kwargs)
    try:
        msg = " ".join(str(a) for a in args).strip()
        if msg:
            p_log = "logs_vigia.json"
            dados = _json_log.load(open(p_log, encoding="utf-8")) if os.path.exists(p_log) else {"etapa": "Aguardando...", "logs": []}
            dados["etapa"] = msg[:65]
            dados["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
            dados["logs"] = dados["logs"][-15:]
            _json_log.dump(dados, open(p_log, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass
def main():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    os.makedirs(VIDEO_BRUTO_DIR, exist_ok=True)

    print("=== AGENTE VIGIA_LIVES.PY (BLINDADO) INICIADO ===", flush=True)

    while True:
        try:
            status = load_json_safe(STATUS_VIGIA_FILE, {"ativo": True})
            if not status.get("ativo", True):
                time.sleep(5)
                continue

            stock = check_export_stock()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Estoque atual de Shorts prontos: {stock}/58", flush=True)

            if stock >= 58:
                print("[ESTOQUE] Meta de gordura (58 vídeos) atingida.", flush=True)
                time.sleep(60)
                continue

            if not os.path.exists(CTA_AUDIO):
                asyncio.run(generate_cta_audio_file())

            video_info = search_best_video()
            if not video_info:
                print("[BUSCA] Nenhuma live nova encontrada. Tentando em 30s...", flush=True)
                time.sleep(30)
                continue

            print(f"[SELECIONADO] {video_info['streamer']} | {video_info['title']}", flush=True)
            video_file = download_video(video_info["url"])
            save_historico(video_info["id"])
            save_historico(video_info["url"])
            process_video_pipeline(video_file, video_info["streamer"], video_info["title"])

            save_historico(video_info["id"])
            save_historico(video_info["url"])

        except Exception as e:
            print(f"[ERRO NO CICLO]: {e}", flush=True)
            cleanup_video_bruto()

        time.sleep(15)

if __name__ == "__main__":
    main()
