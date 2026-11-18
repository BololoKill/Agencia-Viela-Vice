"""
SPEC-004: a busca prioriza lives no ar e vídeos novos de GTA 6.
"""
import unittest
from datetime import datetime, timedelta
from unittest import mock

from apoio import AmbienteIsolado
from src.pipeline import downloader, searcher, transcriber


def data_recente(dias=1):
    return (datetime.now() - timedelta(days=dias)).strftime("%Y%m%d")


class BaseBusca(AmbienteIsolado):

    def _configurar(self, lives=(), novos=(), reserva=(), detalhes=None):
        detalhes = detalhes or {}

        def listar(url):
            if "ytsearch" in url:
                return list(reserva)
            if searcher.FILTRO_LIVE in url:
                return list(lives)
            return list(novos)

        def detalhar(url):
            video_id = url.rsplit("=", 1)[-1]
            return detalhes.get(video_id, {"upload_date": data_recente(), "duration": 900, "live_status": "not_live"})

        for nome, efeito in (("_listar", listar), ("_detalhar", detalhar)):
            patcher = mock.patch.object(searcher, nome, side_effect=efeito)
            patcher.start()
            self.addCleanup(patcher.stop)


class TestPrioridade(BaseBusca):

    def test_live_de_gta6_no_ar_vem_primeiro(self):
        self._configurar(
            lives=[{"id": "live1", "title": "GTA 6 AO VIVO! JOGANDO PELA PRIMEIRA VEZ", "live_status": "is_live"}],
            novos=[{"id": "novo1", "title": "GTA 6 gameplay em português", "duration": 900}],
        )
        video = searcher.buscar_melhor_live()
        self.assertEqual((video["id"], video["origem"], video["ao_vivo"]), ("live1", "live_gta6", True))

    def test_video_novo_de_gta6_vence_o_gta_rp(self):
        self._configurar(
            novos=[{"id": "novo1", "title": "GTA 6 gameplay em português", "duration": 900}],
            reserva=[{"id": "rp1", "title": "GTA RP treta", "duration": 900}],
        )
        video = searcher.buscar_melhor_live()
        self.assertEqual((video["id"], video["origem"], video["ao_vivo"]), ("novo1", "novo_gta6", False))

    def test_gta_rp_continua_como_reserva(self):
        self._configurar(reserva=[{"id": "rp1", "title": "GTA RP treta", "duration": 900}])
        self.assertEqual(searcher.buscar_melhor_live()["origem"], "gta_rp")


class TestFiltros(BaseBusca):

    def test_ignora_transmissoes_fora_do_tema(self):
        self._configurar(lives=[
            {"id": "a", "title": "GTA 6 AO VIVO: CONTAGEM REGRESSIVA PARA O LANÇAMENTO", "live_status": "is_live"},
            {"id": "b", "title": "MARATONA ANTES DO GTA 6! - GTA 5 ENHANCED", "live_status": "is_live"},
            {"id": "c", "title": "GTA 6 LIVE - New Zealand Launch Stream", "live_status": "is_live"},
            {"id": "d", "title": "🎮 GTA 6 AO VIVO! O JOGO MAIS ESPERADO DA HISTÓRIA!", "live_status": "is_live"},
        ])
        self.assertEqual(searcher.buscar_melhor_live()["id"], "d")

    def test_ignora_live_de_outro_jogo_que_cita_gta6(self):
        self._configurar(lives=[
            {"id": "ff", "title": "RANK COM CHAT - PRE GTA 6 - FREE FIRE AO VIVO!!!", "live_status": "is_live"},
            {"id": "ok", "title": "JOGANDO GTA 6 AO VIVO NO BRASIL", "live_status": "is_live"},
        ])
        self.assertEqual(searcher.buscar_melhor_live()["id"], "ok")

    def test_video_antigo_nao_conta_como_novo(self):
        self._configurar(
            novos=[{"id": "velho", "title": "GTA 6 gameplay em português", "duration": 900}],
            detalhes={"velho": {"upload_date": data_recente(30), "duration": 900, "live_status": "not_live"}},
            reserva=[{"id": "rp1", "title": "GTA RP treta", "duration": 900}],
        )
        self.assertEqual(searcher.buscar_melhor_live()["id"], "rp1")

    def test_video_ja_processado_nao_repete(self):
        self.historico_file.write_text("novo1\n", encoding="utf-8")
        self._configurar(
            novos=[{"id": "novo1", "title": "GTA 6 gameplay em português", "duration": 900},
                   {"id": "novo2", "title": "GTA VI novidades do jogo", "duration": 900}],
        )
        self.assertEqual(searcher.buscar_melhor_live()["id"], "novo2")

    def test_reconhece_as_grafias_do_jogo(self):
        for titulo in ("GTA 6 ao vivo", "GTA VI gameplay", "GTA6 novidades", "Grand Theft Auto VI no Brasil"):
            self.assertTrue(searcher.titulo_e_gta6(titulo), titulo)
        for titulo in ("GTA RP treta", "GTA 5 online", "GTA V gameplay"):
            self.assertFalse(searcher.titulo_e_gta6(titulo), titulo)


class TestGravacaoDeLive(AmbienteIsolado):

    def _opcoes_usadas(self, **kw):
        instancia = mock.MagicMock()
        destino = self.bruto_dir / "live_bruta.mp4"
        destino.write_bytes(b"x")
        instancia.__enter__.return_value.extract_info.return_value = {"id": "x"}
        instancia.__enter__.return_value.prepare_filename.return_value = str(destino)
        with mock.patch.object(downloader.yt_dlp, "YoutubeDL", return_value=instancia) as ydl:
            downloader.baixar_video("https://youtu.be/x", self.bruto_dir, **kw)
        return ydl.call_args.args[0]

    def test_live_e_gravada_por_tempo_limitado(self):
        opcoes = self._opcoes_usadas(ao_vivo=True, duracao_captura=600)
        self.assertEqual(opcoes["external_downloader_args"]["ffmpeg_i"], ["-t", "600"])

    def test_live_junta_video_e_audio_separados(self):
        """Regressão: lives só oferecem vídeo e áudio em faixas separadas."""
        opcoes = self._opcoes_usadas(ao_vivo=True, duracao_captura=600)
        self.assertIn("bestvideo[height<=720]+bestaudio", opcoes["format"])

    def test_video_comum_e_baixado_inteiro(self):
        self.assertNotIn("external_downloader_args", self._opcoes_usadas())


class TestTituloDaTwitch(unittest.TestCase):

    def test_titulos_reais_de_gta_6_sao_aceitos(self):
        for titulo in ("VICE CITY BABYYYYYYYYYYY - JOGANDO NO PS5 PRO", "GTA 6. (jogando no PS5)",
                       "182 / GTA 6 VAMOS NESSA UIA", "+18 SPEEDRUN DE GTA VI - !exitlag"):
            self.assertTrue(searcher.titulo_twitch_no_tema(titulo), titulo)

    def test_outros_conteudos_sao_recusados(self):
        for titulo in ("368 | DIA MUNDIAL DA PISCADA", "RERUN: GTA 6 no lobby", "GTA V RP na cidade alta", "", None):
            self.assertFalse(searcher.titulo_twitch_no_tema(titulo), titulo)


class TestLivesDaTwitch(AmbienteIsolado):

    def setUp(self):
        super().setUp()
        for alvo, nome, valor in ((searcher, "CANAIS_TWITCH", ["alanzoka", "cellbit"]),
                                  (searcher.random, "shuffle", lambda _lista: None)):
            patcher = mock.patch.object(alvo, nome, valor)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(searcher, "_listar", return_value=[])
        self.listar = patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def _live(canal, titulo="GTA 6 ao vivo", stream="123"):
        return {"id": stream, "description": titulo, "uploader": canal.capitalize(), "uploader_id": canal}

    def _responder(self, **lives):
        self.consultar_twitch.side_effect = lambda canal: lives.get(canal)

    def test_streamer_em_live_de_gta_6_e_escolhido_antes_do_youtube(self):
        self._responder(alanzoka=self._live("alanzoka", "VICE CITY BABY"))
        video = searcher.buscar_melhor_live()
        self.assertEqual((video["origem"], video["streamer"], video["ao_vivo"]), ("live_twitch", "Alanzoka", True))
        self.assertEqual(video["url"], "https://www.twitch.tv/alanzoka")
        self.listar.assert_not_called()

    def test_vale_para_qualquer_canal_da_lista(self):
        self._responder(cellbit=self._live("cellbit"))
        self.assertEqual(searcher.buscar_melhor_live()["streamer"], "Cellbit")

    def test_live_de_outro_jogo_segue_para_o_youtube(self):
        self._responder(alanzoka=self._live("alanzoka", "Jogando Minecraft"))
        self.assertIsNone(searcher.buscar_melhor_live())
        self.listar.assert_called()

    def test_mesma_transmissao_nao_e_gravada_duas_vezes(self):
        self._responder(alanzoka=self._live("alanzoka", stream="999"), cellbit=self._live("cellbit", stream="555"))
        searcher.registrar_historico("twitch_999")
        self.assertEqual(searcher.buscar_melhor_live()["id"], "twitch_555")

    def test_falha_em_um_canal_nao_impede_os_outros(self):
        respostas = {"alanzoka": RuntimeError("instável"), "cellbit": self._live("cellbit")}

        def consultar(canal):
            if isinstance(respostas[canal], Exception):
                raise respostas[canal]
            return respostas[canal]

        self.consultar_twitch.side_effect = consultar
        self.assertEqual(searcher.buscar_melhor_live()["streamer"], "Cellbit")

    def test_bloqueio_do_youtube_nao_afeta_a_twitch(self):
        self._responder(cellbit=self._live("cellbit"))
        self.listar.side_effect = RuntimeError("Sign in to confirm you're not a bot")
        self.assertEqual(searcher.buscar_melhor_live()["origem"], "live_twitch")


class TestConsultaDoCanalNaTwitch(unittest.TestCase):

    def _consultar(self, erro):
        ydl = mock.MagicMock()
        ydl.__enter__.return_value.extract_info.side_effect = erro
        with mock.patch.object(searcher.yt_dlp, "YoutubeDL", return_value=ydl):
            return searcher._consultar_canal_twitch("alanzoka")

    def test_canal_offline_nao_e_erro(self):
        self.assertIsNone(self._consultar(RuntimeError("alanzoka: The channel is not currently live")))

    def test_canal_inexistente_nao_e_erro(self):
        self.assertIsNone(self._consultar(RuntimeError("alanzoka does not exist")))

    def test_falha_de_rede_e_informada(self):
        with self.assertRaises(RuntimeError):
            self._consultar(RuntimeError("Connection reset"))


class TestIdiomaDoAudio(AmbienteIsolado):

    def _avaliar(self, *amostras):
        with mock.patch.object(transcriber, "_probabilidades_idioma", return_value=list(amostras)):
            return transcriber.e_audio_em_portugues("a.wav")

    def test_cutscene_em_ingles_nao_descarta_a_live_inteira(self):
        """Regressão: lives brasileiras eram recusadas quando a amostra caía numa cena do jogo."""
        self.assertTrue(self._avaliar({"en": 0.95, "pt": 0.01}, {"pt": 0.9, "en": 0.02}, {"en": 0.9, "pt": 0.02}))

    def test_live_toda_em_outro_idioma_e_recusada(self):
        self.assertFalse(self._avaliar({"en": 0.95, "pt": 0.01}, {"en": 0.9, "pt": 0.02}, {"es": 0.9, "pt": 0.03}))

    def test_portugues_e_aceito(self):
        self.assertTrue(self._avaliar({"pt": 0.9, "es": 0.05}))

    def test_outro_idioma_e_recusado(self):
        self.assertFalse(self._avaliar({"en": 0.93, "pt": 0.02}))

    def test_audio_indefinido_nao_descarta_o_video(self):
        self.assertTrue(self._avaliar({"en": 0.35, "pt": 0.3, "es": 0.2}))


class TestIdiomaDeCadaFala(AmbienteIsolado):

    def _medir(self, segmentos, respostas, deslocamento=0.0):
        taxa = transcriber.whisper.audio.SAMPLE_RATE
        modelo = mock.Mock()
        modelo.detect_language.side_effect = [(None, r) for r in respostas]
        self.recortes = []

        def ajustar(trecho):
            self.recortes.append(len(trecho) / taxa)
            return trecho

        with mock.patch.object(transcriber, "_obter_modelo", return_value=modelo), \
                mock.patch.object(transcriber.whisper, "load_audio", return_value=[0.0] * (taxa * 30)), \
                mock.patch.object(transcriber.whisper, "pad_or_trim", side_effect=ajustar), \
                mock.patch.object(transcriber.whisper, "log_mel_spectrogram"):
            return transcriber.identificar_idioma_dos_segmentos("a.wav", segmentos, deslocamento=deslocamento)

    def test_cada_fala_recebe_a_propria_medicao(self):
        falas = [{"start": 1.0, "end": 5.0, "text": "mano"}, {"start": 6.0, "end": 10.0, "text": "watch out"}]
        medidas = self._medir(falas, [{"pt": 0.91, "en": 0.03}, {"pt": 0.02, "en": 0.95}])
        self.assertEqual([m["prob_pt"] for m in medidas], [0.91, 0.02])
        self.assertEqual(medidas[1]["text"], "watch out")

    def test_usa_o_tempo_relativo_ao_audio_extraido(self):
        self._medir([{"start": 361.0, "end": 365.0, "text": "mano"}], [{"pt": 0.9}], deslocamento=360.0)
        self.assertAlmostEqual(self.recortes[0], 4.0, places=2)

    def test_fala_curta_ganha_contexto_para_ser_reconhecida(self):
        self._medir([{"start": 10.0, "end": 10.4, "text": "oi"}], [{"pt": 0.9}])
        self.assertAlmostEqual(self.recortes[0], transcriber.JANELA_MINIMA_IDIOMA_S, places=2)

    def test_frases_vizinhas_dividem_a_mesma_medicao(self):
        falas = [{"start": i * 1.5, "end": (i + 1) * 1.5, "text": "mano"} for i in range(3)]
        medidas = self._medir(falas, [{"pt": 0.95}])
        self.assertEqual([m["prob_pt"] for m in medidas], [0.95, 0.95, 0.95])
        self.assertEqual(len(self.recortes), 1)

    def test_pausa_longa_separa_as_medicoes(self):
        falas = [{"start": 0.0, "end": 2.0, "text": "mano"}, {"start": 5.0, "end": 7.0, "text": "watch out"}]
        medidas = self._medir(falas, [{"pt": 0.95}, {"pt": 0.01}])
        self.assertEqual([m["prob_pt"] for m in medidas], [0.95, 0.01])

    def test_sem_falas_nao_carrega_o_modelo(self):
        with mock.patch.object(transcriber, "_obter_modelo") as obter:
            self.assertEqual(transcriber.identificar_idioma_dos_segmentos("a.wav", []), [])
        obter.assert_not_called()
