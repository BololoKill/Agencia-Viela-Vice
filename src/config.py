"""
Configurações centrais do sistema Agência Viela Vice.
Define parâmetros de produção, canais de publicação, streamers monitorados e regras de qualidade.
"""
import os
from pathlib import Path

# Diretório raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# O notebook tem um SSD (D:) além do HD onde estão o Windows e os arquivos do dono. Os downloads e os arquivos
# temporários da produção, que são o trabalho pesado do disco, ficam no SSD: mais rápido e poupa o HD.
SSD_DE_TRABALHO = Path("D:/VielaVice")


def pasta_de_trabalho(ssd: Path = SSD_DE_TRABALHO) -> Path:
    """Pasta dos downloads e temporários: no SSD quando ele está no notebook; sem ele, na pasta do projeto."""
    return ssd / "video-bruto" if Path(ssd.anchor).exists() else BASE_DIR / "video-bruto"


# Diretórios de trabalho de mídia
EXPORT_DIR = BASE_DIR / "exportacao"
VIDEO_BRUTO_DIR = pasta_de_trabalho()
SPRITES_DIR = BASE_DIR / "sprites"
ASSETS_DIR = BASE_DIR / "assets"

# Arquivos de estado e persistência JSON
AFILIADOS_FILE = BASE_DIR / "afiliados_config.json"
AGENDADOS_FILE = BASE_DIR / "agendados.json"
DESCARTADOS_FILE = BASE_DIR / "descartados.json"
HISTORICO_FILE = BASE_DIR / "historico.txt"
DESCOBERTOS_PATH = BASE_DIR / "streamers_descobertos.json"
STATUS_VIGIA_FILE = BASE_DIR / "status_vigia.json"
RANKING_CURADORIA_FILE = BASE_DIR / "ranking_curadoria.json"
METADADOS_FILE = BASE_DIR / "metadados_cortes.json"
TRAVA_CICLO_FILE = BASE_DIR / ".ciclo_producao.lock"
FALHAS_FILE = BASE_DIR / "falhas_pipeline.json"
CONTROLE_PRODUCAO_FILE = BASE_DIR / "controle_producao.json"
COTAS_FILE = BASE_DIR / "cotas_youtube.json"
TRECHOS_SEM_FALA_FILE = BASE_DIR / "trechos_sem_fala.json"

# Padrão dark de cada canal em cada ciclo, que reinicia às 05:00: 1 vídeo longo e 2 Shorts (as "3 estrelas" do painel).
# Canais dark grandes publicam pouco e todo dia. Muitos vídeos parecidos por dia é o que o YouTube trata como
# conteúdo produzido em massa, que pode tirar a monetização do canal inteiro.
COTA_POR_TIPO = {"longo": 1, "short": 2}
COTA_DIARIA_CANAL = sum(COTA_POR_TIPO.values())
HORA_REINICIO_COTA = 5

# Arquivos de assets fundamentais
CTA_AUDIO = EXPORT_DIR / "cta.mp3"
FONT_PATH = BASE_DIR / "arial.ttf"
MARCA_PATH = ASSETS_DIR / "marca_viela_vice.png"
WHOOSH_PATH = ASSETS_DIR / "whoosh.wav"

# Streamers brasileiros usados nas buscas de vídeos de GTA 6 no YouTube
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

# A agência publica num canal só: todo o público e as horas assistidas vão para a mesma monetização
CANAIS_VIELA_VICE = {
    "1": {"nome": "Viela Vice (Principal - GTA 6)", "token": "token.json", "cota_diaria": COTA_DIARIA_CANAL},
}

# Canais parados: não recebem vídeos até um formato próprio e diferente justificar um segundo canal
CANAIS_PAUSADOS = {
    "2": {"nome": "Viela Vice RP (Policia e Fugas)", "token": "token_policia.json", "cota_diaria": COTA_DIARIA_CANAL},
    "3": {"nome": "Viela Vice Clipes (Memes e Zueira)", "token": "token_memes.json", "cota_diaria": COTA_DIARIA_CANAL},
    "4": {"nome": "Viela Vice Stories (Historias)", "token": "token_stories.json", "cota_diaria": COTA_DIARIA_CANAL},
    "5": {"nome": "Viela Vice Underground (Favela)", "token": "token_underground.json", "cota_diaria": COTA_DIARIA_CANAL},
    "6": {"nome": "Viela Vice News (Vazamentos GTA 6)", "token": "token_news.json", "cota_diaria": COTA_DIARIA_CANAL},
    "7": {"nome": "Viela Vice Best Moments", "token": "token_best.json", "cota_diaria": COTA_DIARIA_CANAL}
}

# Horário de publicação de cada tipo (Brasília): Shorts no almoço e à noite, o longo antes do horário nobre
HORARIOS_POR_TIPO = {"short": ["12:00", "19:00"], "longo": ["17:00"]}
DEFAULT_HORARIOS = sorted(h for grade in HORARIOS_POR_TIPO.values() for h in grade)

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
    "duracao_min_shorts": 45.0,  # Shorts entre 45 e 60 s: boa retenção e sem bloqueio de Content ID acima de 1 min
    "duracao_max_shorts": 60.0,
    "limite_estoque_max": 9,  # 3 dias de publicação do canal no padrão dark: 6 Shorts e 3 longos
    "limite_shorts": 6,
    "limite_longos": 3,
    "shorts_por_ciclo": 4,
    "longos_por_ciclo": 1,  # O longo é o Top da semana, montado com um trecho de cada vídeo viral
    "duracao_longo_s": 510.0,  # 8min30: passa dos 8 min exigidos para anúncios no meio do vídeo
    "duracao_minima_longo_s": 485.0,
    "janela_transcricao_s": 1260.0,  # Trecho analisado pelo Whisper quando nada mais é indicado
    "janela_fonte_s": 360.0,  # De cada vídeo viral só 6 min são baixados e analisados: a internet é lenta
    "fontes_por_compilacao": 5,  # Top 5 da semana, um trecho de cada vídeo viral
    "fontes_minimas_compilacao": 4,
    "duracao_conteudo_s": 55.0,  # Conteúdo do Short, sem contar a intro narrada
    "modelo_whisper": "small",
    # Roteiros do canal dark. Cada modelo tem cota própria no Google: os do fim são a reserva quando os primeiros esgotam
    "modelos_texto": ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash-lite",
                      "gemini-3.1-flash-lite", "gemma-4-31b-it"],
    # Identificam o jogo na imagem; o lite fica por último porque sobra cota nele quando os outros esgotam
    "modelos_visao": ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite",
                      "gemini-3.1-flash-lite"],
}

# Palavras-chave de alto CTR/viralidade
PALAVRAS_CHAVE_VIRAIS = [
    "gta 6", "vazamento", "polícia", "fuga", "batedor", 
    "treta", "tiroteio", "surto", "mitou", "apagou", "ironia",
    "admin", "ban", "hospital", "apreendido"
]
