"""
SPEC-003: o log de produção precisa ser confiável mesmo sob concorrência e falhas.
"""
import io
import re
import threading
import unittest
from unittest import mock

from apoio import AmbienteIsolado
from src import utils


class StdoutQuebrado(io.StringIO):
    def write(self, _texto):
        raise UnicodeEncodeError("charmap", "😱", 0, 1, "console sem suporte")


class TestLogDeProducao(AmbienteIsolado):

    def test_grava_no_arquivo_padrao(self):
        utils.log_terminal("[TESTE] mensagem")
        self.assertIn("[TESTE] mensagem", self.log_file.read_text(encoding="utf-8"))

    def test_caos_console_sem_emoji_nao_derruba_o_ciclo(self):
        with mock.patch("sys.stdout", StdoutQuebrado()):
            utils.log_terminal("Live insana 😱")
        self.assertIn("😱", self.log_file.read_text(encoding="utf-8"))

    def test_caos_disco_indisponivel_nao_derruba_o_ciclo(self):
        with mock.patch("builtins.open", side_effect=OSError("sem acesso")):
            utils.log_terminal("segue o jogo")

    def test_caos_threads_simultaneas_nao_perdem_linhas(self):
        def escrever(n):
            for i in range(25):
                utils.log_terminal(f"thread-{n}-linha-{i}")

        threads = [threading.Thread(target=escrever, args=(n,)) for n in range(6)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        linhas = self.log_file.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(linhas), 150)
        self.assertTrue(all(re.match(r"^\[\d\d:\d\d:\d\d\] thread-\d-linha-\d+$", l) for l in linhas))

    def test_arquivo_tem_tamanho_limitado(self):
        with mock.patch.object(utils, "LIMITE_BYTES_LOG", 2000), mock.patch.object(utils, "MAX_LINHAS_LOG", 10):
            for i in range(200):
                utils.log_terminal(f"linha numero {i} " + "x" * 40)
        linhas = utils.ler_ultimas_linhas(500)
        self.assertLessEqual(len(linhas), 40)
        self.assertIn("linha numero 199", linhas[-1])

    def test_mensagem_de_varias_linhas_vira_uma_so(self):
        utils.log_terminal("erro\nsegunda parte\r\nterceira")
        self.assertEqual(len(utils.ler_ultimas_linhas(10)), 1)

    def test_credenciais_nunca_aparecem_no_console(self):
        utils.log_terminal("GET https://x.test/v?api_key=SEGREDO123&token=OUTRO456&id=1")
        conteudo = self.log_file.read_text(encoding="utf-8")
        self.assertNotIn("SEGREDO123", conteudo)
        self.assertNotIn("OUTRO456", conteudo)
        self.assertIn("id=1", conteudo)


if __name__ == "__main__":
    unittest.main()
