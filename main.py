"""
Ponto de Entrada Principal (CLI) da Agência Viela Vice.

Uso:
  python main.py server      # Inicia o painel da agência (Flask) na porta 8501
  python main.py worker      # Inicia o robô de produção (vídeos virais de GTA 6)
  python main.py run         # Inicia painel + robô juntos
  python main.py curadoria   # Executa a auditoria técnica dos vídeos prontos
  python main.py purge       # Limpa arquivos temporários da produção
"""
import sys
import argparse
import threading
import psutil
from src.web.app import iniciar_servidor, porta_em_uso
from src.pipeline.estado import ciclo_em_andamento
from src.pipeline.worker import loop_vigia_continuo, limpar_video_bruto
from src.pipeline.quality import executar_curadoria
from src.youtube.cota import iniciar_monitor_cotas

CODIGO_JA_EM_EXECUCAO = 3


# Abaixo do normal: a produção usa todo o processador livre, mas o Windows atende primeiro os programas do usuário.
# Os processos do FFmpeg e do Whisper herdam essa prioridade. Nada muda na qualidade dos vídeos.
PRIORIDADE_PRODUCAO = getattr(psutil, "BELOW_NORMAL_PRIORITY_CLASS", 10)


def reduzir_prioridade():
    try:
        psutil.Process().nice(PRIORIDADE_PRODUCAO)
    except (OSError, psutil.Error):
        pass


def main():
    parser = argparse.ArgumentParser(description="Agência Viela Vice - Operação Autônoma")
    parser.add_argument("comando", choices=["server", "worker", "run", "curadoria", "purge"],
                        help="Ação a ser executada")
    parser.add_argument("--port", type=int, default=8501, help="Porta para o servidor web (padrão: 8501)")
    parser.add_argument("--host", type=str, default="127.0.0.1",
                        help="Host do servidor web (padrão: 127.0.0.1, acessível só neste computador)")

    args = parser.parse_args()

    if args.comando in ("server", "run") and porta_em_uso(args.port):
        print(f"⚠️ A Agência já está rodando em http://localhost:{args.port}. Nada foi iniciado.")
        return CODIGO_JA_EM_EXECUCAO

    if args.comando == "server":
        print(f"🎬 Iniciando o painel da Agência Viela Vice em http://localhost:{args.port}...")
        iniciar_monitor_cotas()
        iniciar_servidor(host=args.host, port=args.port)

    elif args.comando == "worker":
        reduzir_prioridade()
        print("🤖 Iniciando o robô de produção dos vídeos virais...")
        loop_vigia_continuo()

    elif args.comando == "run":
        reduzir_prioridade()
        print("🚀 Inicializando a agência completa: painel + robô de produção...")
        t_worker = threading.Thread(target=loop_vigia_continuo, daemon=True)
        t_worker.start()
        iniciar_monitor_cotas()
        iniciar_servidor(host=args.host, port=args.port)

    elif args.comando == "curadoria":
        print("🛡️ Executando a auditoria técnica dos vídeos prontos...")
        rel = executar_curadoria()
        print(f"✅ Concluído: {rel.get('pauta_reuniao')}")

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
