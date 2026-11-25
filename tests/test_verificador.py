"""
Conferência pela imagem: só vira vídeo a gravação que mostra GTA 6 de verdade.
"""
import io
import unittest
from unittest import mock

from PIL import Image

from apoio import AmbienteIsolado, gerar_clipe
from src.pipeline import verificador


def jpeg(cor, tamanho=(64, 36)) -> bytes:
    saida = io.BytesIO()
    Image.new("RGB", tamanho, cor).save(saida, "JPEG")
    return saida.getvalue()


CINZA = jpeg((128, 128, 128))
COLORIDO = jpeg((220, 40, 120))
PRETO = jpeg((0, 0, 0))


class TestDecisao(AmbienteIsolado):

    def _conferir(self, veredito, quadros=(COLORIDO, COLORIDO, COLORIDO)):
        with mock.patch.object(verificador, "extrair_quadros", return_value=list(quadros)), \
                mock.patch.object(verificador, "_perguntar_a_ia", return_value=veredito):
            return verificador.confere_gta6("live.mp4")

    def test_outro_jogo_e_recusado_mesmo_com_titulo_de_gta_6(self):
        self.assertFalse(self._conferir({"jogo": "Terror", "tem_jogo_na_tela": True, "e_gta6": False, "confianca": 0.95}))

    def test_gta_6_na_tela_e_aprovado(self):
        self.assertTrue(self._conferir({"jogo": "GTA VI", "tem_jogo_na_tela": True, "e_gta6": True, "confianca": 0.9}))

    def test_duvida_da_ia_nao_descarta_a_live(self):
        self.assertTrue(self._conferir({"jogo": "?", "tem_jogo_na_tela": True, "e_gta6": False, "confianca": 0.3}))

    def test_anuncio_ou_tela_de_espera_nao_descarta_a_live(self):
        self.assertTrue(self._conferir({"jogo": "", "tem_jogo_na_tela": False, "e_gta6": False, "confianca": 0.99}))

    def test_resposta_incompleta_nao_descarta_a_live(self):
        for veredito in ({}, {"e_gta6": False}, {"tem_jogo_na_tela": True, "e_gta6": False, "confianca": "alta"}, ["x"]):
            self.assertTrue(self._conferir(veredito), veredito)

    def test_resposta_fora_do_formato_fica_registrada_e_vale_a_cor(self):
        """Regressão: a conferência do LOUD Coringa passou sem deixar nenhuma linha no registro."""
        for veredito in (["x"], "GTA VI", 1):
            with self.subTest(veredito=veredito), mock.patch.object(verificador, "log_terminal") as log:
                self.assertTrue(self._conferir(veredito))
                self.assertFalse(self._conferir(veredito, (CINZA, CINZA, COLORIDO)), "a imagem sem cor ainda é recusada")
                self.assertIn("fora do formato combinado", log.call_args.args[0])

    def test_sem_ia_a_imagem_em_preto_e_branco_e_recusada(self):
        self.assertFalse(self._conferir(None, (CINZA, CINZA, COLORIDO)))

    def test_sem_ia_a_imagem_colorida_segue_para_a_diretoria(self):
        self.assertTrue(self._conferir(None, (COLORIDO, COLORIDO, CINZA)))

    def test_telas_pretas_nao_contam_como_preto_e_branco(self):
        self.assertTrue(self._conferir(None, (PRETO, PRETO, PRETO, COLORIDO)))

    def test_gravacao_sem_quadros_legiveis_nao_e_julgada(self):
        with mock.patch.object(verificador, "_perguntar_a_ia") as perguntar:
            self.assertTrue(self._conferir(None, ()))
        perguntar.assert_not_called()


class TestPerguntaAIa(AmbienteIsolado):

    def _cliente(self, texto=None, erro=None):
        cliente = mock.Mock()
        cliente.models.generate_content.return_value = mock.Mock(text=texto)
        cliente.models.generate_content.side_effect = erro
        return cliente

    def test_interpreta_a_resposta(self):
        cliente = self._cliente('{"jogo": "GTA VI", "tem_jogo_na_tela": true, "e_gta6": true, "confianca": 0.9}')
        with mock.patch.object(verificador, "_chave_da_ia", return_value="chave-de-teste"), \
                mock.patch.object(verificador.genai, "Client", return_value=cliente):
            self.assertTrue(verificador._perguntar_a_ia([COLORIDO])["e_gta6"])

    def test_sem_chave_nao_chama_o_servico(self):
        with mock.patch.object(verificador, "_chave_da_ia", return_value=None), \
                mock.patch.object(verificador.genai, "Client") as cliente:
            self.assertIsNone(verificador._perguntar_a_ia([COLORIDO]))
        cliente.assert_not_called()

    def test_falha_do_servico_nao_expoe_a_chave(self):
        cliente = self._cliente(erro=RuntimeError("falhou com key=chave-secreta"))
        with mock.patch.object(verificador, "_chave_da_ia", return_value="chave-secreta"), \
                mock.patch.object(verificador.genai, "Client", return_value=cliente), \
                mock.patch.object(verificador, "log_terminal") as log:
            self.assertIsNone(verificador._perguntar_a_ia([COLORIDO]))
        self.assertNotIn("chave-secreta", str(log.call_args_list))

    def test_falha_pausa_a_ia_para_nao_atrasar_a_producao(self):
        cliente = self._cliente(erro=RuntimeError("429 RESOURCE_EXHAUSTED"))
        with mock.patch.object(verificador, "_chave_da_ia", return_value="chave-de-teste"), \
                mock.patch.object(verificador.genai, "Client", return_value=cliente) as criar:
            verificador._perguntar_a_ia([COLORIDO])
            self.assertIsNone(verificador._perguntar_a_ia([COLORIDO]))
        self.assertEqual(criar.call_count, 1)

    def test_ia_volta_a_ser_consultada_depois_da_pausa(self):
        verificador._ia["pausada_ate"] = verificador.time.monotonic() - 1
        cliente = self._cliente('{"jogo": "GTA VI", "tem_jogo_na_tela": true, "e_gta6": true, "confianca": 0.9}')
        with mock.patch.object(verificador, "_chave_da_ia", return_value="chave-de-teste"), \
                mock.patch.object(verificador.genai, "Client", return_value=cliente):
            self.assertTrue(verificador._perguntar_a_ia([COLORIDO])["e_gta6"])

    def test_cada_modelo_tem_pouco_tempo_para_responder(self):
        self.assertLessEqual(verificador.TEMPO_LIMITE_IA_MS, 20_000)

    def test_resposta_dentro_de_uma_lista_vale_o_primeiro_objeto(self):
        cliente = self._cliente('[{"jogo": "Far Cry 6", "tem_jogo_na_tela": true, "e_gta6": false, "confianca": 0.9}]')
        with mock.patch.object(verificador, "_chave_da_ia", return_value="chave-de-teste"), \
                mock.patch.object(verificador.genai, "Client", return_value=cliente), \
                mock.patch.object(verificador, "extrair_quadros", return_value=[COLORIDO] * 3):
            self.assertEqual(verificador._perguntar_a_ia([COLORIDO])["jogo"], "Far Cry 6")
            self.assertFalse(verificador.confere_gta6("live.mp4"), "outro jogo com certeza é recusado")

    def test_resposta_que_nao_e_json_conta_como_indisponivel(self):
        with mock.patch.object(verificador, "_chave_da_ia", return_value="chave-de-teste"), \
                mock.patch.object(verificador.genai, "Client", return_value=self._cliente("não sei")):
            self.assertIsNone(verificador._perguntar_a_ia([COLORIDO]))


class TestQuadros(AmbienteIsolado):

    def test_retira_quadros_da_gravacao(self):
        quadros = verificador.extrair_quadros(gerar_clipe(self.raiz / "clipe.mp4", 4), quantidade=3)
        self.assertEqual(len(quadros), 3)
        self.assertTrue(all(q.startswith(b"\xff\xd8") for q in quadros))

    def test_amostra_mais_curta_que_o_inicio_pedido_ainda_e_analisada(self):
        quadros = verificador.extrair_quadros(gerar_clipe(self.raiz / "clipe.mp4", 3), inicio=20.0, quantidade=2)
        self.assertEqual(len(quadros), 2)

    def test_arquivo_invalido_nao_derruba_a_producao(self):
        falso = self.raiz / "falso.mp4"
        falso.write_bytes(b"nada")
        self.assertEqual(verificador.extrair_quadros(falso), [])


if __name__ == "__main__":
    unittest.main()
