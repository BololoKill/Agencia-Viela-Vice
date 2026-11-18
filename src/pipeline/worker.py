"""
Módulo Worker de Produção Autônoma (Vigia de Lives).
Executa o ciclo contínuo: monitoramento -> download -> fatiamento -> renderização -> auditoria técnica.
"""
import time
import re
from pathlib import Path
from datetime import datetime
from src.config import EXPORT_DIR, VIDEO_BRUTO_DIR, STATUS_VIGIA_FILE, VIDEO_SPECS
from src.utils import load_json_safe, save_json_safe, log_terminal
from src.pipeline.searcher import buscar_melhor_live, registrar_historico
from src.pipeline.downloader import baixar_video
from src.pipeline.transcriber import extrair_audio_wav, transcrever_audio, fatiar_em_chunks, gerar_arquivo_srt
from src.pipeline.renderer import renderizar_short
from src.pipeline.quality import auditar_video

def limpar_video_bruto():
    """Remove arquivos intermediários na pasta de processamento bruto."""
    if VIDEO_BRUTO_DIR.exists():
        for f in VIDEO_BRUTO_DIR.iterdir():
            if f.is_file():
                try:
                    f.unlink()
                except Exception:
                    pass

def obter_quantidade_estoque():
    """Conta vídeos válidos aguardando na pasta de exportação."""
    if not EXPORT_DIR.exists():
        return 0
    return len([f for f in EXPORT_DIR.glob("*.mp4") if f.stat().st_size > 100_000])

def atualizar_status_producao(etapa: str, progresso_pct: int = 0, streamer: str = ""):
    """Publica status ao vivo para consumo da interface web do escritório virtual."""
    dados = {
        "etapa": etapa,
        "progresso": progresso_pct,
        "streamer": streamer,
        "atualizado_em": datetime.now().strftime("%H:%M:%S")
    }
    save_json_safe(STATUS_VIGIA_FILE, dados)

def executar_ciclo_producao():
    """Executa um ciclo único completo de produção."""
    limite_estoque = VIDEO_SPECS.get("limite_estoque_max", 24)
    estoque_atual = obter_quantidade_estoque()

    if estoque_atual >= limite_estoque:
        log_terminal(f"[ESTOQUE] Fila cheia ({estoque_atual}/{limite_estoque}). Aguardando aprovações da Diretoria...")
        atualizar_status_producao(f"Estoque completo ({estoque_atual}/{limite_estoque}). Em pausa.")
        return False

    atualizar_status_producao("Varrendo lives brasileiras...", 10)
    video_info = buscar_melhor_live()
    if not video_info:
        log_terminal("[BUSCA] Nenhuma live nova pendente encontrada no momento.")
        atualizar_status_producao("Nenhuma live nova encontrada.", 0)
        return False

    streamer = video_info["streamer"]
    titulo = video_info["title"]
    url = video_info["url"]
    log_terminal(f"[SELECIONADO] {streamer} | {titulo}")

    try:
        atualizar_status_producao(f"Baixando live de {streamer}...", 25, streamer)
        video_baixado = baixar_video(url)

        atualizar_status_producao(f"Extraindo áudio da live...", 45, streamer)
        audio_wav = VIDEO_BRUTO_DIR / "audio_temp.wav"
        extrair_audio_wav(video_baixado, audio_wav)

        atualizar_status_producao(f"Transcrevendo áudio em PT-BR (Whisper)...", 60, streamer)
        segmentos = transcrever_audio(audio_wav, model_name="base")
        chunks = fatiar_em_chunks(segmentos, duracao_alvo=65.0, max_chunks=3)

        streamer_slug = re.sub(r"[^a-z0-9]", "", streamer.lower())
        for idx, (st, en, segs) in enumerate(chunks):
            duracao = en - st
            if duracao < 15:
                continue

            pct = 70 + int((idx / len(chunks)) * 25)
            atualizar_status_producao(f"Renderizando Short {idx+1}/{len(chunks)} ({streamer})...", pct, streamer)

            srt_path = VIDEO_BRUTO_DIR / f"sub_{idx}.srt"
            gerar_arquivo_srt(segs, offset_base=max(0, st - 0.5), srt_output=srt_path)

            ts_id = int(time.time() * 1000)
            output_final = EXPORT_DIR / f"short-{streamer_slug}-corte{idx+1}-{ts_id}.mp4"

            renderizar_short(
                video_original=video_baixado,
                start_sec=st,
                duracao_corte=duracao,
                srt_path=srt_path,
                streamer=streamer,
                output_final=output_final
            )

            # Auditoria imediata de qualidade
            valido, motivo, score = auditar_video(output_final)
            if valido:
                log_terminal(f"[SUCESSO] Short aprovado pela auditoria técnica: {output_final.name} (Score: {score})")
            else:
                log_terminal(f"[AVISO] Short descartado pela auditoria: {motivo}")
                try:
                    output_final.unlink()
                except Exception:
                    pass

        registrar_historico(video_info["id"])
        registrar_historico(video_info["url"])
        atualizar_status_producao("Ciclo concluído com sucesso!", 100, streamer)
        return True

    except Exception as e:
        log_terminal(f"[ERRO NO PIPELINE]: {e}")
        atualizar_status_producao(f"Erro: {str(e)}", 0)
        return False
    finally:
        limpar_video_bruto()

def loop_vigia_continuo(intervalo_segundos: int = 30):
    """Loop principal de serviço em background."""
    log_terminal("=== ROBÔ VIGIA DE LIVES INICIADO (ARQUITETURA REESTRUTURADA) ===")
    while True:
        try:
            status = load_json_safe(STATUS_VIGIA_FILE, {"ativo": True})
            if status.get("ativo", True):
                executar_ciclo_producao()
            else:
                log_terminal("[PAUSA] Produção pausada pelo painel administrativo.")
        except Exception as e:
            log_terminal(f"[FALHA NÃO TRATADA]: {e}")

        # Resfriamento do hardware
        time.sleep(intervalo_segundos)
