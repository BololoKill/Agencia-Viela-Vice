"""
Utilitários de suporte ao pipeline e gerenciamento de dados.
"""
import os
import json
import re
from datetime import datetime
from pathlib import Path

def load_json_safe(filepath, default_val):
    """Lê um arquivo JSON de forma segura sem quebrar por concorrência ou formato."""
    p = Path(filepath)
    if not p.exists():
        return default_val
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_val

def save_json_safe(filepath, data):
    """Salva dados em formato JSON com UTF-8 e indentação."""
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[ERRO JSON] Falha ao salvar {filepath}: {e}")
        return False

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

def log_terminal(mensagem: str, log_file: Path = None):
    """Registra uma mensagem formatada no console e em arquivo de log."""
    agora = datetime.now().strftime("%H:%M:%S")
    linha = f"[{agora}] {mensagem}"
    print(linha, flush=True)
    if log_file:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(linha + "\n")
        except Exception:
            pass
