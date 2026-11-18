import os
import time
import subprocess
import threading

def rodar_motor_triagem():
    while True:
        try:
            # Roda o robô de triagem a cada 5 minutos em segundo plano
            print("[MOTOR AGÊNCIA] Executando varredura e triagem automática de cortes...")
            subprocess.run(["python", "robo_cortes.py"], capture_output=True, text=True)
        except Exception as e:
            print(f"[ERRO NO MOTOR] {e}")
        time.sleep(300) # 5 minutos

if __name__ == "__main__":
    print("=== INICIALIZANDO AGÊNCIA VIELA VICE (MODO TOTALMENTE AUTOMÁTICO) ===")
    
    # Inicia a thread de triagem automática
    t = threading.Thread(target=rodar_motor_triagem, daemon=True)
    t.start()
    
    # Inicia o Servidor Flask principal
    subprocess.run(["python", "servidor_agencia.py"])
