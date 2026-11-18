"""
Ponto de Entrada Principal (CLI) da Agência Viela Vice.

Uso:
  python main.py server      # Inicia o Escritório Virtual (Flask) na porta 8501
  python main.py worker      # Inicia o Robô Vigia de Lives (Produção contínua)
  python main.py run         # Inicia Servidor + Robô simultaneamente
  python main.py curadoria   # Executa auditoria técnica imediata da pasta de exportação
  python main.py reuniao     # Registra ata formal de governança
"""
import sys
import argparse
import threading
from src.web.app import iniciar_servidor
from src.pipeline.worker import loop_vigia_continuo
from src.pipeline.quality import executar_curadoria
from src.governance.meetings import realizar_reuniao_governada

def main():
    parser = argparse.ArgumentParser(description="Agência Viela Vice - Operação Autônoma")
    parser.add_argument("comando", choices=["server", "worker", "run", "curadoria", "reuniao"],
                        help="Ação a ser executada")
    parser.add_argument("--port", type=int, default=8501, help="Porta para o servidor web (padrão: 8501)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host para o servidor web (padrão: 0.0.0.0)")

    args = parser.parse_args()

    if args.comando == "server":
        print(f"🎬 Iniciando Escritório Virtual da Agência Viela Vice em http://localhost:{args.port}...")
        iniciar_servidor(host=args.host, port=args.port)

    elif args.comando == "worker":
        print("🤖 Iniciando Robô Vigia de Produção Contínua...")
        loop_vigia_continuo()

    elif args.comando == "run":
        print("🚀 Inicializando Sistema Completo: Escritório Virtual + Robô Vigia...")
        t_worker = threading.Thread(target=loop_vigia_continuo, daemon=True)
        t_worker.start()
        iniciar_servidor(host=args.host, port=args.port)

    elif args.comando == "curadoria":
        print("🛡️ Executando Auditoria Técnica e Curadoria da Fila...")
        rel = executar_curadoria()
        print(f"✅ Concluído: {rel.get('pauta_reuniao')}")

    elif args.comando == "reuniao":
        print("🤝 Realizando Reunião Executiva de Governança...")
        ata = realizar_reuniao_governada()
        print(f"✅ Ata registrada: {ata.get('resumo')}")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Se chamado sem argumentos, executa o modo completo (run)
        sys.argv.append("run")
    main()
