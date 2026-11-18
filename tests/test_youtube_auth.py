"""
SPEC-004: a renovação do token precisa pedir somente as permissões já autorizadas no canal.
"""
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

from src.youtube import auth, uploader

UPLOAD = "https://www.googleapis.com/auth/youtube.upload"
LEITURA = "https://www.googleapis.com/auth/youtube.readonly"
TOTAL = "https://www.googleapis.com/auth/youtube"


class TestCredenciaisDoCanal(unittest.TestCase):

    def setUp(self):
        self.raiz = Path(tempfile.mkdtemp(prefix="viela auth "))
        self.addCleanup(shutil.rmtree, self.raiz, ignore_errors=True)
        patcher = mock.patch.object(auth, "BASE_DIR", self.raiz)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.token = self.raiz / "token.json"

    def _gravar_token(self, **campos):
        dados = {
            "token": "acesso-antigo",
            "refresh_token": "renovacao-teste",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "cliente-teste",
            "client_secret": "segredo-teste",
            "scopes": [UPLOAD, LEITURA],
            "expiry": "2020-01-01T00:00:00Z",
        }
        dados.update(campos)
        self.token.write_text(json.dumps(dados), encoding="utf-8")

    def test_codigo_nao_exige_acesso_total_ao_canal(self):
        self.assertEqual(set(auth.SCOPES), {UPLOAD, LEITURA})
        self.assertNotIn(TOTAL, auth.SCOPES)

    def test_renovacao_pede_apenas_as_permissoes_do_token(self):
        """Regressão: pedir um escopo não autorizado gerava invalid_scope no Google."""
        self._gravar_token()
        pedidos = []

        def renovar(creds, _request):
            pedidos.append(set(creds.scopes))
            creds.token = "acesso-novo"
            creds.expiry = datetime.utcnow() + timedelta(hours=1)

        with mock.patch.object(Credentials, "refresh", autospec=True, side_effect=renovar):
            creds = auth.obter_credenciais("1")

        self.assertEqual(pedidos, [{UPLOAD, LEITURA}])
        self.assertEqual(creds.token, "acesso-novo")

    def test_token_renovado_preserva_a_renovacao_futura(self):
        self._gravar_token()

        def renovar(creds, _request):
            creds.token = "acesso-novo"
            creds.expiry = datetime.utcnow() + timedelta(hours=1)

        with mock.patch.object(Credentials, "refresh", autospec=True, side_effect=renovar):
            auth.obter_credenciais("1")

        salvo = json.loads(self.token.read_text(encoding="utf-8"))
        self.assertEqual((salvo["token"], salvo["refresh_token"]), ("acesso-novo", "renovacao-teste"))
        self.assertEqual(list(self.raiz.glob("*.tmp")), [])

    def test_autorizacao_recusada_gera_orientacao_clara_e_preserva_o_token(self):
        self._gravar_token()
        original = self.token.read_text(encoding="utf-8")
        erro = RefreshError("invalid_grant: Token has been expired or revoked.")
        with mock.patch.object(Credentials, "refresh", autospec=True, side_effect=erro):
            with self.assertRaises(auth.CredencialYouTubeError) as ctx:
                auth.obter_credenciais("1")
        self.assertIn("gerar_tokens_correto.py", str(ctx.exception))
        self.assertEqual(self.token.read_text(encoding="utf-8"), original)

    def test_caos_token_corrompido_gera_orientacao_clara(self):
        self.token.write_text('{"token": "metade', encoding="utf-8")
        with self.assertRaises(auth.CredencialYouTubeError):
            auth.obter_credenciais("1")

    def test_servidor_nunca_abre_login_no_navegador(self):
        """O login interativo travaria a aprovação do vídeo dentro do painel."""
        self.assertIsNone(auth.obter_credenciais("1"))
        self.assertFalse(hasattr(auth, "InstalledAppFlow"))

    def test_envio_devolve_motivo_sem_derrubar_a_aprovacao(self):
        erro = auth.CredencialYouTubeError("Autorização recusada.")
        with mock.patch.object(uploader, "obter_credenciais", side_effect=erro):
            resultado = uploader.enviar_video_agendado(Path("v.mp4"), "t", "d", "2026-11-20", "10:00", "1")
        self.assertEqual(resultado, (False, "Autorização recusada.", None))


class TestEtiquetasDoEnvio(unittest.TestCase):

    def _tags(self, titulo):
        youtube = mock.MagicMock()
        requisicao = youtube.videos.return_value.insert.return_value
        requisicao.next_chunk.return_value = (None, {"id": "abc"})
        with mock.patch.object(uploader, "obter_credenciais", return_value=object()),                 mock.patch.object(uploader, "build", return_value=youtube),                 mock.patch.object(uploader, "MediaFileUpload"):
            ok, _, _ = uploader.enviar_video_agendado(Path("v.mp4"), titulo, "desc", "2026-12-01", "18:00")
        self.assertTrue(ok)
        return youtube.videos.return_value.insert.call_args.kwargs["body"]["snippet"]["tags"]

    def test_short_recebe_a_etiqueta_shorts(self):
        self.assertIn("Shorts", self._tags("Olha isso #Shorts"))

    def test_video_longo_nao_e_marcado_como_short(self):
        self.assertNotIn("Shorts", self._tags("Alanzoka no GTA 6: os melhores momentos | Parte 1"))


if __name__ == "__main__":
    unittest.main()
