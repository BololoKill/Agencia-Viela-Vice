"""
Apoio aos testes: ambiente descartável que nunca toca nos dados reais da agência.
"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import src.utils as utils
import src.web.app as web
from src.pipeline import estado, renderer, roteiro, searcher, verificador, worker
from src.youtube import cota


class AmbienteIsolado(unittest.TestCase):
    """Redireciona todos os arquivos de estado e mídia para uma pasta temporária."""

    def setUp(self):
        # Espaço e acento de propósito: o caminho real do projeto também tem espaço.
        self.raiz = Path(tempfile.mkdtemp(prefix="viela teste á "))
        self.addCleanup(shutil.rmtree, self.raiz, ignore_errors=True)
        self.export_dir = self.raiz / "exportacao"
        self.bruto_dir = self.raiz / "video-bruto"
        self.export_dir.mkdir()
        self.bruto_dir.mkdir()

        self.log_file = self.raiz / "log_producao.txt"
        self.status_file = self.raiz / "status_vigia.json"
        self.agendados_file = self.raiz / "agendados.json"
        self.historico_file = self.raiz / "historico.txt"

        alvos = [
            (utils, "LOG_FILE_PADRAO", self.log_file),
            (estado, "STATUS_VIGIA_FILE", self.status_file),
            (estado, "TRAVA_CICLO_FILE", self.raiz / ".ciclo_producao.lock"),
            (estado, "FALHAS_FILE", self.raiz / "falhas_pipeline.json"),
            (estado, "CONTROLE_PRODUCAO_FILE", self.raiz / "controle_producao.json"),
            (worker, "EXPORT_DIR", self.export_dir),
            (worker, "VIDEO_BRUTO_DIR", self.bruto_dir),
            (worker, "METADADOS_FILE", self.raiz / "metadados_cortes.json"),
            (worker, "DESCARTADOS_FILE", self.raiz / "descartados.json"),
            (worker, "AGENDADOS_FILE", self.agendados_file),
            (worker, "TRECHOS_SEM_FALA_FILE", self.raiz / "trechos_sem_fala.json"),
            (web, "METADADOS_FILE", self.raiz / "metadados_cortes.json"),
            (cota, "COTAS_FILE", self.raiz / "cotas_youtube.json"),
            (renderer, "VIDEO_BRUTO_DIR", self.bruto_dir),
            (searcher, "HISTORICO_FILE", self.historico_file),
            (searcher, "PAUSA_YOUTUBE_FILE", self.raiz / "pausa_youtube.json"),
            (web, "EXPORT_DIR", self.export_dir),
            (web, "VIDEO_BRUTO_DIR", self.bruto_dir),
            (web, "AGENDADOS_FILE", self.agendados_file),
            (web, "DESCARTADOS_FILE", self.raiz / "descartados.json"),
            (web, "HISTORICO_FILE", self.historico_file),
            (web, "AFILIADOS_FILE", self.raiz / "afiliados.json"),
        ]
        for modulo, nome, valor in alvos:
            patcher = mock.patch.object(modulo, nome, valor)
            patcher.start()
            self.addCleanup(patcher.stop)

        # Os números do canal no painel nunca vêm do YouTube de verdade nos testes.
        patcher = mock.patch.object(web, "estatisticas_do_canal", return_value={})
        patcher.start()
        self.addCleanup(patcher.stop)

        # Nenhum teste consulta o YouTube de verdade.
        patcher = mock.patch.object(cota, "consultar_envios_youtube", return_value=[])
        self.consultar_youtube = patcher.start()
        self.addCleanup(patcher.stop)


        self.addCleanup(cota._reservas.clear)

        # A pausa do YouTube e as pausas das IAs não passam de um teste para o outro.
        for dicionario, valores in ((searcher._fontes, {"youtube_pausado_ate": 0.0}),
                                    (verificador._ia, {"pausada_ate": 0.0}),
                                    (roteiro._ia, {"pausada_ate": 0.0})):
            patcher = mock.patch.dict(dicionario, valores, clear=True)
            patcher.start()
            self.addCleanup(patcher.stop)


def gerar_clipe(destino: Path, duracao: int = 8) -> Path:
    """Cria um vídeo sintético com áudio, sem depender de internet."""
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"testsrc2=size=1280x720:rate=30:duration={duracao}",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={duracao}",
         "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", str(destino)],
        check=True, capture_output=True,
    )
    return destino


def gerar_audio(destino: Path, duracao: int = 2) -> Path:
    """Cria um MP3 curto para substituir a narração online nos testes."""
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency=330:duration={duracao}", str(destino)],
        check=True, capture_output=True,
    )
    return destino


def gerar_srt(destino: Path) -> Path:
    """Cria uma legenda com acentos."""
    destino.write_text(
        "1\n00:00:00,000 --> 00:00:03,000\nOlha só o que aconteceu, irmão!\n\n"
        "2\n00:00:03,000 --> 00:00:05,000\nA polícia não acreditou\n\n",
        encoding="utf-8",
    )
    return destino
