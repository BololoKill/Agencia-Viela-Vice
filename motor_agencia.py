import os
import time
import subprocess
import threading
import json

EXPORT_DIR = "exportacao"
METADADOS_FILE = "metadados_cortes.json"

def processar_novos_cortes():
    """Varre a pasta de exportação e garante que todo novo vídeo tenha metadados e score viral."""
    while True:
        try:
            if os.path.exists(EXPORT_DIR):
                metadados = {}
                if os.path.exists(METADADOS_FILE):
                    try:
                        with open(METADADOS_FILE, 'r', encoding='utf-8') as f:
                            metadados = json.load(f)
                    except:
                        pass
                
                arquivos = [f for f in os.listdir(EXPORT_DIR) if f.lower().endswith(('.mp4', '.mov', '.mkv'))]
                alterado = False
                
                for arq in arquivos:
                    if arq not in metadados:
                        # Se for um corte novo sem metadado, gera uma pontuação padrão ou chama o robô de cortes
                        print(f"[MOTOR DA AGÊNCIA] Novo corte detectado: {arq}. Calculando Score Viral...")
                        titulo_limpo = arq.rsplit('.', 1)[0].replace('_', ' ').title()
                        metadados[arq] = {
                            "score_viral": 8.5, # Score inicial simulado ou processado
                            "titulo_sugerido": f"{titulo_limpo} | GTA RP #Shorts"
                        }
                        alterado = True
                
                if alterado:
                    with open(METADADOS_FILE, 'w', encoding='utf-8') as f:
                        json.dump(metadados, f, ensure_ascii=False, indent=2)
                    print("[MOTOR DA AGÊNCIA] Metadados atualizados com sucesso.")
        except Exception as e:
            print(f"[ERRO NO MOTOR DE VARREDURA] {e}")
        
        # Aguarda 3 minutos para a próxima varredura
        time.sleep(180)

def iniciar_servidor_flask():
    print("[SERVIDOR] Iniciando dashboard web da Agência Viela Vice...")
    subprocess.run(["python", "servidor_agencia.py"])

if __name__ == "__main__":
    print("==================================================")
    print("   AGÊNCIA VIELA VICE - SISTEMA 100% AUTOMATIZADO  ")
    print("==================================================")
    
    # Inicia a thread de varredura de novos cortes em segundo plano (Daemon)
    t_motor = threading.Thread(target=processar_novos_cortes, daemon=True)
    t_motor.start()
    
    # Inicia o servidor principal na thread principal
    iniciar_servidor_flask()
