"""
SPEC-004: regras de edição que definem o padrão dos Shorts.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from src.pipeline import edicao


def seg(inicio, fim, texto):
    palavras = texto.split()
    passo = (fim - inicio) / len(palavras)
    return {
        "start": inicio, "end": fim, "text": texto,
        "words": [{"word": " " + p, "start": inicio + i * passo, "end": inicio + (i + 1) * passo}
                  for i, p in enumerate(palavras)],
    }


def palavra(inicio, fim, texto="fala"):
    return {"inicio": inicio, "fim": fim, "texto": texto}


class TestPalavras(unittest.TestCase):

    def test_usa_o_tempo_real_de_cada_palavra(self):
        palavras = edicao.palavras_dos_segmentos([seg(10.0, 12.0, "olha isso")])
        self.assertEqual([p["texto"] for p in palavras], ["olha", "isso"])
        self.assertEqual((palavras[1]["inicio"], palavras[1]["fim"]), (11.0, 12.0))

    def test_segmento_sem_palavras_distribui_o_tempo(self):
        palavras = edicao.palavras_dos_segmentos([{"start": 0.0, "end": 4.0, "text": "um dois"}])
        self.assertEqual((palavras[1]["inicio"], palavras[1]["fim"]), (2.0, 4.0))

    def test_palavrao_sai_censurado(self):
        palavras = edicao.palavras_dos_segmentos([seg(0.0, 1.0, "porra")])
        self.assertEqual(palavras[0]["texto"], "p***a")


class TestTrechosUteis(unittest.TestCase):

    def test_remove_pausas_longas(self):
        trechos = edicao.calcular_trechos_uteis(
            [palavra(10.0, 10.5), palavra(10.6, 11.0), palavra(13.0, 13.5)], pausa_max=0.6, folga=0.1)
        self.assertEqual(len(trechos), 2)
        self.assertLessEqual(trechos[0][1], 11.1)
        self.assertGreaterEqual(trechos[1][0], 12.9)

    def test_nunca_inclui_tela_preta(self):
        palavras = [palavra(float(t), t + 0.9) for t in range(10, 20)]
        trechos = edicao.calcular_trechos_uteis(palavras, bloqueios=[(14.0, 16.0)])
        for inicio, fim in trechos:
            self.assertTrue(fim <= 14.0 or inicio >= 16.0, (inicio, fim))

    def test_respeita_duracao_maxima(self):
        palavras = [palavra(float(t), t + 0.9) for t in range(0, 30)]
        trechos = edicao.calcular_trechos_uteis(palavras, duracao_max=5.0)
        self.assertAlmostEqual(edicao.duracao_trechos(trechos), 5.0, places=2)

    def test_remapeia_para_a_linha_do_tempo_editada(self):
        trechos = [(10.0, 12.0), (20.0, 22.0)]
        self.assertEqual(edicao.remapear_tempo(11.0, trechos), 1.0)
        self.assertEqual(edicao.remapear_tempo(21.0, trechos), 3.0)
        self.assertIsNone(edicao.remapear_tempo(15.0, trechos))


class TestFalaEmPortugues(unittest.TestCase):

    def _medido(self, prob_pt, **extra):
        return {**seg(0.0, 4.0, "olha isso aqui mano"), "prob_pt": prob_pt, **extra}

    def test_fala_do_streamer_em_portugues_e_mantida(self):
        self.assertTrue(edicao.fala_em_portugues(self._medido(0.93)))

    def test_dialogo_do_jogo_em_ingles_e_removido(self):
        """Regressão: o Whisper escrevia falas em inglês como 'VOCÊIYOR' e 'NECLAS' nas legendas e títulos."""
        self.assertFalse(edicao.fala_em_portugues(self._medido(0.02)))

    def test_transcricao_sem_confianca_e_removida(self):
        self.assertFalse(edicao.fala_em_portugues(self._medido(0.93, avg_logprob=-1.6)))

    def test_fala_clara_nao_e_removida_pelo_indice_de_silencio(self):
        """Regressão: em live real, fala nítida vinha com no_speech_prob de 0,85."""
        self.assertTrue(edicao.fala_em_portugues(self._medido(0.96, no_speech_prob=0.85, avg_logprob=-0.23)))

    def test_segmento_sem_medicao_continua_valendo(self):
        self.assertTrue(edicao.fala_em_portugues(seg(0.0, 4.0, "olha isso aqui mano")))

    def test_filtro_mantem_a_ordem_das_falas(self):
        falas = [self._medido(0.9, text="um"), self._medido(0.01, text="two"), self._medido(0.8, text="tres")]
        self.assertEqual([s["text"] for s in edicao.filtrar_fala_em_portugues(falas)], ["um", "tres"])

    def test_corte_nao_emenda_falas_muito_distantes(self):
        """Sem as cenas em inglês, sobram falas soltas que não formam um momento único."""
        soltas = [seg(i * 120.0, i * 120.0 + 9.0, "polícia correndo tiro fuga") for i in range(12)]
        self.assertEqual(edicao.selecionar_melhores_cortes(soltas, duracao_alvo=60, max_cortes=1), [])

    def test_gameplay_com_pouca_fala_ainda_gera_corte(self):
        """Regressão: em live de ação o streamer fala pouco e nenhum Short era produzido."""
        esparsas = [seg(i * 20.0, i * 20.0 + 5.0, "olha a polícia correndo aqui mano") for i in range(6)]
        cortes = edicao.selecionar_melhores_cortes(esparsas, duracao_alvo=66, max_cortes=1)
        self.assertEqual(len(cortes), 1)
        self.assertGreaterEqual(len(cortes[0][2]), 4)

    def test_texto_com_outro_alfabeto_e_removido(self):
        for texto in ("Eu 먹는i nós e serem sozinho", "me ensina tank моirinho", "Cadê o chですね?"):
            self.assertFalse(edicao.fala_em_portugues(self._medido(0.95, text=texto)), texto)

    def test_fala_sem_texto_e_removida(self):
        self.assertFalse(edicao.fala_em_portugues(self._medido(0.95, text="   ")))

    def test_acentos_do_portugues_sao_aceitos(self):
        self.assertTrue(edicao.fala_em_portugues(self._medido(0.95, text="Ação, coração e pôr do sol à vista!")))


class TestCortesNaGradeDeQuadros(unittest.TestCase):

    def test_todo_corte_comeca_e_termina_em_um_quadro_exato(self):
        for inicio, fim in edicao.alinhar_trechos_aos_quadros([(1.013, 2.507), (3.351, 5.019)], 30):
            self.assertAlmostEqual(inicio * 30, round(inicio * 30), places=6)
            self.assertAlmostEqual(fim * 30, round(fim * 30), places=6)

    def test_cortes_vizinhos_nunca_se_sobrepoem(self):
        alinhados = edicao.alinhar_trechos_aos_quadros([(1.0, 2.01), (2.015, 3.0)], 30)
        self.assertLessEqual(alinhados[0][1], alinhados[1][0])

    def test_corte_menor_que_um_quadro_e_descartado(self):
        self.assertEqual(edicao.alinhar_trechos_aos_quadros([(1.0, 1.005)], 30), [])

    def test_duracao_total_nao_acumula_desvio(self):
        trechos = [(i * 2.013, i * 2.013 + 1.27) for i in range(40)]
        alinhados = edicao.alinhar_trechos_aos_quadros(trechos, 30)
        self.assertAlmostEqual(edicao.duracao_trechos(alinhados), edicao.duracao_trechos(trechos), delta=0.4)


class TestLegendas(unittest.TestCase):

    def test_legenda_nao_pisca_entre_grupos_proximos(self):
        raiz = Path(tempfile.mkdtemp(prefix="viela"))
        self.addCleanup(shutil.rmtree, raiz, ignore_errors=True)
        destino = raiz / "legenda.ass"
        grupos = [
            {"inicio": 0.0, "fim": 1.0, "palavras": [{"texto": "um", "inicio": 0.0, "fim": 1.0}]},
            {"inicio": 1.2, "fim": 2.0, "palavras": [{"texto": "dois", "inicio": 1.2, "fim": 2.0}]},
        ]
        edicao.gerar_ass(grupos, destino)
        linhas = [l for l in destino.read_text(encoding="utf-8").splitlines() if l.startswith("Dialogue:")]
        self.assertEqual(linhas[0].split(",")[2], linhas[1].split(",")[1])

    def _grupos(self, textos, **kw):
        palavras = [palavra(i * 0.4, i * 0.4 + 0.35, t) for i, t in enumerate(textos)]
        trechos = [(0.0, len(textos) * 0.4 + 1)]
        return edicao.agrupar_legendas(palavras, trechos, **kw)

    def test_no_maximo_tres_palavras_por_vez(self):
        grupos = self._grupos(["a", "b", "c", "d", "e", "f", "g"])
        self.assertTrue(all(len(g["palavras"]) <= 3 for g in grupos))
        self.assertEqual(sum(len(g["palavras"]) for g in grupos), 7)

    def test_pontuacao_encerra_o_grupo(self):
        grupos = self._grupos(["corre!", "agora", "mesmo"])
        self.assertEqual([p["texto"] for p in grupos[0]["palavras"]], ["corre!"])

    def test_legenda_termina_antes_da_chamada_final(self):
        grupos = self._grupos(["a"] * 30, limite=3.0)
        self.assertTrue(grupos)
        self.assertLessEqual(max(g["fim"] for g in grupos), 3.0)

    def test_arquivo_de_legenda_destaca_a_palavra_falada(self):
        raiz = Path(tempfile.mkdtemp(prefix="viela"))
        self.addCleanup(shutil.rmtree, raiz, ignore_errors=True)
        destino = raiz / "legenda.ass"
        edicao.gerar_ass(self._grupos(["olha", "{isso}", "aqui"]), destino)
        conteudo = destino.read_text(encoding="utf-8")
        self.assertIn("PlayResX: 1080", conteudo)
        self.assertIn("PlayResY: 1920", conteudo)
        self.assertEqual(conteudo.count("Dialogue:"), 3)
        self.assertIn("&H0000FFFF&", conteudo)
        self.assertIn("OLHA", conteudo)
        self.assertNotIn("{ISSO}", conteudo)


class TestGancho(unittest.TestCase):

    def test_prefere_a_frase_mais_forte_do_corte(self):
        gancho = edicao.gerar_gancho([
            seg(0, 3, "vamos ali na loja comprar uma coisa"),
            seg(3, 6, "a polícia pegou ele na fuga!"),
        ], "Luqueta")
        self.assertIn("POLÍCIA", gancho)

    def test_gancho_e_curto(self):
        gancho = edicao.gerar_gancho([seg(0, 5, "a polícia pegou ele na fuga depois de muito tempo correndo")], "Luqueta")
        self.assertLessEqual(len(gancho.split()), 6)

    def test_sem_fala_usa_o_nome_do_streamer(self):
        self.assertIn("DAVY JONES", edicao.gerar_gancho([], "Davy Jones (Gameplayrj)"))

    def test_quebra_em_ate_duas_linhas(self):
        linhas = edicao.quebrar_linhas("A POLÍCIA PEGOU ELE NA FUGA", max_chars=16)
        self.assertLessEqual(len(linhas), 2)
        self.assertTrue(all(len(l) <= 16 for l in linhas))

    def test_nome_falado_remove_parenteses(self):
        self.assertEqual(edicao.nome_falado("Davy Jones (Gameplayrj)"), "Davy Jones")


class TestMelhoresCortes(unittest.TestCase):

    def _live(self):
        calmo = [seg(float(t), t + 9.0, "calma aqui") for t in range(0, 180, 10)]
        quente = [seg(float(t), t + 9.0, "polícia correndo tiro fuga treta agora corre vai vai!")
                  for t in range(180, 260, 10)]
        final = [seg(float(t), t + 9.0, "calma aqui") for t in range(260, 460, 10)]
        return calmo + quente + final

    def test_escolhe_o_momento_mais_intenso_primeiro(self):
        cortes = edicao.selecionar_melhores_cortes(self._live(), duracao_alvo=60, max_cortes=1)
        self.assertGreaterEqual(cortes[0][0], 150)
        self.assertLessEqual(cortes[0][1], 290)

    def test_cortes_nao_se_sobrepoem(self):
        cortes = sorted(edicao.selecionar_melhores_cortes(self._live(), duracao_alvo=60, max_cortes=3))
        self.assertEqual(len(cortes), 3)
        for atual, proximo in zip(cortes, cortes[1:]):
            self.assertLessEqual(atual[1], proximo[0])

    def test_live_curta_demais_nao_gera_corte(self):
        self.assertEqual(edicao.selecionar_melhores_cortes([seg(0, 5, "oi")], duracao_alvo=60), [])


class TestVideosLongos(unittest.TestCase):

    def test_gravacao_de_21_minutos_rende_duas_partes_de_10(self):
        partes = edicao.planejar_longos(1260.0)
        self.assertEqual(len(partes), 2)
        self.assertTrue(all(duracao == 600.0 for _, duracao in partes))
        self.assertLessEqual(partes[0][0] + partes[0][1], partes[1][0])
        self.assertLessEqual(partes[1][0] + partes[1][1], 1260.0)

    def test_gravacao_media_rende_uma_parte(self):
        self.assertEqual(len(edicao.planejar_longos(700.0)), 1)

    def test_gravacao_curta_nao_rende_video_longo(self):
        self.assertEqual(edicao.planejar_longos(300.0), [])

    def test_respeita_a_quantidade_de_vagas(self):
        self.assertEqual(len(edicao.planejar_longos(7200.0, quantidade=1)), 1)

    def test_tela_preta_sai_do_video_longo(self):
        trechos = edicao.trechos_sem_bloqueios(100.0, 600.0, [(200.0, 210.0)])
        self.assertEqual(trechos, [(100.0, 200.0), (210.0, 700.0)])

    def test_publicacao_longa_nao_e_marcada_como_short(self):
        dados = edicao.montar_publicacao_longa("Davy Jones (Gameplayrj)", 2)
        self.assertNotIn("#Shorts", dados["titulo"] + dados["descricao"])
        self.assertIn("Parte 2", dados["titulo"])
        self.assertIn("Créditos: Live de Davy Jones", dados["descricao"])
        self.assertLessEqual(len(dados["titulo"]), 98)


class TestPublicacao(unittest.TestCase):

    def test_titulo_e_descricao_prontos_para_o_youtube(self):
        dados = edicao.montar_publicacao("A POLÍCIA PEGOU ELE", "Davy Jones (Gameplayrj)")
        self.assertLessEqual(len(dados["titulo"]), 98)
        self.assertIn("#Shorts", dados["titulo"])
        self.assertIn("Créditos: Live de Davy Jones", dados["descricao"])

    def test_hashtags_variam_entre_videos(self):
        descricoes = {edicao.montar_publicacao("X", "Luqueta", semente=i)["descricao"] for i in range(4)}
        self.assertGreater(len(descricoes), 1)


if __name__ == "__main__":
    unittest.main()
