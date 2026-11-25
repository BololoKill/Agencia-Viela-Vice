"""
Roteirista do canal dark: a narração própria só entra quando a IA entrega um roteiro válido,
e sem roteiro o vídeo não é feito (não existe mais o formato antigo).
"""
import json
import unittest
from unittest import mock

from apoio import AmbienteIsolado
from src.pipeline import roteiro

SEGMENTOS = [{"text": "mano a polícia tá vindo"}, {"text": "pega o carro pega o carro"}]
SHORT_OK = {"titulo": "Ele achou que ia escapar da polícia", "gancho": "A fuga mais absurda",
            "narracao": "Ele roubou o carro errado na hora errada, e o que a polícia fez depois ninguém esperava."}


class BaseRoteiro(AmbienteIsolado):

    def _responder(self, *respostas):
        cliente = mock.Mock()
        cliente.models.generate_content.side_effect = [
            r if isinstance(r, Exception) else mock.Mock(text=json.dumps(r) if not isinstance(r, str) else r) for r in respostas]
        for alvo, nome, valor in ((roteiro.verificador, "_chave_da_ia", lambda: "chave-de-teste"),
                                  (roteiro.verificador.genai, "Client", lambda **_kw: cliente)):
            patcher = mock.patch.object(alvo, nome, side_effect=valor)
            patcher.start()
            self.addCleanup(patcher.stop)
        # A rodada extra espera 20 s entre tentativas; nos testes ela é instantânea
        patcher = mock.patch.object(roteiro.time, "sleep")
        patcher.start()
        self.addCleanup(patcher.stop)
        return cliente


class TestRoteiroDoShort(BaseRoteiro):

    def test_roteiro_valido_vira_titulo_gancho_e_narracao(self):
        self._responder(SHORT_OK)
        r = roteiro.roteiro_short(SEGMENTOS, "Paulinho o Loko")
        self.assertEqual(r["gancho"], "A FUGA MAIS ABSURDA")
        self.assertIn("polícia", r["narracao"])
        self.assertEqual(r["titulo"], SHORT_OK["titulo"])

    def test_gancho_que_nao_cabe_na_tela_da_lugar_ao_automatico(self):
        """Regressão: saiu 'A BATERIA DO CONTROLE QUASE' na tela, sem o fim da frase."""
        self._responder({**SHORT_OK, "gancho": "A bateria do controle quase acabou!"})
        r = roteiro.roteiro_short(SEGMENTOS, "X")
        self.assertIsNone(r["gancho"])
        self.assertEqual(r["narracao"], SHORT_OK["narracao"])

    def test_narracao_longa_demais_e_recusada(self):
        self._responder({**SHORT_OK, "narracao": "palavra " * 60})
        self.assertIsNone(roteiro.roteiro_short(SEGMENTOS, "X"))

    def test_resposta_quebrada_nao_vira_roteiro(self):
        self._responder("isso não é json")
        self.assertIsNone(roteiro.roteiro_short(SEGMENTOS, "X"))

    def test_hashtag_sai_do_titulo(self):
        self._responder({**SHORT_OK, "titulo": "Fuga insana #gta6"})
        self.assertNotIn("#", roteiro.roteiro_short(SEGMENTOS, "X")["titulo"])

    def test_tenta_o_proximo_modelo_quando_um_falha(self):
        cliente = self._responder(RuntimeError("503"), SHORT_OK)
        self.assertIsNotNone(roteiro.roteiro_short(SEGMENTOS, "X"))
        self.assertEqual(cliente.models.generate_content.call_count, 2)

    def test_ia_fora_do_ar_pausa_para_nao_atrasar(self):
        falhas = [RuntimeError("503")] * (len(roteiro.VIDEO_SPECS["modelos_texto"]) * roteiro.RODADAS_IA)
        cliente = self._responder(*falhas)
        with mock.patch.object(roteiro.time, "sleep"):
            self.assertIsNone(roteiro.roteiro_short(SEGMENTOS, "X"))
            self.assertIsNone(roteiro.roteiro_short(SEGMENTOS, "X"))
        self.assertEqual(cliente.models.generate_content.call_count, len(falhas))

    def test_queda_passageira_da_ia_ganha_nova_rodada(self):
        """Regressão: um 503 de segundos fazia o vídeo longo sair sem narração própria."""
        falhas = [RuntimeError("503")] * len(roteiro.VIDEO_SPECS["modelos_texto"])
        self._responder(*falhas, SHORT_OK)
        with mock.patch.object(roteiro.time, "sleep") as esperar:
            self.assertIsNotNone(roteiro.roteiro_short(SEGMENTOS, "X"))
        esperar.assert_called_once_with(roteiro.ESPERA_ENTRE_RODADAS_S)


class TestRoteiroDoTopDaSemana(BaseRoteiro):

    TRECHOS = [("Criador B", "ele roubou o carro"), ("Criador A", "a polícia chegou"), ("alanzoka", "fugiu pela praia")]
    OK = {"titulo": "TOP 3 momentos mais insanos de GTA 6 da semana",
          "abertura": "Os vídeos de GTA 6 mais vistos da semana estão aqui, e o primeiro lugar é surreal.",
          "capitulos": ["Em terceiro lugar, o Criador B rouba o carro errado na hora errada.",
                        "Em segundo lugar, o Criador A vê a polícia chegar do nada.",
                        "E em primeiro lugar, o alanzoka foge pela praia do jeito mais absurdo."]}

    def test_roteiro_traz_uma_narracao_por_trecho(self):
        self._responder(self.OK)
        r = roteiro.roteiro_compilacao(self.TRECHOS)
        self.assertEqual(len(r["capitulos"]), 3)
        self.assertTrue(r["titulo"].startswith("TOP 3"))

    def test_pedido_traz_posicao_criador_e_fala_de_cada_trecho(self):
        cliente = self._responder(self.OK)
        roteiro.roteiro_compilacao(self.TRECHOS)
        pedido = cliente.models.generate_content.call_args.kwargs["contents"][1]
        self.assertIn('3º lugar, vídeo de Criador B: "ele roubou o carro"', pedido)
        self.assertIn('1º lugar, vídeo de alanzoka: "fugiu pela praia"', pedido)
        self.assertIn("exatamente 3 frases", pedido)

    def test_quantidade_errada_de_narracoes_e_recusada(self):
        self._responder({**self.OK, "capitulos": self.OK["capitulos"][:2]})
        self.assertIsNone(roteiro.roteiro_compilacao(self.TRECHOS))


class TestConferenciaAntesDeGravar(BaseRoteiro):
    """Sem a IA de roteiro nenhum vídeo pode ser narrado: ela é conferida antes de gravar a live."""

    def test_ia_respondendo_libera_a_gravacao(self):
        cliente = self._responder({"ok": True})
        self.assertTrue(roteiro.ia_respondendo())
        self.assertEqual(cliente.models.generate_content.call_count, 1)

    def test_resposta_recente_dispensa_a_conferencia(self):
        cliente = self._responder(SHORT_OK)
        roteiro.roteiro_short(SEGMENTOS, "X")
        self.assertTrue(roteiro.ia_respondendo())
        self.assertEqual(cliente.models.generate_content.call_count, 1)

    def test_ia_fora_do_ar_segura_a_gravacao(self):
        modelos = len(roteiro.VIDEO_SPECS["modelos_texto"])
        cliente = self._responder(*[RuntimeError("503")] * modelos)
        self.assertFalse(roteiro.ia_respondendo())
        self.assertTrue(roteiro.ia_em_pausa())
        self.assertFalse(roteiro.ia_respondendo(), "em pausa, nem pergunta de novo")
        self.assertEqual(cliente.models.generate_content.call_count, modelos)
        self.assertIn("fora do ar", roteiro.situacao_da_ia())

    def test_sem_chave_o_painel_diz_o_motivo(self):
        with mock.patch.object(roteiro.verificador, "_chave_da_ia", return_value=None):
            self.assertFalse(roteiro.ia_respondendo())
        self.assertIn("GEMINI_API_KEY", roteiro.situacao_da_ia())


class TestSemFormatoAntigo(AmbienteIsolado):
    """A produção insiste no roteiro e espera a IA voltar, em vez de fazer vídeo sem narração própria."""

    def _relogio(self):
        agora = [1000.0]
        for nome, efeito in (("monotonic", lambda: agora[0]), ("sleep", lambda s: agora.__setitem__(0, agora[0] + s))):
            patcher = mock.patch.object(roteiro.time, nome, side_effect=efeito)
            patcher.start()
            self.addCleanup(patcher.stop)
        return agora

    def test_roteiro_que_chega_na_hora_e_usado(self):
        gerar = mock.Mock(return_value={"narracao": "ok"})
        self.assertEqual(roteiro.com_roteiro(gerar, "trecho"), {"narracao": "ok"})
        gerar.assert_called_once_with("trecho")

    def test_resposta_fora_do_combinado_e_pedida_de_novo(self):
        gerar = mock.Mock(side_effect=[None, {"narracao": "ok"}])
        self.assertEqual(roteiro.com_roteiro(gerar), {"narracao": "ok"})
        self.assertEqual(gerar.call_count, 2)

    def test_ia_que_sempre_erra_o_roteiro_desiste_so_deste_video(self):
        gerar = mock.Mock(return_value=None)
        self.assertIsNone(roteiro.com_roteiro(gerar))
        self.assertEqual(gerar.call_count, roteiro.TENTATIVAS_ROTEIRO)

    def test_ia_fora_do_ar_espera_ela_voltar(self):
        agora = self._relogio()
        respostas = iter([None, {"narracao": "ok"}])

        def gerar():
            resposta = next(respostas)
            if resposta is None:
                roteiro._ia["pausada_ate"] = agora[0] + roteiro.PAUSA_FALHA_S
            return resposta

        avisos = []
        self.assertEqual(roteiro.com_roteiro(gerar, avisar=avisos.append), {"narracao": "ok"})
        self.assertEqual(avisos, [roteiro.PAUSA_FALHA_S // 60])
        self.assertGreaterEqual(agora[0], 1000.0 + roteiro.PAUSA_FALHA_S)

    def test_ia_que_nao_volta_a_tempo_para_a_producao(self):
        agora = self._relogio()

        def gerar():
            roteiro._ia["pausada_ate"] = agora[0] + roteiro.PAUSA_FALHA_S
            return None

        with self.assertRaises(roteiro.IaDeRoteiroFora):
            roteiro.com_roteiro(gerar)
        self.assertLessEqual(agora[0] - 1000.0, roteiro.ESPERA_MAXIMA_ROTEIRO_S)

    def test_sem_chave_para_a_producao_na_hora(self):
        with mock.patch.object(roteiro.verificador, "_chave_da_ia", return_value=None):
            with self.assertRaises(roteiro.IaDeRoteiroFora):
                roteiro.com_roteiro(roteiro.roteiro_short, SEGMENTOS, "X")


if __name__ == "__main__":
    unittest.main()
