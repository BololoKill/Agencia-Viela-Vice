"""
Configurações centrais do sistema Agência Viela Vice.
Define parâmetros de produção, canais de publicação, streamers monitorados e regras de qualidade.
"""
import os
from pathlib import Path

# Diretório raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Diretórios de trabalho de mídia
EXPORT_DIR = BASE_DIR / "exportacao"
VIDEO_BRUTO_DIR = BASE_DIR / "video-bruto"
SPRITES_DIR = BASE_DIR / "sprites"
ASSETS_DIR = BASE_DIR / "assets"

# Arquivos de estado e persistência JSON
STATE_FILE = BASE_DIR / "painel_state.json"
AFILIADOS_FILE = BASE_DIR / "afiliados_config.json"
AGENDADOS_FILE = BASE_DIR / "agendados.json"
DESCARTADOS_FILE = BASE_DIR / "descartados.json"
MEMORIA_FILE = BASE_DIR / "memoria_agentes.json"
FINANCEIRO_FILE = BASE_DIR / "financeiro_agencia.json"
NOTICIAS_FILE = BASE_DIR / "noticias_gta6.json"
HISTORICO_FILE = BASE_DIR / "historico.txt"
DESCOBERTOS_PATH = BASE_DIR / "streamers_descobertos.json"
STATUS_VIGIA_FILE = BASE_DIR / "status_vigia.json"
RANKING_CURADORIA_FILE = BASE_DIR / "ranking_curadoria.json"
ATA_REUNIOES_FILE = BASE_DIR / "ata_reunioes.json"
METADADOS_FILE = BASE_DIR / "metadados_cortes.json"
TRAVA_CICLO_FILE = BASE_DIR / ".ciclo_producao.lock"
FALHAS_FILE = BASE_DIR / "falhas_pipeline.json"
CONTROLE_PRODUCAO_FILE = BASE_DIR / "controle_producao.json"
COTAS_FILE = BASE_DIR / "cotas_youtube.json"

# Limite de envios por canal em cada ciclo, que reinicia às 05:00 (as "6 estrelas" do painel)
COTA_DIARIA_CANAL = 6
HORA_REINICIO_COTA = 5

# Arquivos de assets fundamentais
CTA_AUDIO = EXPORT_DIR / "cta.mp3"
FONT_PATH = BASE_DIR / "arial.ttf"
IMAGE_PATH = BASE_DIR / "arte_original" / "novo_vice.png.jpeg"
MARCA_PATH = ASSETS_DIR / "marca_viela_vice.png"
WHOOSH_PATH = ASSETS_DIR / "whoosh.wav"

# Streamers Oficiais de GTA RP (Brasil)
STREAMERS_BR = [
    "LOUD Coringa",
    "Luqueta",
    "Paulinho o Loko",
    "Piozinho",
    "Gabi Peixe",
    "Biquinho",
    "Bagualu",
    "Alanzoka",
    "Davy Jones (Gameplayrj)",
    "Mount",
    "Jon Vlogs"
]

# Canais da Twitch verificados a cada varredura (login usado no endereço do canal)
CANAIS_TWITCH = [
    "alanzoka", "cellbit", "casimito", "coringa", "luqueta", "paulinholoko", "piuzinho", "gabepeixe",
    "biquinho", "bagualu", "davyjones", "gameplayrj", "mount", "jonvlogs", "felps", "baiano",
    "nobru", "brino", "rakin", "yetz", "thurzin", "bauky", "mwzera", "tck10",
]

# Rede Oficial de 7 Canais do YouTube da Agência Viela Vice
CANAIS_VIELA_VICE = {
    "1": {"nome": "Viela Vice (Principal - GTA 6)", "token": "token.json", "cota_diaria": 6},
    "2": {"nome": "Viela Vice RP (Policia e Fugas)", "token": "token_policia.json", "cota_diaria": 6},
    "3": {"nome": "Viela Vice Clipes (Memes e Zueira)", "token": "token_memes.json", "cota_diaria": 6},
    "4": {"nome": "Viela Vice Stories (Historias)", "token": "token_stories.json", "cota_diaria": 6},
    "5": {"nome": "Viela Vice Underground (Favela)", "token": "token_underground.json", "cota_diaria": 6},
    "6": {"nome": "Viela Vice News (Vazamentos GTA 6)", "token": "token_news.json", "cota_diaria": 6},
    "7": {"nome": "Viela Vice Best Moments", "token": "token_best.json", "cota_diaria": 6}
}

# Horários padrão para agendamento dos 6 envios diários
DEFAULT_HORARIOS = ["10:00", "13:00", "16:00", "19:00", "21:00", "22:30"]

# Padrões Técnicos Obrigatórios (Diretrizes GEMINI.md)
VIDEO_SPECS = {
    "width": 1080,
    "height": 1920,
    "fps": 30,
    "pix_fmt": "yuv420p",
    "codec_v": "libx264",
    "codec_a": "aac",
    "bitrate_a": "192k",
    "preset": "medium",
    "crf": "18",
    "duracao_min_shorts": 60.0,
    "duracao_max_shorts": 75.0,
    "limite_estoque_max": 60,  # Mantém a proporção diária de 4 Shorts para 2 Longos
    "limite_shorts": 40,
    "limite_longos": 20,
    "shorts_por_ciclo": 4,
    "longos_por_ciclo": 2,
    "duracao_longo_s": 600.0,
    "duracao_minima_longo_s": 480.0,
    "janela_transcricao_s": 480.0,  # Trecho da live analisado pelo Whisper em cada ciclo
    "duracao_conteudo_s": 66.0,  # Conteúdo do Short, sem contar a intro narrada
    "captura_live_s": 1260,  # Tempo de gravação de uma live que ainda está no ar
    "modelo_whisper": "small"
}

# Palavras-chave de alto CTR/viralidade
PALAVRAS_CHAVE_VIRAIS = [
    "gta 6", "vazamento", "polícia", "fuga", "batedor", 
    "treta", "tiroteio", "surto", "mitou", "apagou", "ironia",
    "admin", "ban", "hospital", "apreendido"
]
