"""
Testes Unitários para o Launcher Interativo da Agência Viela Vice (TDD via unittest).
"""
import unittest
import socket
import sys
from pathlib import Path

# Adiciona o diretório raiz ao sys.path para importação do src
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from src.launcher import (
        obter_menu_opcoes,
        formatar_cabecalho_branding,
        verificar_porta_ocupada,
        mapear_comando_opcao
    )
except ImportError:
    # Permite execução do teste para registrar falha na fase Red do TDD
    obter_menu_opcoes = None
    formatar_cabecalho_branding = None
    verificar_porta_ocupada = None
    mapear_comando_opcao = None

class TestLauncher(unittest.TestCase):

    def test_imports_existem(self):
        """Verifica se o módulo launcher existe e pode ser importado."""
        self.assertIsNotNone(obter_menu_opcoes, "src.launcher ainda não foi implementado")

    def test_obter_menu_opcoes(self):
        """Valida se o menu contém todas as opções essenciais para o usuário."""
        if not obter_menu_opcoes:
            self.fail("Módulo não implementado")
        opcoes = obter_menu_opcoes()
        self.assertIn("1", opcoes)
        self.assertIn("2", opcoes)
        self.assertIn("3", opcoes)
        self.assertIn("4", opcoes)
        self.assertIn("5", opcoes)
        self.assertIn("6", opcoes)
        self.assertIn("0", opcoes)
        self.assertIn("Completo", opcoes["1"]["titulo"])
        self.assertIn("Escritório", opcoes["2"]["titulo"])
        self.assertIn("Robô", opcoes["3"]["titulo"])

    def test_formatar_cabecalho_branding(self):
        """Valida se o branding da Agência Viela Vice e identidade visual estão presentes."""
        if not formatar_cabecalho_branding:
            self.fail("Módulo não implementado")
        cabecalho = formatar_cabecalho_branding()
        self.assertTrue("AGENCIA VIELA VICE" in cabecalho or "VIELA VICE" in cabecalho)
        self.assertIn("Dr. Ricardo", cabecalho)

    def test_verificar_porta_ocupada(self):
        """Valida detecção correta de portas abertas/fechadas."""
        if not verificar_porta_ocupada:
            self.fail("Módulo não implementado")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            porta_livre = s.getsockname()[1]
        self.assertFalse(verificar_porta_ocupada("127.0.0.1", porta_livre))

    def test_mapear_comando_opcao(self):
        """Valida o mapeamento de opções para os subcomandos do sistema."""
        if not mapear_comando_opcao:
            self.fail("Módulo não implementado")
        self.assertEqual(mapear_comando_opcao("1"), "run")
        self.assertEqual(mapear_comando_opcao("2"), "server")
        self.assertEqual(mapear_comando_opcao("3"), "worker")
        self.assertEqual(mapear_comando_opcao("4"), "curadoria")
        self.assertEqual(mapear_comando_opcao("5"), "purge")
        self.assertEqual(mapear_comando_opcao("6"), "reuniao")
        self.assertEqual(mapear_comando_opcao("0"), "exit")
        self.assertIsNone(mapear_comando_opcao("99"))
        self.assertIsNone(mapear_comando_opcao("xyz"))

if __name__ == "__main__":
    unittest.main()
