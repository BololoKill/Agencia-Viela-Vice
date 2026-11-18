import os
import glob
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]

CANAIS_TOKENS = {
    "1. Principal (GTA 6)": "token.json",
    "2. Polícia & Fugas": "token_policia.json",
    "3. Memes & Zoeira": "token_memes.json",
    "4. Stories": "token_stories.json",
    "5. Underground": "token_underground.json",
    "6. News": "token_news.json",
    "7. Best Moments": "token_best.json"
}

def encontrar_arquivo_cliente():
    # Procura arquivos padrão de credenciais do Google na pasta
    possiveis = glob.glob("client*.json") + glob.glob("credentials*.json")
    return possiveis[0] if possiveis else None

def gerar_tokens():
    client_file = encontrar_arquivo_cliente()
    if not client_file:
        print("[ERRO] Nenhum arquivo 'client_secret.json' ou 'credentials.json' foi encontrado na pasta!")
        print("Certifique-se de que o arquivo JSON de credenciais do Google Cloud está na pasta do projeto.")
        return

    print(f"[OK] Usando arquivo de credenciais: {client_file}")
    print("=== AUTORIZAÇÃO DA REDE DE 7 CANAIS (MODO SEGURO) ===")
    
    for nome, token_file in CANAIS_TOKENS.items():
        print(f"\n--- Configurando canal: {nome} ({token_file}) ---")
        if os.path.exists(token_file):
            print(f"O arquivo {token_file} já existe. Pulando para o próximo...")
            continue
        
        print(f"ATENÇÃO: Quando o navegador abrir, selecione a conta exata do canal [{nome}].")
        input("Pressione ENTER para abrir a autenticação deste canal...")
        try:
            flow = InstalledAppFlow.from_client_secrets_file(client_file, SCOPES)
            creds = flow.run_local_server(port=0, prompt='select_account')
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
            print(f"Sucesso! Token salvo em {token_file}")
        except Exception as e:
            print(f"Erro ao autenticar {nome}: {e}")

if __name__ == "__main__":
    gerar_tokens()
