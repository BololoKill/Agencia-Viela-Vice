"""
Módulo de Transcrição Whisper e Geração de Legendas.
"""
import threading
from pathlib import Path
import torch
import whisper
from src.config import VIDEO_SPECS
from src.pipeline.ffmpeg_runner import executar_ffmpeg
from src.utils import censor_text, log_terminal

_modelos = {}
_trava_modelo = threading.Lock()
POSICOES_AMOSTRA_IDIOMA = (0.2, 0.5, 0.8)
JANELA_MINIMA_IDIOMA_S = 2.0
DURACAO_BLOCO_IDIOMA_S = 5.0
PAUSA_ENTRE_BLOCOS_S = 0.8
CONTEXTO_WHISPER = (
    "Live brasileira de GTA 6 e GTA RP. Termos comuns: viatura, polícia, facção, fuga, "
    "perseguição, assalto, Vice City, Leonida, Lucia, Jason, mano, tá ligado."
)


def calcular_janela_transcricao(duracao_total: float, janela: float = None) -> tuple:
    """
    Define o trecho do vídeo enviado ao Whisper: (início em segundos, duração ou None para tudo).
    Pula a abertura e evita transcrever horas para aproveitar poucos cortes.
    """
    janela = float(janela or VIDEO_SPECS["janela_transcricao_s"])
    if not duracao_total or duracao_total <= 0:
        return 0.0, janela
    if duracao_total <= janela:
        return 0.0, None
    return round(min(duracao_total * 0.10, duracao_total - janela), 1), janela


def extrair_audio_wav(video_path: Path, output_wav: Path, inicio: float = 0.0, duracao: float = None) -> Path:
    """Extrai faixa de áudio em PCM mono 16kHz otimizada para o Whisper."""
    args = ["-ss", str(inicio)] if inicio else []
    args += ["-i", str(video_path)]
    if duracao:
        args += ["-t", str(duracao)]
    args += ["-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(output_wav), "-y"]
    executar_ffmpeg(args, etapa="extracao_audio")
    return output_wav


def _sem_memoria_na_placa(erro: Exception) -> bool:
    return "out of memory" in str(erro).lower()


def _esta_na_placa(modelo) -> bool:
    return getattr(getattr(modelo, "device", None), "type", "cpu") == "cuda"


def _carregar_modelo(model_name: str):
    """Prefere a placa de vídeo e usa o processador quando ela não está disponível ou não tem memória."""
    if not torch.cuda.is_available():
        return whisper.load_model(model_name, device="cpu")
    try:
        modelo = whisper.load_model(model_name, device="cuda")
        log_terminal("[WHISPER] Transcrição usando a placa de vídeo.")
        return modelo
    except RuntimeError as erro:
        if not _sem_memoria_na_placa(erro):
            raise
        log_terminal("[WHISPER] Placa de vídeo sem memória livre. Usando o processador.")
        return whisper.load_model(model_name, device="cpu")


def _obter_modelo(model_name: str):
    """Carrega o modelo uma única vez por processo."""
    with _trava_modelo:
        if model_name not in _modelos:
            _modelos[model_name] = _carregar_modelo(model_name)
        return _modelos[model_name]


def _mover_para_processador(model_name: str):
    """Recarrega o modelo no processador depois que a memória da placa acabou."""
    with _trava_modelo:
        torch.cuda.empty_cache()
        _modelos[model_name] = whisper.load_model(model_name, device="cpu")
        return _modelos[model_name]


def _probabilidades_idioma(audio_wav: Path) -> list:
    """Avalia o idioma em pontos diferentes do áudio, porque uma cutscene pode ocupar um trecho inteiro."""
    modelo = _obter_modelo(VIDEO_SPECS["modelo_whisper"])
    audio = whisper.load_audio(str(audio_wav))
    resultados = []
    for posicao in POSICOES_AMOSTRA_IDIOMA:
        inicio = max(0, int(len(audio) * posicao) - 15 * whisper.audio.SAMPLE_RATE)
        trecho = whisper.pad_or_trim(audio[inicio:])
        mel = whisper.log_mel_spectrogram(trecho, n_mels=modelo.dims.n_mels).to(modelo.device)
        _, probabilidades = modelo.detect_language(mel)
        resultados.append(probabilidades)
    return resultados


def _amostra_aceitavel(probabilidades: dict) -> bool:
    dominante = max(probabilidades, key=probabilidades.get)
    if dominante == "pt":
        return True
    return not (probabilidades[dominante] >= 0.6 and probabilidades.get("pt", 0.0) < 0.15)


def e_audio_em_portugues(audio_wav: Path) -> bool:
    """Recusa o vídeo só quando nenhum dos pontos avaliados tem fala em português."""
    return any(_amostra_aceitavel(p) for p in _probabilidades_idioma(audio_wav))


def _audio_do_segmento(audio, seg: dict, deslocamento: float):
    """Recorta a fala do segmento, com um mínimo de áudio para o idioma ser reconhecido."""
    taxa = whisper.audio.SAMPLE_RATE
    inicio = seg["start"] - deslocamento
    fim = seg["end"] - deslocamento
    folga = max(0.0, JANELA_MINIMA_IDIOMA_S - (fim - inicio)) / 2
    return audio[max(0, int((inicio - folga) * taxa)):max(0, int((fim + folga) * taxa))]


def _blocos_de_fala(segmentos: list) -> list:
    """Agrupa frases vizinhas: cada medição custa o mesmo, seja qual for o tamanho do trecho."""
    blocos = []
    atual = []
    for seg in segmentos:
        pausa_longa = atual and seg["start"] - atual[-1]["end"] > PAUSA_ENTRE_BLOCOS_S
        bloco_completo = atual and atual[-1]["end"] - atual[0]["start"] >= DURACAO_BLOCO_IDIOMA_S
        if pausa_longa or bloco_completo:
            blocos.append(atual)
            atual = []
        atual.append(seg)
    if atual:
        blocos.append(atual)
    return blocos


def identificar_idioma_dos_segmentos(audio_wav: Path, segmentos: list, deslocamento: float = 0.0,
                                     model_name: str = None) -> list:
    """Mede no próprio áudio a chance de cada fala estar em português."""
    if not segmentos:
        return []
    modelo = _obter_modelo(model_name or VIDEO_SPECS["modelo_whisper"])
    audio = whisper.load_audio(str(audio_wav))
    marcados = []
    for bloco in _blocos_de_fala(segmentos):
        janela = {"start": bloco[0]["start"], "end": bloco[-1]["end"]}
        trecho = whisper.pad_or_trim(_audio_do_segmento(audio, janela, deslocamento))
        mel = whisper.log_mel_spectrogram(trecho, n_mels=modelo.dims.n_mels).to(modelo.device)
        _, probabilidades = modelo.detect_language(mel)
        marcados.extend({**seg, "prob_pt": float(probabilidades.get("pt", 0.0))} for seg in bloco)
    return marcados


def _deslocar_segmento(seg: dict, deslocamento: float) -> dict:
    novo = {**seg, "start": seg["start"] + deslocamento, "end": seg["end"] + deslocamento}
    if seg.get("words"):
        novo["words"] = [
            {**p, "start": p["start"] + deslocamento, "end": p["end"] + deslocamento} for p in seg["words"]
        ]
    return novo


def _transcrever(modelo, audio_wav: Path) -> dict:
    return modelo.transcribe(
        str(audio_wav), language="pt", task="transcribe", fp16=_esta_na_placa(modelo), verbose=None,
        word_timestamps=True, initial_prompt=CONTEXTO_WHISPER, condition_on_previous_text=False,
    )


def transcrever_audio(audio_wav: Path, model_name: str = None, deslocamento: float = 0.0) -> list:
    """
    Transcreve áudio com Whisper em português brasileiro, com o tempo de cada palavra.
    Os tempos retornados são relativos ao vídeo original.
    """
    nome = model_name or VIDEO_SPECS["modelo_whisper"]
    modelo = _obter_modelo(nome)
    try:
        resultado = _transcrever(modelo, audio_wav)
    except RuntimeError as erro:
        if not (_esta_na_placa(modelo) and _sem_memoria_na_placa(erro)):
            raise
        log_terminal("[WHISPER] A memória da placa de vídeo acabou. Refazendo no processador.")
        resultado = _transcrever(_mover_para_processador(nome), audio_wav)
    return [_deslocar_segmento(seg, deslocamento) for seg in resultado.get("segments", [])]


def fatiar_em_chunks(segments: list, duracao_alvo: float = 65.0, max_chunks: int = 3) -> list:
    """
    Divide a transcrição em blocos contínuos de aproximadamente 60s a 75s.
    Retorna lista de tuplas: (start_time, end_time, segmentos_do_chunk).
    """
    if not segments:
        return []

    chunks = []
    chunk_atual = []
    chunk_start = segments[0]["start"]

    for seg in segments:
        chunk_atual.append(seg)
        duracao_corrente = seg["end"] - chunk_start
        if duracao_corrente >= duracao_alvo:
            chunks.append((chunk_start, seg["end"], list(chunk_atual)))
            chunk_atual = []
            if len(chunks) >= max_chunks:
                break
            chunk_start = seg["start"]

    if chunk_atual and len(chunks) < max_chunks:
        chunks.append((chunk_start, segments[-1]["end"], chunk_atual))

    return chunks


def gerar_arquivo_srt(segmentos: list, offset_base: float, srt_output: Path) -> Path:
    """Gera arquivo SRT limpo e com profanidades censuradas."""
    with open(srt_output, "w", encoding="utf-8") as f:
        idx = 1
        for s in segmentos:
            st = max(0.0, s["start"] - offset_base)
            en = max(st + 0.2, s["end"] - offset_base)
            t1 = f"{int(st//3600):02d}:{int((st%3600)//60):02d}:{int(st%60):02d},{int((st%1)*1000):03d}"
            t2 = f"{int(en//3600):02d}:{int((en%3600)//60):02d}:{int(en%60):02d},{int((en%1)*1000):03d}"
            texto = censor_text(s.get("text", "").strip())
            if texto:
                f.write(f"{idx}\n{t1} --> {t2}\n{texto}\n\n")
                idx += 1
    return srt_output
