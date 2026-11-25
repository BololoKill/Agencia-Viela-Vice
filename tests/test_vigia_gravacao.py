"""
Vigia do download: um trecho que para de chegar não pode travar a produção por horas.
Regressão: o download do LOUD Coringa ficou 60 min recebendo 0 bytes, duas vezes seguidas.
"""
import http.server
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from apoio import AmbienteIsolado
from src.pipeline import downloader, estado


class BaseVigia(AmbienteIsolado):

    def setUp(self):
        super().setUp()
        for nome, valor in (("INTERVALO_VIGIA_S", 0.05), ("SEM_PROGRESSO_S", 0.4), ("FOLGA_EXTRA_S", 0.0)):
            patcher = mock.patch.object(downloader, nome, valor)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.encerrado = threading.Event()
        patcher = mock.patch.object(downloader, "_encerrar_ffmpeg", side_effect=lambda _alvo: self.encerrado.set() or 1)
        self.encerrar = patcher.start()
        self.addCleanup(patcher.stop)

    def _baixar_trecho(self, descer, duracao=360.0):
        """Baixa um trecho com um yt-dlp de mentira: a imagem e o som descem pela mesma função "descer"."""
        instancia = mock.MagicMock()
        instancia.__enter__.return_value.extract_info.side_effect = descer
        nomes = instancia.__enter__.return_value.prepare_filename
        nomes.side_effect = lambda _info: str(self.bruto_dir / f"live_bruta.parte{nomes.call_count}.mp4")
        with mock.patch.object(downloader.yt_dlp, "YoutubeDL", return_value=instancia), \
                mock.patch.object(downloader, "_duracoes", return_value={"video": duracao, "audio": duracao}), \
                mock.patch.object(downloader, "executar_ffmpeg"), \
                mock.patch.object(downloader, "_arquivo_completo", return_value=True):
            return downloader.baixar_video("https://youtu.be/x", self.bruto_dir, trecho=(600.0, duracao))

    def _travar_ate_encerrar(self, *_args, **_kw):
        """Imita o FFmpeg parado: nada chega até o vigia encerrá-lo."""
        (self.bruto_dir / "live_bruta.imagem.mp4.part").write_bytes(b"")
        if not self.encerrado.wait(5):
            raise AssertionError("o vigia não encerrou o download travado")
        raise downloader.yt_dlp.utils.DownloadError("ffmpeg exited with code 1")


class TestVigiaDoDownload(BaseVigia):

    def test_trecho_sem_dados_e_encerrado(self):
        with self.assertRaises(downloader.GravacaoTravada) as erro:
            self._baixar_trecho(self._travar_ate_encerrar)
        self.assertIn("sem mandar dados", str(erro.exception))
        self.assertEqual(self.encerrar.call_args.args[0], str(self.bruto_dir / "live_bruta."))

    def test_download_que_cresce_nao_e_interrompido(self):
        def descer(*_args, **_kw):
            arquivo = self.bruto_dir / "live_bruta.imagem.mp4.part"
            for _ in range(12):
                with open(arquivo, "ab") as saida:
                    saida.write(b"x" * 1000)
                time.sleep(0.05)
            return {"id": "x"}

        self.assertEqual(self._baixar_trecho(descer).name, "live_bruta.mp4")
        self.encerrar.assert_not_called()

    def test_download_que_passa_muito_do_tempo_e_encerrado(self):
        def descer_sem_fim(*_args, **_kw):
            arquivo = self.bruto_dir / "live_bruta.imagem.mp4.part"
            while not self.encerrado.is_set():
                with open(arquivo, "ab") as saida:
                    saida.write(b"x" * 1000)
                time.sleep(0.03)
            raise downloader.yt_dlp.utils.DownloadError("ffmpeg exited with code 1")

        with self.assertRaises(downloader.GravacaoTravada) as erro:
            self._baixar_trecho(descer_sem_fim, duracao=0.1)
        self.assertIn("passou de", str(erro.exception))

    def test_video_curto_baixado_inteiro_nao_tem_vigia(self):
        instancia = mock.MagicMock()
        destino = self.bruto_dir / "live_bruta.mp4"
        destino.write_bytes(b"x")
        instancia.__enter__.return_value.extract_info.return_value = {"id": "x"}
        instancia.__enter__.return_value.prepare_filename.return_value = str(destino)
        with mock.patch.object(downloader.yt_dlp, "YoutubeDL", return_value=instancia), \
                mock.patch.object(downloader, "_Vigia") as vigia:
            downloader.baixar_video("https://youtu.be/x", self.bruto_dir)
        vigia.assert_not_called()

    def test_imagem_e_som_tem_vigia_e_retomam_a_conexao_que_cai(self):
        """O trecho do viral desce pelo FFmpeg: uma conexão parada não pode travar o ciclo nem cortar o som."""
        instancia = mock.MagicMock()
        instancia.__enter__.return_value.extract_info.return_value = {"id": "x"}
        instancia.__enter__.return_value.prepare_filename.return_value = str(self.bruto_dir / "live_bruta.parte.mp4")
        with mock.patch.object(downloader.yt_dlp, "YoutubeDL", return_value=instancia) as ydl, \
                mock.patch.object(downloader, "_Vigia") as vigia, \
                mock.patch.object(downloader, "_duracoes", return_value={"video": 360.0, "audio": 360.0}), \
                mock.patch.object(downloader, "_arquivo_completo", return_value=True), \
                mock.patch.object(downloader, "executar_ffmpeg"):
            vigia.return_value.motivo = None
            downloader.baixar_video("https://youtu.be/x", self.bruto_dir, trecho=(600.0, 360.0))
        # Um vigia para cada descida (imagem e som)
        self.assertEqual(vigia.call_count, 2)
        for chamada in vigia.call_args_list:
            self.assertAlmostEqual(chamada.args[1], 360.0 * downloader.FOLGA_TEMPO_TOTAL * 2 + downloader.FOLGA_EXTRA_S)
        for chamada in ydl.call_args_list:
            argumentos = chamada.args[0]["external_downloader_args"]["ffmpeg_i"]
            self.assertEqual(argumentos, downloader.RECONEXAO_FFMPEG)
            # Regressão: o -rw_timeout cortava o som do trecho (240 s de imagem com 139 s de som)
            self.assertNotIn("-rw_timeout", argumentos)

    def test_erro_de_download_travado_e_classificado(self):
        info = estado.classificar_erro(downloader.GravacaoTravada("Download encerrado: o YouTube ficou 3 min sem mandar dados."))
        self.assertEqual(info["categoria"], "gravacao_travada")
        self.assertTrue(info["transitorio"])
        self.assertNotIn("live", info["mensagem"])


class TestParteCortada(AmbienteIsolado):
    """
    Regressões: o trecho do Leozinn chegou sem o índice do MP4 ("moov atom not found") e o do alanzoka com
    149 s de som em 6 min de imagem. Só a parte com defeito é baixada de novo.
    """

    def _baixar(self, *medidas):
        """medidas: quantos segundos cada descida trouxe, na ordem em que acontecem (a imagem vem antes do som)."""
        self.descidas = []
        fila = iter(medidas)

        def descer(_url, pasta, rotulo, *_args):
            self.descidas.append(rotulo)
            parte = pasta / f"live_bruta.{rotulo}.mp4"
            parte.write_bytes(b"x")
            return parte

        def medir(_parte):
            segundos = next(fila)
            return {"video": segundos, "audio": segundos} if segundos else {}

        with mock.patch.object(downloader, "_descer", side_effect=descer), \
                mock.patch.object(downloader, "_duracoes", side_effect=medir), \
                mock.patch.object(downloader, "executar_ffmpeg",
                                  side_effect=lambda args, **_kw: Path(args[-2]).write_bytes(b"junto")), \
                mock.patch.object(downloader, "_arquivo_completo", return_value=True), \
                mock.patch.object(downloader, "log_terminal") as self.log:
            return downloader.baixar_video("https://youtu.be/x", self.bruto_dir, trecho=(600.0, 360.0))

    def test_som_cortado_e_baixado_de_novo_sozinho(self):
        self.assertEqual(self._baixar(360.0, 149.0, 360.0).name, "live_bruta.mp4")
        self.assertEqual(self.descidas, ["imagem", "som", "som"], "a imagem de 6 min não desce de novo")
        self.assertIn("O som do trecho chegou com 149 de 360 s", self.log.call_args.args[0])

    def test_imagem_quebrada_e_baixada_de_novo(self):
        self.assertEqual(self._baixar(0, 360.0, 360.0).name, "live_bruta.mp4")
        self.assertEqual(self.descidas, ["imagem", "imagem", "som"])

    def test_parte_cortada_duas_vezes_fica_para_o_proximo_ciclo(self):
        with self.assertRaises(downloader.DownloadIncompleto) as erro:
            self._baixar(360.0, 92.0, 92.0)
        self.assertIn("O som do trecho chegou com 92 de 360 s duas vezes", str(erro.exception))
        self.assertEqual(list(self.bruto_dir.iterdir()), [], "nenhuma parte fica ocupando o disco")
        info = estado.classificar_erro(erro.exception)
        self.assertEqual(info["categoria"], "download_incompleto")
        self.assertTrue(info["transitorio"], "o vídeo não vai para a quarentena por uma falha de rede")

    def _baixar_com_quedas(self, *erros):
        """erros: o que cada descida faz, na ordem (None baixa a parte inteira)."""
        self.descidas = []
        fila = iter(erros)

        def descer(_url, pasta, rotulo, *_args):
            self.descidas.append(rotulo)
            erro = next(fila, None)
            if erro:
                raise erro
            parte = pasta / f"live_bruta.{rotulo}.mp4"
            parte.write_bytes(b"x")
            return parte

        with mock.patch.object(downloader, "_descer", side_effect=descer), \
                mock.patch.object(downloader, "_duracoes", return_value={"video": 360.0, "audio": 360.0}), \
                mock.patch.object(downloader, "executar_ffmpeg",
                                  side_effect=lambda args, **_kw: Path(args[-2]).write_bytes(b"junto")), \
                mock.patch.object(downloader, "_arquivo_completo", return_value=True), \
                mock.patch.object(downloader, "log_terminal") as self.log:
            return downloader.baixar_video("https://youtu.be/x", self.bruto_dir, trecho=(600.0, 360.0))

    def test_ffmpeg_que_cai_no_meio_ganha_outra_tentativa(self):
        """Regressão: o FFmpeg caiu no meio do trecho do alanzoka (código 3436169992) e o vídeo foi perdido."""
        queda = downloader.yt_dlp.utils.DownloadError("ERROR: ffmpeg exited with code 3436169992")
        self.assertEqual(self._baixar_com_quedas(queda).name, "live_bruta.mp4")
        self.assertEqual(self.descidas, ["imagem", "imagem", "som"])
        self.assertIn("parou no meio do download", self.log.call_args.args[0])

    def test_ffmpeg_que_cai_duas_vezes_fica_para_o_proximo_ciclo(self):
        queda = downloader.yt_dlp.utils.DownloadError("ERROR: ffmpeg exited with code 1")
        with self.assertRaises(downloader.DownloadIncompleto) as erro:
            self._baixar_com_quedas(queda, queda)
        self.assertTrue(estado.classificar_erro(erro.exception)["transitorio"])
        self.assertEqual(list(self.bruto_dir.iterdir()), [])

    def test_bloqueio_do_youtube_nao_e_repetido(self):
        """O pedido de confirmação anti-robô sobe na hora: o ciclo pausa o YouTube em vez de insistir."""
        bloqueio = downloader.yt_dlp.utils.DownloadError("ERROR: Sign in to confirm you're not a bot")
        with self.assertRaises(downloader.yt_dlp.utils.DownloadError):
            self._baixar_com_quedas(bloqueio)
        self.assertEqual(self.descidas, ["imagem"])
        self.assertEqual(estado.classificar_erro(bloqueio)["categoria"], "bloqueio_youtube")

    def test_arquivo_juntado_que_nao_abre_fica_para_o_proximo_ciclo(self):
        with mock.patch.object(downloader, "_baixar_trecho", return_value=self.bruto_dir / "live_bruta.mp4"), \
                mock.patch.object(downloader, "_arquivo_completo", return_value=False):
            with self.assertRaises(downloader.DownloadIncompleto):
                downloader.baixar_video("https://youtu.be/x", self.bruto_dir, trecho=(600.0, 360.0))

    def test_arquivo_sem_indice_nao_e_legivel(self):
        quebrado = self.bruto_dir / "quebrado.mp4"
        quebrado.write_bytes(b"\x00" * 4096)
        self.assertFalse(downloader._arquivo_completo(quebrado))
        self.assertFalse(downloader._arquivo_completo(self.bruto_dir / "nao_existe.mp4"))

    def test_video_inteiro_e_legivel(self):
        from apoio import gerar_clipe
        self.assertTrue(downloader._arquivo_completo(gerar_clipe(self.bruto_dir / "ok.mp4", duracao=2)))

    def test_som_mais_curto_que_a_imagem_nao_serve(self):
        """Regressão: o trecho do Skorpion Gamer tinha 6 min de imagem e só 1min32 de som."""
        cortado = self.bruto_dir / "som_cortado.mp4"
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=30:duration=8",
                        "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:v", "libx264", "-preset", "ultrafast",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", str(cortado)], check=True, capture_output=True)
        self.assertFalse(downloader._arquivo_completo(cortado))


class TestImagemESomSeparados(AmbienteIsolado):
    """Regressão: descendo juntos, o som do trecho parava no meio (alanzoka: 360 s de imagem e 149 s de som)."""

    def _parte(self, nome, *entrada):
        destino = self.raiz / nome
        subprocess.run(["ffmpeg", "-y", *entrada, str(destino)], check=True, capture_output=True)
        return destino

    def test_imagem_e_som_descem_separados_e_sao_juntados_sem_recodificar(self):
        imagem = self._parte("imagem.webm", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=30:duration=6",
                             "-c:v", "libvpx-vp9", "-deadline", "realtime", "-an")
        som = self._parte("som.webm", "-f", "lavfi", "-i", "sine=frequency=440:duration=6", "-c:a", "libopus", "-vn")
        baixados = iter([imagem, som])
        instancia = mock.MagicMock()
        instancia.__enter__.return_value.extract_info.return_value = {"id": "x"}

        def preparar(_info):
            origem = next(baixados)
            copia = self.bruto_dir / f"live_bruta.{origem.stem}.webm"
            copia.write_bytes(origem.read_bytes())
            return str(copia)

        instancia.__enter__.return_value.prepare_filename.side_effect = preparar
        with mock.patch.object(downloader.yt_dlp, "YoutubeDL", return_value=instancia):
            arquivo = downloader.baixar_video("https://youtu.be/x", self.bruto_dir, trecho=(600.0, 6.0))
        duracoes = downloader._duracoes(arquivo)
        self.assertAlmostEqual(duracoes["video"], 6.0, delta=0.2)
        self.assertAlmostEqual(duracoes["audio"], 6.0, delta=0.2)
        self.assertEqual(sorted(p.name for p in self.bruto_dir.iterdir()), ["live_bruta.mp4"], "as partes saem da pasta")


def _servidor_que_derruba_a_conexao(conteudo: bytes):
    """
    Servidor local que imita o YouTube: toda resposta que começa antes da metade do arquivo é encerrada
    na metade, antes do tamanho que ela mesma anunciou. Quem pede o resto a partir dali recebe até o fim.
    """
    total, metade = len(conteudo), len(conteudo) // 2

    class Resposta(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args):
            pass

        def do_GET(self):
            faixa = self.headers.get("Range", "")
            inicio = int(faixa.split("=")[1].split("-")[0]) if faixa.startswith("bytes=") else 0
            self.send_response(206 if faixa else 200)
            self.send_header("Content-Type", "audio/webm")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(total - inicio))
            if faixa:
                self.send_header("Content-Range", f"bytes {inicio}-{total - 1}/{total}")
            self.end_headers()
            fim = metade if inicio < metade else total
            try:
                self.wfile.write(conteudo[inicio:fim])
                self.wfile.flush()
            except OSError:
                pass
            self.close_connection = fim < total

    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Resposta)
    servidor.daemon_threads = True
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg não está disponível")
class TestConexaoQueCaiNoMeio(unittest.TestCase):
    """
    Regressão: o YouTube encerrava a conexão no meio do trecho e o FFmpeg entregava o som cortado como se
    o vídeo tivesse acabado ali (alanzoka: 149 s de som em 360 s). Com a reconexão ele pede o resto.
    """

    @classmethod
    def setUpClass(cls):
        cls.pasta = Path(tempfile.mkdtemp(prefix="viela reconexao "))
        som = cls.pasta / "som.webm"
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=20", "-c:a", "libopus",
                        "-b:a", "96k", str(som)], check=True, capture_output=True)
        cls.servidor = _servidor_que_derruba_a_conexao(som.read_bytes())
        cls.url = f"http://127.0.0.1:{cls.servidor.server_address[1]}/som.webm"

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        shutil.rmtree(cls.pasta, ignore_errors=True)

    def _baixar(self, nome, argumentos):
        saida = self.pasta / nome
        subprocess.run(["ffmpeg", "-y", "-loglevel", "quiet", *argumentos, "-i", self.url, "-c", "copy", str(saida)],
                       capture_output=True, timeout=120)
        return downloader._duracoes(saida).get("audio", 0.0)

    def test_sem_reconexao_o_som_chega_cortado(self):
        """Confere que o servidor de teste corta mesmo: sem isto o teste de baixo não provaria nada."""
        self.assertLess(self._baixar("cortado.webm", []), 15.0)

    def test_com_reconexao_o_som_chega_inteiro(self):
        self.assertAlmostEqual(self._baixar("inteiro.webm", downloader.RECONEXAO_FFMPEG), 20.0, delta=0.5)


class TestEncerrarSoAGravacaoCerta(unittest.TestCase):

    def _processo(self, nome, linha):
        processo = mock.Mock()
        processo.name.return_value = nome
        processo.cmdline.return_value = linha
        return processo

    def test_encerra_so_o_ffmpeg_que_grava_naquela_pasta(self):
        principal = self._processo("ffmpeg.exe", ["ffmpeg", "-i", "x", r"file:C:\p\video-bruto\fonte1\live_bruta.mp4.part"])
        outra_fonte = self._processo("ffmpeg.exe", ["ffmpeg", "-i", "x", r"file:C:\p\video-bruto\fonte2\live_bruta.mp4.part"])
        outro = self._processo("python.exe", ["python", r"C:\p\video-bruto\fonte1\live_bruta.mp4"])
        eu = mock.Mock()
        eu.children.return_value = [principal, outra_fonte, outro]
        with mock.patch.object(downloader.psutil, "Process", return_value=eu):
            self.assertEqual(downloader._encerrar_ffmpeg(r"C:\p\video-bruto\fonte1\live_bruta."), 1)
        principal.kill.assert_called_once()
        outra_fonte.kill.assert_not_called()
        outro.kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
