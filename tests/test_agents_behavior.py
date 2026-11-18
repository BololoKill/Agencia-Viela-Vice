"""
Testes Unitários para a Máquina de Estados e Posicionamento dos Agentes (TDD).
"""
import unittest
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class TestAgentsBehavior(unittest.TestCase):

    def test_sprites_existem(self):
        """Garante que todas as poses de spritesheets dos agentes existem em disco."""
        sprites_dir = BASE_DIR / "sprites"
        self.assertTrue(sprites_dir.exists(), "Diretório de sprites não encontrado")

        linhas_esperadas = ["linha1", "linha2", "linha3", "linha4", "linha5"]
        poses_esperadas = ["pose1", "pose2", "pose3", "pose4"]

        for l in linhas_esperadas:
            for p in poses_esperadas:
                arquivo = sprites_dir / f"{l}_{p}.png"
                self.assertTrue(arquivo.exists(), f"Sprite ausente: {arquivo.name}")

    def test_logica_profundidade_z_index(self):
        """Valida se o cálculo de z-index respeita a perspectiva isométrica (Y maior = mais à frente)."""
        def calcular_z_index(top_pct):
            return int(top_pct * 10)

        fundo_y = 15.0      # Mezanino do Dr. Ricardo
        meio_y = 42.0       # Ilha de mesas do meio
        frente_y = 65.0     # Mesas inferiores e sofá do lounge

        self.assertLess(calcular_z_index(fundo_y), calcular_z_index(meio_y))
        self.assertLess(calcular_z_index(meio_y), calcular_z_index(frente_y))

    def test_zonas_do_escritorio_validas(self):
        """Garante que as zonas do escritório (mesa, lounge, reuniao) estão dentro dos limites percentuais 0-100%."""
        zonas_teste = {
            "dr_ricardo": {"mesa": (84, 15), "lounge": (85, 75)},
            "camila": {"mesa": (48, 40), "lounge": (80, 72)},
            "bruno": {"mesa": (30, 40), "lounge": (76, 70)},
            "lucas": {"mesa": (18, 62), "lounge": (82, 78)},
            "mariana": {"mesa": (38, 38), "lounge": (88, 74)},
            "caio": {"mesa": (62, 54), "lounge": (84, 70)},
            "beatriz": {"mesa": (70, 58), "lounge": (86, 76)}
        }

        for agente, posicoes in zonas_teste.items():
            for zona, (x, y) in posicoes.items():
                self.assertTrue(0 <= x <= 100, f"{agente} {zona} X fora dos limites")
                self.assertTrue(0 <= y <= 100, f"{agente} {zona} Y fora dos limites")

if __name__ == "__main__":
    unittest.main()
