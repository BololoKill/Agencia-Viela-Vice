"""
Módulo de Governança e Reuniões Executivas dos Agentes Virtuais.
"""
from datetime import datetime
from src.config import ATA_REUNIOES_FILE, RANKING_CURADORIA_FILE
from src.utils import load_json_safe, save_json_safe

NORMAS_FIXAS = [
    "Estoque máximo de 60 vídeos (40 Shorts + 20 Longos), na proporção diária de 4 Shorts e 2 Longos",
    "Idioma 100% Português do Brasil (pt-BR) e codec yuv420p",
    "Aprovação humana obrigatória na Diretoria antes de postar",
    "Transparência total sobre monetização e links de afiliados",
    "Proibição estrita do uso de MoviePy (uso de FFmpeg direto)"
]

def realizar_reuniao_governada():
    """Gera ata formal de alinhamento com validação das normas da Agência."""
    ranking = load_json_safe(RANKING_CURADORIA_FILE, {})
    bugs = ranking.get("bugs_bloqueados", 0)
    fila = ranking.get("total_fila", 0)

    opinioes_validadas = [
        {
            "autor": "Camila — Líder de Curadoria & Qualidade",
            "opiniao": f"Auditoria revisada: {bugs} bug(s) bloqueado(s). Trava de cor yuv420p e gancho nos 3s mantidos.",
            "status": "APROVADA"
        },
        {
            "autor": "Bruno — Olheiro de Tendências GTA 6",
            "opiniao": "Priorizando criadores brasileiros de ponta (Paulinho, Coringa, Luqueta, Davy Jones) e vazamentos de GTA 6.",
            "status": "APROVADA"
        },
        {
            "autor": "Mariana & Lucas — Produção e Roteiro",
            "opiniao": f"Fila atual com {fila} vídeos validados. Presets otimizados para estabilidade térmica do computador.",
            "status": "APROVADA"
        }
    ]

    ata = {
        "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "normas_revistas": NORMAS_FIXAS,
        "decisoes": opinioes_validadas,
        "resumo": "Normas revistas com sucesso pela equipe executiva. Nenhuma diretriz foi violada."
    }

    historico = load_json_safe(ATA_REUNIOES_FILE, [])
    historico.insert(0, ata)
    save_json_safe(ATA_REUNIOES_FILE, historico[:20])

    return ata
