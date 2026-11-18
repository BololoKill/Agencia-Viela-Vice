"""
Utilitários de suporte ao pipeline: persistência atômica, log de produção e censura.
"""
import os
import json
import re
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE_PADRAO = BASE_DIR / "log_producao.txt"
LIMITE_BYTES_LOG = 256 * 1024
MAX_LINHAS_LOG = 400

_trava_log = threading.Lock()
_PADRAO_SEGREDO = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|token|secret|password|senha|signature|sig)=([^&\s\"']+)"
)


def load_json_safe(filepath, default_val):
    """Lê um JSON sem quebrar por concorrência ou formato inválido."""
    p = Path(filepath)
    for tentativa in range(4):
        if not p.exists():
            return default_val
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except PermissionError:
            # No Windows o arquivo fica bloqueado por instantes durante a troca atômica.
            time.sleep(0.02 * (tentativa + 1))
        except Exception:
            return default_val
    return default_val


def save_json_safe(filepath, data):
    """Salva JSON de forma atômica: quem lê nunca encontra um arquivo pela metade."""
    p = Path(filepath)
    tmp = p.with_name(f"{p.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        for tentativa in range(10):
            try:
                os.replace(tmp, p)
                return True
            except PermissionError:
                if tentativa == 9:
                    raise
                time.sleep(0.02 * (tentativa + 1))
        return False
    except Exception as e:
        _escrever_console(f"[ERRO JSON] Falha ao salvar {p.name}: {e}")
        return False
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def censor_text(text: str) -> str:
    """Substitui profanidades e palavras sensíveis por asteriscos para conformidade com o YouTube."""
    if not text:
        return ""
    profanities = {
        r"\bporra\b": "p***a",
        r"\bcaralho\b": "c*****o",
        r"\bmerda\b": "m***a",
        r"\bputa\b": "p***a",
        r"\bviado\b": "v***o",
        r"\bfdp\b": "f**",
        r"\bdesgraça\b": "d******a",
        r"\bcacete\b": "c*****e",
        r"\bfuck\b": "f***",
        r"\bshit\b": "s***",
        r"\bcu\b": "c*",
        r"\barrombado\b": "a********o"
    }
    for pattern, replacement in profanities.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _escrever_console(linha: str):
    """Console sem suporte a emoji nunca pode interromper a produção."""
    try:
        print(linha, flush=True)
    except Exception:
        pass


def _higienizar_mensagem(mensagem) -> str:
    """Mantém cada evento em uma linha e remove credenciais antes de exibir no painel."""
    texto = " ".join(str(mensagem).replace("\x00", "").split())
    return _PADRAO_SEGREDO.sub(lambda m: f"{m.group(1)}=***", texto)


def _rotacionar_log(alvo: Path):
    """Mantém apenas as linhas recentes quando o arquivo atinge o limite."""
    with open(alvo, "r", encoding="utf-8", errors="replace") as f:
        recentes = list(deque(f, maxlen=MAX_LINHAS_LOG))
    tmp = alvo.with_name(f"{alvo.name}.{os.getpid()}.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.writelines(recentes)
    os.replace(tmp, alvo)


def log_terminal(mensagem: str, log_file: Path = None):
    """Registra o evento no console e no log consumido pelo painel, sem nunca lançar exceção."""
    alvo = Path(log_file) if log_file else LOG_FILE_PADRAO
    linha = f"[{datetime.now().strftime('%H:%M:%S')}] {_higienizar_mensagem(mensagem)}"
    _escrever_console(linha)

    with _trava_log:
        try:
            with open(alvo, "a", encoding="utf-8") as f:
                f.write(linha + "\n")
            if alvo.stat().st_size > LIMITE_BYTES_LOG:
                _rotacionar_log(alvo)
        except OSError:
            pass


def ler_ultimas_linhas(quantidade: int = 60, log_file: Path = None) -> list:
    """Retorna as últimas linhas do log de produção, tolerando arquivo ausente ou danificado."""
    alvo = Path(log_file) if log_file else LOG_FILE_PADRAO
    try:
        with open(alvo, "r", encoding="utf-8", errors="replace") as f:
            ultimas = deque(f, maxlen=quantidade)
    except OSError:
        return []
    return [linha.replace("\x00", "").rstrip("\r\n") for linha in ultimas if linha.strip()]
