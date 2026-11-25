"""
O trabalho pesado da produção (downloads e arquivos temporários) fica no SSD D:, mais rápido e poupando o HD
onde estão o Windows e os arquivos do dono. Sem o SSD, a produção continua na pasta do projeto.
"""
import tempfile
import unittest
from pathlib import Path

from src import config


def unidade_que_nao_existe() -> Path:
    for letra in "ZYXWVUTSRQPONMLKJIHGFE":
        if not Path(f"{letra}:/").exists():
            return Path(f"{letra}:/VielaVice")
    raise unittest.SkipTest("todas as letras de unidade estão em uso")


class TestPastaDeTrabalho(unittest.TestCase):

    def test_trabalho_pesado_fica_no_ssd_quando_ele_existe(self):
        with tempfile.TemporaryDirectory() as pasta:
            ssd = Path(pasta) / "VielaVice"
            self.assertEqual(config.pasta_de_trabalho(ssd), ssd / "video-bruto")

    def test_sem_o_ssd_a_producao_continua_na_pasta_do_projeto(self):
        self.assertEqual(config.pasta_de_trabalho(unidade_que_nao_existe()), config.BASE_DIR / "video-bruto")

    def test_videos_prontos_continuam_na_pasta_do_projeto(self):
        self.assertEqual(config.EXPORT_DIR, config.BASE_DIR / "exportacao")


if __name__ == "__main__":
    unittest.main()
