"""
SPEC-004: a matéria-prima são os vídeos de GTA 6 em português mais vistos da semana; lives não são mais gravadas.
"""
import unittest
from unittest import mock

from apoio import AmbienteIsolado
from src.pipeline import downloader, estado, searcher, transcriber


def entrada(video_id, titulo="GTA 6 gameplay em português", visualizacoes=1000, canal=None, duracao=3600, **extra):
    return {"id": video_id, "title": titulo, "view_count": visualizacoes, "channel": canal or f"Canal {video_id}",
            "duration": duracao, "live_status": extra.pop("live_status", "not_live"), **extra}


class BaseBusca(AmbienteIsolado):

    def _configurar(self, semana=(), mes=(), detalhes=None):
        detalhes = detalhes or {}

        def listar(url):
            if searcher.FILTRO_MAIS_VISTOS_SEMANA in url:
                return list(semana)
            if searcher.FILTRO_MAIS_VISTOS_MES in url:
                return list(mes)
            return []

        def detalhar(url):
            video_id = url.rsplit("=", 1)[-1]
            return detalhes.get(video_id, {"duration": 3600, "live_status": "not_live", "channel": f"Canal {video_id}"})

        for nome, efeito in (("_listar", listar), ("_detalhar", detalhar)):
            patcher = mock.patch.object(searcher, nome, side_effect=efeito)
            patcher.start()
            self.addCleanup(patcher.stop)
        # A ordem e os filtros são testados com números pequenos; o mínimo de visualizações tem teste próprio
        patcher = mock.patch.object(searcher, "VISUALIZACOES_MINIMAS", 0)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _ids(self, quantidade=5, **kw):
        return [v["id"] for v in searcher.buscar_videos_virais(quantidade, **kw)]


class TestMaisVistosDaSemana(BaseBusca):

    def test_do_mais_visto_para_o_menos_visto(self):
        self._configurar(semana=[entrada("b", visualizacoes=500), entrada("a", visualizacoes=9_000_000), entrada("c", visualizacoes=40_000)])
        self.assertEqual(self._ids(), ["a", "c", "b"])

    def test_video_traz_criador_visualizacoes_e_origem_viral(self):
        self._configurar(semana=[entrada("a", visualizacoes=8_196_705, canal="PAULINHO O LOKO")])
        video = searcher.buscar_videos_virais(1)[0]
        self.assertEqual((video["streamer"], video["visualizacoes"], video["origem"], video["ao_vivo"]),
                         ("PAULINHO O LOKO", 8_196_705, "viral", False))
        self.assertEqual(video["url"], "https://www.youtube.com/watch?v=a")

    def test_um_video_por_criador(self):
        self._configurar(semana=[entrada("a1", visualizacoes=900, canal="Paulinho"), entrada("a2", visualizacoes=800, canal="Paulinho"),
                                 entrada("b", visualizacoes=700, canal="Alanzoka")])
        self.assertEqual(self._ids(), ["a1", "b"])

    def test_gravacao_de_live_ja_encerrada_conta_como_video(self):
        self._configurar(semana=[entrada("vod", titulo="GTA 6 É AGORA, O INÍCIO DA GAMEPLAY", duracao=40815, live_status="was_live")])
        self.assertEqual(self._ids(), ["vod"])

    def test_live_no_ar_ou_agendada_fica_de_fora(self):
        self._configurar(semana=[entrada("ao_vivo", live_status="is_live"), entrada("agendada", live_status="is_upcoming"),
                                 entrada("processando", live_status="post_live"), entrada("ok")])
        self.assertEqual(self._ids(), ["ok"])

    def test_video_em_outro_idioma_fica_de_fora(self):
        """Títulos reais da busca de 24/11: os gringos têm mais visualizações, mas o canal é em português."""
        self._configurar(semana=[
            entrada("mrbeast", titulo="I Survived 100 Hours In GTA 6", visualizacoes=69_690_773),
            entrada("speed", titulo="🔴 BEATING GTA 6 RIGHT NOW 100% (FINAL MISSION)", visualizacoes=24_482_648),
            entrada("carry", titulo="CARRYMINATI PLAYS GTA VI | NO PROMOTIONS", visualizacoes=18_636_211),
            entrada("windah", titulo="GTA VI SIAP TAMAT 100%.... GAMEPLAY #1", visualizacoes=15_554_824),
            entrada("cory", titulo="GTA 6", visualizacoes=11_520_636),
            entrada("ign", titulo="GTA 6 Review", visualizacoes=8_409_073),
            entrada("tmartn", titulo="Grand Theft Auto 6 - Part 1 - The Beginning", visualizacoes=4_725_813),
            entrada("alanzoka", titulo="BEM VINDO A LEONIDA! - GRAND THEFT AUTO 6 - Parte 1", visualizacoes=5_736_574),
            entrada("gameplayrj", titulo="GTA 6 É AGORA , O INICIO DA GAMEPLAY", visualizacoes=10_999_401),
            entrada("coringa", titulo="GTA VI: DIA 2 🔴 CORINGA AO VIVO", visualizacoes=3_876_390),
            entrada("brksedu", titulo="GTA 6 #1 - Gameplay Start!!! | Grand Theft Auto VI in Portuguese on PS", visualizacoes=3_805_135),
        ])
        self.assertEqual(self._ids(quantidade=10), ["gameplayrj", "alanzoka", "coringa", "brksedu"])

    def test_video_curto_ou_short_fica_de_fora(self):
        self._configurar(semana=[entrada("curto", duracao=200), entrada("medio", duracao=searcher.DURACAO_MINIMA_S - 1),
                                 entrada("bom", duracao=searcher.DURACAO_MINIMA_S)])
        self.assertEqual(self._ids(), ["bom"])

    def test_video_com_poucas_visualizacoes_nao_e_viral(self):
        """Regressão: a busca do mês trouxe um vídeo com 797 visualizações para o Top da semana."""
        self._configurar(semana=[entrada("viral", visualizacoes=3_261_149), entrada("pequeno", visualizacoes=797)])
        with mock.patch.object(searcher, "VISUALIZACOES_MINIMAS", 100_000):
            self.assertEqual(self._ids(), ["viral"])

    def test_nosso_proprio_canal_fica_de_fora(self):
        self._configurar(semana=[entrada("nosso", canal="Viela Vice"), entrada("outro")])
        self.assertEqual(self._ids(), ["outro"])

    def test_video_ja_aproveitado_nao_repete(self):
        self.historico_file.write_text("a\n", encoding="utf-8")
        self._configurar(semana=[entrada("a", visualizacoes=900), entrada("b", visualizacoes=800)])
        self.assertEqual(self._ids(), ["b"])

    def test_videos_tentados_no_ciclo_sao_ignorados(self):
        self._configurar(semana=[entrada("a", visualizacoes=900), entrada("b", visualizacoes=800)])
        self.assertEqual(self._ids(ignorar={"a"}), ["b"])

    def test_video_em_quarentena_e_ignorado(self):
        for _ in range(estado.MAX_TENTATIVAS_VIDEO):
            estado.registrar_falha("ruim", {"categoria": "render", "mensagem": "x"})
        self._configurar(semana=[entrada("ruim", visualizacoes=900), entrada("bom", visualizacoes=800)])
        self.assertEqual(self._ids(), ["bom"])

    def test_semana_aproveitada_completa_com_os_mais_vistos_do_mes(self):
        self._configurar(semana=[entrada("semana")], mes=[entrada("mes1", visualizacoes=5), entrada("semana")])
        self.assertEqual(self._ids(), ["semana", "mes1"])

    def test_semana_suficiente_nem_consulta_o_mes(self):
        self._configurar(semana=[entrada("a"), entrada("b")])
        self.assertEqual(self._ids(quantidade=2), ["a", "b"])
        self.assertFalse(any(searcher.FILTRO_MAIS_VISTOS_MES in str(c) for c in searcher._listar.call_args_list))

    def test_busca_sem_duracao_ou_canal_consulta_a_pagina_do_video(self):
        self._configurar(semana=[{"id": "a", "title": "GTA 6 gameplay em português", "view_count": 9}],
                         detalhes={"a": {"duration": 1200, "uploader": "Canal da Página", "live_status": "not_live"}})
        video = searcher.buscar_videos_virais(1)[0]
        self.assertEqual((video["streamer"], video["duration"]), ("Canal da Página", 1200))

    def test_busca_completa_nao_faz_consulta_extra(self):
        self._configurar(semana=[entrada("a")])
        self._ids()
        searcher._detalhar.assert_not_called()

    def test_busca_usa_o_filtro_de_mais_vistos(self):
        self._configurar(semana=[entrada("a")])
        self._ids(quantidade=1)
        self.assertTrue(all(searcher.FILTRO_MAIS_VISTOS_SEMANA in c.args[0] for c in searcher._listar.call_args_list))


class TestFiltros(BaseBusca):

    def test_ignora_titulos_fora_do_tema(self):
        self._configurar(semana=[
            entrada("a", titulo="GTA 6: CONTAGEM REGRESSIVA PARA O LANÇAMENTO", visualizacoes=9),
            entrada("b", titulo="MARATONA ANTES DO GTA 6! - GTA 5 ENHANCED", visualizacoes=8),
            entrada("c", titulo="RANK COM CHAT - PRE GTA 6 - FREE FIRE AO VIVO!!!", visualizacoes=7),
            entrada("d", titulo="🎮 GTA 6: O JOGO MAIS ESPERADO DA HISTÓRIA!", visualizacoes=6),
            entrada("tv", titulo="Reportagem Do FANTÁSTICO Sobre GTA 6 - 22/11/2026", visualizacoes=5),
        ])
        self.assertEqual(self._ids(), ["d"], "reportagem de TV não é gameplay e a emissora derruba o vídeo")

    def test_reconhece_as_grafias_do_jogo(self):
        for titulo in ("GTA 6 ao vivo", "GTA VI gameplay", "GTA6 novidades", "Grand Theft Auto VI no Brasil"):
            self.assertTrue(searcher.titulo_e_gta6(titulo), titulo)
        for titulo in ("GTA RP treta", "GTA 5 online", "GTA V gameplay"):
            self.assertFalse(searcher.titulo_e_gta6(titulo), titulo)


class TestYoutube(BaseBusca):

    def test_youtube_em_pausa_nao_busca_nada(self):
        self._configurar(semana=[entrada("a")])
        searcher.pausar_youtube(600)
        self.assertEqual(searcher.buscar_videos_virais(5), [])
        searcher._listar.assert_not_called()

    def test_youtube_volta_quando_a_pausa_termina(self):
        self._configurar(semana=[entrada("a")])
        searcher.pausar_youtube(-1)
        self.assertEqual(self._ids(), ["a"])

    def test_bloqueio_do_youtube_e_informado(self):
        self._configurar()
        searcher._listar.side_effect = RuntimeError("Sign in to confirm you're not a bot")
        with self.assertRaises(RuntimeError):
            searcher.buscar_videos_virais(5)

    def test_caos_rate_limit_aparece_em_vez_de_fingir_que_nao_ha_videos(self):
        self._configurar()
        searcher._listar.side_effect = RuntimeError("HTTP Error 429: Too Many Requests")
        with self.assertRaisesRegex(RuntimeError, "429"):
            searcher.buscar_videos_virais(5)

    def test_falha_isolada_de_uma_busca_nao_para_as_outras(self):
        self._configurar(semana=[entrada("a")])
        original = searcher._listar.side_effect
        chamadas = []

        def instavel(url):
            chamadas.append(url)
            if len(chamadas) == 1:
                raise RuntimeError("instável")
            return original(url)

        searcher._listar.side_effect = instavel
        self.assertEqual(self._ids(), ["a"])

    def test_nao_busca_nem_grava_mais_lives(self):
        for nome in ("buscar_melhor_live", "_buscar_live_prioritaria", "_buscar_live_gta6", "_consultar_live_do_canal", "adiar_live"):
            self.assertFalse(hasattr(searcher, nome), nome)


class TestDownloadDoVideo(AmbienteIsolado):

    def _opcoes_usadas(self, **kw):
        instancia = mock.MagicMock()
        destino = self.bruto_dir / "live_bruta.mp4"
        destino.write_bytes(b"x")
        instancia.__enter__.return_value.extract_info.return_value = {"id": "x"}
        instancia.__enter__.return_value.prepare_filename.return_value = str(destino)
        with mock.patch.object(downloader.yt_dlp, "YoutubeDL", return_value=instancia) as ydl, \
                mock.patch.object(downloader, "_arquivo_completo", return_value=True):
            downloader.baixar_video("https://youtu.be/x", self.bruto_dir, **kw)
        return ydl.call_args.args[0]

    def test_video_curto_e_baixado_inteiro_com_imagem_e_som(self):
        opcoes = self._opcoes_usadas()
        self.assertNotIn("external_downloader_args", opcoes)
        self.assertNotIn("download_ranges", opcoes)
        self.assertIn("bestvideo[height<=720]+bestaudio", opcoes["format"])

    def test_download_nao_aceita_mais_gravacao_de_live(self):
        with self.assertRaises(TypeError):
            downloader.baixar_video("https://youtu.be/x", self.bruto_dir, ao_vivo=True)

    def test_video_viral_baixa_so_o_trecho_analisado(self):
        """Os virais chegam a ter 11 horas: com a internet lenta, só os 6 min analisados descem."""
        instancia = mock.MagicMock()
        instancia.__enter__.return_value.extract_info.return_value = {"id": "x"}
        instancia.__enter__.return_value.prepare_filename.side_effect = (
            lambda _info: str(self.bruto_dir / f"parte{instancia.__enter__.return_value.prepare_filename.call_count}.webm"))
        with mock.patch.object(downloader.yt_dlp, "YoutubeDL", return_value=instancia) as ydl, \
                mock.patch.object(downloader, "_duracoes", return_value={"video": 360.0, "audio": 360.0}), \
                mock.patch.object(downloader, "_arquivo_completo", return_value=True), \
                mock.patch.object(downloader, "executar_ffmpeg") as juntar:
            arquivo = downloader.baixar_video("https://youtu.be/x", self.bruto_dir, trecho=(4081.5, 360.0))
        opcoes = [c.args[0] for c in ydl.call_args_list]
        self.assertEqual([o["format"] for o in opcoes], [downloader.FORMATO_IMAGEM_TRECHO, downloader.FORMATO_SOM_TRECHO])
        for o in opcoes:
            self.assertEqual(list(o["download_ranges"]({"duration": 40815, "id": "x"}, None)),
                             [{"start_time": 4081.5, "end_time": 4441.5}])
        self.assertIn("bestvideo[height<=720]", opcoes[0]["format"])
        self.assertTrue(opcoes[1]["format"].startswith("bestaudio"))
        argumentos = juntar.call_args.args[0]
        self.assertEqual(argumentos[argumentos.index("-c") + 1], "copy")
        self.assertEqual(arquivo.name, "live_bruta.mp4")


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


if __name__ == "__main__":
    unittest.main()
