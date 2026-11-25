"""
Números do canal no painel: a consulta ao YouTube roda em segundo plano, no máximo uma vez por hora,
e o painel nunca espera por ela.
"""
import threading
import time
import unittest
from unittest import mock

from src.youtube import canal


class TestNumerosDoCanal(unittest.TestCase):

    NUMEROS = {"nome": "Viela Vice", "inscritos": 1200, "visualizacoes": 50000, "videos": 30, "atualizado_em": "17:00"}

    def setUp(self):
        patcher = mock.patch.dict(canal._cache, {"dados": {}, "consultado_em": None, "consultando": False}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(canal, "log_terminal")
        self.log = patcher.start()
        self.addCleanup(patcher.stop)

    def _esperar_consulta(self):
        for _ in range(500):
            if not canal._cache["consultando"]:
                return
            time.sleep(0.01)
        self.fail("a consulta em segundo plano não terminou")

    def test_painel_nao_espera_o_youtube_responder(self):
        liberar = threading.Event()

        def consultar():
            liberar.wait(5)
            return dict(self.NUMEROS)

        with mock.patch.object(canal, "_consultar", side_effect=consultar) as consulta:
            self.assertEqual(canal.estatisticas_do_canal(), {})
            self.assertEqual(canal.estatisticas_do_canal(), {}, "a segunda chamada não abre outra consulta")
            liberar.set()
            self._esperar_consulta()
            self.assertEqual(canal.estatisticas_do_canal()["inscritos"], 1200)
        self.assertEqual(consulta.call_count, 1)

    def test_numeros_valem_por_uma_hora(self):
        canal._cache.update(dados=dict(self.NUMEROS), consultado_em=time.monotonic() - canal.INTERVALO_S + 60)
        with mock.patch.object(canal, "_consultar", return_value=dict(self.NUMEROS)) as consulta:
            self.assertEqual(canal.estatisticas_do_canal()["inscritos"], 1200)
            consulta.assert_not_called()
            canal._cache["consultado_em"] = time.monotonic() - canal.INTERVALO_S
            canal.estatisticas_do_canal()
            self._esperar_consulta()
            consulta.assert_called_once()

    def test_falha_do_youtube_mantem_os_ultimos_numeros(self):
        canal._cache.update(dados=dict(self.NUMEROS), consultado_em=time.monotonic() - canal.INTERVALO_S)
        with mock.patch.object(canal, "_consultar", side_effect=OSError("sem internet")):
            self.assertEqual(canal.estatisticas_do_canal()["inscritos"], 1200)
            self._esperar_consulta()
        self.assertEqual(canal.estatisticas_do_canal()["inscritos"], 1200)
        self.assertIn("nova consulta em 1 hora", self.log.call_args.args[0])

    def test_canal_sem_autorizacao_fica_sem_numeros(self):
        with mock.patch.object(canal, "obter_credenciais", return_value=None), \
                mock.patch.object(canal, "build") as youtube:
            self.assertEqual(canal._consultar(), {})
        youtube.assert_not_called()

    def test_le_os_numeros_do_proprio_canal_so_para_leitura(self):
        youtube = mock.MagicMock()
        youtube.channels.return_value.list.return_value.execute.return_value = {"items": [{
            "snippet": {"title": "Viela Vice"},
            "statistics": {"subscriberCount": "1200", "viewCount": "50000", "videoCount": "30"}}]}
        with mock.patch.object(canal, "obter_credenciais", return_value=object()), \
                mock.patch.object(canal, "build", return_value=youtube):
            numeros = canal._consultar()
        self.assertEqual((numeros["nome"], numeros["inscritos"], numeros["visualizacoes"], numeros["videos"]),
                         ("Viela Vice", 1200, 50000, 30))
        youtube.channels.return_value.list.assert_called_once_with(part="statistics,snippet", mine=True)


if __name__ == "__main__":
    unittest.main()
