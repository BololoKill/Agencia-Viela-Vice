"""
Ponto de Entrada Principal (CLI) da Agência Viela Vice.

Uso:
  python main.py server      # Inicia o Escritório Virtual (Flask) na porta 8501
  python main.py worker      # Inicia o Robô Vigia de Lives (Produção contínua)
  python main.py run         # Inicia Servidor + Robô simultaneamente
  python main.py curadoria   # Executa auditoria técnica imediata da pasta de exportação
  python main.py reuniao     # Registra ata formal de governança
  python main.py purge       # Limpa arquivos temporários da produção
"""
import sys
import argparse
import threading
from src.web.app import iniciar_servidor, porta_em_uso
from src.pipeline.estado import ciclo_em_andamento
from src.pipeline.worker import loop_vigia_continuo, limpar_video_bruto
from src.pipeline.quality import executar_curadoria
from src.governance.meetings import realizar_reuniao_governada
from src.youtube.cota import iniciar_monitor_cotas

CODIGO_JA_EM_EXECUCAO = 3


def main():
    parser = argparse.ArgumentParser(description="Agência Viela Vice - Operação Autônoma")
    parser.add_argument("comando", choices=["server", "worker", "run", "curadoria", "reuniao", "purge"],
                        help="Ação a ser executada")
    parser.add_argument("--port", type=int, default=8501, help="Porta para o servidor web (padrão: 8501)")
    parser.add_argument("--host", type=str, default="127.0.0.1",
                        help="Host do servidor web (padrão: 127.0.0.1, acessível só neste computador)")

    args = parser.parse_args()

    if args.comando in ("server", "run") and porta_em_uso(args.port):
        print(f"⚠️ A Agência já está rodando em http://localhost:{args.port}. Nada foi iniciado.")
        return CODIGO_JA_EM_EXECUCAO

    if args.comando == "server":
        print(f"🎬 Iniciando Escritório Virtual da Agência Viela Vice em http://localhost:{args.port}...")
        iniciar_monitor_cotas()
        iniciar_servidor(host=args.host, port=args.port)

    elif args.comando == "worker":
        print("🤖 Iniciando Robô Vigia de Produção Contínua...")
        loop_vigia_continuo()

    elif args.comando == "run":
        print("🚀 Inicializando Sistema Completo: Escritório Virtual + Robô Vigia...")
        t_worker = threading.Thread(target=loop_vigia_continuo, daemon=True)
        t_worker.start()
        iniciar_monitor_cotas()
        iniciar_servidor(host=args.host, port=args.port)

    elif args.comando == "curadoria":
        print("🛡️ Executando Auditoria Técnica e Curadoria da Fila...")
        rel = executar_curadoria()
        print(f"✅ Concluído: {rel.get('pauta_reuniao')}")

    elif args.comando == "reuniao":
        print("🤝 Realizando Reunião Executiva de Governança...")
        ata = realizar_reuniao_governada()
        print(f"✅ Ata registrada: {ata.get('resumo')}")

    elif args.comando == "purge":
        if ciclo_em_andamento():
            print("⚠️ Produção em andamento. Limpeza cancelada para não apagar arquivos em uso.")
            return 1
        limpar_video_bruto()
        print("✅ Arquivos temporários removidos.")

    return 0


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Se chamado sem argumentos, executa o modo completo (run)
        sys.argv.append("run")
    sys.exit(main())
