"""
SPEC-003: integração do ciclo de produção com falhas injetadas em cada etapa.
"""
import json
import unittest
from collections import namedtuple
from unittest import mock

from apoio import AmbienteIsolado
from src.pipeline import estado, searcher, transcriber, worker
from src.pipeline.ffmpeg_runner import FFmpegError

Disco = namedtuple("Disco", "total used free")


class BaseCiclo(AmbienteIsolado):

    def setUp(self):
        super().setUp()
        self.video = {"id": "abc123", "url": "https://youtu.be/abc123", "title": "Live 😱",
                      "streamer": "Luqueta", "duration": 3600}
        self.segmentos = [{"start": 360.0 + i * 10, "end": 370.0 + i * 10, "text": "fala"} for i in range(30)]
        self.m = {}
        padroes = {
            "buscar_melhor_live": mock.Mock(return_value=self.video),
            "baixar_video": mock.Mock(side_effect=self._baixar),
            "extrair_audio_wav": mock.Mock(),
            "transcrever_audio": mock.Mock(return_value=self.segmentos),
            "e_audio_em_portugues": mock.Mock(return_value=True),
            "identificar_idioma_dos_segmentos": mock.Mock(side_effect=lambda _audio, segs, **_kw: segs),
            "detectar_telas_pretas": mock.Mock(return_value=[]),
            "renderizar_short": mock.Mock(side_effect=self._renderizar),
            "renderizar_longo": mock.Mock(side_effect=self._renderizar),
            "obter_duracao_audio": mock.Mock(return_value=1260.0),
            "auditar_video": mock.Mock(return_value=(True, "ok", 90)),
            "registrar_historico": mock.Mock(),
        }
        for nome, valor in padroes.items():
            patcher = mock.patch.object(worker, nome, valor)
            self.m[nome] = patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(worker.shutil, "disk_usage", return_value=Disco(0, 0, 500 * 1024 ** 3))
        self.disco = patcher.start()
        self.addCleanup(patcher.stop)

    def _baixar(self, _url, **_kw):
        destino = self.bruto_dir / "live_bruta.webm"
        destino.write_bytes(b"video")
        return destino

    def _renderizar(self, **kw):
        kw["output_final"].write_bytes(b"x" * 200_000)
        return kw["output_final"]

    def _status(self):
        return json.loads(self.status_file.read_text(encoding="utf-8"))


class TestCicloDeProducao(BaseCiclo):

    def test_ciclo_feliz_publica_e_registra_historico(self):
        self.assertTrue(worker.executar_ciclo_producao())
        self.assertEqual(self.m["renderizar_short"].call_count, 4)
        self.assertEqual(self.m["renderizar_longo"].call_count, 2)
        self.m["registrar_historico"].assert_any_call("abc123")
        self.assertEqual(self._status()["progresso"], 100)
        self.assertIsNone(self._status().get("erro"))
        self.assertFalse(estado.ciclo_em_andamento())

    def test_falas_em_ingles_nao_viram_short(self):
        self.m["identificar_idioma_dos_segmentos"].side_effect = (
            lambda _audio, segs, **_kw: [{**s, "prob_pt": 0.01} for s in segs])
        self.assertFalse(worker.executar_ciclo_producao())
        self.m["renderizar_short"].assert_not_called()

    def test_idioma_e_medido_no_trecho_certo_da_live(self):
        worker.executar_ciclo_producao()
        self.assertEqual(self.m["identificar_idioma_dos_segmentos"].call_args.kwargs["deslocamento"], 360.0)

    def test_pedido_duplicado_nao_baixa_de_novo(self):
        trava = estado.TravaCiclo()
        self.assertTrue(trava.adquirir())
        self.addCleanup(trava.liberar)
        self.assertFalse(worker.executar_ciclo_producao())
        self.m["baixar_video"].assert_not_called()

    def _criar_estoque(self, shorts=0, longos=0):
        for i in range(shorts):
            (self.export_dir / f"short-x-corte{i}.mp4").write_bytes(b"x" * 200_000)
        for i in range(longos):
            (self.export_dir / f"longo-x-parte{i}.mp4").write_bytes(b"x" * 200_000)

    def test_longos_saem_com_nome_titulo_e_partes_sem_repetir(self):
        worker.executar_ciclo_producao()
        chamadas = self.m["renderizar_longo"].call_args_list
        self.assertTrue(all(c.kwargs["output_final"].name.startswith("longo-") for c in chamadas))
        fim_da_primeira = chamadas[0].kwargs["inicio"] + chamadas[0].kwargs["duracao"]
        self.assertLessEqual(fim_da_primeira, chamadas[1].kwargs["inicio"])
        metadados = json.loads((self.raiz / "metadados_cortes.json").read_text(encoding="utf-8"))
        titulos = [v["titulo"] for k, v in metadados.items() if k.startswith("longo-")]
        self.assertEqual(len(titulos), 2)
        self.assertFalse(any("#Shorts" in t for t in titulos))

    def test_estoque_cheio_com_60_videos_nao_baixa_nada(self):
        self._criar_estoque(shorts=40, longos=20)
        self.assertFalse(worker.executar_ciclo_producao())
        self.m["baixar_video"].assert_not_called()

    def test_com_40_shorts_produz_apenas_longos(self):
        self._criar_estoque(shorts=40)
        worker.executar_ciclo_producao()
        self.m["renderizar_short"].assert_not_called()
        self.assertEqual(self.m["renderizar_longo"].call_count, 2)

    def test_com_20_longos_produz_apenas_shorts(self):
        self._criar_estoque(longos=20)
        worker.executar_ciclo_producao()
        self.m["renderizar_longo"].assert_not_called()
        self.assertEqual(self.m["renderizar_short"].call_count, 4)

    def test_nunca_passa_de_60_videos_na_fila(self):
        self._criar_estoque(shorts=39, longos=19)
        self.assertEqual(worker.calcular_vagas(), (1, 1))
        self._criar_estoque(shorts=0, longos=0)

    def test_gravacao_curta_nao_gera_longo(self):
        self.m["obter_duracao_audio"].return_value = 300.0
        worker.executar_ciclo_producao()
        self.m["renderizar_longo"].assert_not_called()
        self.assertEqual(self.m["renderizar_short"].call_count, 4)

    def test_falha_no_longo_nao_perde_os_shorts(self):
        self.m["renderizar_longo"].side_effect = FFmpegError("longo", 1, "x")
        self.assertTrue(worker.executar_ciclo_producao())
        self.assertEqual(self.m["renderizar_short"].call_count, 4)

    def test_live_sem_fala_em_portugues_nao_gera_longo(self):
        self.m["identificar_idioma_dos_segmentos"].side_effect = (
            lambda _audio, segs, **_kw: [{**s, "prob_pt": 0.01} for s in segs])
        worker.executar_ciclo_producao()
        self.m["renderizar_longo"].assert_not_called()

    def test_todos_os_cortes_falham_nao_marca_como_concluido(self):
        self.m["renderizar_short"].side_effect = FFmpegError("legendas", 1, "Unable to open")
        self.m["renderizar_longo"].side_effect = FFmpegError("legendas", 1, "Unable to open")
        self.assertFalse(worker.executar_ciclo_producao())
        self.m["registrar_historico"].assert_not_called()
        self.assertEqual(self._status()["erro"]["categoria"], "render")
        self.assertIn("legendas", self._status()["erro"]["mensagem"])

    def test_falha_parcial_aproveita_os_cortes_bons(self):
        self.m["renderizar_short"].side_effect = [FFmpegError("cta", 1, "x"), mock.DEFAULT, mock.DEFAULT, mock.DEFAULT]
        self.m["renderizar_short"].return_value = None
        self.assertTrue(worker.executar_ciclo_producao())
        self.m["registrar_historico"].assert_any_call("abc123")

    def test_video_sem_fala_nao_fica_em_loop(self):
        self.m["transcrever_audio"].return_value = []
        self.assertFalse(worker.executar_ciclo_producao())
        self.m["renderizar_short"].assert_not_called()
        self.m["registrar_historico"].assert_any_call("abc123")

    def test_live_em_outro_idioma_e_descartada_antes_do_render(self):
        self.m["e_audio_em_portugues"].return_value = False
        self.assertFalse(worker.executar_ciclo_producao())
        self.m["transcrever_audio"].assert_not_called()
        self.m["renderizar_short"].assert_not_called()
        self.m["registrar_historico"].assert_any_call("abc123")

    def test_live_no_ar_e_gravada_por_tempo_limitado(self):
        self.video.update(ao_vivo=True, duration=None)
        worker.executar_ciclo_producao()
        self.assertTrue(self.m["baixar_video"].call_args.kwargs["ao_vivo"])

    def test_corte_aprovado_guarda_titulo_para_o_painel(self):
        worker.executar_ciclo_producao()
        metadados = json.loads((self.raiz / "metadados_cortes.json").read_text(encoding="utf-8"))
        shorts = [item for nome, item in metadados.items() if nome.startswith("short-")]
        self.assertEqual(len(shorts), 4)
        self.assertTrue(all("#Shorts" in item["titulo"] for item in shorts))

    def test_caos_sobra_de_ciclo_interrompido_e_limpa_antes_de_baixar(self):
        sobra = self.bruto_dir / "live_bruta.webm"
        sobra.write_bytes(b"video de OUTRO streamer")

        def verificar(_url, **_kw):
            self.assertFalse(sobra.exists(), "sobra antiga seria reaproveitada como se fosse o vídeo novo")
            return self._baixar(_url)

        self.m["baixar_video"].side_effect = verificar
        self.assertTrue(worker.executar_ciclo_producao())

    def test_transcreve_apenas_uma_janela_da_live(self):
        worker.executar_ciclo_producao()
        _, kwargs = self.m["extrair_audio_wav"].call_args
        self.assertEqual((kwargs["inicio"], kwargs["duracao"]), (360.0, 480.0))
        self.assertEqual(self.m["transcrever_audio"].call_args.kwargs["deslocamento"], 360.0)

    def test_caos_disco_cheio_aborta_antes_de_baixar(self):
        self.disco.return_value = Disco(0, 0, 1024 ** 3)
        self.assertFalse(worker.executar_ciclo_producao())
        self.m["baixar_video"].assert_not_called()
        self.assertEqual(self._status()["erro"]["categoria"], "disco")

    def test_caos_rate_limit_nao_condena_o_video(self):
        self.m["baixar_video"].side_effect = RuntimeError("HTTP Error 429: Too Many Requests")
        for _ in range(estado.MAX_TENTATIVAS_VIDEO + 1):
            self.assertFalse(worker.executar_ciclo_producao())
        self.assertEqual(self._status()["erro"]["categoria"], "rate_limit")
        self.assertFalse(estado.em_quarentena("abc123"))

    def test_erro_de_render_repetido_vai_para_quarentena(self):
        self.m["renderizar_short"].side_effect = FFmpegError("legendas", 1, "x")
        self.m["renderizar_longo"].side_effect = FFmpegError("legendas", 1, "x")
        for _ in range(estado.MAX_TENTATIVAS_VIDEO):
            worker.executar_ciclo_producao()
        self.assertTrue(estado.em_quarentena("abc123"))

    def test_bruto_e_limpo_mesmo_com_erro(self):
        self.m["transcrever_audio"].side_effect = RuntimeError("whisper caiu")
        worker.executar_ciclo_producao()
        self.assertEqual(list(self.bruto_dir.iterdir()), [])
        self.assertFalse(estado.ciclo_em_andamento())

    def test_sucesso_limpa_erro_anterior(self):
        estado.publicar_status(erro={"categoria": "rede", "mensagem": "caiu"})
        self.assertTrue(worker.executar_ciclo_producao())
        self.assertIsNone(self._status().get("erro"))


class TestLoopDoVigia(BaseCiclo):

    def test_espera_cresce_e_tem_teto(self):
        self.assertEqual(worker.calcular_espera(0), 30)
        self.assertEqual(worker.calcular_espera(1), 60)
        self.assertEqual(worker.calcular_espera(2), 120)
        self.assertEqual(worker.calcular_espera(20), worker.ESPERA_MAXIMA_S)
        self.assertEqual(worker.calcular_espera(1, espera_minima=900), 900)

    def test_caos_excecao_inesperada_nao_mata_o_loop(self):
        with mock.patch.object(worker, "_aguardar"), \
             mock.patch.object(worker, "executar_ciclo_producao", side_effect=[RuntimeError("boom"), True]) as ciclo:
            worker.loop_vigia_continuo(max_iteracoes=2)
        self.assertEqual(ciclo.call_count, 2)

    def test_loop_aguarda_ciclo_manual_sem_repetir_aviso(self):
        trava = estado.TravaCiclo()
        self.assertTrue(trava.adquirir())
        self.addCleanup(trava.liberar)
        with mock.patch.object(worker, "_aguardar"), \
             mock.patch.object(worker, "executar_ciclo_producao") as ciclo:
            worker.loop_vigia_continuo(max_iteracoes=2)
        ciclo.assert_not_called()

    def test_pausa_impede_novo_ciclo(self):
        estado.definir_producao_ativa(False)
        with mock.patch.object(worker, "_aguardar"), \
             mock.patch.object(worker, "executar_ciclo_producao") as ciclo:
            worker.loop_vigia_continuo(max_iteracoes=2)
        ciclo.assert_not_called()


class TestBuscaDeLives(AmbienteIsolado):

    def _ydl(self, **config):
        instancia = mock.MagicMock()
        instancia.__enter__.return_value.extract_info.configure_mock(**config)
        return mock.patch.object(searcher.yt_dlp, "YoutubeDL", return_value=instancia)

    def test_caos_rate_limit_aparece_em_vez_de_fingir_que_nao_ha_lives(self):
        with self._ydl(side_effect=RuntimeError("HTTP Error 429: Too Many Requests")):
            with self.assertRaisesRegex(RuntimeError, "429"):
                searcher.buscar_melhor_live()

    def test_video_em_quarentena_e_ignorado(self):
        for _ in range(estado.MAX_TENTATIVAS_VIDEO):
            estado.registrar_falha("ruim", {"categoria": "render", "mensagem": "x"})
        entradas = {"entries": [
            {"id": "ruim", "title": "A", "duration": 600},
            {"id": "bom", "title": "B", "duration": 600},
        ]}
        with self._ydl(return_value=entradas):
            self.assertEqual(searcher.buscar_melhor_live()["id"], "bom")


class TestJanelaDeTranscricao(unittest.TestCase):

    def test_janelas(self):
        self.assertEqual(transcriber.calcular_janela_transcricao(3600), (360.0, 480.0))
        self.assertEqual(transcriber.calcular_janela_transcricao(300), (0.0, None))
        self.assertEqual(transcriber.calcular_janela_transcricao(0), (0.0, 480.0))

    def test_timestamps_voltam_para_a_posicao_real_da_live(self):
        modelo = mock.Mock()
        modelo.transcribe.return_value = {"segments": [{"start": 1.0, "end": 2.0, "text": "oi"}]}
        with mock.patch.object(transcriber, "_obter_modelo", return_value=modelo):
            segmentos = transcriber.transcrever_audio("a.wav", deslocamento=360.0)
        self.assertEqual((segmentos[0]["start"], segmentos[0]["end"]), (361.0, 362.0))

    def test_extracao_recorta_a_janela(self):
        with mock.patch.object(transcriber, "executar_ffmpeg") as ffmpeg:
            transcriber.extrair_audio_wav("v.webm", "a.wav", inicio=360.0, duracao=480.0)
        args = ffmpeg.call_args.args[0]
        self.assertEqual(args[args.index("-ss") + 1], "360.0")
        self.assertEqual(args[args.index("-t") + 1], "480.0")


class TestWhisperNaPlacaDeVideo(unittest.TestCase):

    def setUp(self):
        for patcher in (mock.patch.dict(transcriber._modelos, clear=True),
                        mock.patch.object(transcriber, "log_terminal")):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _modelo(self, dispositivo):
        modelo = mock.Mock()
        modelo.device.type = dispositivo
        modelo.transcribe.return_value = {"segments": []}
        return modelo

    def _com_placa(self, disponivel, **kw):
        return (mock.patch.object(transcriber.torch.cuda, "is_available", return_value=disponivel),
                mock.patch.object(transcriber.whisper, "load_model", **kw))

    def test_usa_a_placa_quando_ela_esta_disponivel(self):
        placa, carregar = self._com_placa(True, return_value=self._modelo("cuda"))
        with placa, carregar as load:
            transcriber._obter_modelo("small")
        self.assertEqual(load.call_args.kwargs["device"], "cuda")

    def test_sem_placa_compativel_usa_o_processador(self):
        placa, carregar = self._com_placa(False, return_value=self._modelo("cpu"))
        with placa, carregar as load:
            transcriber._obter_modelo("small")
        self.assertEqual(load.call_args.kwargs["device"], "cpu")

    def test_placa_sem_memoria_ao_carregar_cai_para_o_processador(self):
        placa, carregar = self._com_placa(True, side_effect=[RuntimeError("CUDA out of memory"), self._modelo("cpu")])
        with placa, carregar as load:
            modelo = transcriber._obter_modelo("small")
        self.assertEqual(modelo.device.type, "cpu")
        self.assertEqual(load.call_args.kwargs["device"], "cpu")

    def test_na_placa_transcreve_em_meia_precisao(self):
        modelo = self._modelo("cuda")
        with mock.patch.object(transcriber, "_obter_modelo", return_value=modelo):
            transcriber.transcrever_audio("a.wav")
        self.assertTrue(modelo.transcribe.call_args.kwargs["fp16"])

    def test_no_processador_transcreve_em_precisao_normal(self):
        modelo = self._modelo("cpu")
        with mock.patch.object(transcriber, "_obter_modelo", return_value=modelo):
            transcriber.transcrever_audio("a.wav")
        self.assertFalse(modelo.transcribe.call_args.kwargs["fp16"])

    def test_memoria_acaba_no_meio_e_refaz_no_processador(self):
        na_placa = self._modelo("cuda")
        na_placa.transcribe.side_effect = RuntimeError("CUDA out of memory")
        no_processador = self._modelo("cpu")
        with mock.patch.object(transcriber, "_obter_modelo", return_value=na_placa), \
                mock.patch.object(transcriber.whisper, "load_model", return_value=no_processador), \
                mock.patch.object(transcriber.torch.cuda, "empty_cache"):
            self.assertEqual(transcriber.transcrever_audio("a.wav"), [])
        no_processador.transcribe.assert_called_once()

    def test_outros_erros_nao_sao_escondidos(self):
        modelo = self._modelo("cuda")
        modelo.transcribe.side_effect = RuntimeError("arquivo corrompido")
        with mock.patch.object(transcriber, "_obter_modelo", return_value=modelo):
            with self.assertRaises(RuntimeError):
                transcriber.transcrever_audio("a.wav")


if __name__ == "__main__":
    unittest.main()
