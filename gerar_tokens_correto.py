import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]

# Procura qualquer variação do arquivo client_secret na pasta
client_file = None
for f in os.listdir("."):
    if f.startswith("client_secret") and f.endswith(".json"):
        client_file = f
        break

channels = {
    "canal_principal": "token.json",
    "canal_policia": "token_policia.json",
    "canal_memes": "token_memes.json",
    "canal_stories": "token_stories.json",
    "canal_underground": "token_underground.json",
    "canal_news": "token_news.json",
    "canal_best": "token_best.json"
}

print("=== GERADOR DE TOKENS DA REDE VIELA VICE ===")
if not client_file:
    print("[ERRO] Arquivo de credenciais client_secret*.json não encontrado na pasta!")
else:
    print(f"[OK] Usando arquivo de credenciais: {client_file}")
    for key, token_file in channels.items():
        print(f"\n-> Gerando token para: {key} ({token_file})")
        input(f"Pressione ENTER para abrir o navegador e selecione a conta/canal correta para '{key}'...")
        
        flow = InstalledAppFlow.from_client_secrets_file(client_file, SCOPES)
        creds = flow.run_local_server(port=0)
        
        with open(token_file, 'w', encoding='utf-8') as token:
            token.write(creds.to_json())
        print(f"[SUCESSO] Token salvo em {token_file}")

    print("\n🎉 Todos os tokens da rede foram gerados e vinculados com sucesso!")
