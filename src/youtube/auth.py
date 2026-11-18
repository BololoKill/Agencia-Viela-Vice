"""
Módulo de Autenticação e Gestão de Canais do YouTube via OAuth 2.0.
"""
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from src.config import BASE_DIR, CANAIS_VIELA_VICE

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]

def obter_credenciais(canal_id: str = "1") -> Credentials:
    """
    Recupera ou atualiza o token de autenticação do canal especificado (1 a 7).
    """
    canal_info = CANAIS_VIELA_VICE.get(str(canal_id), CANAIS_VIELA_VICE["1"])
    token_filename = canal_info.get("token", "token.json")
    token_path = BASE_DIR / token_filename
    client_secret_path = BASE_DIR / "client_secret.json"

    creds = None
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        elif client_secret_path.exists():
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
            creds = flow.run_local_server(port=8088, prompt="select_account")
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())

    return creds
