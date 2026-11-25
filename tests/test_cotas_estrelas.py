"""
SPEC-004: o padrão dark de publicação (1 vídeo longo e 2 Shorts por canal) não pode falhar e só reinicia às 05:00.
"""
import itertools
import json
import threading
from datetime import datetime
from unittest import mock

from apoio import AmbienteIsolado
import src.web.app as web
from src.config import CANAIS_VIELA_VICE, COTA_DIARIA_CANAL, COTA_POR_TIPO, DEFAULT_HORARIOS, HORARIOS_POR_TIPO, VIDEO_SPECS
from src.youtube import cota

COTA = COTA_DIARIA_CANAL
CANAL_CHEIO = [f"v{i}" for i in range(COTA)]
QUASE_CHEIO = CANAL_CHEIO[:-1]

ANTES_DAS_5 = datetime(2026, 11, 18, 4, 59)
AS_5 = datetime(2026, 11, 18, 5, 0)


class TestCicloDaCota(AmbienteIsolado):

    def test_padrao_dark_e_um_longo_e_dois_shorts_por_canal(self):
        self.assertEqual(COTA_POR_TIPO, {"longo": 1, "short": 2})
        self.assertEqual(COTA, 3)
        resumo = cota.resumo()["1"]
        self.assertEqual(resumo["limite"], 3)
        self.assertEqual(resumo["por_tipo"], {"longo": {"usados": 0, "limite": 1}, "short": {"usados": 0, "limite": 2}})

    def test_cada_tipo_tem_um_horario_para_cada_envio(self):
        for tipo, limite in COTA_POR_TIPO.items():
            self.assertEqual(len(HORARIOS_POR_TIPO[tipo]), limite)
        self.assertEqual(len(DEFAULT_HORARIOS), COTA)
        self.assertEqual(DEFAULT_HORARIOS, sorted(DEFAULT_HORARIOS))

    def test_agencia_publica_num_canal_so(self):
        self.assertEqual(list(CANAIS_VIELA_VICE), ["1"])
        self.assertEqual(list(cota.resumo()), ["1"])

    def test_estoque_guarda_tres_dias_de_publicacao_do_canal(self):
        canais = len(CANAIS_VIELA_VICE)
        self.assertEqual(VIDEO_SPECS["limite_shorts"], 3 * canais * COTA_POR_TIPO["short"])
        self.assertEqual(VIDEO_SPECS["limite_longos"], 3 * canais * COTA_POR_TIPO["longo"])
        self.assertEqual(VIDEO_SPECS["limite_estoque_max"], VIDEO_SPECS["limite_shorts"] + VIDEO_SPECS["limite_longos"])

    def test_ciclo_vira_somente_as_cinco_da_manha(self):
        self.assertEqual(cota.inicio_ciclo_cota(ANTES_DAS_5), datetime(2026, 11, 17, 5, 0))
        self.assertEqual(cota.inicio_ciclo_cota(AS_5), AS_5)

    def test_estrelas_vem_dos_envios_reais_do_youtube(self):
        self.consultar_youtube.return_value = ["a", "b"]
        cota.sincronizar_canal("1", agora=ANTES_DAS_5)
        resumo = cota.resumo(agora=ANTES_DAS_5)
        self.assertEqual((resumo["1"]["usados"], resumo["1"]["limite"]), (2, COTA))
        self.assertTrue(resumo["1"]["verificado"])

    def test_estrelas_so_zeram_as_cinco(self):
        self.consultar_youtube.return_value = ["a", "b"]
        cota.sincronizar_canal("1", agora=ANTES_DAS_5)
        self.assertEqual(cota.resumo(agora=ANTES_DAS_5)["1"]["usados"], 2)
        self.assertEqual(cota.resumo(agora=AS_5)["1"]["usados"], 0)

    def test_video_apagado_continua_contando_no_ciclo(self):
        self.consultar_youtube.return_value = ["a", "b"]
        cota.sincronizar_canal("1", agora=ANTES_DAS_5)
        self.consultar_youtube.return_value = ["a"]
        cota.sincronizar_canal("1", agora=ANTES_DAS_5)
        self.assertEqual(cota.resumo(agora=ANTES_DAS_5)["1"]["usados"], 2)

    def test_video_agendado_no_ciclo_anterior_nao_conta_de_novo(self):
        """Ao ser publicado, o agendado muda de data no YouTube, mas já gastou a cota do ciclo em que foi enviado."""
        self.consultar_youtube.return_value = ["agendado"]
        cota.sincronizar_canal("1", agora=ANTES_DAS_5)
        self.consultar_youtube.return_value = ["agendado", "novo"]
        cota.sincronizar_canal("1", agora=AS_5)
        self.assertEqual(cota.resumo(agora=AS_5)["1"]["usados"], 1)

    def test_cota_cheia_bloqueia_o_canal(self):
        self.consultar_youtube.return_value = CANAL_CHEIO
        cota.sincronizar_canal("1", agora=ANTES_DAS_5)
        self.assertTrue(cota.resumo(agora=ANTES_DAS_5)["1"]["bloqueado"])


class TestGradeDeHorarios(AmbienteIsolado):
    HORARIOS = ["11:30", "14:00", "16:30"]
    AGORA = datetime(2026, 11, 18, 10, 0)

    def _proximo(self, agendados, canal="1", agora=None):
        return web.calcular_proximo_horario(agendados, self.HORARIOS, canal, agora or self.AGORA)

    def test_cada_canal_tem_a_propria_grade(self):
        agendados = [{"canal": "2", "data": "2026-11-18", "horario": "11:30"}]
        self.assertEqual(self._proximo(agendados, canal="1"), ("2026-11-18", "11:30"))

    def test_mesmo_canal_usa_o_proximo_horario_livre(self):
        agendados = [{"canal": "1", "data": "2026-11-18", "horario": "11:30"}]
        self.assertEqual(self._proximo(agendados), ("2026-11-18", "14:00"))

    def test_horario_que_ja_passou_nao_e_escolhido(self):
        self.assertEqual(self._proximo([], agora=datetime(2026, 11, 18, 15, 0)), ("2026-11-18", "16:30"))

    def test_horario_em_cima_da_hora_vai_para_o_proximo(self):
        self.assertEqual(self._proximo([], agora=datetime(2026, 11, 18, 11, 10)), ("2026-11-18", "14:00"))

    def test_dia_cheio_passa_para_o_dia_seguinte(self):
        self.assertEqual(self._proximo([], agora=datetime(2026, 11, 18, 20, 0)), ("2026-11-19", "11:30"))


class TestRegraNoEnvio(AmbienteIsolado):

    def setUp(self):
        super().setUp()
        self.client = web.app.test_client()
        self.video = self._criar_video("short-luqueta-corte1.mp4")

    def _criar_video(self, nome):
        caminho = self.export_dir / nome
        caminho.write_bytes(b"x" * 1000)
        return caminho

    def _aprovar(self, nome=None, canal="1"):
        return self.client.post("/api/aprovar", json={"filename": nome or self.video.name, "canal": canal})

    def test_envio_alem_da_cota_e_recusado_sem_chamar_o_youtube(self):
        self.consultar_youtube.return_value = CANAL_CHEIO
        with mock.patch.object(web, "enviar_video_agendado") as enviar:
            resposta = self._aprovar()
        self.assertEqual(resposta.status_code, 409)
        self.assertTrue(resposta.get_json()["cota_esgotada"])
        enviar.assert_not_called()
        self.assertTrue(self.video.exists())

    def test_canal_parado_nao_recebe_video(self):
        """Os canais 2 a 7 estão parados: um pedido para eles vai para o canal principal."""
        with mock.patch.object(web, "enviar_video_agendado", return_value=(True, "ok", "yt9")) as enviar:
            self.assertEqual(self._aprovar(canal="2").status_code, 200)
        self.assertEqual(enviar.call_args.kwargs["canal_id"], "1")

    def test_sem_confirmacao_do_youtube_o_envio_e_cancelado(self):
        self.consultar_youtube.side_effect = ConnectionError("sem internet")
        with mock.patch.object(web, "enviar_video_agendado") as enviar:
            resposta = self._aprovar()
        self.assertEqual(resposta.status_code, 503)
        self.assertTrue(resposta.get_json()["cota_nao_verificada"])
        enviar.assert_not_called()
        self.assertTrue(self.video.exists())

    def test_envio_conta_na_hora_mesmo_se_o_youtube_atrasar(self):
        ids = (f"yt{i}" for i in itertools.count())
        with mock.patch.object(web, "enviar_video_agendado", side_effect=lambda **_: (True, "ok", next(ids))) as enviar:
            for nome in ("short-0.mp4", "short-1.mp4", "longo-0-parte1.mp4"):
                self.assertEqual(self._aprovar(self._criar_video(nome).name).status_code, 200)
            self.assertEqual(self._aprovar().status_code, 409)
        self.assertEqual(enviar.call_count, COTA)

    def test_segundo_longo_do_dia_no_mesmo_canal_e_recusado(self):
        primeiro, segundo = (self._criar_video(f"longo-a-parte{i}.mp4").name for i in (1, 2))
        with mock.patch.object(web, "enviar_video_agendado", return_value=(True, "ok", "yt-longo")):
            self.assertEqual(self._aprovar(primeiro).status_code, 200)
        with mock.patch.object(web, "enviar_video_agendado") as enviar:
            resposta = self._aprovar(segundo)
        self.assertEqual(resposta.status_code, 409)
        self.assertIn("1/1 vídeo longo", resposta.get_json()["error"])
        enviar.assert_not_called()
        self.assertEqual(cota.resumo()["1"]["por_tipo"]["longo"]["usados"], 1)

    def test_terceiro_short_do_dia_espera_o_proximo_ciclo(self):
        nomes = [self._criar_video(f"short-extra-{i}.mp4").name for i in range(3)]
        ids = (f"yt{i}" for i in itertools.count())
        with mock.patch.object(web, "enviar_video_agendado", side_effect=lambda **_: (True, "ok", next(ids))):
            for nome in nomes[:2]:
                self.assertEqual(self._aprovar(nome).status_code, 200)
            resposta = self._aprovar(nomes[2])
        self.assertEqual(resposta.status_code, 409)
        self.assertIn("2/2 Shorts", resposta.get_json()["error"])
        self.assertIn("05:00", resposta.get_json()["error"])

    def test_cada_tipo_e_publicado_no_seu_horario(self):
        longo = self._criar_video("longo-a-parte1.mp4").name
        with mock.patch.object(web, "enviar_video_agendado", return_value=(True, "ok", "yt1")) as enviar:
            self._aprovar(longo)
            self.assertIn(enviar.call_args.kwargs["hora_agenda"], HORARIOS_POR_TIPO["longo"])
            self._aprovar()
            self.assertIn(enviar.call_args.kwargs["hora_agenda"], HORARIOS_POR_TIPO["short"])

    def test_grade_de_cada_tipo_pode_ser_trocada_no_arquivo_de_afiliados(self):
        (self.raiz / "afiliados.json").write_text(json.dumps({"horarios_por_tipo": {"longo": ["20:00"]}}), encoding="utf-8")
        self.assertEqual(web.grade_do_tipo("longo"), ["20:00"])
        self.assertEqual(web.grade_do_tipo("short"), HORARIOS_POR_TIPO["short"])

    def test_video_do_formato_antigo_nao_vai_para_o_canal(self):
        nome = self._criar_video("longo-antigo-parte1.mp4").name
        (self.raiz / "metadados_cortes.json").write_text(
            json.dumps({nome: {"titulo": "Sem narração", "formato": "padrao"}}), encoding="utf-8")
        with mock.patch.object(web, "enviar_video_agendado") as enviar:
            resposta = self._aprovar(nome)
        self.assertEqual(resposta.status_code, 409)
        self.assertTrue(resposta.get_json()["fora_do_padrao"])
        enviar.assert_not_called()
        self.assertTrue((self.export_dir / nome).exists())

    def test_caos_envios_simultaneos_nao_ultrapassam_a_cota(self):
        self.consultar_youtube.return_value = QUASE_CHEIO
        outro = self._criar_video("short-outro.mp4")
        liberar = threading.Event()
        iniciou = threading.Event()

        def enviar(**_):
            iniciou.set()
            liberar.wait(5)
            return True, "ok", "yt-novo"

        with mock.patch.object(web, "enviar_video_agendado", side_effect=enviar) as envio:
            t = threading.Thread(target=lambda: web.app.test_client().post(
                "/api/aprovar", json={"filename": self.video.name, "canal": "1"}))
            t.start()
            self.assertTrue(iniciou.wait(5))
            resposta = self._aprovar(outro.name)
            liberar.set()
            t.join()
        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(envio.call_count, 1)

    def test_falha_no_envio_devolve_a_vaga(self):
        self.consultar_youtube.return_value = QUASE_CHEIO
        with mock.patch.object(web, "enviar_video_agendado", return_value=(False, "falha de rede", None)):
            self._aprovar()
        with mock.patch.object(web, "enviar_video_agendado", return_value=(True, "ok", "yt1")) as enviar:
            self.assertEqual(self._aprovar().status_code, 200)
        enviar.assert_called_once()

    def test_cota_esgotada_na_api_bloqueia_tudo_ate_as_cinco(self):
        with mock.patch.object(web, "enviar_video_agendado", return_value=(False, "Erro YouTube API: quotaExceeded", None)):
            self._aprovar()
        outro = self._criar_video("short-outro.mp4").name
        with mock.patch.object(web, "enviar_video_agendado") as enviar:
            self.assertEqual(self._aprovar(outro).status_code, 409)
        enviar.assert_not_called()
        self.assertTrue(cota.resumo()["1"]["bloqueado"])

    def test_limite_do_proprio_youtube_trava_o_canal(self):
        recusa = "Erro YouTube API: uploadLimitExceeded The user has exceeded the number of videos they may upload."
        with mock.patch.object(web, "enviar_video_agendado", return_value=(False, recusa, None)):
            self._aprovar()
        with mock.patch.object(web, "enviar_video_agendado") as enviar:
            resposta = self._aprovar()
        self.assertEqual(resposta.status_code, 409)
        enviar.assert_not_called()
        self.assertTrue(cota.resumo()["1"]["bloqueado"])

    def test_limite_do_youtube_libera_no_proximo_ciclo(self):
        cota.marcar_canal_no_limite("1", agora=ANTES_DAS_5)
        self.assertTrue(cota.resumo(agora=ANTES_DAS_5)["1"]["bloqueado"])
        self.assertFalse(cota.resumo(agora=AS_5)["1"]["bloqueado"])

    def test_caos_registro_corrompido_e_reconstruido_pelo_youtube(self):
        cota.COTAS_FILE.write_text('{"ciclo": "quebr', encoding="utf-8")
        self.consultar_youtube.return_value = CANAL_CHEIO
        with mock.patch.object(web, "enviar_video_agendado") as enviar:
            self.assertEqual(self._aprovar().status_code, 409)
        enviar.assert_not_called()


class TestPainelDeEstrelas(AmbienteIsolado):

    def setUp(self):
        super().setUp()
        self.client = web.app.test_client()

    def test_painel_recebe_estrelas_e_envios_do_ciclo(self):
        self.consultar_youtube.return_value = ["a", "b"]
        cota.sincronizar_canal("1")
        dados = self.client.get("/api/data").get_json()
        self.assertEqual(dados["cotas"]["1"]["usados"], 2)
        self.assertEqual((dados["envios_hoje"], dados["limite_envios"]), (2, COTA * len(CANAIS_VIELA_VICE)))
        self.assertEqual(dados["limite_envios"], 3)
        self.assertEqual(dados["canais"], [{"id": "1", "nome": "1. Viela Vice (Principal - GTA 6)"}])
        self.assertEqual(dados["cota_por_tipo"], COTA_POR_TIPO)
        self.assertEqual(dados["limite_estoque"], VIDEO_SPECS["limite_estoque_max"])

    def test_titulo_do_corte_chega_ao_painel(self):
        video = self.export_dir / "short-a.mp4"
        video.write_bytes(b"x" * 1000)
        (self.raiz / "metadados_cortes.json").write_text(
            json.dumps({video.name: {"titulo": "A POLÍCIA PEGOU ELE #Shorts", "descricao": "Créditos"}}), encoding="utf-8")
        item = self.client.get("/api/data").get_json()["pendentes"][0]
        self.assertEqual((item["titulo"], item["descricao"]), ("A POLÍCIA PEGOU ELE #Shorts", "Créditos"))

    def test_botao_play_pause_mostra_se_a_producao_esta_ligada(self):
        js = self.client.get("/painel.js").get_data(as_text=True)
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("function desenharBotaoVarredura(", js)
        self.assertIn("ponto-ao-vivo", js)
        self.assertIn("PRODUZINDO", js)
        self.assertNotIn("AO VIVO", js)
        self.assertIn(".ponto-ao-vivo", html)
        self.assertIn("prefers-reduced-motion", html)

    def test_painel_mostra_estrelas_no_gerente_e_no_botao(self):
        js = self.client.get("/painel.js").get_data(as_text=True)
        html = self.client.get("/").get_data(as_text=True)
        for trecho in ("function desenharEstrelas(", "function verificarTravaCanal(", "btn-enviar-hoje", "estrelas-canal"):
            self.assertIn(trecho, js)
        self.assertIn('id="b-niv"', html)
