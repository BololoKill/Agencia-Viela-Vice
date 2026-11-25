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
    "#GTA6 #GTA6Brasil #Shorts #GamerBrasil",
    "#GTAVI #GTA6Brasil #Shorts #Gameplay",
    "#GTA6 #ViralGTA6 #Shorts #Narrado",
]
TITULO_COMPILACAO = "TOP {quantidade} momentos mais virais de GTA 6 da semana"
FALA_MINIMA_DO_TRECHO = 0.4  # Trecho da compilação com menos de 40% de fala vira silêncio na tela
FOLGA_FIM_DA_FRASE = 1.12  # O trecho pode crescer até 12% para não cortar a frase no meio
ESTILO_ASS = (
    "Style: Viela,Arial Black,68,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,"
    "0,0,0,0,100,100,0,0,3,14,0,2,50,50,430,1"
)
PAUSA_SEM_PISCAR_S = 0.35
PROB_MINIMA_PORTUGUES = 0.7
CONFIANCA_MINIMA_TRANSCRICAO = -1.0
FOLGA_MAXIMA_DO_CORTE = 2.5
DURACAO_MINIMA_CORTE_S = 42.5  # Com a abertura narrada, o Short completo fica com pelo menos 45 s


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
    return _titulo_curto(melhor)


PALAVRAS_SOLTAS = {
    "a", "o", "as", "os", "um", "uma", "de", "da", "do", "das", "dos", "e", "que", "me", "te", "se", "lhe",
    "em", "no", "na", "nos", "nas", "pra", "pro", "para", "por", "com", "mas", "ou", "ao", "aos", "meu", "minha",
    "seu", "sua", "esse", "essa", "este", "esta", "isso", "vou", "vai", "eu",
}


def _titulo_curto(texto: str, limite: int = 6) -> str:
    """Fecha o título no fim da frase e nunca o deixa terminar numa palavra que pede continuação."""
    frase = re.split(r"(?<=[.!?…])\s+", texto.strip())[0]
    termos = (frase if len(frase.split()) >= 4 else texto).split()[:limite]
    while len(termos) > 3 and re.sub(r"[^\w]", "", termos[-1].lower()) in PALAVRAS_SOLTAS:
        termos.pop()
    return re.sub(r"[.,;:…]+$", "", " ".join(termos)).upper()


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


def melhor_trecho(segmentos: list, duracao: float, bloqueios=(), fim_maximo: float = None):
    """
    O trecho contínuo de pelo menos `duracao` segundos com a fala mais intensa, sem telas pretas.
    Termina no fim de uma frase quando ela acaba logo depois. Devolve (início, fim, falas) ou None.
    """
    melhor = None
    for i, seg in enumerate(segmentos):
        inicio = max(0.0, seg["start"] - 0.5)
        fim = inicio + duracao
        dentro = [s for s in segmentos[i:] if s["start"] < fim]
        fim_da_frase = [s["end"] for s in dentro if fim <= s["end"] <= inicio + duracao * FOLGA_FIM_DA_FRASE]
        fim = max(fim_da_frase) if fim_da_frase else fim
        if fim_maximo is not None and fim > fim_maximo:
            break
        if any(inicio < b_fim and fim > b_ini for b_ini, b_fim in bloqueios):
            continue
        fala = sum(min(s["end"], fim) - s["start"] for s in dentro)
        if fala < duracao * FALA_MINIMA_DO_TRECHO:
            continue
        nota = _nota_corte(dentro)
        if melhor is None or nota > melhor[0]:
            melhor = (nota, round(inicio, 3), round(fim, 3), dentro)
    return None if melhor is None else melhor[1:]


def trechos_sem_bloqueios(inicio: float, duracao: float, bloqueios=(), minimo: float = 0.5) -> list:
    """Mantém a parte escolhida do vídeo, retirando as telas pretas."""
    return [(a, b) for a, b in _subtrair_bloqueios([(inicio, inicio + duracao)], bloqueios) if b - a >= minimo]


def _rotulo_do_capitulo(texto: str, palavras: int = 7) -> str:
    return re.sub(r"[.,;:!?…]+$", "", " ".join(str(texto).split()[:palavras]))


def _lista_de_capitulos(capitulos) -> str:
    """Capítulos com horário na descrição: o YouTube só os reconhece com 3 ou mais, o primeiro em 00:00."""
    marcos = []
    for instante, texto in capitulos:
        if texto and (not marcos or instante - marcos[-1][0] >= 10):
            marcos.append((instante, texto))
    if len(marcos) < 3 or marcos[0][0] > 0.5:
        return ""
    linhas = [f"{int(i // 60):02d}:{int(i % 60):02d} {_rotulo_do_capitulo(t)}" for i, t in marcos]
    return "Capítulos:\n" + "\n".join(linhas)


def montar_publicacao(gancho: str, streamer: str, semente: int = 0, titulo_roteiro: str = None, resumo: str = None,
                      url: str = None) -> dict:
    """Prepara título e descrição com crédito e link do vídeo original e hashtags variadas."""
    nome = nome_falado(streamer)
    sufixo = " #Shorts"
    titulo = f"{(titulo_roteiro or gancho)[:98 - len(sufixo)].strip()}{sufixo}"
    hashtags = HASHTAGS_ROTATIVAS[semente % len(HASHTAGS_ROTATIVAS)]
    credito = f"Créditos: vídeo de {nome}" + (f" — {url}" if url else "")
    descricao = (
        f"{resumo or gancho}\n\n{credito}\n\n"
        f"Inscreva-se no canal Viela Vice para os melhores momentos de GTA 6!\n\n{hashtags}"
    )
    return {"titulo": titulo, "descricao": descricao}


def montar_publicacao_compilacao(fontes: list, titulo_roteiro: str = None, resumo: str = None, capitulos=()) -> dict:
    """
    Título e descrição do Top da semana: resumo narrado, capítulos com horário e o crédito,
    com link, de cada vídeo original usado. "fontes" traz {"streamer", "url"} na ordem do vídeo.
    """
    titulo = (titulo_roteiro or TITULO_COMPILACAO.format(quantidade=len(fontes)))[:98]
    lista = _lista_de_capitulos(capitulos)
    creditos = "\n".join(f"{i}. {nome_falado(f['streamer'])} — {f['url']}" for i, f in enumerate(fontes, 1))
    descricao = (
        f"{resumo or titulo}\n\n" + (f"{lista}\n\n" if lista else "") + f"Créditos dos vídeos originais:\n{creditos}\n\n"
        f"Inscreva-se no canal Viela Vice para os melhores momentos de GTA 6!\n\n#GTA6 #GTAVI #VielaVice #Gameplay"
    )
    return {"titulo": titulo, "descricao": descricao}
