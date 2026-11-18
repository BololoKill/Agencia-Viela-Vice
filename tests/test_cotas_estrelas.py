"""
SPEC-004: a regra de 6 envios por canal não pode falhar e só reinicia às 05:00.
"""
import itertools
import json
import threading
from datetime import datetime
from unittest import mock

from apoio import AmbienteIsolado
import src.web.app as web
from src.youtube import cota

ANTES_DAS_5 = datetime(2026, 11, 18, 4, 59)
AS_5 = datetime(2026, 11, 18, 5, 0)


class TestCicloDaCota(AmbienteIsolado):

    def test_ciclo_vira_somente_as_cinco_da_manha(self):
        self.assertEqual(cota.inicio_ciclo_cota(ANTES_DAS_5), datetime(2026, 11, 17, 5, 0))
        self.assertEqual(cota.inicio_ciclo_cota(AS_5), AS_5)

    def test_estrelas_vem_dos_envios_reais_do_youtube(self):
        self.consultar_youtube.return_value = ["a", "b", "c"]
        cota.sincronizar_canal("2", agora=ANTES_DAS_5)
        resumo = cota.resumo(agora=ANTES_DAS_5)
        self.assertEqual((resumo["2"]["usados"], resumo["2"]["limite"]), (3, 6))
        self.assertTrue(resumo["2"]["verificado"])
        self.assertEqual(resumo["1"]["usados"], 0)

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
        cota.sincronizar_canal("3", agora=ANTES_DAS_5)
        self.consultar_youtube.return_value = ["agendado", "novo"]
        cota.sincronizar_canal("3", agora=AS_5)
        self.assertEqual(cota.resumo(agora=AS_5)["3"]["usados"], 1)

    def test_seis_estrelas_bloqueiam_o_canal(self):
        self.consultar_youtube.return_value = list("abcdef")
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

    def test_setimo_envio_e_recusado_sem_chamar_o_youtube(self):
        self.consultar_youtube.return_value = list("abcdef")
        with mock.patch.object(web, "enviar_video_agendado") as enviar:
            resposta = self._aprovar()
        self.assertEqual(resposta.status_code, 409)
        self.assertTrue(resposta.get_json()["cota_esgotada"])
        enviar.assert_not_called()
        self.assertTrue(self.video.exists())

    def test_outro_canal_continua_liberado(self):
        self.consultar_youtube.side_effect = lambda canal, _inicio: list("abcdef") if canal == "1" else []
        with mock.patch.object(web, "enviar_video_agendado", return_value=(True, "ok", "yt9")) as enviar:
            self.assertEqual(self._aprovar(canal="2").status_code, 200)
        enviar.assert_called_once()

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
            for i in range(6):
                nome = self._criar_video(f"short-{i}.mp4").name
                self.assertEqual(self._aprovar(nome).status_code, 200)
            self.assertEqual(self._aprovar().status_code, 409)
        self.assertEqual(enviar.call_count, 6)

    def test_caos_envios_simultaneos_nao_ultrapassam_a_cota(self):
        self.consultar_youtube.return_value = list("abcde")
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
        self.consultar_youtube.return_value = list("abcde")
        with mock.patch.object(web, "enviar_video_agendado", return_value=(False, "falha de rede", None)):
            self._aprovar()
        with mock.patch.object(web, "enviar_video_agendado", return_value=(True, "ok", "yt1")) as enviar:
            self.assertEqual(self._aprovar().status_code, 200)
        enviar.assert_called_once()

    def test_cota_esgotada_na_api_bloqueia_tudo_ate_as_cinco(self):
        with mock.patch.object(web, "enviar_video_agendado", return_value=(False, "Erro YouTube API: quotaExceeded", None)):
            self._aprovar()
        with mock.patch.object(web, "enviar_video_agendado") as enviar:
            self.assertEqual(self._aprovar(canal="5").status_code, 409)
        enviar.assert_not_called()
        self.assertTrue(cota.resumo()["5"]["bloqueado"])

    def test_caos_registro_corrompido_e_reconstruido_pelo_youtube(self):
        cota.COTAS_FILE.write_text('{"ciclo": "quebr', encoding="utf-8")
        self.consultar_youtube.return_value = list("abcdef")
        with mock.patch.object(web, "enviar_video_agendado") as enviar:
            self.assertEqual(self._aprovar().status_code, 409)
        enviar.assert_not_called()


class TestPainelDeEstrelas(AmbienteIsolado):

    def setUp(self):
        super().setUp()
        self.client = web.app.test_client()

    def test_painel_recebe_estrelas_e_envios_do_ciclo(self):
        self.consultar_youtube.return_value = ["a", "b"]
        cota.sincronizar_canal("2")
        dados = self.client.get("/api/data").get_json()
        self.assertEqual(dados["cotas"]["2"]["usados"], 2)
        self.assertEqual((dados["envios_hoje"], dados["limite_envios"]), (2, 42))

    def test_titulo_do_corte_chega_ao_painel(self):
        video = self.export_dir / "short-a.mp4"
        video.write_bytes(b"x" * 1000)
        (self.raiz / "metadados_cortes.json").write_text(
            json.dumps({video.name: {"titulo": "A POLÍCIA PEGOU ELE #Shorts", "descricao": "Créditos"}}), encoding="utf-8")
        item = self.client.get("/api/data").get_json()["pendentes"][0]
        self.assertEqual((item["titulo"], item["descricao"]), ("A POLÍCIA PEGOU ELE #Shorts", "Créditos"))

    def test_botao_play_pause_tem_bolinha_ao_vivo(self):
        js = self.client.get("/painel.js").get_data(as_text=True)
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("function desenharBotaoVarredura(", js)
        self.assertIn("ponto-ao-vivo", js)
        self.assertIn("AO VIVO", js)
        self.assertIn(".ponto-ao-vivo", html)
        self.assertIn("prefers-reduced-motion", html)

    def test_painel_mostra_estrelas_no_gerente_e_no_botao(self):
        js = self.client.get("/painel.js").get_data(as_text=True)
        html = self.client.get("/").get_data(as_text=True)
        for trecho in ("function desenharEstrelas(", "function verificarTravaCanal(", "btn-enviar-hoje", "estrelas-canal"):
            self.assertIn(trecho, js)
        self.assertIn('id="b-niv"', html)
