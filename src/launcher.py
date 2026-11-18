"""
Módulo do Launcher Interativo da Agência Viela Vice.
Fornece interface em terminal estilizada com ASCII art, menu numérico simples e automação de abertura de navegador.
"""
import sys
import os
import socket
import time
import webbrowser
import subprocess
from pathlib import Path

# Cores ANSI para ambientação neon Vice City
MAGENTA = "\033[95m"
CIANO = "\033[96m"
VERDE = "\033[92m"
AMARELO = "\033[93m"
VERMELHO = "\033[91m"
NEGRITO = "\033[1m"
RESET = "\033[0m"

def formatar_cabecalho_branding() -> str:
    """Gera o cabeçalho estilizado da Agência Viela Vice para o terminal."""
    arte = f"""
{MAGENTA}{NEGRITO}========================================================================{RESET}
{CIANO}{NEGRITO}   ██╗   ██╗██╗███████╗██╗      █████╗     ██╗   ██╗██╗ ██████╗███████╗
   ██║   ██║██║██╔════╝██║     ██╔══██╗    ██║   ██║██║██╔════╝██╔════╝
   ██║   ██║██║█████╗  ██║     ███████║    ██║   ██║██║██║     █████╗  
   ╚██╗ ██╔╝██║██╔══╝  ██║     ██╔══██║    ╚██╗ ██╔╝██║██║     ██╔══╝  
    ╚████╔╝ ██║███████╗███████╗██║  ██║     ╚████╔╝ ██║╚██████╗███████╗
     ╚═══╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝      ╚═══╝  ╚═╝ ╚═════╝╚══════╝{RESET}
{MAGENTA}{NEGRITO}                 ★ AGENCIA VIELA VICE — SISTEMA 6 ESTRELAS ★{RESET}
{AMARELO}    Diretor: Dr. Ricardo | Curadoria: Camila | Olheiro GTA 6: Bruno{RESET}
{MAGENTA}========================================================================{RESET}
"""
    return arte

def obter_menu_opcoes() -> dict:
    """Retorna as opções disponíveis no menu do launcher."""
    return {
        "1": {"titulo": "🚀 Iniciar Sistema Completo (Escritório + Robô Vigia) [RECOMENDADO]", "cmd": "run"},
        "2": {"titulo": "🏢 Iniciar Apenas Escritório Virtual (Dashboard Web)", "cmd": "server"},
        "3": {"titulo": "🤖 Iniciar Apenas Robô Vigia (Cortes e Produção)", "cmd": "worker"},
        "4": {"titulo": "🛡️ Executar Curadoria Técnica da Fila (Top 6)", "cmd": "curadoria"},
        "5": {"titulo": "🧹 Suporte T.I.: Limpeza de Temporários e Purga", "cmd": "purge"},
        "6": {"titulo": "🤝 Realizar Reunião Executiva de Governança", "cmd": "reuniao"},
        "0": {"titulo": "❌ Encerrar e Sair", "cmd": "exit"}
    }

def mapear_comando_opcao(opcao: str) -> str:
    """Mapeia a tecla de opção digitada para o comando correspondente."""
    opcoes = obter_menu_opcoes()
    if opcao in opcoes:
        return opcoes[opcao]["cmd"]
    return None

def verificar_porta_ocupada(host: str = "127.0.0.1", port: int = 8501) -> bool:
    """Verifica se a porta especificada está em uso por algum processo."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        resultado = s.connect_ex((host, port))
        return resultado == 0

def aguardar_e_abrir_navegador(url: str = "http://localhost:8501", max_tentativas: int = 15):
    """Aguarda o servidor web iniciar e abre automaticamente no navegador padrão."""
    for _ in range(max_tentativas):
        if verificar_porta_ocupada("127.0.0.1", 8501):
            time.sleep(0.5)
            webbrowser.open(url)
            return True
        time.sleep(0.5)
    return False

def exibir_menu_interativo():
    """Loop principal de interação com o usuário."""
    # Habilita cores ANSI no console do Windows se suportado
    if os.name == 'nt':
        os.system('')

    base_dir = Path(__file__).resolve().parent.parent

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(formatar_cabecalho_branding())

        status_porta = verificar_porta_ocupada("127.0.0.1", 8501)
        if status_porta:
            print(f" {VERDE}● PAINEL ONLINE:{RESET} http://localhost:8501 (Servidor ativo)")
        else:
            print(f" {AMARELO}○ PAINEL OFFLINE:{RESET} Servidor parado na porta 8501")
        print()

        print(f"{CIANO}{NEGRITO}Selecione o que deseja fazer:{RESET}\n")
        opcoes = obter_menu_opcoes()
        for k, v in opcoes.items():
            cor = VERDE if k == "1" else (VERMELHO if k == "0" else CIANO)
            print(f"  {cor}[{k}]{RESET} {v['titulo']}")

        print(f"\n{MAGENTA}------------------------------------------------------------------------{RESET}")
        escolha = input(f"{AMARELO}Digite o número da opção (0-6): {RESET}").strip()

        cmd = mapear_comando_opcao(escolha)
        if not cmd:
            print(f"\n{VERMELHO}Opção inválida! Escolha um número de 0 a 6.{RESET}")
            time.sleep(1.5)
            continue

        if cmd == "exit":
            print(f"\n{CIANO}Até logo, Chefe! Dr. Ricardo e a equipe estão em stand-by.{RESET}\n")
            break

        elif cmd == "purge":
            print(f"\n{AMARELO}Executando limpeza de arquivos temporários do T.I...{RESET}")
            subprocess.run([sys.executable, str(base_dir / "main.py"), "purge"], cwd=str(base_dir))
            time.sleep(2)

        elif cmd in ("run", "server") and status_porta:
            print(f"\n{VERDE}A Agência já está rodando. Abrindo o painel no navegador...{RESET}")
            webbrowser.open("http://localhost:8501")
            time.sleep(2)

        elif cmd in ("run", "server"):
            print(f"\n{VERDE}Iniciando a Agência Viela Vice no modo '{cmd}'...{RESET}")
            print(f"{CIANO}O navegador será aberto automaticamente assim que o painel carregar.{RESET}\n")

            import threading
            threading.Thread(target=aguardar_e_abrir_navegador, daemon=True).start()

            # Executa o comando via main.py
            subprocess.run([sys.executable, str(base_dir / "main.py"), cmd])
            break

        elif cmd in ("worker", "curadoria", "reuniao"):
            print(f"\n{VERDE}Executando comando '{cmd}'...{RESET}\n")
            subprocess.run([sys.executable, str(base_dir / "main.py"), cmd])
            print(f"\n{CIANO}Pressione ENTER para voltar ao menu principal...{RESET}")
            input()

if __name__ == "__main__":
    exibir_menu_interativo()
