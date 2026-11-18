"""
Módulo Worker de Produção Autônoma (Vigia de Lives).
Executa o ciclo contínuo: monitoramento -> download -> fatiamento -> renderização -> auditoria técnica.
"""
import errno
import re
import shutil
import threading
import time
from datetime import datetime, timedelta
from src.config import EXPORT_DIR, VIDEO_BRUTO_DIR, VIDEO_SPECS, METADADOS_FILE
from src.utils import load_json_safe, log_terminal, save_json_safe
from src.pipeline import estado
from src.pipeline.edicao import (
    DURACAO_MINIMA_CORTE_S, filtrar_fala_em_portugues, gerar_gancho, montar_publicacao, montar_publicacao_longa,
    planejar_longos, selecionar_melhores_cortes
)
from src.pipeline.ffmpeg_runner import detectar_telas_pretas
from src.pipeline.searcher import buscar_melhor_live, registrar_historico
from src.pipeline.downloader import baixar_video
from src.pipeline.transcriber import (
    calcular_janela_transcricao, e_audio_em_portugues, extrair_audio_wav, identificar_idioma_dos_segmentos,
    transcrever_audio
)
from src.pipeline.renderer import obter_duracao_audio, renderizar_longo, renderizar_short
from src.pipeline.quality import auditar_video

ESPERA_MAXIMA_S = 900
ESPACO_MINIMO_BYTES = 5 * 1024 ** 3
INTERVALO_BATIMENTO_S = 10
INTERVALO_LOG_ANDAMENTO_S = 60
PREFIXO_LONGO = "longo-"

_etapa_atual = {"nome": "", "desde": time.monotonic()}


def limpar_video_bruto():
    """Remove arquivos intermediários na pasta de processamento bruto."""
    if VIDEO_BRUTO_DIR.exists():
        for f in VIDEO_BRUTO_DIR.iterdir():
            if f.is_file():
                try:
                    f.unlink()
                except Exception:
                    pass


def contar_estoque() -> tuple:
    """Conta os vídeos válidos aguardando aprovação: (Shorts, Longos)."""
    if not EXPORT_DIR.exists():
        return 0, 0
    videos = [f.name for f in EXPORT_DIR.glob("*.mp4") if f.stat().st_size > 100_000]
    longos = sum(nome.startswith(PREFIXO_LONGO) for nome in videos)
    return len(videos) - longos, longos


def obter_quantidade_estoque():
    """Conta todos os vídeos válidos aguardando na pasta de exportação."""
    return sum(contar_estoque())


def calcular_vagas() -> tuple:
    """Define quantos Shorts e Longos cabem neste ciclo sem passar do estoque de 60 vídeos."""
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


def _salvar_metadados(nome_arquivo: str, publicacao: dict, video_info: dict):
    """Guarda título e descrição do vídeo para o painel do gerente."""
    metadados = load_json_safe(METADADOS_FILE, {})
    metadados = metadados if isinstance(metadados, dict) else {}
    metadados[nome_arquivo] = {
        **publicacao,
        "streamer": video_info["streamer"],
        "origem": video_info.get("origem", "gta_rp"),
    }
    save_json_safe(METADADOS_FILE, metadados)


def _renderizar_cortes(video_baixado, chunks: list, video_info: dict, bloqueios: list) -> tuple:
    """Renderiza cada corte de forma independente. Retorna (aprovados, tentados, último erro)."""
    aprovados = 0
    tentados = 0
    ultimo_erro = None
    streamer = video_info["streamer"]
    streamer_slug = re.sub(r"[^a-z0-9]", "", streamer.lower()) or "gta6"

    for idx, (st, en, segs) in enumerate(chunks):
        duracao = en - st
        if duracao < 15:
            continue

        tentados += 1
        pct = 70 + int((idx / len(chunks)) * 25)
        atualizar_status_producao(f"Renderizando Short {idx+1}/{len(chunks)} ({streamer})...", pct, streamer)

        output_final = EXPORT_DIR / f"short-{streamer_slug}-corte{idx+1}-{int(time.time() * 1000)}.mp4"
        gancho = gerar_gancho(segs, streamer)
        try:
            renderizar_short(
                video_original=video_baixado,
                segmentos=segs,
                streamer=streamer,
                output_final=output_final,
                gancho=gancho,
                bloqueios=bloqueios
            )
        except Exception as e:
            ultimo_erro = e
            log_terminal(f"[ERRO] Short {idx+1} não renderizado: {e}")
            continue

        valido, motivo, score = auditar_video(output_final)
        if valido:
            aprovados += 1
            publicacao = montar_publicacao(gancho, streamer, semente=int(time.time()) + idx)
            _salvar_metadados(output_final.name, publicacao, video_info)
            log_terminal(f"[SUCESSO] Short aprovado pela auditoria técnica: {output_final.name} (Score: {score})")
        else:
            log_terminal(f"[AVISO] Short descartado pela auditoria: {motivo}")
            try:
                output_final.unlink()
            except OSError:
                pass

    return aprovados, tentados, ultimo_erro


def _renderizar_longos(video_baixado, video_info: dict, vagas: int) -> tuple:
    """Monta os vídeos longos da gravação. Retorna (aprovados, último erro)."""
    partes = planejar_longos(obter_duracao_audio(video_baixado), quantidade=vagas, alvo=VIDEO_SPECS["duracao_longo_s"],
                             minimo=VIDEO_SPECS["duracao_minima_longo_s"])
    if not partes:
        return 0, None

    streamer = video_info["streamer"]
    slug = re.sub(r"[^a-z0-9]", "", streamer.lower()) or "gta6"
    bloqueios = detectar_telas_pretas(video_baixado)
    aprovados = 0
    ultimo_erro = None
    for parte, (inicio, duracao) in enumerate(partes, 1):
        atualizar_status_producao(f"Montando vídeo longo {parte}/{len(partes)} ({streamer})...", 96, streamer)
        output_final = EXPORT_DIR / f"{PREFIXO_LONGO}{slug}-parte{parte}-{int(time.time() * 1000)}.mp4"
        try:
            renderizar_longo(video_original=video_baixado, inicio=inicio, duracao=duracao, streamer=streamer,
                             parte=parte, output_final=output_final, bloqueios=bloqueios)
        except Exception as e:
            ultimo_erro = e
            log_terminal(f"[ERRO] Vídeo longo {parte} não renderizado: {e}")
            continue

        valido, motivo, score = auditar_video(output_final)
        if valido:
            aprovados += 1
            publicacao = montar_publicacao_longa(streamer, parte, semente=int(time.time()) + parte)
            _salvar_metadados(output_final.name, publicacao, video_info)
            log_terminal(f"[SUCESSO] Vídeo longo aprovado pela auditoria técnica: {output_final.name} (Score: {score})")
        else:
            log_terminal(f"[AVISO] Vídeo longo descartado pela auditoria: {motivo}")
            try:
                output_final.unlink()
            except OSError:
                pass
    return aprovados, ultimo_erro


def _produzir(video_info: dict, vagas_shorts: int, vagas_longos: int) -> bool:
    """Processa uma live selecionada, do download à auditoria."""
    streamer = video_info["streamer"]
    ao_vivo = bool(video_info.get("ao_vivo"))
    captura = VIDEO_SPECS["captura_live_s"]
    log_terminal(f"[SELECIONADO] {video_info.get('origem', 'gta_rp')} | {streamer} | {video_info['title']}")

    etapa_download = f"Gravando live de {streamer} no ar ({captura // 60} min)..." if ao_vivo else f"Baixando vídeo de {streamer}..."
    atualizar_status_producao(etapa_download, 25, streamer)
    video_baixado = baixar_video(video_info["url"], ao_vivo=ao_vivo, duracao_captura=captura)

    atualizar_status_producao("Extraindo áudio da live...", 45, streamer)
    audio_wav = VIDEO_BRUTO_DIR / "audio_temp.wav"
    duracao_total = video_info.get("duration") or (captura if ao_vivo else 0)
    inicio, duracao = calcular_janela_transcricao(duracao_total)
    extrair_audio_wav(video_baixado, audio_wav, inicio=inicio, duracao=duracao)

    if not e_audio_em_portugues(audio_wav):
        log_terminal(f"[AVISO] Áudio fora do português, vídeo ignorado: {video_info['title']}")
        registrar_historico(video_info["id"])
        registrar_historico(video_info["url"])
        atualizar_status_producao("Vídeo em outro idioma. Buscando outro.", 0)
        return False

    atualizar_status_producao("Transcrevendo áudio em PT-BR (Whisper)...", 60, streamer)
    segmentos = transcrever_audio(audio_wav, deslocamento=inicio)
    atualizar_status_producao("Separando a fala do streamer dos diálogos do jogo...", 65, streamer)
    medidos = identificar_idioma_dos_segmentos(audio_wav, segmentos, deslocamento=inicio)
    falas = filtrar_fala_em_portugues(medidos)
    if len(falas) < len(medidos):
        log_terminal(f"[IDIOMA] {len(medidos) - len(falas)} de {len(medidos)} falas fora do português foram ignoradas.")
    bloqueios = detectar_telas_pretas(video_baixado, inicio, duracao)
    chunks = selecionar_melhores_cortes(
        falas, duracao_alvo=VIDEO_SPECS["duracao_conteudo_s"], max_cortes=vagas_shorts, bloqueios=bloqueios
    ) if vagas_shorts else []

    aprovados, tentados, ultimo_erro = _renderizar_cortes(video_baixado, chunks, video_info, bloqueios)

    # O vídeo longo só faz sentido quando há streamer falando português na gravação
    tem_fala = sum(seg["end"] - seg["start"] for seg in falas) >= DURACAO_MINIMA_CORTE_S
    longos = 0
    if vagas_longos and tem_fala:
        longos, erro_longo = _renderizar_longos(video_baixado, video_info, vagas_longos)
        ultimo_erro = ultimo_erro or erro_longo
    aprovados += longos

    if tentados == 0 and longos == 0 and ultimo_erro is None:
        log_terminal(f"[AVISO] Live sem fala aproveitável: {video_info['title']}")
        registrar_historico(video_info["id"])
        registrar_historico(video_info["url"])
        atualizar_status_producao("Live sem fala aproveitável. Buscando outra.", 0)
        return False
    if aprovados == 0:
        raise ultimo_erro or RuntimeError("Nenhum corte foi aprovado pela auditoria técnica.")

    registrar_historico(video_info["id"])
    registrar_historico(video_info["url"])
    atualizar_status_producao(f"Ciclo concluído: {aprovados - longos} Short(s) e {longos} vídeo(s) longo(s) pronto(s)!", 100, streamer)
    return True


def _registrar_erro(erro: Exception, video_info: dict):
    """Publica o diagnóstico da falha e contabiliza erros definitivos do vídeo."""
    info = estado.classificar_erro(erro)
    log_terminal(f"[ERRO] {info['categoria'].upper()}: {info['mensagem']}")
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

    video_info = None
    try:
        estado.publicar_status(erro=None, proxima_tentativa_em=None)
        with Batimento():
            vagas_shorts, vagas_longos = calcular_vagas()
            if not vagas_shorts and not vagas_longos:
                limite_estoque = VIDEO_SPECS["limite_estoque_max"]
                atualizar_status_producao(f"Estoque completo ({obter_quantidade_estoque()}/{limite_estoque}). Em pausa.")
                return False

            _garantir_espaco_em_disco()
            limpar_video_bruto()

            atualizar_status_producao("Varrendo lives brasileiras...", 10)
            video_info = buscar_melhor_live()
            if not video_info:
                atualizar_status_producao("Nenhuma live nova encontrada.")
                return False
            return _produzir(video_info, vagas_shorts, vagas_longos)
    except Exception as e:
        _registrar_erro(e, video_info)
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
    log_terminal("=== ROBÔ VIGIA DE LIVES INICIADO ===")
    estado.publicar_status(etapa="Robô Vigia iniciado.", progresso=0)
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
