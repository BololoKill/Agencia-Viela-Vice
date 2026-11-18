"""
SPEC-003 e SPEC-004: regressão do FFmpeg e padrão final dos Shorts.
Unitário + integração com FFmpeg real + E2E do renderizador.
"""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from apoio import AmbienteIsolado, gerar_audio, gerar_clipe, gerar_srt
from src.config import MARCA_PATH
from src.pipeline import ffmpeg_runner, renderer
from src.pipeline.ffmpeg_runner import FFmpegError, executar_ffmpeg
from src.pipeline.quality import auditar_video


class TestMontagemDeFiltros(unittest.TestCase):

    def test_caminho_windows_tem_dois_pontos_escapado(self):
        texto = ffmpeg_runner.escapar_caminho_filtro(Path(r"C:\Users\Barbara Bn3\sub.srt"))
        self.assertIn(r"C\:/Users/Barbara Bn3/sub.srt", texto)

    def test_legenda_nao_usa_aspas_duplas(self):
        """Regressão: aspas duplas + barra dupla geravam 'Unable to open' em todo render."""
        filtro = ffmpeg_runner.filtro_legendas(Path(r"C:\Users\Barbara Bn3\sub.srt"))
        self.assertTrue(filtro.startswith("subtitles=filename='"))
        self.assertNotIn('"', filtro)

    def test_todo_drawtext_tem_fonte_explicita(self):
        """Regressão: drawtext sem fonte derrubava o FFmpeg com 0xC0000005."""
        filtro = ffmpeg_runner.filtro_texto("@VielaVice", "fontcolor=white:fontsize=32:x=10:y=10")
        self.assertIn("fontfile='", filtro)

    def test_texto_perigoso_nao_quebra_o_filtro(self):
        limpo = ffmpeg_runner.limpar_texto_filtro("Davy Jones' (Gameplayrj): 100%")
        self.assertEqual(limpo, "Davy Jones (Gameplayrj) 100")

    def test_ambiente_aponta_para_fonts_conf(self):
        self.assertTrue(ffmpeg_runner.ambiente_ffmpeg()["FONTCONFIG_FILE"].endswith("fonts.conf"))


class TestDiagnosticoDeErro(unittest.TestCase):

    def test_erro_informa_etapa_e_motivo_real(self):
        with self.assertRaises(FFmpegError) as ctx:
            executar_ffmpeg(["-i", "arquivo-que-nao-existe.mp4", "saida.mp4"], etapa="corte")
        self.assertEqual(ctx.exception.etapa, "corte")
        self.assertIn("arquivo-que-nao-existe", str(ctx.exception))

    def test_crash_nativo_e_traduzido(self):
        falso = subprocess.CompletedProcess([], 3221225477, b"", b"Fontconfig error")
        with mock.patch.object(ffmpeg_runner.subprocess, "run", return_value=falso):
            with self.assertRaises(FFmpegError) as ctx:
                executar_ffmpeg(["-version"], etapa="legendas")
        self.assertIn("0xC0000005", str(ctx.exception))

    def test_travamento_vira_erro_com_timeout(self):
        expirou = subprocess.TimeoutExpired("ffmpeg", 1)
        with mock.patch.object(ffmpeg_runner.subprocess, "run", side_effect=expirou):
            with self.assertRaises(FFmpegError) as ctx:
                executar_ffmpeg(["-version"], etapa="concat", timeout=1)
        self.assertIn("tempo limite", str(ctx.exception))

    def test_ffmpeg_ausente_vira_erro_claro(self):
        with mock.patch.object(ffmpeg_runner.subprocess, "run", side_effect=FileNotFoundError()):
            with self.assertRaises(FFmpegError) as ctx:
                executar_ffmpeg(["-version"], etapa="corte")
        self.assertIn("não encontrado", str(ctx.exception))


class TestFFmpegReal(unittest.TestCase):

    def setUp(self):
        self.raiz = Path(tempfile.mkdtemp(prefix="viela"))
        self.addCleanup(shutil.rmtree, self.raiz, ignore_errors=True)

    def test_legenda_e_marca_em_caminho_hostil(self):
        """Caminho com espaço, acento, colchete, vírgula e apóstrofo."""
        pasta = self.raiz / "Bárbara Bn3 [viela], d'água"
        pasta.mkdir()
        clip = gerar_clipe(pasta / "clip.mp4", duracao=2)
        srt = gerar_srt(pasta / "sub.srt")
        saida = pasta / "saida.mp4"
        vf = f"{ffmpeg_runner.filtro_legendas(srt)}," + ffmpeg_runner.filtro_texto(
            "@VielaVice", "fontcolor=white:fontsize=32:x=10:y=10")
        executar_ffmpeg(["-i", str(clip), "-vf", vf, "-preset", "ultrafast", str(saida), "-y"], etapa="teste")
        self.assertGreater(saida.stat().st_size, 1000)

    def test_detecta_tela_preta_no_trecho_analisado(self):
        video = self.raiz / "preto.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            "testsrc2=size=320x240:rate=10:duration=6,drawbox=enable='between(t,2,4)':color=black:t=fill",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(video),
        ], check=True, capture_output=True)
        telas = ffmpeg_runner.detectar_telas_pretas(video, inicio=0.0)
        self.assertEqual(len(telas), 1)
        self.assertAlmostEqual(telas[0][0], 2.0, delta=0.5)
        self.assertAlmostEqual(telas[0][1], 4.0, delta=0.5)


class TestRenderizadorE2E(AmbienteIsolado):

    def setUp(self):
        super().setUp()
        self.cta = gerar_audio(self.raiz / "cta.mp3", duracao=3)
        for nome, valor in (("CTA_AUDIO", self.cta), ("PRESET_FINAL", "ultrafast")):
            patcher = mock.patch.object(renderer, nome, valor)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(renderer, "criar_narração_intro",
                                    side_effect=lambda _s, destino: gerar_audio(destino))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.clip = gerar_clipe(self.raiz / "live.mp4", duracao=22)
        self.segmentos = [
            {
                "start": 1.0 + 2 * i, "end": 3.0 + 2 * i, "text": "olha só a polícia",
                "words": [{"word": f" {p}", "start": 1.0 + 2 * i + j * 0.5, "end": 1.5 + 2 * i + j * 0.5}
                          for j, p in enumerate(["olha", "só", "a", "polícia"])],
            }
            for i in range(8)
        ]
        self.final = self.export_dir / "short-luqueta-corte1.mp4"

    def _renderizar(self):
        return renderer.renderizar_short(
            self.clip, self.segmentos, "Davy Jones (Gameplayrj)", self.final, gancho="A POLÍCIA PEGOU ELE")

    def _sonda(self, caminho):
        saida = subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height,pix_fmt", "-of", "json", str(caminho)])
        return json.loads(saida)["streams"][0]

    def _volume_na_frequencia_do_cta(self, inicio, duracao):
        resultado = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostdin", "-ss", str(inicio), "-t", str(duracao), "-i", str(self.final),
             "-af", "bandpass=f=330:width_type=h:w=30,volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, errors="replace")
        return float(re.search(r"mean_volume: (-?[\d.]+)", resultado.stderr).group(1))

    def test_short_sai_no_padrao_com_a_marca_e_sem_residuos(self):
        with mock.patch.object(renderer, "executar_ffmpeg", wraps=renderer.executar_ffmpeg) as ffmpeg:
            self._renderizar()
        stream = self._sonda(self.final)
        self.assertEqual((stream["width"], stream["height"], stream["pix_fmt"]), (1080, 1920, "yuv420p"))
        aprovado, motivo, _ = auditar_video(self.final)
        self.assertTrue(aprovado, motivo)
        passo_final = next(c for c in ffmpeg.call_args_list if c.kwargs.get("etapa") == "final")
        args = passo_final.args[0]
        posicao_marca = args.index(str(MARCA_PATH))
        self.assertEqual(args[posicao_marca - 3:posicao_marca - 1], ["-loop", "1"], "a marca precisa ficar no vídeo inteiro")
        self.assertEqual(list(self.bruto_dir.iterdir()), [])

    def test_narracao_final_fica_audivel_sobre_o_jogo(self):
        """Regressão: a chamada final começava atrasada e era cortada pelo fim do vídeo."""
        self._renderizar()
        total = renderer.obter_duracao_audio(self.final)
        meio = self._volume_na_frequencia_do_cta(6.0, 3.0)
        inicio_da_chamada = self._volume_na_frequencia_do_cta(total - 3.8, 0.9)
        self.assertGreater(inicio_da_chamada, meio + 12, f"meio={meio} dB, início da chamada={inicio_da_chamada} dB")

    def test_audio_continuo_e_do_tamanho_exato_da_imagem(self):
        """Regressão: 3,5 s de som ficavam amontoados na emenda da abertura e a fala saía da imagem."""
        self._renderizar()
        medida = ffmpeg_runner.medir_linha_do_tempo(self.final)
        self.assertLessEqual(medida["pacotes_amontoados"], 1)
        self.assertAlmostEqual(medida["audio_s"], medida["video_s"], delta=0.08)

    def test_arquivo_dessincronizado_e_recusado(self):
        medida = {"audio_s": 39.6, "video_s": 36.1, "pacotes_amontoados": 150}
        with mock.patch.object(ffmpeg_runner, "medir_linha_do_tempo", return_value=medida):
            with self.assertRaises(FFmpegError) as ctx:
                ffmpeg_runner.garantir_sincronia("qualquer.mp4")
        self.assertEqual(ctx.exception.etapa, "sincronia")

    def test_falha_nao_publica_video_parcial_nem_deixa_lixo(self):
        real = renderer.executar_ffmpeg

        def falha_no_fim(args, etapa, **kw):
            if etapa == "final":
                raise FFmpegError(etapa, 1, "falha simulada")
            return real(args, etapa=etapa, **kw)

        with mock.patch.object(renderer, "executar_ffmpeg", side_effect=falha_no_fim):
            with self.assertRaises(FFmpegError):
                self._renderizar()
        self.assertEqual(list(self.export_dir.glob("*.mp4")), [])
        self.assertEqual(list(self.bruto_dir.iterdir()), [])


class TestVideoLongoE2E(AmbienteIsolado):

    def setUp(self):
        super().setUp()
        self.cta = gerar_audio(self.raiz / "cta.mp3", duracao=3)
        patcher = mock.patch.object(renderer, "CTA_AUDIO", self.cta)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(renderer, "criar_narracao_longo",
                                    side_effect=lambda _s, _p, destino: gerar_audio(destino))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.clip = gerar_clipe(self.raiz / "live.mp4", duracao=24)
        self.final = self.export_dir / "longo-luqueta-parte1-1.mp4"

    def test_longo_sai_horizontal_sincronizado_e_sem_residuos(self):
        renderer.renderizar_longo(self.clip, 1.0, 20.0, "Davy Jones (Gameplayrj)", 1, self.final)
        saida = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                         "stream=width,height,pix_fmt", "-of", "json", str(self.final)])
        stream = json.loads(saida)["streams"][0]
        self.assertEqual((stream["width"], stream["height"], stream["pix_fmt"]), (1280, 720, "yuv420p"))
        medida = ffmpeg_runner.medir_linha_do_tempo(self.final)
        self.assertAlmostEqual(medida["video_s"], 20.0, delta=0.1)
        self.assertAlmostEqual(medida["audio_s"], medida["video_s"], delta=0.08)
        self.assertEqual(medida["pacotes_amontoados"], 0)
        self.assertEqual(list(self.bruto_dir.iterdir()), [])

    def test_tela_preta_e_retirada_do_longo(self):
        renderer.renderizar_longo(self.clip, 1.0, 20.0, "Luqueta", 2, self.final, bloqueios=[(8.0, 12.0)])
        self.assertAlmostEqual(ffmpeg_runner.medir_linha_do_tempo(self.final)["video_s"], 16.0, delta=0.1)

    def test_falha_nao_publica_longo_parcial(self):
        with mock.patch.object(renderer, "executar_ffmpeg", side_effect=FFmpegError("longo", 1, "falha simulada")):
            with self.assertRaises(FFmpegError):
                renderer.renderizar_longo(self.clip, 1.0, 20.0, "Luqueta", 1, self.final)
        self.assertFalse(self.final.exists())
        self.assertEqual(list(self.bruto_dir.iterdir()), [])


class TestCodificadorDoVideoFinal(AmbienteIsolado):

    def _renderizar_final(self, disponivel, efeito=None):
        with mock.patch.object(renderer, "quick_sync_disponivel", return_value=disponivel), \
                mock.patch.object(renderer, "executar_ffmpeg", side_effect=efeito) as ffmpeg:
            renderer._renderizar_final(Path("intro.mp4"), Path("conteudo.mp4"), 900, Path("final.mp4"))
        return [c.args[0] for c in ffmpeg.call_args_list]

    def test_usa_a_placa_intel_quando_disponivel(self):
        chamadas = self._renderizar_final(True)
        self.assertEqual(len(chamadas), 1)
        self.assertIn("h264_qsv", chamadas[0])
        self.assertNotIn("-crf", chamadas[0])

    def test_sem_placa_compativel_usa_o_processador(self):
        chamadas = self._renderizar_final(False)
        self.assertIn("libx264", chamadas[0])
        self.assertIn("-crf", chamadas[0])

    def test_falha_na_placa_refaz_no_processador(self):
        chamadas = self._renderizar_final(True, efeito=[FFmpegError("final", 1, "qsv indisponível"), None])
        self.assertIn("h264_qsv", chamadas[0])
        self.assertIn("libx264", chamadas[1])

    def test_falha_no_processador_nao_e_repetida(self):
        with self.assertRaises(FFmpegError):
            self._renderizar_final(False, efeito=FFmpegError("final", 1, "erro real"))


class TestSincroniaDeFalaEImagem(AmbienteIsolado):
    """Um clarão e um bipe nascem juntos na live e precisam continuar juntos depois dos cortes."""

    INSTANTES = [6.7, 9.1, 11.9, 14.3, 17.2, 19.6, 22.5, 24.8, 27.7, 30.1, 33.0, 35.4]

    def setUp(self):
        super().setUp()
        self.cta = gerar_audio(self.raiz / "cta.mp3", duracao=3)
        for nome, valor in (("CTA_AUDIO", self.cta), ("PRESET_FINAL", "ultrafast")):
            patcher = mock.patch.object(renderer, nome, valor)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(renderer, "criar_narração_intro",
                                    side_effect=lambda _s, destino: gerar_audio(destino))
        patcher.start()
        self.addCleanup(patcher.stop)

    def _gerar_live(self) -> Path:
        destino = self.raiz / "live_sincronia.mp4"
        claroes = "+".join(f"between(t,{t},{t + 0.07})" for t in self.INSTANTES)
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            f"color=c=black:s=1280x720:r=59.94:d=40,drawbox=enable='{claroes}':color=white:t=fill",
            "-f", "lavfi", "-i", f"aevalsrc='0.8*sin(2*PI*1000*t)*gt({claroes},0)':s=48000:d=40",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", str(destino),
        ], check=True, capture_output=True)
        return destino

    def _segmentos(self) -> list:
        segmentos = []
        for t in self.INSTANTES:
            palavras = [{"word": f" fala{i}", "start": t - 0.6 + i * 0.4, "end": t - 0.25 + i * 0.4} for i in range(4)]
            segmentos.append({"start": palavras[0]["start"], "end": palavras[-1]["end"],
                              "text": "fala fala fala fala", "words": palavras})
        return segmentos

    def _instantes_do_som(self, video: Path) -> list:
        bruto = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostdin", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "8000",
             "-af", "bandpass=f=1000:width_type=h:w=120", "-f", "s16le", "-"], capture_output=True).stdout
        sinal = np.abs(np.frombuffer(bruto, dtype=np.int16).astype(np.float32))
        envelope = np.convolve(sinal, np.ones(40) / 40, mode="same")
        return self._subidas(envelope, envelope.max() * 0.4, 8000)

    def _instantes_da_imagem(self, video: Path) -> list:
        bruto = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostdin", "-v", "error", "-i", str(video), "-an", "-vf",
             "crop=300:300:390:800,scale=2:2,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
        brilho = np.frombuffer(bruto, dtype=np.uint8).reshape(-1, 4).mean(axis=1)
        return self._subidas(brilho, 128, 30)

    @staticmethod
    def _subidas(sinal, limite, taxa) -> list:
        instantes = []
        for i in np.flatnonzero((sinal[1:] >= limite) & (sinal[:-1] < limite)) + 1:
            if not instantes or i / taxa - instantes[-1] > 0.3:
                instantes.append(i / taxa)
        return instantes

    def test_fala_e_imagem_seguem_juntas_do_primeiro_ao_ultimo_corte(self):
        final = self.export_dir / "short-sincronia.mp4"
        renderer.renderizar_short(self._gerar_live(), self._segmentos(), "Luqueta", final, gancho="TESTE DE SINCRONIA")
        som, imagem = self._instantes_do_som(final), self._instantes_da_imagem(final)
        antes_da_chamada = renderer.obter_duracao_audio(final) - renderer.DURACAO_MINIMA_CTA - 0.5
        imagem = [t for t in imagem if t < antes_da_chamada]
        self.assertGreaterEqual(len(imagem), 8)
        for i, instante in enumerate(imagem):
            distancia = min(abs(instante - s) for s in som)
            self.assertLessEqual(distancia, 0.05, f"corte {i}: imagem em {instante:.3f}s longe do som")


if __name__ == "__main__":
    unittest.main()
