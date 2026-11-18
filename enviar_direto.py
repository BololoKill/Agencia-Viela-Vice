import googleapiclient.discovery, googleapiclient.http, os
from google.oauth2.credentials import Credentials

creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/youtube.upload"])
yt = googleapiclient.discovery.build("youtube", "v3", credentials=creds)

caminho = "exportacao/short-paulinhooloko-corte1-977.mp4"
if os.path.exists(caminho):
    print("🚀 Enviando Short do Paulinho o Loko...")
    body = {
        "snippet": {
            "title": "Ninguém esperava essa reação do Paulinho o Loko! #GTARP #Shorts",
            "description": "Melhores momentos de Paulinho o Loko no GTA RP Brasil enquanto aquecemos os motores para o lançamento do GTA 6! Curta o vídeo e inscreva-se no canal Viela Vice (@VielaVice) para clipes diários dos maiores streamers do Brasil. #GTARP #GTA6 #GTAFI #VielaVice #Paulinhooloko #Shorts",
            "tags": ["GTARP", "GTA6", "GTAFI", "VielaVice", "Paulinhooloko", "Shorts"],
            "categoryId": "20"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }
    media = googleapiclient.http.MediaFileUpload(caminho, chunksize=-1, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    res = None
    while res is None:
        status, res = req.next_chunk()
        if status:
            print(f"⏳ Progresso: {int(status.progress() * 100)}%")
    vid_id = res.get("id")
    print(f"✅ Enviado com sucesso! ID do vídeo: {vid_id}")
else:
    print("❌ Arquivo não encontrado na pasta exportacao.")
