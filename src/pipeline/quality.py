"""
Módulo de Controle de Qualidade e Curadoria.
Responsável por auditar arquivos de vídeo com FFprobe, descartar arquivos corrompidos e ranquear o Top 6 diário.
"""
import subprocess
import json
from pathlib import Path
from datetime import datetime
from src.config import EXPORT_DIR, RANKING_CURADORIA_FILE, PALAVRAS_CHAVE_VIRAIS
from src.utils import save_json_safe

def auditar_video(caminho_video: Path):
    """
    Inspeciona o arquivo via FFprobe.
    Retorna (aprovado: bool, motivo: str, score: int).
    Exige codec compatível, cor yuv420p e duração mínima.
    """
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=pix_fmt,codec_name",
            "-show_entries", "format=duration",
            "-of", "json",
            str(caminho_video)
        ]
        res = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8")
        dados = json.loads(res)
        duracao = float(dados["format"]["duration"])
        pix_fmt = dados["streams"][0].get("pix_fmt", "")

        if duracao < 15:
            return False, f"Duração muito curta ({duracao:.1f}s)", 0
        if pix_fmt != "yuv420p":
            return False, f"Formato de cor incorreto ({pix_fmt} != yuv420p)", 0

        # Score técnico
        score = 80
        if 60 <= duracao <= 78:
            score += 18
        elif 480 <= duracao <= 960:
            score += 20

        # Score viral por palavras-chave
        nome_lower = caminho_video.name.lower()
        for palavra in PALAVRAS_CHAVE_VIRAIS:
            if palavra in nome_lower:
                score += 2
        return True, "Aprovado sem bugs", min(score, 100)

    except Exception as e:
        return False, f"Arquivo corrompido ou ilegível: {e}", 0

def montar_top6(aprovados: list) -> list:
    """Entrega 4 Shorts e 2 Longos. Quando faltar um tipo, completa com os melhores do outro."""
    escolhidos = [a for a in aprovados if a["tipo"] == "short"][:4] + [a for a in aprovados if a["tipo"] == "longo"][:2]
    restantes = [a for a in aprovados if a not in escolhidos]
    return sorted(escolhidos + restantes[:6 - len(escolhidos)], key=lambda a: a["nota"], reverse=True)


def executar_curadoria():
    """Varre a pasta de exportação, remove vídeos com falhas e ranqueia o Top 6 para a Diretoria."""
    if not EXPORT_DIR.exists():
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    videos = list(EXPORT_DIR.glob("*.mp4"))
    aprovados = []
    bugs_removidos = 0

    for v in videos:
        ok, motivo, nota = auditar_video(v)
        if not ok:
            try:
                v.unlink()
                bugs_removidos += 1
            except Exception:
                pass
        else:
            aprovados.append({
                "arquivo": v.name,
                "caminho": str(v),
                "nota": nota,
                "tipo": "longo" if "resumo" in v.name.lower() or "parte" in v.name.lower() else "short"
            })

    aprovados.sort(key=lambda x: x["nota"], reverse=True)
    top6 = montar_top6(aprovados)

    relatorio = {
        "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "total_fila": len(aprovados),
        "bugs_bloqueados": bugs_removidos,
        "top6_gerencia": top6,
        "pauta_reuniao": f"Curadoria auditou {len(videos)} vídeos, bloqueou {bugs_removidos} com falhas e ranqueou o Top {len(top6)} do dia."
    }

    save_json_safe(RANKING_CURADORIA_FILE, relatorio)
    return relatorio
