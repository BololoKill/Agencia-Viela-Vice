import re
import subprocess

def parse_srt(srt_path):
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pattern = re.compile(r'(\d+)\n(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})\n(.*?)(?=\n\n|\Z)', re.DOTALL)
    matches = pattern.findall(content)
    
    subtitles = []
    for match in matches:
        start_sec = int(match[1]) * 3600 + int(match[2]) * 60 + int(match[3]) + int(match[4]) / 1000.0
        end_sec = int(match[5]) * 3600 + int(match[6]) * 60 + int(match[7]) + int(match[8]) / 1000.0
        text = match[9].replace('\n', ' ').strip()
        text = text.replace("'", "").replace(":", "\\:")
        subtitles.append((start_sec, end_sec, text))
    
    return subtitles

def main():
    srt_path = 'exportacao/short-gta6-nitido.srt'
    subs = parse_srt(srt_path)
    
    filters = []
    fontfile = "C\\:/Windows/Fonts/arial.ttf"
    
    # 1. Top Title Banner
    filters.append(f"drawbox=x=0:y=0:w=1080:h=140:color=black@0.6:t=fill")
    filters.append(f"drawtext=fontfile={fontfile}:text='REACAO AO NOVO GTA 6':fontcolor=white:fontsize=52:x=(w-text_w)/2:y=(140-text_h)/2")
    
    # 2. Subtitles as drawtext filters
    for start, end, text in subs:
        dt_filter = (
            f"drawtext=fontfile={fontfile}:text='{text}':fontcolor=yellow:fontsize=40:box=1:boxcolor=black@0.7:boxborderw=10:"
            f"x=(w-text_w)/2:y=1550:enable='between(t,{start},{end})'"
        )
        filters.append(dt_filter)
        
    # 3. Slow zoom
    filters.append("scale='iw*(1+0.0004*t)':'ih*(1+0.0004*t)'")
    filters.append("crop=1080:1920")
    
    filter_complex = ",".join(filters)
    
    cmd = [
        'ffmpeg',
        '-i', 'exportacao/short-gta6-nitido.mp4',
        '-vf', filter_complex,
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '18',
        '-c:a', 'aac',
        '-b:a', '128k',
        'exportacao/short-gta6-pronto.mp4',
        '-y'
    ]
    
    print("Executando FFmpeg com fontfile explícito...")
    subprocess.run(cmd, check=True)
    print("Vídeo gerado com sucesso em exportacao/short-gta6-pronto.mp4!")

if __name__ == '__main__':
    main()
