"""
SPEC-003: contrato HTTP, segurança e idempotência das APIs do Escritório Virtual.
"""
import json
import socket
import threading
import unittest
from unittest import mock

import main as cli
from apoio import AmbienteIsolado
from src.pipeline import estado
import src.web.app as web


class BaseApi(AmbienteIsolado):

    def setUp(self):
        super().setUp()
        self.client = web.app.test_client()
        self.video = self.export_dir / "short-luqueta-corte1.mp4"
        self.video.write_bytes(b"x" * 1000)


class TestSeguranca(BaseApi):

    def test_segredos_da_raiz_nao_sao_servidos(self):
        for rota in ("/editor-de-video/.env", "/editor-de-video/token.json",
                     "/editor-de-video/client_secret.json", "/editor-de-video/cookies.txt", "/static/.env"):
            with self.subTest(rota=rota):
                self.assertEqual(self.client.get(rota).status_code, 404)

    def test_negar_nao_apaga_arquivo_fora_da_exportacao(self):
        segredo = self.raiz / "segredo.json"
        segredo.write_text("{}", encoding="utf-8")
        for nome in ("../segredo.json", "..\\segredo.json", str(segredo), "x:y.mp4"):
            with self.subTest(nome=nome):
                self.assertEqual(self.client.post("/api/negar", json={"filename": nome}).status_code, 400)
        self.assertTrue(segredo.exists())

    def test_aprovar_recusa_caminho_invalido(self):
        with mock.patch.object(web, "enviar_video_agendado") as enviar:
            resposta = self.client.post("/api/aprovar", json={"filename": "../token.json"})
        self.assertEqual(resposta.status_code, 400)
        enviar.assert_not_called()

    def test_servidor_escuta_so_na_maquina_por_padrao(self):
        with mock.patch.object(web.app, "run") as run:
            web.iniciar_servidor()
        self.assertEqual(run.call_args.kwargs["host"], "127.0.0.1")


class TestAprovacaoIdempotente(BaseApi):

    def test_duplo_clique_nao_envia_duas_vezes(self):
        def enviar(video_path, **_):
            return True, "ok", "yt123"

        with mock.patch.object(web, "enviar_video_agendado", side_effect=enviar) as envio:
            primeira = self.client.post("/api/aprovar", json={"filename": self.video.name})
            segunda = self.client.post("/api/aprovar", json={"filename": self.video.name})
        self.assertEqual((primeira.status_code, segunda.status_code), (200, 200))
        self.assertTrue(segunda.get_json()["ja_agendado"])
        self.assertEqual(envio.call_count, 1)
        self.assertEqual(len(json.loads(self.agendados_file.read_text(encoding="utf-8"))), 1)

    def test_aprovacao_simultanea_retorna_409(self):
        liberar = threading.Event()
        iniciou = threading.Event()

        def enviar(video_path, **_):
            iniciou.set()
            liberar.wait(5)
            return True, "ok", "yt123"

        with mock.patch.object(web, "enviar_video_agendado", side_effect=enviar):
            t = threading.Thread(target=lambda: web.app.test_client().post(
                "/api/aprovar", json={"filename": self.video.name}))
            t.start()
            self.assertTrue(iniciou.wait(5))
            resposta = self.client.post("/api/aprovar", json={"filename": self.video.name})
            liberar.set()
            t.join()
        self.assertEqual(resposta.status_code, 409)

    def test_falha_no_youtube_preserva_video_e_nao_duplica_registro(self):
        with mock.patch.object(web, "enviar_video_agendado", return_value=(False, "quotaExceeded", None)):
            resposta = self.client.post("/api/aprovar", json={"filename": self.video.name})
            self.client.post("/api/aprovar", json={"filename": self.video.name})
        self.assertFalse(resposta.get_json()["enviado_youtube"])
        self.assertIn("quotaExceeded", resposta.get_json()["message"])
        self.assertTrue(self.video.exists())
        self.assertEqual(len(json.loads(self.agendados_file.read_text(encoding="utf-8"))), 1)

    def test_excecao_no_envio_vira_resposta_tratada(self):
        with mock.patch.object(web, "enviar_video_agendado", side_effect=RuntimeError("token expirado")):
            resposta = self.client.post("/api/aprovar", json={"filename": self.video.name})
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(resposta.get_json()["enviado_youtube"])


class TestRejeicaoNaFila(BaseApi):

    def _fila(self):
        return json.loads(self.agendados_file.read_text(encoding="utf-8"))

    def test_rejeitar_apos_falha_no_envio_tira_o_video_da_fila(self):
        with mock.patch.object(web, "enviar_video_agendado", return_value=(False, "invalid_scope", None)):
            self.client.post("/api/aprovar", json={"filename": self.video.name})
        self.assertEqual(len(self._fila()), 1)
        resposta = self.client.post("/api/negar", json={"filename": self.video.name})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(self._fila(), [])
        self.assertFalse(self.video.exists())

    def test_rejeitar_de_novo_limpa_registro_orfao(self):
        self.video.unlink()
        self.agendados_file.write_text(json.dumps([
            {"filename": self.video.name, "data": "2026-11-18", "horario": "11:30", "youtube_id": None}
        ]), encoding="utf-8")
        self.assertEqual(self.client.post("/api/negar", json={"filename": self.video.name}).status_code, 200)
        self.assertEqual(self._fila(), [])

    def test_rejeitar_preserva_video_ja_enviado_ao_youtube(self):
        registro = {"filename": self.video.name, "data": "2026-11-18", "horario": "11:30", "youtube_id": "yt123"}
        self.agendados_file.write_text(json.dumps([registro]), encoding="utf-8")
        self.client.post("/api/negar", json={"filename": self.video.name})
        self.assertEqual(self._fila(), [registro])

    def test_rejeitar_nao_afeta_outros_videos_da_fila(self):
        outro = {"filename": "short-outro.mp4", "data": "2026-11-18", "horario": "13:00", "youtube_id": None}
        self.agendados_file.write_text(json.dumps([
            {"filename": self.video.name, "data": "2026-11-18", "horario": "11:30", "youtube_id": None}, outro
        ]), encoding="utf-8")
        self.client.post("/api/negar", json={"filename": self.video.name})
        self.assertEqual(self._fila(), [outro])

    def test_rejeitar_durante_o_envio_e_recusado(self):
        liberar = threading.Event()
        iniciou = threading.Event()

        def enviar(video_path, **_):
            iniciou.set()
            liberar.wait(5)
            return False, "falha simulada", None

        with mock.patch.object(web, "enviar_video_agendado", side_effect=enviar):
            t = threading.Thread(target=lambda: web.app.test_client().post(
                "/api/aprovar", json={"filename": self.video.name}))
            t.start()
            self.assertTrue(iniciou.wait(5))
            resposta = self.client.post("/api/negar", json={"filename": self.video.name})
            liberar.set()
            t.join()
        self.assertEqual(resposta.status_code, 409)
        self.assertTrue(self.video.exists())


class TestControleDaProducao(BaseApi):

    def _com_ciclo_rodando(self):
        trava = estado.TravaCiclo()
        self.assertTrue(trava.adquirir())
        self.addCleanup(trava.liberar)

    def test_buscar_lives_inicia_um_ciclo(self):
        chamado = threading.Event()
        with mock.patch.object(web, "executar_ciclo_producao", side_effect=chamado.set):
            resposta = self.client.post("/api/buscar_lives")
            self.assertTrue(chamado.wait(5))
        self.assertTrue(resposta.get_json()["iniciado"])

    def test_buscar_lives_e_idempotente_com_ciclo_rodando(self):
        self._com_ciclo_rodando()
        with mock.patch.object(web, "executar_ciclo_producao") as ciclo:
            resposta = self.client.post("/api/buscar_lives")
        self.assertFalse(resposta.get_json()["iniciado"])
        ciclo.assert_not_called()

    def test_purga_recusada_durante_producao(self):
        self._com_ciclo_rodando()
        (self.bruto_dir / "live_bruta.webm").write_bytes(b"em uso")
        self.assertEqual(self.client.post("/api/ti/purge").status_code, 409)
        self.assertTrue((self.bruto_dir / "live_bruta.webm").exists())

    def test_varredura_pausa_e_retoma(self):
        pausa = self.client.post("/api/varredura", json={"ativo": False}).get_json()
        self.assertFalse(pausa["ativo"])
        self.assertFalse(estado.producao_ativa())
        retoma = self.client.post("/api/varredura", json={"ativo": True}).get_json()
        self.assertTrue(retoma["ativo"])

    def test_varredura_recusa_payload_invalido(self):
        for corpo in ({}, {"ativo": "sim"}, {"ativo": None}):
            with self.subTest(corpo=corpo):
                self.assertEqual(self.client.post("/api/varredura", json=corpo).status_code, 400)


class TestObservabilidadeHttp(BaseApi):

    def test_status_expoe_contrato_completo(self):
        estado.publicar_status(etapa="Baixando", progresso=25, streamer="Luqueta")
        dados = self.client.get("/api/status").get_json()
        for campo in ("saude", "etapa", "progresso", "streamer", "ativo", "erro", "mensagem"):
            self.assertIn(campo, dados)
        self.assertEqual(dados["etapa"], "Baixando")

    def test_aba_aberta_recebe_aviso_de_nova_versao(self):
        self.assertTrue(self.client.get("/api/status").get_json()["versao_painel"])
        self.assertIn("location.reload()", self.client.get("/painel.js").get_data(as_text=True))

    def test_diagnostico_nao_afirma_estabilidade_falsa(self):
        dados = self.client.get("/api/ti_diagnostico").get_json()
        self.assertEqual(dados["saude"], "parado")
        self.assertNotIn("Estável", dados["status"])

    def test_terminal_sem_log_responde_vazio(self):
        dados = self.client.get("/api/ti_terminal").get_json()
        self.assertEqual(dados["linhas"], [])

    def test_caos_log_com_bytes_invalidos_nao_derruba_console(self):
        self.log_file.write_bytes(b"[10:00:00] ok\n\xff\xfe\x00 lixo\n[10:00:01] fim\n")
        resposta = self.client.get("/api/ti_terminal")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json()["linhas"][-1], "[10:00:01] fim")

    def test_painel_sempre_recebe_versao_nova(self):
        for rota in ("/", "/painel.js"):
            self.assertEqual(self.client.get(rota).headers.get("Cache-Control"), "no-store")

    def test_painel_consulta_console_e_status(self):
        js = self.client.get("/painel.js").get_data(as_text=True)
        self.assertIn("/api/ti_terminal", js)
        self.assertIn("/api/status", js)
        self.assertIn("/api/varredura", js)

    def test_console_tem_botao_de_copiar(self):
        html = self.client.get("/").get_data(as_text=True)
        js = self.client.get("/painel.js").get_data(as_text=True)
        self.assertIn('id="btn-copiar-console"', html)
        self.assertIn('onclick="copiarConsole()"', html)
        self.assertIn("function copiarConsole()", js)
        self.assertIn("navigator.clipboard", js)
        self.assertIn("execCommand('copy')", js)


class TestInstanciaUnica(unittest.TestCase):

    def test_detecta_porta_ocupada(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            s.listen(1)
            porta = s.getsockname()[1]
            self.assertTrue(web.porta_em_uso(porta))
        self.assertFalse(web.porta_em_uso(porta))

    def test_segundo_servidor_nao_sobe_nem_liga_outro_robo(self):
        with mock.patch.object(cli, "porta_em_uso", return_value=True), \
             mock.patch.object(cli, "iniciar_servidor") as servidor, \
             mock.patch.object(cli, "loop_vigia_continuo") as robo, \
             mock.patch("sys.argv", ["main.py", "run"]):
            self.assertEqual(cli.main(), 3)
        servidor.assert_not_called()
        robo.assert_not_called()


if __name__ == "__main__":
    unittest.main()
