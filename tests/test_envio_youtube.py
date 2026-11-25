"""
Envio ao YouTube: falhas passageiras de rede não podem perder o vídeo, e os envios saem um por vez.
"""
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from googleapiclient.errors import HttpError

from apoio import AmbienteIsolado
import src.web.app as web
from src.youtube import uploader


def erro_http(status, motivo):
    resposta = mock.Mock(status=status, reason=motivo)
    return HttpError(resposta, f'{{"error": {{"errors": [{{"reason": "{motivo}"}}]}}}}'.encode())


class TestEnvioResiliente(AmbienteIsolado):

    def _enviar(self, *respostas):
        pedido = mock.Mock()
        pedido.next_chunk.side_effect = list(respostas)
        youtube = mock.Mock()
        youtube.videos.return_value.insert.return_value = pedido
        with mock.patch.object(uploader, "obter_credenciais", return_value=mock.Mock()), \
                mock.patch.object(uploader, "_cliente_youtube", return_value=youtube), \
                mock.patch.object(uploader, "MediaFileUpload"), \
                mock.patch.object(uploader.time, "sleep"):
            resultado = uploader.enviar_video_agendado(Path("v.mp4"), "Título", "Descrição", "2026-12-01", "12:00", "1")
        return resultado, pedido

    def test_tempo_esgotado_numa_parte_tenta_de_novo(self):
        (ok, _msg, video_id), pedido = self._enviar(TimeoutError("The read operation timed out"), (None, None), (None, {"id": "yt1"}))
        self.assertTrue(ok)
        self.assertEqual(video_id, "yt1")
        self.assertEqual(pedido.next_chunk.call_count, 3)

    def test_conexao_cortada_tenta_de_novo(self):
        import ssl
        (ok, _msg, video_id), _ = self._enviar(ssl.SSLEOFError("EOF occurred in violation of protocol"), (None, {"id": "yt2"}))
        self.assertTrue(ok)

    def test_instabilidade_do_youtube_tenta_de_novo(self):
        (ok, _msg, _id), _ = self._enviar(erro_http(503, "backendError"), (None, {"id": "yt3"}))
        self.assertTrue(ok)

    def test_recusa_definitiva_nao_insiste(self):
        (ok, msg, _id), pedido = self._enviar(erro_http(400, "uploadLimitExceeded"))
        self.assertFalse(ok)
        self.assertIn("uploadLimitExceeded", msg)
        self.assertEqual(pedido.next_chunk.call_count, 1)

    def test_rede_fora_do_ar_por_muito_tempo_desiste(self):
        falhas = [TimeoutError("timed out")] * (uploader.TENTATIVAS_POR_PARTE + 1)
        (ok, msg, _id), _ = self._enviar(*falhas)
        self.assertFalse(ok)
        self.assertIn("timed out", msg)

    def test_resposta_308_entre_as_partes_nao_e_tratada_como_redirecionamento(self):
        """Regressão: a conexão própria tratava o 308 como redirecionamento e todo envio falhava."""
        with mock.patch.object(uploader, "build") as construir:
            uploader._cliente_youtube(mock.Mock())
        conexao = construir.call_args.kwargs["http"].http
        self.assertNotIn(308, conexao.redirect_codes)
        self.assertEqual(conexao.timeout, uploader.TEMPO_LIMITE_PARTE_S)

    def test_cada_parte_tem_tempo_de_sobra(self):
        self.assertGreaterEqual(uploader.TEMPO_LIMITE_PARTE_S, 300)


class TestUmEnvioPorVez(AmbienteIsolado):

    def test_aprovacoes_seguidas_sobem_uma_de_cada_vez(self):
        videos = []
        for i in range(3):
            caminho = self.export_dir / f"short-{i}.mp4"
            caminho.write_bytes(b"x" * 1000)
            videos.append(caminho.name)
        ativos, maximo, trava = [0], [0], threading.Lock()

        def enviar(**_):
            with trava:
                ativos[0] += 1
                maximo[0] = max(maximo[0], ativos[0])
            time.sleep(0.2)
            with trava:
                ativos[0] -= 1
            return True, "ok", f"yt{time.monotonic()}"

        with mock.patch.object(web, "enviar_video_agendado", side_effect=enviar):
            tarefas = [threading.Thread(target=lambda n=n: web.app.test_client().post("/api/aprovar", json={"filename": n, "canal": str(i + 1)}))
                       for i, n in enumerate(videos)]
            for t in tarefas:
                t.start()
            for t in tarefas:
                t.join()
        self.assertEqual(maximo[0], 1)


if __name__ == "__main__":
    unittest.main()
