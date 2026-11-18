"""
Módulo de Autenticação e Gestão de Canais do YouTube via OAuth 2.0.
A autorização inicial dos canais é feita fora do servidor, com gerar_tokens_correto.py.
"""
import json
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from src.config import BASE_DIR, CANAIS_VIELA_VICE
from src.utils import save_json_safe

# Precisa acompanhar as permissões concedidas em gerar_tokens_correto.py.
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]

ORIENTACAO_REAUTORIZAR = "Autorize novamente executando: python gerar_tokens_correto.py"


class CredencialYouTubeError(RuntimeError):
    """A autorização do canal não pode ser usada e precisa ser refeita."""


def obter_credenciais(canal_id: str = "1"):
    """
    Recupera e renova o token do canal (1 a 7) usando as permissões já autorizadas nele.
    Retorna None quando o canal ainda não foi autorizado.
    """
    canal_info = CANAIS_VIELA_VICE.get(str(canal_id), CANAIS_VIELA_VICE["1"])
    nome_canal = canal_info.get("nome", "Viela Vice")
    token_path = BASE_DIR / canal_info.get("token", "token.json")

    if not token_path.exists():
        return None

    try:
        creds = Credentials.from_authorized_user_file(str(token_path))
    except (ValueError, OSError) as e:
        raise CredencialYouTubeError(f"Token do canal {nome_canal} está inválido. {ORIENTACAO_REAUTORIZAR}") from e

    if creds.valid:
        return creds
    if not creds.refresh_token:
        raise CredencialYouTubeError(f"Token do canal {nome_canal} não pode ser renovado. {ORIENTACAO_REAUTORIZAR}")

    try:
        creds.refresh(Request())
    except RefreshError as e:
        raise CredencialYouTubeError(f"Google recusou a autorização do canal {nome_canal}. {ORIENTACAO_REAUTORIZAR}") from e

    save_json_safe(token_path, json.loads(creds.to_json()))
    return creds
