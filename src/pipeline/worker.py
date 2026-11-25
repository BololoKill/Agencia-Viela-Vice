"""
Módulo Worker de Produção Autônoma.
Ciclo do canal dark: busca os vídeos de GTA 6 mais virais da semana -> baixa só o trecho analisado de cada um ->
confere idioma e jogo -> transcreve -> um Short com o melhor momento de cada vídeo e um vídeo longo
"Top da semana" com um trecho de cada um -> auditoria técnica. Nenhum vídeo sai sem narração própria.
"""
import errno
import re
import shutil
import threading
import time
from collections import namedtuple
from datetime import datetime, timedelta
from src.config import (
    AGENDADOS_FILE, DESCARTADOS_FILE, EXPORT_DIR, METADADOS_FILE, TRECHOS_SEM_FALA_FILE, VIDEO_BRUTO_DIR, VIDEO_SPECS
)
from src.utils import load_json_safe, log_terminal, save_json_safe
from src.pipeline import estado
from src.pipeline.edicao import (
    DURACAO_MINIMA_CORTE_S, filtrar_fala_em_portugues, gerar_gancho, melhor_trecho, montar_publicacao,
    montar_publicacao_compilacao, selecionar_melhores_cortes
)
from src.pipeline.ffmpeg_runner import detectar_intervalos_comerciais, detectar_telas_pretas
from src.pipeline.searcher import (
    CATEGORIAS_BLOQUEIO, buscar_videos_virais, pausar_youtube, registrar_historico, youtube_pausado_ate
)
from src.pipeline.downloader import baixar_video
from src.pipeline.verificador import confere_gta6
from src.pipeline.roteiro import (
    IaDeRoteiroFora, SemRoteiro, com_roteiro, ia_respondendo, roteiro_compilacao, roteiro_short, situacao_da_ia
)
from src.pipeline.transcriber import (
    calcular_janela_transcricao, e_audio_em_portugues, extrair_audio_wav, identificar_idioma_dos_segmentos,
    transcrever_audio
)
from src.pipeline.renderer import montar_compilacao, obter_duracao_audio, renderizar_longo, renderizar_short
from src.pipeline.quality import auditar_video

ESPERA_MAXIMA_S = 900
ESPACO_MINIMO_BYTES = 5 * 1024 ** 3
INTERVALO_BATIMENTO_S = 10
INTERVALO_LOG_ANDAMENTO_S = 60
PREFIXO_LONGO = "longo-"
PREFIXO_FONTE = "fonte"
ESPERA_APOS_BLOQUEIO_S = 60
CANDIDATOS_EXTRAS = 3  # Alguns virais caem na conferência (outro idioma, outro jogo): a busca traz alguns a mais
CATEGORIAS_DO_VIDEO = ("restricao_idade", "so_membros")  # O vídeo nunca abre sem login: sai da busca na hora
TRECHO_MINIMO_S = 60.0
TRECHO_MAXIMO_S = 150.0
PASTAS_ANTIGAS = ("proxima",)  # Gravação adiantada de live, que não existe mais
POSICOES_EXTRAS = (0.5,)  # Segundo trecho do vídeo, no meio, quando o primeiro tem pouca fala do criador
DIAS_MEMORIA_TRECHOS = 30  # O trecho de um vídeo não muda; depois de um mês o vídeo já saiu da lista dos virais
# Tamanho do trecho de cada vídeo no Top completo: os 8min30 divididos entre os 5 vídeos
TRECHO_DO_TOP_S = min(TRECHO_MAXIMO_S, max(TRECHO_MINIMO_S,
                                           VIDEO_SPECS["duracao_longo_s"] / VIDEO_SPECS["fontes_por_compilacao"]))

Fonte = namedtuple("Fonte", "video_info arquivo falas bloqueios duracao")

_etapa_atual = {"nome": "", "desde": time.monotonic()}


def limpar_video_bruto():
    """Remove arquivos intermediários e as pastas dos vídeos virais baixados no ciclo."""
    if not VIDEO_BRUTO_DIR.exists():
        return
    for f in VIDEO_BRUTO_DIR.iterdir():
        if f.is_file():
            try:
                f.unlink()
            except Exception:
                pass
        elif f.is_dir() and (f.name.startswith(PREFIXO_FONTE) or f.name in PASTAS_ANTIGAS):
            shutil.rmtree(f, ignore_errors=True)


def _ja_decididos() -> set:
    """Vídeos rejeitados ou já enviados ao YouTube cujo arquivo o player ainda segurava na hora de apagar."""
    descartados = load_json_safe(DESCARTADOS_FILE, [])
    agendados = load_json_safe(AGENDADOS_FILE, [])
    enviados = {item.get("filename") for item in agendados if isinstance(item, dict) and item.get("youtube_id")}
    return set(descartados if isinstance(descartados, list) else []) | enviados


def limpar_sobras_da_diretoria():
    """Apaga do disco os vídeos que a Diretoria já decidiu. Um arquivo ainda em uso fica para o próximo ciclo."""
    if not EXPORT_DIR.exists():
        return
    for nome in _ja_decididos():
        try:
            (EXPORT_DIR / nome).unlink(missing_ok=True)
        except (OSError, TypeError, ValueError):
            pass


def contar_estoque() -> tuple:
    """Conta os vídeos válidos aguardando aprovação: (Shorts, Longos)."""
    if not EXPORT_DIR.exists():
        return 0, 0
    decididos = _ja_decididos()
    videos = [f.name for f in EXPORT_DIR.glob("*.mp4") if f.stat().st_size > 100_000 and f.name not in decididos]
    longos = sum(nome.startswith(PREFIXO_LONGO) for nome in videos)
    return len(videos) - longos, longos


def obter_quantidade_estoque():
    """Conta todos os vídeos válidos aguardando na pasta de exportação."""
    return sum(contar_estoque())


def calcular_vagas() -> tuple:
    """Define quantos Shorts e Longos cabem neste ciclo sem passar do limite do estoque."""
    shorts, longos = contar_estoque()
    livres = max(0, VIDEO_SPECS["limite_estoque_max"] - shorts - longos)
    vagas_longos = min(VIDEO_SPECS["longos_por_ciclo"], max(0, VIDEO_SPECS["limite_longos"] - longos), livres)
    vagas_shorts = min(VIDEO_SPECS["shorts_por_ciclo"], max(0, VIDEO_SPECS["limite_shorts"] - shorts), livres - vagas_longos)
    return vagas_shorts, vagas_longos


def atualizar_status_producao(etapa: str, progresso_pct: int = 0, streamer: str = ""):
    """Publica a etapa atual no painel e registra no console somente quando ela muda."""
    if etapa != _etapa_atual["nome"]:
        _etapa_atual.update(nome=etapa, desde=time.monotonic())
        log_terminal(f"[{progresso_pct}%] {etapa}" if progresso_pct else etapa)
    estado.publicar_status(etapa=etapa, progresso=progresso_pct, streamer=streamer)


class Batimento:
    """Mantém o painel informado enquanto uma etapa longa, como o Whisper, está em execução."""

    def __init__(self):
        self._parar = threading.Event()
        self._thread = threading.Thread(target=self._rodar, daemon=True)

    def _rodar(self):
        ultimo_log = time.monotonic()
        while not self._parar.wait(INTERVALO_BATIMENTO_S):
            estado.publicar_status()
            agora = time.monotonic()
            if agora - ultimo_log >= INTERVALO_LOG_ANDAMENTO_S:
                ultimo_log = agora
                minutos = int((agora - _etapa_atual["desde"]) // 60)
                log_terminal(f"[EM ANDAMENTO] {_etapa_atual['nome']} (há {minutos} min)")

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._parar.set()
        self._thread.join(timeout=2)


def _garantir_espaco_em_disco():
    VIDEO_BRUTO_DIR.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(str(VIDEO_BRUTO_DIR)).free < ESPACO_MINIMO_BYTES:
        raise OSError(errno.ENOSPC, "No space left: menos de 5 GB livres para produzir")


def _salvar_metadados(nome_arquivo: str, publicacao: dict, video_info: dict, roteiro: dict, fontes: list = None):
    """Guarda título, descrição, roteiro e vídeos de origem para a Diretoria. Só existe vídeo pronto no formato dark."""
    metadados = load_json_safe(METADADOS_FILE, {})
    metadados = metadados if isinstance(metadados, dict) else {}
    metadados[nome_arquivo] = {
        **publicacao,
        "streamer": video_info["streamer"],
        "origem": video_info.get("origem", "viral"),
        "formato": "dark",
        "roteiro": roteiro,
        "fontes": fontes or [{"streamer": video_info["streamer"], "url": video_info.get("url")}],
    }
    save_json_safe(METADADOS_FILE, metadados)


def _trechos_sem_imagem_util(video, inicio: float = 0.0, duracao: float = None) -> list:
    """Telas pretas e intervalos comerciais ficam de fora de todos os vídeos."""
    return sorted([*detectar_telas_pretas(video, inicio, duracao), *detectar_intervalos_comerciais(video)])


def _texto_das_falas(falas: list) -> str:
    return " ".join(str(s.get("text", "")).strip() for s in falas)


def _apagar(caminho):
    try:
        caminho.unlink(missing_ok=True)
    except OSError:
        pass


def janelas_do_video(duracao: float) -> list:
    """
    Onde baixar os 6 min analisados: perto do começo e, num vídeo longo, também no meio.
    Live de 10 h começa nas missões da história, cheias de cena do jogo em inglês e com o criador calado.
    """
    janela = VIDEO_SPECS["janela_fonte_s"]
    primeira = calcular_janela_transcricao(duracao or 0, janela=janela)
    if not primeira[1]:
        return [primeira]
    janelas = [primeira]
    for posicao in POSICOES_EXTRAS:
        inicio = round(min(duracao * posicao, duracao - janela), 1)
        if inicio >= janelas[-1][0] + janela:
            janelas.append((inicio, janela))
    return janelas


def _registros_validos(trechos) -> dict:
    """Só os registros de trecho sem fala do último mês."""
    if not isinstance(trechos, dict):
        return {}
    limite = (datetime.now() - timedelta(days=DIAS_MEMORIA_TRECHOS)).strftime("%Y-%m-%d")
    return {inicio: info for inicio, info in trechos.items()
            if isinstance(info, dict) and str(info.get("em", "")) >= limite and str(inicio).isdigit()}


def trechos_sem_fala(video_id: str) -> dict:
    """Trechos do vídeo já conferidos sem fala do criador em português: {início em segundos: motivo}."""
    dados = load_json_safe(TRECHOS_SEM_FALA_FILE, {})
    trechos = _registros_validos(dados.get(video_id) if isinstance(dados, dict) else None)
    return {int(inicio): info.get("motivo") or "pouca fala aproveitável" for inicio, info in trechos.items()}


def guardar_trecho_sem_fala(video_id: str, inicio: float, motivo: str):
    """Guarda o trecho sem fala para ele não ser baixado e transcrito de novo; registros de mais de um mês saem."""
    dados = load_json_safe(TRECHOS_SEM_FALA_FILE, {})
    dados = {vid: validos for vid, trechos in (dados.items() if isinstance(dados, dict) else ())
             if (validos := _registros_validos(trechos))}
    dados.setdefault(video_id, {})[str(round(inicio))] = {"motivo": motivo, "em": datetime.now().strftime("%Y-%m-%d")}
    save_json_safe(TRECHOS_SEM_FALA_FILE, dados)


def _preparar_fonte(video_info: dict, numero: int, total: int):
    """
    Baixa só o trecho analisado do vídeo viral, confere idioma e jogo e transcreve. None quando ele não serve.
    Se o trecho tiver pouca fala do criador, tenta outro ponto do vídeo antes de desistir dele.
    Trecho já conferido sem fala não é baixado de novo. Regressão: o começo do vídeo do BRKsEDU era baixado
    e transcrito a cada ciclo (25 min na internet lenta) para dar sempre os mesmos 12 s de fala.
    """
    streamer = video_info["streamer"]
    ja_conferidos = trechos_sem_fala(video_info["id"])
    pasta = VIDEO_BRUTO_DIR / f"{PREFIXO_FONTE}{numero}"
    pct = 10 + int(45 * (numero - 1) / max(total, 1))
    janelas = janelas_do_video(video_info.get("duration") or 0)
    motivo = "pouca fala aproveitável"
    jogo_conferido = False
    for tentativa, (inicio, janela) in enumerate(janelas, 1):
        if round(inicio) in ja_conferidos:
            motivo = ja_conferidos[round(inicio)]
            log_terminal(f"[IDIOMA] {streamer}: trecho {tentativa} já foi conferido antes ({motivo}); não é baixado de novo.")
            continue
        shutil.rmtree(pasta, ignore_errors=True)
        trecho = f" (outro trecho, {tentativa}/{len(janelas)})" if tentativa > 1 else ""
        atualizar_status_producao(f"Baixando o trecho do vídeo viral {numero}/{total} ({streamer}){trecho}...", pct, streamer)
        arquivo = baixar_video(video_info["url"], destino_dir=pasta, trecho=(inicio, janela) if janela else None)

        audio = pasta / "audio.wav"
        extrair_audio_wav(arquivo, audio)
        if not e_audio_em_portugues(audio):
            motivo = "áudio fora do português"
            log_terminal(f"[IDIOMA] {streamer}: trecho {tentativa} com o áudio fora do português.")
            guardar_trecho_sem_fala(video_info["id"], inicio, motivo)
            continue
        if not jogo_conferido:
            # Confirmado o GTA 6 num trecho, os outros trechos do mesmo vídeo não são conferidos de novo
            atualizar_status_producao(f"Conferindo o jogo no vídeo viral {numero}/{total} ({streamer})...", pct, streamer)
            if not confere_gta6(arquivo):
                # Live às vezes começa com outro jogo enquanto o GTA 6 não abre: o meio do vídeo é conferido antes de
                # descartá-lo. Regressão: o "jogando GTA 6 pela primeira vez" do Jon Vlogs saiu como Far Cry 6 (25/11)
                motivo = "imagem de outro jogo"
                log_terminal(f"[TEMA] {streamer}: o trecho {tentativa} não mostra GTA 6.")
                guardar_trecho_sem_fala(video_info["id"], inicio, motivo)
                continue
            jogo_conferido = True

        atualizar_status_producao(f"Transcrevendo o vídeo viral {numero}/{total} ({streamer})...", pct + 3, streamer)
        segmentos = transcrever_audio(audio)
        medidos = identificar_idioma_dos_segmentos(audio, segmentos)
        falas = filtrar_fala_em_portugues(medidos)
        fala_s = sum(seg["end"] - seg["start"] for seg in falas)
        log_terminal(f"[IDIOMA] {streamer}: trecho {tentativa} com {len(falas)} de {len(medidos)} falas em português "
                     f"({fala_s:.0f} s de fala do criador).")
        if fala_s < DURACAO_MINIMA_CORTE_S:
            motivo = "pouca fala aproveitável"
            guardar_trecho_sem_fala(video_info["id"], inicio, motivo)
            continue
        medida = obter_duracao_audio(arquivo)
        reserva = janela or video_info.get("duration") or max(s["end"] for s in falas)
        duracao = medida if medida > 5 else reserva
        bloqueios = _trechos_sem_imagem_util(arquivo)
        # Fala espalhada em pedaços curtos soma tempo mas não rende Short nem trecho do Top.
        # Regressão: BRKsEDU (46 s) e LOUD Coringa (56 s) ocuparam duas vagas do ciclo sem render nada (24/11)
        if not _corte_do_short(falas, bloqueios) and not melhor_trecho(falas, TRECHO_DO_TOP_S, bloqueios,
                                                                       fim_maximo=duracao - 0.5):
            motivo = "fala espalhada, sem momento para Short ou Top"
            log_terminal(f"[IDIOMA] {streamer}: trecho {tentativa} com a fala espalhada em pedaços curtos: "
                         "não rende Short nem trecho do Top.")
            guardar_trecho_sem_fala(video_info["id"], inicio, motivo)
            continue
        return Fonte(video_info, arquivo, falas, bloqueios, duracao)

    log_terminal(f"[AVISO] Vídeo ignorado ({motivo} em {len(janelas)} trecho(s)): {streamer} | {video_info['title']}")
    return None


def _preparar_fontes(candidatos: list, precisa: int) -> list:
    """Prepara, na ordem dos mais vistos, até "precisa" vídeos virais aproveitáveis."""
    fontes = []
    for video_info in candidatos:
        if len(fontes) >= precisa:
            break
        try:
            fonte = _preparar_fonte(video_info, len(fontes) + 1, precisa)
        except Exception as e:
            info = estado.classificar_erro(e)
            if info["categoria"] in CATEGORIAS_BLOQUEIO:
                raise
            log_terminal(f"[FONTE] {video_info['streamer']} | {video_info['title']}: {info['mensagem']}")
            if info["categoria"] in CATEGORIAS_DO_VIDEO:
                registrar_historico(video_info["id"])
                registrar_historico(video_info["url"])
                continue
            if not info["transitorio"]:
                estado.registrar_falha(video_info["id"], info)
            continue
        if fonte is None:
            # Outro idioma, outro jogo ou pouca fala: o vídeo não muda, então não é baixado de novo
            registrar_historico(video_info["id"])
            registrar_historico(video_info["url"])
            continue
        fontes.append(fonte)
    return fontes


def _corte_do_short(falas: list, bloqueios) -> list:
    """O melhor momento do vídeo para um Short: fala seguida que preenche de 45 a 60 s. [] quando não há."""
    return selecionar_melhores_cortes(falas, duracao_alvo=VIDEO_SPECS["duracao_conteudo_s"], max_cortes=1,
                                      bloqueios=bloqueios)


def _renderizar_short_da_fonte(fonte: Fonte, numero: int, total: int) -> tuple:
    """
    Um Short com o melhor momento do vídeo viral, narrado pelo roteiro. Devolve (aprovado, erro).
    A queda longa da IA de roteiro (IaDeRoteiroFora) sobe para o ciclo parar.
    """
    video_info = fonte.video_info
    streamer = video_info["streamer"]
    cortes = _corte_do_short(fonte.falas, fonte.bloqueios)
    if not cortes:
        log_terminal(f"[AVISO] {streamer}: nenhum momento com fala suficiente para um Short.")
        return False, None
    _, _, segs = cortes[0]
    pct = 60 + int(25 * (numero - 1) / max(total, 1))
    etapa = f"Renderizando Short {numero}/{total} ({streamer})..."
    atualizar_status_producao(etapa, pct, streamer)
    roteiro = com_roteiro(roteiro_short, segs, streamer, avisar=lambda minutos: atualizar_status_producao(
        f"Esperando a IA de roteiro voltar para narrar o Short {numero} (até {minutos} min)...", pct, streamer))
    if not roteiro:
        log_terminal(f"[ROTEIRO] Short {numero} deixado de lado: sem narração própria ele não entra no canal.")
        return False, SemRoteiro("A IA de roteiro não acertou a narração do corte.")
    atualizar_status_producao(etapa, pct, streamer)

    slug = re.sub(r"[^a-z0-9]", "", streamer.lower()) or "gta6"
    output_final = EXPORT_DIR / f"short-{slug}-{int(time.time() * 1000)}.mp4"
    gancho = roteiro.get("gancho") or gerar_gancho(segs, streamer)
    try:
        renderizar_short(video_original=fonte.arquivo, segmentos=segs, streamer=streamer, output_final=output_final,
                         gancho=gancho, bloqueios=fonte.bloqueios, narracao_roteiro=roteiro["narracao"])
    except Exception as e:
        log_terminal(f"[ERRO] Short {numero} não renderizado: {e}")
        return False, e

    valido, motivo, score = auditar_video(output_final)
    if not valido:
        log_terminal(f"[AVISO] Short descartado pela auditoria: {motivo}")
        _apagar(output_final)
        return False, None
    publicacao = montar_publicacao(gancho, streamer, semente=int(time.time()) + numero, titulo_roteiro=roteiro["titulo"],
                                   resumo=roteiro["narracao"], url=video_info.get("url"))
    _salvar_metadados(output_final.name, publicacao, video_info, roteiro)
    log_terminal(f"[SUCESSO] Short aprovado pela auditoria técnica: {output_final.name} (Score: {score})")
    return True, None


def _escolher_trechos(fontes: list) -> list:
    """
    Um trecho de cada vídeo viral, do mesmo tamanho, somando os 8min30 do vídeo longo.
    Se algum vídeo não tiver um trecho bom, os outros ganham trechos maiores. Devolve [] se não fechar o Top.
    """
    minimo = VIDEO_SPECS["fontes_minimas_compilacao"]
    candidatas = list(fontes)
    while len(candidatas) >= minimo:
        por_trecho = min(TRECHO_MAXIMO_S, max(TRECHO_MINIMO_S, VIDEO_SPECS["duracao_longo_s"] / len(candidatas)))
        trechos = []
        for fonte in candidatas:
            escolhido = melhor_trecho(fonte.falas, por_trecho, fonte.bloqueios, fim_maximo=fonte.duracao - 0.5)
            if escolhido:
                trechos.append((fonte, *escolhido))
        if len(trechos) == len(candidatas):
            return trechos
        candidatas = [t[0] for t in trechos]
    log_terminal(f"[LONGO] Só {len(candidatas)} vídeo(s) viral(is) com trecho bom: o Top da semana fica para o próximo ciclo.")
    return []


def _renderizar_compilacao(fontes: list) -> tuple:
    """
    O vídeo longo Top da semana: um trecho de cada vídeo viral, em contagem regressiva
    (o mais visto fecha o vídeo), com o nome de cada criador na tela. Devolve (aprovado, erro).
    """
    trechos = _escolher_trechos(fontes)
    if not trechos:
        return False, None
    trechos.sort(key=lambda t: t[0].video_info.get("visualizacoes") or 0)
    if sum(fim - ini for _, ini, fim, _ in trechos) < VIDEO_SPECS["duracao_minima_longo_s"]:
        log_terminal("[LONGO] Os trechos somam menos de 8 min: o Top da semana fica para o próximo ciclo.")
        return False, None

    quantidade = len(trechos)
    etapa = f"Montando o Top {quantidade} da semana..."
    atualizar_status_producao(etapa, 90)
    roteiro = com_roteiro(
        roteiro_compilacao, [(t[0].video_info["streamer"], _texto_das_falas(t[3])) for t in trechos],
        avisar=lambda minutos: atualizar_status_producao(
            f"Esperando a IA de roteiro voltar para narrar o Top da semana (até {minutos} min)...", 90))
    if not roteiro:
        log_terminal("[ROTEIRO] Top da semana deixado de lado: sem narração própria ele não entra no canal.")
        return False, SemRoteiro("A IA de roteiro não acertou a narração do Top da semana.")
    atualizar_status_producao(etapa, 92)

    compilacao = VIDEO_BRUTO_DIR / "compilacao.mp4"
    output_final = EXPORT_DIR / f"{PREFIXO_LONGO}top{quantidade}-semana-{int(time.time() * 1000)}.mp4"
    try:
        inicios, total = montar_compilacao([(t[0].arquivo, t[1], t[2]) for t in trechos], compilacao)
        fins = inicios[1:] + [total]
        creditos = [(ini, fim, t[0].video_info["streamer"]) for ini, fim, t in zip(inicios, fins, trechos)]
        narracoes = list(zip(inicios, roteiro["capitulos"]))
        renderizar_longo(video_original=compilacao, inicio=0.0, duracao=total, streamer="GTA 6", parte=1,
                         output_final=output_final, abertura=roteiro["abertura"], narracoes=narracoes,
                         titulo_tela=f"TOP {quantidade} DA SEMANA", subtitulo_tela="OS MAIS VIRAIS DE GTA 6",
                         creditos=creditos)
    except Exception as e:
        log_terminal(f"[ERRO] Top da semana não renderizado: {e}")
        return False, e
    finally:
        _apagar(compilacao)

    valido, motivo, score = auditar_video(output_final)
    if not valido:
        log_terminal(f"[AVISO] Top da semana descartado pela auditoria: {motivo}")
        _apagar(output_final)
        return False, None
    fontes_usadas = [{"streamer": t[0].video_info["streamer"], "url": t[0].video_info["url"]} for t in trechos]
    publicacao = montar_publicacao_compilacao(fontes_usadas, titulo_roteiro=roteiro["titulo"], resumo=roteiro["abertura"],
                                              capitulos=narracoes)
    _salvar_metadados(output_final.name, publicacao, {"streamer": "Top da semana", "origem": "compilacao_viral"}, roteiro,
                      fontes=fontes_usadas)
    log_terminal(f"[SUCESSO] Top da semana aprovado pela auditoria técnica: {output_final.name} (Score: {score})")
    return True, None


def _produzir_virais(candidatos: list, vagas_shorts: int, vagas_longos: int, precisa: int) -> bool:
    """Prepara os vídeos virais e produz os Shorts e o Top da semana que cabem no estoque."""
    fontes = _preparar_fontes(candidatos, precisa)
    if not fontes:
        atualizar_status_producao("Nenhum vídeo viral aproveitável agora. Nova busca no próximo ciclo.", 0)
        return False

    shorts = longos = 0
    ultimo_erro = None
    usadas = set()
    try:
        # O vídeo que não rende Short passa a vaga para o próximo. Regressão: sem momento no BRKsEDU e no
        # LOUD Coringa, o Gameplayrj ficou sem Short e o ciclo fez só 2 dos 4 Shorts (24/11)
        total_shorts = min(vagas_shorts, len(fontes))
        for fonte in fontes:
            if shorts >= vagas_shorts:
                break
            aprovado, erro = _renderizar_short_da_fonte(fonte, shorts + 1, total_shorts)
            ultimo_erro = erro or ultimo_erro
            if aprovado:
                shorts += 1
                usadas.add(fonte.video_info["id"])
        if vagas_longos:
            aprovado, erro = _renderizar_compilacao(fontes)
            ultimo_erro = erro or ultimo_erro
            if aprovado:
                longos += 1
                usadas.update(f.video_info["id"] for f in fontes)
    except IaDeRoteiroFora as e:
        log_terminal(f"[ROTEIRO] {e}")
        ultimo_erro = e

    # Cada vídeo viral entra uma vez só no canal; o que não foi usado volta a concorrer no próximo ciclo
    for fonte in fontes:
        if fonte.video_info["id"] in usadas:
            registrar_historico(fonte.video_info["id"])
            registrar_historico(fonte.video_info["url"])
    if shorts + longos == 0:
        raise ultimo_erro or RuntimeError("Nenhum vídeo foi aprovado pela auditoria técnica.")
    resto = " A IA de roteiro caiu e o resto ficou para o próximo ciclo." if isinstance(ultimo_erro, IaDeRoteiroFora) else ""
    atualizar_status_producao(f"Ciclo concluído: {shorts} Short(s) e {longos} vídeo(s) longo(s) pronto(s)!{resto}", 100)
    return True


def _registrar_erro(erro: Exception, video_info: dict = None):
    """Publica o diagnóstico da falha e contabiliza erros definitivos do vídeo."""
    info = estado.classificar_erro(erro)
    log_terminal(f"[ERRO] {info['categoria'].upper()}: {info['mensagem']}")
    if info["categoria"] in CATEGORIAS_BLOQUEIO:
        pausar_youtube()
        info = {**info, "espera_s": ESPERA_APOS_BLOQUEIO_S}
        log_terminal("[BUSCA] YouTube em pausa por 2 horas por causa do bloqueio anti-robô. A busca volta depois da pausa.")
        # O motivo exato do YouTube fica no registro: é ele que mostra se o bloqueio é da conexão ou de um vídeo só
        log_terminal(f"[BUSCA] Motivo dado pelo YouTube: {' '.join(str(erro).split())[:200]}")
    if video_info and not info["transitorio"]:
        tentativas = estado.registrar_falha(video_info["id"], info)
        if tentativas >= estado.MAX_TENTATIVAS_VIDEO:
            log_terminal(f"[QUARENTENA] Vídeo {video_info['id']} ignorado após {tentativas} falhas.")
    estado.publicar_status(etapa="Produção interrompida por erro.", progresso=0, erro=info)
    _etapa_atual["nome"] = ""


def executar_ciclo_producao():
    """Executa um ciclo completo. Pedidos simultâneos são ignorados com segurança."""
    trava = estado.TravaCiclo()
    if not trava.adquirir():
        log_terminal("[CICLO] Já existe uma produção em andamento. Pedido ignorado.")
        return False

    try:
        estado.publicar_status(erro=None, proxima_tentativa_em=None)
        with Batimento():
            limpar_sobras_da_diretoria()
            vagas_shorts, vagas_longos = calcular_vagas()
            if not vagas_shorts and not vagas_longos:
                limite_estoque = VIDEO_SPECS["limite_estoque_max"]
                atualizar_status_producao(f"Estoque completo ({obter_quantidade_estoque()}/{limite_estoque}). Em pausa.")
                return False

            # Bloqueio anti-robô: nada é pedido ao YouTube até a pausa acabar. Regressão: o painel repetia "Buscando..."
            # e "Nenhum vídeo viral novo" a cada 30 s durante a pausa, sem dizer o motivo (25/11)
            pausa = youtube_pausado_ate()
            if pausa:
                atualizar_status_producao(f"YouTube em pausa até {pausa} por causa do bloqueio anti-robô. "
                                          "A produção volta sozinha depois disso.")
                return False

            # Sem a IA de roteiro nenhum vídeo pode ser narrado: nem vale baixar
            if not ia_respondendo():
                atualizar_status_producao(situacao_da_ia())
                return False

            _garantir_espaco_em_disco()
            limpar_video_bruto()

            precisa = max(vagas_shorts, VIDEO_SPECS["fontes_por_compilacao"] if vagas_longos else 0)
            atualizar_status_producao("Buscando os vídeos de GTA 6 mais virais da semana...", 5)
            candidatos = buscar_videos_virais(precisa + CANDIDATOS_EXTRAS)
            # O painel mostra em "Virais da vez" quais vídeos o Bruno escolheu
            estado.publicar_status(virais=[{"streamer": v["streamer"], "titulo": v.get("title", ""),
                                            "visualizacoes": v.get("visualizacoes") or 0} for v in candidatos])
            if not candidatos:
                atualizar_status_producao("Nenhum vídeo viral novo encontrado.")
                return False
            log_terminal("[VIRAIS] " + "; ".join(
                f"{v['streamer']} ({v.get('visualizacoes') or 0:,} visualizações)".replace(",", ".") for v in candidatos))
            return _produzir_virais(candidatos, vagas_shorts, vagas_longos, precisa)
    except Exception as e:
        _registrar_erro(e)
        return False
    finally:
        limpar_video_bruto()
        trava.liberar()


def calcular_espera(falhas_seguidas: int, intervalo_base: int = 30, espera_minima: int = 0) -> int:
    """Aumenta a espera a cada falha seguida, respeitando o tempo mínimo exigido pelo erro."""
    if falhas_seguidas <= 0:
        return max(intervalo_base, espera_minima)
    return max(espera_minima, min(intervalo_base * (2 ** falhas_seguidas), ESPERA_MAXIMA_S))


def _aguardar(segundos: int):
    """Aguarda mantendo o batimento do robô visível no painel."""
    fim = time.monotonic() + segundos
    while (restante := fim - time.monotonic()) > 0:
        estado.publicar_status()
        time.sleep(min(restante, INTERVALO_BATIMENTO_S))


def loop_vigia_continuo(intervalo_segundos: int = 30, max_iteracoes: int = None):
    """Loop principal de serviço em background."""
    log_terminal("=== ROBÔ VIGIA INICIADO: VÍDEOS VIRAIS DE GTA 6 ===")
    estado.publicar_status(etapa="Robô Vigia iniciado.", progresso=0)
    # Sobras de um ciclo interrompido pelo desligamento não servem mais
    limpar_video_bruto()
    falhas_seguidas = 0
    pausa_avisada = False
    iteracao = 0

    while max_iteracoes is None or iteracao < max_iteracoes:
        iteracao += 1
        espera_minima = 0
        try:
            if estado.producao_ativa():
                pausa_avisada = False
                if not estado.ciclo_em_andamento():
                    executar_ciclo_producao()
                erro = estado.ler_status().get("erro")
                falhas_seguidas = falhas_seguidas + 1 if erro else 0
                espera_minima = (erro or {}).get("espera_s", 0)
            elif not pausa_avisada:
                pausa_avisada = True
                atualizar_status_producao("Produção pausada pelo painel.")
        except Exception as e:
            falhas_seguidas += 1
            log_terminal(f"[ERRO] Falha não tratada no Robô Vigia: {e}")

        espera = calcular_espera(falhas_seguidas, intervalo_segundos, espera_minima)
        if falhas_seguidas:
            retorno = (datetime.now() + timedelta(seconds=espera)).strftime("%H:%M:%S")
            log_terminal(f"[AGUARDANDO] Nova tentativa às {retorno}.")
            estado.publicar_status(proxima_tentativa_em=retorno)
        _aguardar(espera)
