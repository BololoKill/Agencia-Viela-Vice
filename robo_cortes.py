import os
import json
import re

BRUTOS_DIR = "brutos"
EXPORT_DIR = "exportacao"
METADADOS_FILE = "metadados_cortes.json"

PALAVRAS_CHAVE_VIRAIS = [
    "gta 6", "vazamento", "polícia", "fuga", "batedor", 
    "treta", "tiroteio", "surto", "mitou", "apagou", "ironia",
    "admin", "ban", "hospital", "apreendido"
]

def carregar_metadados():
    if not os.path.exists(METADADOS_FILE):
        return {}
    try:
        with open(METADADOS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def salvar_metadados(dados):
    with open(METADADOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def calcular_score_viral(nome_arquivo):
    score = 5.0
    nome_lower = nome_arquivo.lower()
    for palavra in PALAVRAS_CHAVE_VIRAIS:
        if palavra in nome_lower:
            score += 1.5
    if "clipe" in nome_lower or "viral" in nome_lower or "cortes" in nome_lower:
        score += 1.0
    return min(round(score, 1), 10.0)

def processar_fila_cortes():
    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)
    metadados = carregar_metadados()
    arquivos_atuais = [f for f in os.listdir(EXPORT_DIR) if f.lower().endswith(('.mp4', '.mov', '.mkv'))]
    
    atualizado = False
    for arquivo in arquivos_atuais:
        if arquivo not in metadados:
            score = calcular_score_viral(arquivo)
            metadados[arquivo] = {
                "arquivo": arquivo,
                "score_viral": score,
                "status": "pendente",
                "titulo_sugerido": arquivo.rsplit('.', 1)[0].replace('_', ' ').title() + " | GTA RP #Shorts"
            }
            atualizado = True
            print(f"[NOVO CORTE] {arquivo} | Score Viral: {score}")

    arquivos_removidos = [k for k in metadados if k not in arquivos_atuais]
    for k in arquivos_removidos:
        del metadados[k]
        atualizado = True

    if atualizado:
        salvar_metadados(metadados)
    return metadados

if __name__ == "__main__":
    print("Varredura e pontuação de cortes da Agência Viela Vice...")
    res = processar_fila_cortes()
    print(f"Total de vídeos gerenciados: {len(res)}")
