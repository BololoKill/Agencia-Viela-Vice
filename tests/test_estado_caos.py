"""
SPEC-003: estado operacional, trava de ciclo único e engenharia do caos.
"""
import json
import os
import subprocess
import sys
import threading
import time
import unittest
from unittest import mock

from apoio import AmbienteIsolado
from src import utils
from src.pipeline import estado
from src.pipeline.ffmpeg_runner import FFmpegError


class TestClassificacaoDeErros(unittest.TestCase):
    """Responde à pergunta do Gabriel: é rate limit, cota, rede ou o editor?"""

    def test_tabela_de_categorias(self):
        casos = [
            (FFmpegError("legendas", 1, "x"), "render", False),
            (RuntimeError("ERROR: HTTP Error 429: Too Many Requests"), "rate_limit", True),
            (RuntimeError("Sign in to confirm you're not a bot"), "bloqueio_youtube", True),
            (RuntimeError("quotaExceeded: The request cannot be completed"), "cota_api", True),
            (ConnectionError("getaddrinfo failed"), "rede", True),
            (TimeoutError("timed out"), "rede", True),
            (OSError(28, "No space left on device"), "disco", True),
            (ValueError("algo inesperado"), "desconhecido", False),
        ]
        for erro, categoria, transitorio in casos:
            with self.subTest(categoria=categoria):
                info = estado.classificar_erro(erro)
                self.assertEqual(info["categoria"], categoria)
                self.assertEqual(info["transitorio"], transitorio)
                self.assertTrue(info["mensagem"])


class TestTravaDeCicloUnico(AmbienteIsolado):

    def test_apenas_um_ciclo_por_vez_entre_threads(self):
        ganhou = []
        barreira = threading.Barrier(8)
        travas = [estado.TravaCiclo() for _ in range(8)]

        def disputar(trava):
            barreira.wait()
            if trava.adquirir():
                ganhou.append(trava)

        threads = [threading.Thread(target=disputar, args=(t,)) for t in travas]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(len(ganhou), 1)
        ganhou[0].liberar()

    def test_trava_liberada_pode_ser_readquirida(self):
        trava = estado.TravaCiclo()
        self.assertTrue(trava.adquirir())
        self.assertTrue(estado.ciclo_em_andamento())
        trava.liberar()
        self.assertFalse(estado.ciclo_em_andamento())
        self.assertTrue(trava.adquirir())
        trava.liberar()

    def test_caos_processo_morto_nao_bloqueia_producao(self):
        """Queda de energia ou processo encerrado à força deixa a trava órfã."""
        proc = subprocess.Popen([sys.executable, "-c", "pass"])
        proc.wait()
        estado.TRAVA_CICLO_FILE.write_text(json.dumps({"pid": proc.pid, "criado_em": 1.0}), encoding="utf-8")
        self.assertFalse(estado.ciclo_em_andamento())
        trava = estado.TravaCiclo()
        self.assertTrue(trava.adquirir())
        trava.liberar()

    def test_caos_trava_corrompida_e_recuperada(self):
        estado.TRAVA_CICLO_FILE.write_bytes(b"\x00\xff lixo")
        antigo = time.time() - 60
        os.utime(estado.TRAVA_CICLO_FILE, (antigo, antigo))
        trava = estado.TravaCiclo()
        self.assertTrue(trava.adquirir())
        trava.liberar()


class TestSaudeDerivada(AmbienteIsolado):

    def _status(self, **campos):
        self.status_file.write_text(json.dumps(campos), encoding="utf-8")

    def test_ocioso_com_batimento_recente(self):
        self._status(heartbeat=time.time(), etapa="Aguardando")
        self.assertEqual(estado.ler_status()["saude"], "ocioso")

    def test_robo_desligado_quando_batimento_e_antigo(self):
        self._status(heartbeat=time.time() - 3600)
        self.assertEqual(estado.ler_status()["saude"], "parado")

    def test_produzindo_e_travado(self):
        trava = estado.TravaCiclo()
        self.assertTrue(trava.adquirir())
        self.addCleanup(trava.liberar)
        self._status(heartbeat=time.time())
        self.assertEqual(estado.ler_status()["saude"], "produzindo")
        self._status(heartbeat=time.time() - estado.LIMITE_TRAVADO_S - 5)
        self.assertEqual(estado.ler_status()["saude"], "travado")

    def test_pausa_e_erro(self):
        self._status(heartbeat=time.time(), erro={"categoria": "rede", "mensagem": "sem internet"})
        self.assertEqual(estado.ler_status()["saude"], "erro")
        estado.definir_producao_ativa(False)
        self.assertEqual(estado.ler_status()["saude"], "pausado")
        self.assertFalse(estado.producao_ativa())

    def test_caos_status_corrompido_nao_derruba_leitura(self):
        self.status_file.write_bytes(b'{"etapa": "cortad')
        self.assertEqual(estado.ler_status()["saude"], "parado")
        self.status_file.write_text("[1, 2, 3]", encoding="utf-8")
        self.assertEqual(estado.ler_status()["saude"], "parado")

    def test_publicar_preserva_campos_anteriores(self):
        estado.publicar_status(etapa="Baixando", streamer="Luqueta")
        estado.publicar_status(progresso=40)
        dados = json.loads(self.status_file.read_text(encoding="utf-8"))
        self.assertEqual((dados["etapa"], dados["streamer"], dados["progresso"]), ("Baixando", "Luqueta", 40))


class TestQuarentena(AmbienteIsolado):

    def test_video_problematico_entra_em_quarentena_na_terceira_falha(self):
        info = {"categoria": "render", "mensagem": "falhou"}
        for _ in range(estado.MAX_TENTATIVAS_VIDEO - 1):
            estado.registrar_falha("abc", info)
            self.assertFalse(estado.em_quarentena("abc"))
        estado.registrar_falha("abc", info)
        self.assertTrue(estado.em_quarentena("abc"))
        self.assertFalse(estado.em_quarentena("outro"))


class TestPersistenciaAtomica(AmbienteIsolado):

    def test_caos_escritas_concorrentes_nunca_corrompem_o_json(self):
        alvo = self.raiz / "concorrente.json"
        utils.save_json_safe(alvo, {"n": 0, "dados": "x" * 2000})
        parar = threading.Event()
        erros = []

        def leitor():
            while not parar.is_set():
                try:
                    json.loads(alvo.read_text(encoding="utf-8"))
                except PermissionError:
                    continue
                except ValueError as e:
                    erros.append(e)

        def escritor(n):
            for i in range(40):
                utils.save_json_safe(alvo, {"n": n * i, "dados": "x" * 2000})

        t_leitor = threading.Thread(target=leitor)
        t_leitor.start()
        escritores = [threading.Thread(target=escritor, args=(n,)) for n in range(5)]
        [t.start() for t in escritores]
        [t.join() for t in escritores]
        parar.set()
        t_leitor.join()
        self.assertEqual(erros, [])
        self.assertEqual(list(self.raiz.glob("*.tmp")), [])

    def test_falha_ao_salvar_preserva_arquivo_anterior(self):
        alvo = self.raiz / "seguro.json"
        utils.save_json_safe(alvo, {"versao": 1})
        with mock.patch.object(utils.os, "replace", side_effect=OSError("disco cheio")):
            self.assertFalse(utils.save_json_safe(alvo, {"versao": 2}))
        self.assertEqual(json.loads(alvo.read_text(encoding="utf-8")), {"versao": 1})


if __name__ == "__main__":
    unittest.main()
