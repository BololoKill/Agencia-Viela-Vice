"""
Regras de edição dos Shorts: ritmo, legendas, título-gancho e escolha dos melhores momentos.
"""
import re
import unicodedata
from pathlib import Path
from src.config import PALAVRAS_CHAVE_VIRAIS
from src.utils import censor_text

PALAVRAS_FORTES = {
    "policia", "fuga", "tiro", "tiroteio", "treta", "corre", "correndo", "morreu", "matou", "preso", "presa",
    "banido", "ban", "socorro", "assalto", "roubo", "roubou", "perseguicao", "explodiu", "bateu", "surto",
    "surtou", "mitou", "apagou", "insano", "absurdo", "inacreditavel", "gta", "vazou", "vazamento",
    "viatura", "faccao", "hospital", "admin", "batedor", "ironia",
}
HASHTAGS_ROTATIVAS = [
    "#GTA6 #GTAVI #Shorts #VielaVice",
    "#GTA6 #GTARP #Shorts #GamerBrasil",
    "#GTAVI #GTA6Brasil #Shorts #Gameplay",
    "#GTA6 #LiveBrasil #Shorts #CortesDeLive",
]
ESTILO_ASS = (
    "Style: Viela,Arial Black,68,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,"
    "0,0,0,0,100,100,0,0,3,14,0,2,50,50,430,1"
)
PAUSA_SEM_PISCAR_S = 0.35
TITULOS_LONGOS = [
    "{nome} no GTA 6: os melhores momentos da live | Parte {parte}",
    "GTA 6 com {nome}: momentos insanos da live | Parte {parte}",
    "{nome} jogando GTA 6: o melhor da live | Parte {parte}",
]
PROB_MINIMA_PORTUGUES = 0.7
CONFIANCA_MINIMA_TRANSCRICAO = -1.0
FOLGA_MAXIMA_DO_CORTE = 2.5
DURACAO_MINIMA_CORTE_S = 20.0


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")


def _e_palavra_forte(palavra: str) -> bool:
    limpa = re.sub(r"[^\w]", "", _normalizar(palavra))
    return limpa in PALAVRAS_FORTES or limpa in {_normalizar(p) for p in PALAVRAS_CHAVE_VIRAIS}


def nome_falado(streamer: str) -> str:
    """Remove complementos do nome para narração e títulos."""
    return re.sub(r"\s*\(.*?\)", "", str(streamer)).replace("_", " ").strip()


def palavras_dos_segmentos(segmentos: list) -> list:
    """Extrai cada palavra com seu tempo real, já censurada."""
    palavras = []
    for seg in segmentos:
        brutas = seg.get("words")
        if not brutas:
            termos = str(seg.get("text", "")).split()
            passo = (seg["end"] - seg["start"]) / max(len(termos), 1)
            brutas = [
                {"word": termo, "start": seg["start"] + i * passo, "end": seg["start"] + (i + 1) * passo}
                for i, termo in enumerate(termos)
            ]
        for item in brutas:
            texto = censor_text(str(item.get("word", "")).strip())
            if texto:
                palavras.append({"inicio": float(item["start"]), "fim": float(item["end"]), "texto": texto})
    return palavras


def _texto_legivel(texto: str) -> bool:
    """Letras de outros alfabetos indicam que o Whisper não entendeu o áudio."""
    letras = [c for c in str(texto) if c.isalpha()]
    return bool(letras) and all(unicodedata.name(c, "").startswith("LATIN") for c in letras)


def fala_em_portugues(seg: dict) -> bool:
    """Aceita só a fala em português que o Whisper entendeu com segurança."""
    return (seg.get("prob_pt", 1.0) >= PROB_MINIMA_PORTUGUES
            and seg.get("avg_logprob", 0.0) >= CONFIANCA_MINIMA_TRANSCRICAO
            and _texto_legivel(seg.get("text", "")))


def filtrar_fala_em_portugues(segmentos: list) -> list:
    """Remove diálogos do jogo em outro idioma, que virariam legendas e títulos sem sentido."""
    return [seg for seg in segmentos if fala_em_portugues(seg)]


def _subtrair_bloqueios(trechos: list, bloqueios) -> list:
    resultado = list(trechos)
    for b_ini, b_fim in bloqueios:
        proximos = []
        for ini, fim in resultado:
            if fim <= b_ini or ini >= b_fim:
                proximos.append((ini, fim))
                continue
            if ini < b_ini:
                proximos.append((ini, b_ini))
            if fim > b_fim:
                proximos.append((b_fim, fim))
        resultado = proximos
    return resultado


def duracao_trechos(trechos: list) -> float:
    return sum(fim - ini for ini, fim in trechos)


def calcular_trechos_uteis(palavras: list, pausa_max: float = 0.6, folga: float = 0.12,
                           bloqueios=(), duracao_max: float = None) -> list:
    """Mantém a fala e remove pausas longas e telas pretas."""
    trechos = []
    ultimo_fim = None
    for p in sorted(palavras, key=lambda item: item["inicio"]):
        ini = max(0.0, p["inicio"] - folga)
        fim = p["fim"] + folga
        if trechos and p["inicio"] - ultimo_fim <= pausa_max:
            trechos[-1] = (trechos[-1][0], max(trechos[-1][1], fim))
        else:
            trechos.append((ini, fim))
        ultimo_fim = p["fim"]

    trechos = [(round(a, 3), round(b, 3)) for a, b in _subtrair_bloqueios(trechos, bloqueios) if b - a >= 0.3]
    if duracao_max is None:
        return trechos

    limitados = []
    restante = duracao_max
    for ini, fim in trechos:
        if restante <= 0:
            break
        limitados.append((ini, round(min(fim, ini + restante), 3)))
        restante -= limitados[-1][1] - ini
    return limitados


def alinhar_trechos_aos_quadros(trechos: list, fps: int) -> list:
    """Encaixa cada corte em quadros inteiros para imagem, som e legenda usarem a mesma medida."""
    alinhados = []
    ultimo_quadro = 0
    for ini, fim in trechos:
        primeiro = max(int(round(ini * fps)), ultimo_quadro)
        final = int(round(fim * fps))
        if final > primeiro:
            alinhados.append((primeiro / fps, final / fps))
            ultimo_quadro = final
    return alinhados


def remapear_tempo(tempo: float, trechos: list):
    """Converte um tempo da live para a linha do tempo já editada."""
    acumulado = 0.0
    for ini, fim in trechos:
        if ini <= tempo <= fim:
            return round(acumulado + tempo - ini, 3)
        acumulado += fim - ini
    return None


def agrupar_legendas(palavras: list, trechos: list, max_palavras: int = 3, limite: float = None) -> list:
    """Agrupa até 3 palavras por vez na linha do tempo editada."""
    grupos = []
    atual = []

    def fechar():
        if atual:
            grupos.append({"inicio": atual[0]["inicio"], "fim": atual[-1]["fim"], "palavras": list(atual)})
            atual.clear()

    for p in palavras:
        inicio = remapear_tempo(p["inicio"], trechos)
        if inicio is None or (limite is not None and inicio >= limite):
            continue
        fim = remapear_tempo(p["fim"], trechos)
        fim = fim if fim is not None else inicio + max(0.15, p["fim"] - p["inicio"])
        if limite is not None:
            fim = min(fim, limite)
        if atual and inicio - atual[-1]["fim"] > 0.45:
            fechar()
        atual.append({"texto": p["texto"], "inicio": inicio, "fim": fim})
        if len(atual) >= max_palavras or p["texto"][-1] in ".,!?":
            fechar()
    fechar()
    return grupos


def _tempo_ass(segundos: float) -> str:
    centesimos = int(round(max(0.0, segundos) * 100))
    horas, resto = divmod(centesimos, 360000)
    minutos, resto = divmod(resto, 6000)
    segs, cent = divmod(resto, 100)
    return f"{horas}:{minutos:02d}:{segs:02d}.{cent:02d}"


def _texto_ass(texto: str) -> str:
    return re.sub(r"[{}\\]", "", texto).upper()


def gerar_ass(grupos: list, destino: Path) -> Path:
    """Gera legendas com a palavra falada em destaque amarelo sobre box preto."""
    linhas = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding",
        ESTILO_ASS, "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for indice, grupo in enumerate(grupos):
        palavras = grupo["palavras"]
        proximo = grupos[indice + 1]["inicio"] if indice + 1 < len(grupos) else None
        fim_grupo = proximo if proximo is not None and proximo - grupo["fim"] <= PAUSA_SEM_PISCAR_S else grupo["fim"]
        for i, ativa in enumerate(palavras):
            inicio = grupo["inicio"] if i == 0 else ativa["inicio"]
            fim = palavras[i + 1]["inicio"] if i + 1 < len(palavras) else fim_grupo
            partes = [
                f"{{\\c&H0000FFFF&}}{_texto_ass(p['texto'])}{{\\c&H00FFFFFF&}}" if j == i else _texto_ass(p["texto"])
                for j, p in enumerate(palavras)
            ]
            entrada = "{\\fscx106\\fscy106\\t(0,90,\\fscx100\\fscy100)}" if i == 0 else ""
            linhas.append(f"Dialogue: 0,{_tempo_ass(inicio)},{_tempo_ass(fim)},Viela,,0,0,0,,{entrada}{' '.join(partes)}")
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return destino


def gerar_gancho(segmentos: list, streamer: str) -> str:
    """Escolhe a frase mais forte do corte para o título no topo do vídeo."""
    melhor = ""
    melhor_nota = 0
    for seg in segmentos:
        texto = censor_text(str(seg.get("text", "")).strip())
        termos = texto.split()
        if len(termos) < 3:
            continue
        nota = 3 * sum(_e_palavra_forte(t) for t in termos) + (2 if re.search(r"[!?]", texto) else 0)
        if nota > melhor_nota:
            melhor, melhor_nota = texto, nota
    if not melhor:
        return f"OLHA O QUE {nome_falado(streamer).upper()} FEZ!"
    return re.sub(r"[.,;:]+$", "", " ".join(melhor.split()[:6])).upper()


def quebrar_linhas(texto: str, max_chars: int = 18, max_linhas: int = 2) -> list:
    """Distribui o título em até duas linhas legíveis no celular."""
    linhas = []
    atual = ""
    for termo in texto.split():
        candidata = f"{atual} {termo}".strip()
        if len(candidata) <= max_chars:
            atual = candidata
            continue
        if atual:
            linhas.append(atual)
        atual = termo[:max_chars]
        if len(linhas) == max_linhas:
            return linhas
    if atual and len(linhas) < max_linhas:
        linhas.append(atual)
    return linhas


def _nota_corte(segmentos: list) -> float:
    palavras = palavras_dos_segmentos(segmentos)
    duracao = max(segmentos[-1]["end"] - segmentos[0]["start"], 1.0)
    fortes = sum(_e_palavra_forte(p["texto"]) for p in palavras)
    enfase = sum(p["texto"][-1] in "!?" for p in palavras)
    return (len(palavras) / duracao) * 10 + (fortes + enfase) * 60 / duracao


def selecionar_melhores_cortes(segmentos: list, duracao_alvo: float = 66.0, max_cortes: int = 3,
                               duracao_minima: float = DURACAO_MINIMA_CORTE_S, bloqueios=()) -> list:
    """Ranqueia janelas de fala e devolve os momentos mais intensos, sem sobreposição."""
    candidatos = []
    janela_maxima = duracao_alvo * FOLGA_MAXIMA_DO_CORTE
    for i in range(len(segmentos)):
        util = 0.0
        ultimo = i
        for j in range(i, len(segmentos)):
            if segmentos[j]["end"] - segmentos[i]["start"] > janela_maxima:
                break
            util += segmentos[j]["end"] - segmentos[j]["start"]
            ultimo = j
            if util >= duracao_alvo:
                break
        if util < duracao_minima:
            continue
        trecho = segmentos[i:ultimo + 1]
        aproveitado = duracao_trechos(calcular_trechos_uteis(palavras_dos_segmentos(trecho), bloqueios=bloqueios))
        if aproveitado >= duracao_minima:
            candidatos.append((_nota_corte(trecho), trecho[0]["start"], trecho[-1]["end"], trecho))

    escolhidos = []
    for _, inicio, fim, trecho in sorted(candidatos, key=lambda c: c[0], reverse=True):
        if all(fim <= e[0] or inicio >= e[1] for e in escolhidos):
            escolhidos.append((inicio, fim, trecho))
        if len(escolhidos) >= max_cortes:
            break
    return escolhidos


def planejar_longos(duracao_total: float, quantidade: int = 2, alvo: float = 600.0, minimo: float = 480.0,
                    margem: float = 20.0) -> list:
    """Divide a gravação em partes sem repetição. Devolve (início, duração) de cada vídeo longo."""
    for partes in range(quantidade, 0, -1):
        fatia = (duracao_total - margem) / partes
        if fatia >= minimo:
            return [(round(margem + i * fatia, 3), round(min(alvo, fatia - margem), 3)) for i in range(partes)]
    return []


def trechos_sem_bloqueios(inicio: float, duracao: float, bloqueios=(), minimo: float = 0.5) -> list:
    """Mantém a parte escolhida da live, retirando as telas pretas."""
    return [(a, b) for a, b in _subtrair_bloqueios([(inicio, inicio + duracao)], bloqueios) if b - a >= minimo]


def montar_publicacao_longa(streamer: str, parte: int, semente: int = 0) -> dict:
    """Prepara título e descrição do vídeo longo, com os créditos do criador."""
    nome = nome_falado(streamer)
    modelo = TITULOS_LONGOS[semente % len(TITULOS_LONGOS)]
    titulo = modelo.format(nome=nome, parte=parte)[:98]
    descricao = (
        f"{titulo}\n\nCréditos: Live de {nome}\n\n"
        f"Inscreva-se no canal Viela Vice para os melhores momentos de GTA 6!\n\n#GTA6 #GTAVI #VielaVice #Gameplay"
    )
    return {"titulo": titulo, "descricao": descricao}


def montar_publicacao(gancho: str, streamer: str, semente: int = 0) -> dict:
    """Prepara título e descrição com créditos ao criador e hashtags variadas."""
    nome = nome_falado(streamer)
    sufixo = " #Shorts"
    titulo = f"{gancho[:98 - len(sufixo)].strip()}{sufixo}"
    hashtags = HASHTAGS_ROTATIVAS[semente % len(HASHTAGS_ROTATIVAS)]
    descricao = (
        f"{gancho}\n\nCréditos: Live de {nome}\n\n"
        f"Inscreva-se no canal Viela Vice para os melhores momentos de GTA 6!\n\n{hashtags}"
    )
    return {"titulo": titulo, "descricao": descricao}
