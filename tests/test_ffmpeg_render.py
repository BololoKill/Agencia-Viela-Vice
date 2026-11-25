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
        texto = ffmpeg_runner.escapar_caminho_filtro(Path(r"C:\Users\Dono Viela\sub.srt"))
        self.assertIn(r"C\:/Users/Dono Viela/sub.srt", texto)

    def test_legenda_nao_usa_aspas_duplas(self):
        """Regressão: aspas duplas + barra dupla geravam 'Unable to open' em todo render."""
        filtro = ffmpeg_runner.filtro_legendas(Path(r"C:\Users\Dono Viela\sub.srt"))
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
        pasta = self.raiz / "Dôno Viela [viela], d'água"
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


def quadro_rgb(video, instante, largura, altura):
    bruto = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(instante), "-i", str(video), "-frames:v", "1",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(bruto, dtype=np.uint8).reshape(altura, largura, 3).astype(float)


class TestRenderizadorE2E(AmbienteIsolado):

    def setUp(self):
        super().setUp()
        self.cta = gerar_audio(self.raiz / "cta.mp3", duracao=3)
        for nome, valor in (("CTA_AUDIO", self.cta), ("PRESET_FINAL", "ultrafast")):
            patcher = mock.patch.object(renderer, nome, valor)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(renderer, "criar_narração_intro",
                                    side_effect=lambda _s, destino, **_kw: gerar_audio(destino))
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

    def test_marca_dagua_do_short_tem_aro_claro_do_inicio_ao_fim(self):
        self._renderizar()
        total = renderer.obter_duracao_audio(self.final)
        lado = renderer.MARCA_SHORT + 2 * renderer.ARO_MARCA
        centro_x = 1080 - 30 - lado // 2
        topo = renderer.TOPO_GAMEPLAY + 24
        for instante in (0.3, total / 2, total - 0.3):
            with self.subTest(instante=instante):
                quadro = quadro_rgb(self.final, instante, 1080, 1920)
                self.assertGreater(quadro[topo + renderer.ARO_MARCA // 2 + 1, centro_x - 1:centro_x + 2].mean(), 200)

    def test_short_usa_a_narracao_do_roteiro(self):
        with mock.patch.object(renderer, "criar_narração_intro", side_effect=lambda _s, destino, **_kw: gerar_audio(destino)) as narrar:
            renderer.renderizar_short(self.clip, self.segmentos, "Luqueta", self.final, gancho="A FUGA",
                                      narracao_roteiro="Ele achou que ia escapar, mas a polícia tinha outros planos.")
        self.assertEqual(narrar.call_args.kwargs["texto"], "Ele achou que ia escapar, mas a polícia tinha outros planos.")

    def test_narracao_comprida_nao_deixa_o_short_passar_de_um_minuto(self):
        with mock.patch.object(renderer, "criar_narração_intro", side_effect=lambda _s, destino, **_kw: gerar_audio(destino, duracao=12)),                 mock.patch.object(renderer.edicao, "calcular_trechos_uteis", wraps=renderer.edicao.calcular_trechos_uteis) as trechos:
            self._renderizar()
        self.assertLessEqual(trechos.call_args.kwargs["duracao_max"], renderer.DURACAO_MAXIMA_SHORT - 12)

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

    def _volume_em(self, inicio, duracao, frequencia):
        resultado = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostdin", "-ss", str(inicio), "-t", str(duracao), "-i", str(self.final),
             "-af", f"bandpass=f={frequencia}:width_type=h:w=30,volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, errors="replace")
        return float(re.search(r"mean_volume: (-?[\d.]+)", resultado.stderr).group(1))

    def test_roteiro_narra_abertura_e_capitulos_com_o_jogo_mais_baixo(self):
        falas = []

        def tts(texto, destino, rate="+0%"):
            falas.append(texto)
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=880:duration=1.5", str(destino)],
                           check=True, capture_output=True)
            return destino

        with mock.patch.object(renderer, "_gerar_tts_com_retentativa", side_effect=tts), \
                mock.patch.object(renderer, "_codificar", wraps=renderer._codificar) as codificar:
            renderer.renderizar_longo(self.clip, 1.0, 20.0, "Luqueta", 1, self.final, abertura="Abertura do roteiro",
                                      narracoes=[(0.0, "Primeiro capitulo"), (7.0, "Capitulo dois"), (19.0, "Em cima da chamada final")])
        self.assertEqual(falas[0], "Abertura do roteiro")
        medida = ffmpeg_runner.medir_linha_do_tempo(self.final)
        self.assertAlmostEqual(medida["audio_s"], medida["video_s"], delta=0.08)
        self.assertEqual(medida["pacotes_amontoados"], 0)
        silencio = self._volume_em(12.5, 1.0, 880)
        # O primeiro capítulo espera a abertura (1,5 s) terminar e entra logo depois dela
        self.assertGreater(self._volume_em(3.2, 0.8, 880), silencio + 15)
        self.assertGreater(self._volume_em(7.2, 1.0, 880), silencio + 15)
        self.assertLess(self._volume_em(19.0, 0.8, 880), silencio + 6, "narração em cima da chamada final fica de fora")
        grafo = " ".join(codificar.call_args.args[0])
        self.assertIn("Capitulo dois", grafo, "a fala do narrador aparece escrita na tela")
        self.assertEqual(list(self.bruto_dir.iterdir()), [])

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

    def _live_que_muda_de_resolucao(self, trechos=(("1280x720", 12), ("1920x1080", 12))) -> Path:
        """Simula a Twitch trocando de resolução no meio da gravação, como acontece nos comerciais."""
        destino = self.raiz / "live_mista.ts"
        deslocamento = 0
        with open(destino, "wb") as saida:
            for indice, (tamanho, duracao) in enumerate(trechos):
                parte = self.raiz / f"parte{indice}.ts"
                subprocess.run(
                    ["ffmpeg", "-y", "-f", "lavfi", "-i", f"testsrc2=size={tamanho}:rate=30:duration={duracao}",
                     "-f", "lavfi", "-i", f"sine=frequency=440:duration={duracao}", "-c:v", "libx264", "-preset", "ultrafast",
                     "-pix_fmt", "yuv420p", "-c:a", "aac", "-output_ts_offset", str(deslocamento), "-f", "mpegts", str(parte)],
                    check=True, capture_output=True)
                saida.write(parte.read_bytes())
                deslocamento += duracao
        return destino

    def test_troca_de_resolucao_na_live_nao_quebra_o_som(self):
        """Regressão: a troca reiniciava a edição no meio e o som saía com minutos a mais."""
        renderer.renderizar_longo(self._live_que_muda_de_resolucao(), 1.0, 20.0, "Luqueta", 1, self.final)
        medida = ffmpeg_runner.medir_linha_do_tempo(self.final)
        self.assertAlmostEqual(medida["video_s"], 20.0, delta=0.1)
        self.assertAlmostEqual(medida["audio_s"], medida["video_s"], delta=0.08)
        self.assertEqual(medida["pacotes_amontoados"], 0)

    def test_comercial_da_twitch_e_localizado_pela_resolucao(self):
        live = self._live_que_muda_de_resolucao((("1280x720", 14), ("1920x1080", 6), ("1280x720", 10)))
        trechos = ffmpeg_runner.detectar_intervalos_comerciais(live)
        self.assertEqual(len(trechos), 1)
        self.assertAlmostEqual(trechos[0][0], 14.0 - ffmpeg_runner.MARGEM_COMERCIAL_S, delta=0.3)
        self.assertAlmostEqual(trechos[0][1], 20.0 + ffmpeg_runner.MARGEM_COMERCIAL_S, delta=0.3)

    def test_live_em_resolucao_unica_nao_tem_comercial(self):
        self.assertEqual(ffmpeg_runner.detectar_intervalos_comerciais(self.clip), [])

    def test_arquivo_invalido_nao_impede_a_edicao(self):
        falso = self.raiz / "falso.mp4"
        falso.write_bytes(b"nada")
        self.assertEqual(ffmpeg_runner.detectar_intervalos_comerciais(falso), [])

    def test_mudanca_duradoura_de_resolucao_nao_e_comercial(self):
        quadros = "0.0,1280,720\n1000.0,1920,1080\n1500.0,1920,1080\n1990.0,1920,1080\n"
        with mock.patch.object(ffmpeg_runner.subprocess, "check_output", return_value=quadros):
            self.assertEqual(ffmpeg_runner.detectar_intervalos_comerciais("live.mp4"), [])

    def test_marca_dagua_tem_aro_claro_do_inicio_ao_fim(self):
        """A marca precisa aparecer sobre qualquer imagem da live, inclusive na abertura e no encerramento."""
        renderer.renderizar_longo(self.clip, 1.0, 20.0, "Luqueta", 1, self.final)
        lado = renderer.MARCA_LONGO + 2 * renderer.ARO_MARCA
        centro_x = 1280 - 24 - lado // 2
        for instante in (0.5, 10.0, 19.5):
            with self.subTest(instante=instante):
                quadro = quadro_rgb(self.final, instante, 1280, 720)
                aro = quadro[24 + renderer.ARO_MARCA // 2 + 1, centro_x - 1:centro_x + 2].mean()
                self.assertGreater(aro, 200)

    def test_tela_preta_e_retirada_do_longo(self):
        renderer.renderizar_longo(self.clip, 1.0, 20.0, "Luqueta", 2, self.final, bloqueios=[(8.0, 12.0)])
        self.assertAlmostEqual(ffmpeg_runner.medir_linha_do_tempo(self.final)["video_s"], 16.0, delta=0.1)

    def test_falha_nao_publica_longo_parcial(self):
        with mock.patch.object(renderer, "executar_ffmpeg", side_effect=FFmpegError("longo", 1, "falha simulada")):
            with self.assertRaises(FFmpegError):
                renderer.renderizar_longo(self.clip, 1.0, 20.0, "Luqueta", 1, self.final)
        self.assertFalse(self.final.exists())
        self.assertEqual(list(self.bruto_dir.iterdir()), [])


class TestTopDaSemanaE2E(AmbienteIsolado):
    """O longo junta um trecho de cada vídeo viral: cada um com a própria imagem e o próprio som, sem desalinhar."""

    def setUp(self):
        super().setUp()
        self.cta = gerar_audio(self.raiz / "cta.mp3", duracao=3)
        patcher = mock.patch.object(renderer, "CTA_AUDIO", self.cta)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.videos = [
            self._video("a.mp4", "1280x720", 30, 440),
            self._video("b.mp4", "1920x1080", 60, 660),
            self._video("c.mp4", "854x480", 30, 990, som_s=4),  # som acaba antes da imagem
        ]
        self.compilacao = self.bruto_dir / "compilacao.mp4"

    def _video(self, nome, tamanho, quadros, frequencia, som_s=10):
        destino = self.raiz / nome
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", f"testsrc2=size={tamanho}:rate={quadros}:duration=10",
             "-f", "lavfi", "-i", f"sine=frequency={frequencia}:duration={som_s}",
             "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", str(destino)],
            check=True, capture_output=True)
        return destino

    def _volume_em(self, video, inicio, duracao, frequencia):
        resultado = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostdin", "-ss", str(inicio), "-t", str(duracao), "-i", str(video),
             "-af", f"bandpass=f={frequencia}:width_type=h:w=30,volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, errors="replace")
        return float(re.search(r"mean_volume: (-?[\d.]+)", resultado.stderr).group(1))

    def _montar(self):
        trechos = [(self.videos[0], 2.0, 6.0), (self.videos[1], 1.0, 5.5), (self.videos[2], 3.0, 7.0)]
        return renderer.montar_compilacao(trechos, self.compilacao)

    def test_trechos_entram_em_ordem_e_em_quadros_inteiros(self):
        inicios, total = self._montar()
        self.assertEqual(inicios, [0.0, 4.0, 8.5])
        self.assertAlmostEqual(total, 12.5, places=3)
        medida = ffmpeg_runner.medir_linha_do_tempo(self.compilacao)
        self.assertAlmostEqual(medida["video_s"], 12.5, delta=0.05)
        self.assertAlmostEqual(medida["audio_s"], medida["video_s"], delta=0.08)
        self.assertEqual(medida["pacotes_amontoados"], 0)
        saida = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                         "stream=width,height,r_frame_rate", "-of", "json", str(self.compilacao)])
        stream = json.loads(saida)["streams"][0]
        self.assertEqual((stream["width"], stream["height"], stream["r_frame_rate"]), (1280, 720, "30/1"))

    def test_cada_trecho_leva_o_proprio_som(self):
        self._montar()
        self.assertGreater(self._volume_em(self.compilacao, 1.0, 1.5, 440), self._volume_em(self.compilacao, 1.0, 1.5, 660) + 15)
        self.assertGreater(self._volume_em(self.compilacao, 5.5, 1.5, 660), self._volume_em(self.compilacao, 5.5, 1.5, 440) + 15)

    def test_som_que_acaba_antes_da_imagem_vira_silencio_sem_desalinhar(self):
        inicios, total = self._montar()
        self.assertGreater(self._volume_em(self.compilacao, 8.6, 0.8, 990), -45, "o começo do trecho tem o som dele")
        self.assertLess(self._volume_em(self.compilacao, 10.5, 1.5, 990), -60, "depois que o som acaba fica silêncio")
        self.assertAlmostEqual(ffmpeg_runner.medir_linha_do_tempo(self.compilacao)["video_s"], total, delta=0.05)

    def test_top_mostra_titulo_e_o_nome_de_cada_criador(self):
        inicios, total = self._montar()
        final = self.export_dir / "longo-top3-semana-1.mp4"

        def tts(texto, destino, rate="+0%"):
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=880:duration=1", str(destino)],
                           check=True, capture_output=True)
            return destino

        fins = inicios[1:] + [total]
        creditos = [(ini, fim, nome) for ini, fim, nome in zip(inicios, fins, ("Criador A", "Criador B", "Criador C"))]
        with mock.patch.object(renderer, "_gerar_tts_com_retentativa", side_effect=tts), \
                mock.patch.object(renderer, "_codificar", wraps=renderer._codificar) as codificar:
            renderer.renderizar_longo(self.compilacao, 0.0, total, "GTA 6", 1, final, abertura="Top da semana",
                                      narracoes=list(zip(inicios, ("Terceiro lugar", "Segundo lugar", "Primeiro lugar"))),
                                      titulo_tela="TOP 3 DA SEMANA", subtitulo_tela="OS MAIS VIRAIS DE GTA 6", creditos=creditos)
        grafo = " ".join(codificar.call_args.args[0])
        for texto in ("TOP 3 DA SEMANA", "OS MAIS VIRAIS DE GTA 6", "VÍDEO DE CRIADOR A", "VÍDEO DE CRIADOR C"):
            self.assertIn(texto, grafo)
        medida = ffmpeg_runner.medir_linha_do_tempo(final)
        self.assertAlmostEqual(medida["video_s"], total, delta=0.1)
        self.assertAlmostEqual(medida["audio_s"], medida["video_s"], delta=0.08)

    def test_sem_trechos_nao_monta_nada(self):
        with self.assertRaises(FFmpegError):
            renderer.montar_compilacao([], self.compilacao)
        self.assertFalse(self.compilacao.exists())


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

    def _tempos_limite(self, disponivel, efeito=None, quadros=15300):
        with mock.patch.object(renderer, "quick_sync_disponivel", return_value=disponivel),                 mock.patch.object(renderer, "executar_ffmpeg", side_effect=efeito) as ffmpeg:
            renderer._renderizar_final(Path("intro.mp4"), Path("conteudo.mp4"), quadros, Path("final.mp4"))
        return [c.kwargs.get("timeout") for c in ffmpeg.call_args_list]

    def test_placa_intel_travada_e_percebida_cedo(self):
        """Regressão: a placa travou 36 min num longo de 8min30 antes de o sistema desistir dela."""
        limites = self._tempos_limite(True, efeito=[FFmpegError("final", "timeout", "travou"), None])
        self.assertLessEqual(limites[0], 900)

    def test_processador_tem_tempo_para_terminar_um_longo(self):
        """Regressão: refazer no processador estourava os 30 min e o vídeo longo era perdido."""
        limites = self._tempos_limite(True, efeito=[FFmpegError("final", "timeout", "travou"), None])
        self.assertGreaterEqual(limites[1], 510 * 6)

    def test_short_continua_com_tempo_minimo_de_folga(self):
        limites = self._tempos_limite(False, quadros=1800)
        self.assertGreaterEqual(limites[0], 600)

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
                                    side_effect=lambda _s, destino, **_kw: gerar_audio(destino))
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
