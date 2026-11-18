import os, glob, json, subprocess
from datetime import datetime

os.makedirs("exportacao", exist_ok=True)
os.makedirs("aprovados_top6", exist_ok=True)

def auditar_video(caminho):
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt,codec_name", "-show_entries", "format=duration", "-of", "json", caminho]
        res = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8")
        dados = json.loads(res)
        duracao = float(dados["format"]["duration"])
        pix_fmt = dados["streams"][0].get("pix_fmt", "")
        if duracao < 15 or pix_fmt != "yuv420p":
            return False, f"Bug detectado (duracao={duracao:.1f}s, cor={pix_fmt})", 0
        score = 80
        if 60 <= duracao <= 78:
            score += 18
        elif 480 <= duracao <= 960:
            score += 20
        return True, "Aprovado sem bugs", score
    except Exception as e:
        return False, f"Arquivo corrompido: {e}", 0

def executar_curadoria():
    videos = glob.glob("exportacao/*.mp4")
    aprovados = []
    bugs_removidos = 0
    for v in videos:
        ok, motivo, nota = auditar_video(v)
        if not ok:
            try:
                os.remove(v)
                bugs_removidos += 1
            except Exception:
                pass
        else:
            aprovados.append({"arquivo": os.path.basename(v), "caminho": v, "nota": nota, "tipo": "longo" if "resumo" in v.lower() or "parte" in v.lower() else "short"})
    aprovados.sort(key=lambda x: x["nota"], reverse=True)
    top6 = aprovados[:6]
    relatorio = {
        "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "total_fila_24": len(aprovados),
        "bugs_bloqueados": bugs_removidos,
        "top6_gerencia": top6,
        "pauta_reuniao": f"Curadoria auditou {len(videos)} videos, bloqueou {bugs_removidos} com bugs e ranqueou o Top {len(top6)} do dia para o Gerente."
    }
    with open("ranking_curadoria.json", "w", encoding="utf-8") as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False)
    print("CURADORIA CONCLUIDA:", relatorio["pauta_reuniao"])

if __name__ == "__main__":
    executar_curadoria()
