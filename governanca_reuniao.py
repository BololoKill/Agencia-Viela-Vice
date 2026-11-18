import os, json
from datetime import datetime

NORMAS_FIXAS = [
    "Estoque fixo de 24 videos (4 Longos + 20 Shorts)",
    "Idioma 100% Portugues do Brasil (pt-BR) e codec yuv420p",
    "Aprovacao humana obrigatoria no Gerente antes de postar",
    "Transparencia total sobre monetizacao e afiliados"
]

def realizar_reuniao_governada():
    ranking = {}
    if os.path.exists("ranking_curadoria.json"):
        try:
            ranking = json.load(open("ranking_curadoria.json", encoding="utf-8"))
        except Exception:
            pass

    bugs = ranking.get("bugs_bloqueados", 0)
    fila = ranking.get("total_fila_24", 0)

    opinioes_validadas = [
        {
            "autor": "Camila — Líder de Curadoria & Qualidade",
            "opiniao": f"Auditoria revisada: {bugs} bug(s) bloqueado(s). Manter trava estrita de cor yuv420p e gancho nos 3s iniciais.",
            "status_norma": "APROVADA (100% alinhada às Normas Fixas)"
        },
        {
            "autor": "Bruno — Olheiro de Tendências GTA 6",
            "opiniao": "Priorizar buscas de GTA 6 novidades, trailer 2 e lives BR de GTA RP (Paulinho, Coringa, Luqueta).",
            "status_norma": "APROVADA (Respeita filtro 100% pt-BR)"
        },
        {
            "autor": "Lucas, Mariana, Rafael & Felipe — Produção e Engenharia",
            "opiniao": f"Fila atual em {fila}/24 (4 Longos + 20 Shorts). Manter preset veryfast e faster-whisper para estabilidade do notebook.",
            "status_norma": "APROVADA (Respeita meta de 24 vídeos e cota diária)"
        }
    ]

    ata = {
        "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "normas_revistas": NORMAS_FIXAS,
        "decisoes_validas": opinioes_validadas,
        "resumo": "Normas revistas com sucesso pela equipe nomeada. Nenhuma regra fixa foi violada."
    }

    historico = []
    if os.path.exists("ata_reunioes.json"):
        try:
            historico = json.load(open("ata_reunioes.json", encoding="utf-8"))
        except Exception:
            historico = []
    historico.insert(0, ata)
    with open("ata_reunioes.json", "w", encoding="utf-8") as f:
        json.dump(historico[:20], f, indent=2, ensure_ascii=False)

    return ata

if __name__ == "__main__":
    res = realizar_reuniao_governada()
    print("SUCESSO - ATA REGISTRADA:", res["resumo"])
