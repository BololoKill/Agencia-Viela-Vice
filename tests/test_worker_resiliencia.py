"""
SPEC-003: integração do ciclo de produção com falhas injetadas em cada etapa.
O ciclo usa os vídeos de GTA 6 mais virais da semana: um Short por vídeo e o Top da semana com um trecho de cada.
"""
import json
import time
import unittest
from collections import namedtuple
from unittest import mock

from apoio import AmbienteIsolado
from src.pipeline import estado, roteiro, searcher, transcriber, worker
from src.pipeline.ffmpeg_runner import FFmpegError

Disco = namedtuple("Disco", "total used free")

ROTEIRO_SHORT = {"titulo": "Ele achou que ia escapar", "gancho": "A FUGA MAIS ABSURDA",
                 "narracao": "Ele roubou o carro errado na hora errada, e o que veio depois ninguém esperava."}


def roteiro_compilacao_valido(trechos):
    return {"titulo": "TOP 5 momentos mais insanos de GTA 6", "abertura": "Hoje tem os vídeos mais vistos da semana, se segura que vem coisa.",
            "capitulos": [f"Em {len(trechos) - i}º lugar, {criador} aprontou uma daquelas" for i, (criador, _) in enumerate(trechos)]}


def viral(numero, visualizacoes=None, duracao=3600):
    return {"id": f"v{numero}", "url": f"https://www.youtube.com/watch?v=v{numero}", "title": f"GTA 6 o início {numero}",
            "streamer": f"Criador {numero}", "duration": duracao,
            "visualizacoes": visualizacoes if visualizacoes is not None else (10 - numero) * 1_000_000,
            "origem": "viral", "ao_vivo": False}


class BaseCiclo(AmbienteIsolado):

    def setUp(self):
        super().setUp()
        self.virais = [viral(i) for i in range(1, 9)]
        # Fala contínua do criador nos 6 min baixados de cada vídeo
        self.segmentos = [{"start": 5.0 + i * 10, "end": 15.0 + i * 10, "text": "fala"} for i in range(34)]
        self.m = {}
        padroes = {
            "buscar_videos_virais": mock.Mock(side_effect=lambda quantidade, ignorar=(): self.virais[:quantidade]),
            "baixar_video": mock.Mock(side_effect=self._baixar),
            "extrair_audio_wav": mock.Mock(),
            "transcrever_audio": mock.Mock(return_value=self.segmentos),
            "e_audio_em_portugues": mock.Mock(return_value=True),
            "identificar_idioma_dos_segmentos": mock.Mock(side_effect=lambda _audio, segs, **_kw: segs),
            "detectar_telas_pretas": mock.Mock(return_value=[]),
            "detectar_intervalos_comerciais": mock.Mock(return_value=[]),
            "renderizar_short": mock.Mock(side_effect=self._renderizar),
            "renderizar_longo": mock.Mock(side_effect=self._renderizar),
            "montar_compilacao": mock.Mock(side_effect=self._compilar),
            "obter_duracao_audio": mock.Mock(return_value=360.0),
            "auditar_video": mock.Mock(return_value=(True, "ok", 90)),
            "registrar_historico": mock.Mock(),
            "confere_gta6": mock.Mock(return_value=True),
            # Todo vídeo do canal dark tem roteiro; os testes de falha da IA trocam estas respostas
            "roteiro_short": mock.Mock(return_value=ROTEIRO_SHORT),
            "roteiro_compilacao": mock.Mock(side_effect=roteiro_compilacao_valido),
            "ia_respondendo": mock.Mock(return_value=True),
        }
        for nome, valor in padroes.items():
            patcher = mock.patch.object(worker, nome, valor)
            self.m[nome] = patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(worker.shutil, "disk_usage", return_value=Disco(0, 0, 500 * 1024 ** 3))
        self.disco = patcher.start()
        self.addCleanup(patcher.stop)

    def _baixar(self, url, **kw):
        pasta = kw.get("destino_dir") or self.bruto_dir
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / "live_bruta.mp4"
        destino.write_bytes(url.encode())
        return destino

    def _renderizar(self, **kw):
        kw["output_final"].write_bytes(b"x" * 200_000)
        return kw["output_final"]

    def _compilar(self, trechos, saida):
        saida.write_bytes(b"x" * 200_000)
        inicios, posicao = [], 0.0
        for _, ini, fim in trechos:
            inicios.append(round(posicao, 3))
            posicao += fim - ini
        return inicios, round(posicao, 3)

    def _status(self):
        return json.loads(self.status_file.read_text(encoding="utf-8"))

    def _metadados(self):
        caminho = self.raiz / "metadados_cortes.json"
        return json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else {}

    def _historico(self):
        return [c.args[0] for c in self.m["registrar_historico"].call_args_list]

    def _criar_estoque(self, shorts=0, longos=0):
        for i in range(shorts):
            (self.export_dir / f"short-x-corte{i}.mp4").write_bytes(b"x" * 200_000)
        for i in range(longos):
            (self.export_dir / f"longo-x-parte{i}.mp4").write_bytes(b"x" * 200_000)


class TestCicloViral(BaseCiclo):
    """Os vídeos mais virais da semana viram 4 Shorts e o Top 5 da semana."""

    def test_ciclo_feliz_faz_os_shorts_e_o_top_da_semana(self):
        self.assertTrue(worker.executar_ciclo_producao())
        self.assertEqual(self.m["renderizar_short"].call_count, 4)
        self.assertEqual(self.m["montar_compilacao"].call_count, 1)
        self.assertEqual(len(self.m["montar_compilacao"].call_args.args[0]), 5)
        self.assertEqual(self.m["renderizar_longo"].call_count, 1)
        self.assertEqual(self._status()["progresso"], 100)
        self.assertIsNone(self._status().get("erro"))
        self.assertFalse(estado.ciclo_em_andamento())

    def test_cada_video_viral_entra_uma_vez_so(self):
        worker.executar_ciclo_producao()
        for numero in range(1, 6):
            self.assertIn(f"v{numero}", self._historico())
            self.assertIn(f"https://www.youtube.com/watch?v=v{numero}", self._historico())
        self.assertNotIn("v6", self._historico(), "o que não foi usado volta a concorrer")

    def test_baixa_so_o_trecho_analisado_de_cada_video(self):
        worker.executar_ciclo_producao()
        chamadas = self.m["baixar_video"].call_args_list
        self.assertEqual(len(chamadas), 5)
        self.assertTrue(all(c.kwargs["trecho"] == (360.0, 360.0) for c in chamadas))
        pastas = {c.kwargs["destino_dir"].name for c in chamadas}
        self.assertEqual(pastas, {f"fonte{i}" for i in range(1, 6)})

    def test_um_short_por_video_viral(self):
        worker.executar_ciclo_producao()
        pastas = [c.kwargs["video_original"].parent.name for c in self.m["renderizar_short"].call_args_list]
        self.assertEqual(pastas, [f"fonte{i}" for i in range(1, 5)], "cada Short vem de um vídeo diferente")

    def test_top_da_semana_em_contagem_regressiva(self):
        worker.executar_ciclo_producao()
        criadores = [criador for criador, _ in self.m["roteiro_compilacao"].call_args.args[0]]
        self.assertEqual(criadores, [f"Criador {i}" for i in range(5, 0, -1)], "o mais visto fecha o Top")
        pastas = [arquivo.parent.name for arquivo, _, _ in self.m["montar_compilacao"].call_args.args[0]]
        self.assertEqual(pastas, [f"fonte{i}" for i in range(5, 0, -1)])

    def test_top_mostra_o_nome_de_cada_criador_e_soma_8min30(self):
        worker.executar_ciclo_producao()
        chamada = self.m["renderizar_longo"].call_args.kwargs
        self.assertEqual([nome for _, _, nome in chamada["creditos"]], [f"Criador {i}" for i in range(5, 0, -1)])
        self.assertEqual(chamada["titulo_tela"], "TOP 5 DA SEMANA")
        self.assertGreaterEqual(chamada["duracao"], worker.VIDEO_SPECS["duracao_minima_longo_s"])
        self.assertEqual(chamada["inicio"], 0.0)

    def test_descricoes_trazem_credito_e_link_do_video_original(self):
        worker.executar_ciclo_producao()
        metadados = self._metadados()
        longo = next(v for k, v in metadados.items() if k.startswith("longo-"))
        for numero in range(1, 6):
            self.assertIn(f"https://www.youtube.com/watch?v=v{numero}", longo["descricao"])
        self.assertEqual(len(longo["fontes"]), 5)
        short = next(v for k, v in metadados.items() if k.startswith("short-criador1-"))
        self.assertIn("Créditos: vídeo de Criador 1 — https://www.youtube.com/watch?v=v1", short["descricao"])

    def test_short_aprovado_guarda_titulo_para_o_painel(self):
        worker.executar_ciclo_producao()
        shorts = [item for nome, item in self._metadados().items() if nome.startswith("short-")]
        self.assertEqual(len(shorts), 4)
        self.assertTrue(all("#Shorts" in item["titulo"] for item in shorts))

    def test_trecho_sem_fala_tenta_outro_ponto_do_video(self):
        """Regressão: as lives do LOUD Coringa e do Gameplayrj foram descartadas por cair em cenas do jogo."""
        self.m["transcrever_audio"].side_effect = [[]] + [self.segmentos] * 10
        self.assertTrue(worker.executar_ciclo_producao())
        trechos = [c.kwargs["trecho"] for c in self.m["baixar_video"].call_args_list[:2]]
        self.assertEqual(trechos, [(360.0, 360.0), (1800.0, 360.0)])
        self.assertIn("v1", self._historico(), "o vídeo foi aproveitado pelo segundo trecho")
        self.assertEqual(self.m["confere_gta6"].call_count, 5, "o jogo é conferido uma vez por vídeo")

    def test_audio_fora_do_portugues_no_comeco_tenta_o_meio(self):
        self.m["e_audio_em_portugues"].side_effect = [False] + [True] * 10
        self.assertTrue(worker.executar_ciclo_producao())
        self.assertIn("v1", self._historico())
        self.assertEqual(self.m["baixar_video"].call_count, 6)

    def test_trechos_de_cada_video(self):
        self.assertEqual(worker.janelas_do_video(3600), [(360.0, 360.0), (1800.0, 360.0)])
        self.assertEqual(worker.janelas_do_video(40815), [(4081.5, 360.0), (20407.5, 360.0)])
        self.assertEqual(worker.janelas_do_video(600), [(60.0, 360.0)], "vídeo curto: o meio repetiria o começo")
        self.assertEqual(worker.janelas_do_video(300), [(0.0, None)])

    def test_video_em_outro_idioma_e_trocado_pelo_proximo(self):
        self.m["e_audio_em_portugues"].side_effect = [False, False] + [True] * 10
        self.assertTrue(worker.executar_ciclo_producao())
        self.assertIn("v1", self._historico(), "o vídeo em outro idioma não é baixado de novo")
        criadores = {c for c, _ in self.m["roteiro_compilacao"].call_args.args[0]}
        self.assertEqual(criadores, {f"Criador {i}" for i in range(2, 7)})
        self.m["transcrever_audio"].assert_called()

    def test_video_de_outro_jogo_e_trocado_pelo_proximo(self):
        self.m["confere_gta6"].side_effect = [False] + [True] * 10
        self.assertTrue(worker.executar_ciclo_producao())
        self.assertIn("v1", self._historico())
        self.assertEqual(self.m["baixar_video"].call_count, 6)

    def test_falha_ao_baixar_um_video_nao_para_o_ciclo(self):
        def baixar(url, **kw):
            if url.endswith("v1"):
                raise RuntimeError("conexão caiu")
            return self._baixar(url, **kw)

        self.m["baixar_video"].side_effect = baixar
        self.assertTrue(worker.executar_ciclo_producao())
        self.assertNotIn("v1", self._historico(), "falha passageira: o vídeo volta a concorrer")
        self.assertEqual(self.m["renderizar_longo"].call_count, 1)

    def test_sem_virais_novos_nao_faz_nada(self):
        self.m["buscar_videos_virais"].side_effect = lambda quantidade, ignorar=(): []
        self.assertFalse(worker.executar_ciclo_producao())
        self.m["baixar_video"].assert_not_called()
        self.assertIn("Nenhum vídeo viral novo", self._status()["etapa"])

    def test_poucos_virais_fazem_so_os_shorts(self):
        self.virais = self.virais[:3]
        self.assertTrue(worker.executar_ciclo_producao())
        self.assertEqual(self.m["renderizar_short"].call_count, 3)
        self.m["renderizar_longo"].assert_not_called()

    def test_quatro_virais_ainda_fecham_o_top(self):
        self.virais = self.virais[:4]
        worker.executar_ciclo_producao()
        self.assertEqual(len(self.m["montar_compilacao"].call_args.args[0]), 4)
        self.assertEqual(self.m["renderizar_longo"].call_args.kwargs["titulo_tela"], "TOP 4 DA SEMANA")

    def test_trecho_nunca_passa_do_fim_do_arquivo_baixado(self):
        self.m["obter_duracao_audio"].return_value = 100.0
        worker.executar_ciclo_producao()
        self.m["montar_compilacao"].assert_not_called()
        self.assertEqual(self.m["renderizar_short"].call_count, 4)

    def test_video_sem_fala_e_deixado_de_lado(self):
        self.m["transcrever_audio"].return_value = []
        self.assertFalse(worker.executar_ciclo_producao())
        self.m["renderizar_short"].assert_not_called()
        self.assertIn("v1", self._historico())

    def test_falha_no_top_nao_perde_os_shorts(self):
        self.m["renderizar_longo"].side_effect = FFmpegError("longo", 1, "x")
        self.assertTrue(worker.executar_ciclo_producao())
        self.assertEqual(self.m["renderizar_short"].call_count, 4)
        self.assertNotIn("v5", self._historico(), "o vídeo que só entraria no Top volta a concorrer")

    def test_todos_os_videos_falham_nao_marca_como_concluido(self):
        self.m["renderizar_short"].side_effect = FFmpegError("legendas", 1, "Unable to open")
        self.m["renderizar_longo"].side_effect = FFmpegError("legendas", 1, "Unable to open")
        self.assertFalse(worker.executar_ciclo_producao())
        self.m["registrar_historico"].assert_not_called()
        self.assertEqual(self._status()["erro"]["categoria"], "render")
        self.assertIn("legendas", self._status()["erro"]["mensagem"])

    def test_falha_parcial_aproveita_os_videos_bons(self):
        self.m["renderizar_short"].side_effect = [FFmpegError("cta", 1, "x"), mock.DEFAULT, mock.DEFAULT, mock.DEFAULT]
        self.m["renderizar_short"].return_value = None
        self.assertTrue(worker.executar_ciclo_producao())
        self.assertIn("v2", self._historico())

    def test_pedido_duplicado_nao_baixa_de_novo(self):
        trava = estado.TravaCiclo()
        self.assertTrue(trava.adquirir())
        self.addCleanup(trava.liberar)
        self.assertFalse(worker.executar_ciclo_producao())
        self.m["baixar_video"].assert_not_called()

    def test_caos_disco_cheio_aborta_antes_de_baixar(self):
        self.disco.return_value = Disco(0, 0, 1024 ** 3)
        self.assertFalse(worker.executar_ciclo_producao())
        self.m["baixar_video"].assert_not_called()
        self.assertEqual(self._status()["erro"]["categoria"], "disco")

    def test_bruto_e_limpo_mesmo_com_erro(self):
        self.m["transcrever_audio"].side_effect = RuntimeError("whisper caiu")
        worker.executar_ciclo_producao()
        self.assertEqual(list(self.bruto_dir.iterdir()), [])
        self.assertFalse(estado.ciclo_em_andamento())

    def test_caos_sobra_de_ciclo_interrompido_e_limpa_antes_de_baixar(self):
        sobra = self.bruto_dir / "fonte1" / "live_bruta.mp4"
        sobra.parent.mkdir(parents=True)
        sobra.write_bytes(b"video de OUTRO criador")
        antiga = self.bruto_dir / "proxima"
        antiga.mkdir()

        def verificar(url, **kw):
            self.assertFalse(sobra.exists(), "sobra antiga seria reaproveitada como se fosse o vídeo novo")
            self.assertFalse(antiga.exists())
            return self._baixar(url, **kw)

        self.m["baixar_video"].side_effect = verificar
        self.assertTrue(worker.executar_ciclo_producao())

    def test_sucesso_limpa_erro_anterior(self):
        estado.publicar_status(erro={"categoria": "rede", "mensagem": "caiu"})
        self.assertTrue(worker.executar_ciclo_producao())
        self.assertIsNone(self._status().get("erro"))

    def test_erro_definitivo_repetido_vai_para_quarentena(self):
        self.m["baixar_video"].side_effect = RuntimeError("vídeo indisponível")
        for _ in range(estado.MAX_TENTATIVAS_VIDEO):
            worker.executar_ciclo_producao()
        self.assertTrue(estado.em_quarentena("v1"))

    def test_caos_rate_limit_nao_condena_o_video(self):
        self.m["baixar_video"].side_effect = RuntimeError("HTTP Error 429: Too Many Requests")
        for _ in range(estado.MAX_TENTATIVAS_VIDEO + 1):
            self.assertFalse(worker.executar_ciclo_producao())
        self.assertEqual(self._status()["erro"]["categoria"], "rate_limit")
        self.assertFalse(estado.em_quarentena("v1"))


class TestVideoQueRendeShortOuTop(BaseCiclo):
    """
    Regressão de 24/11: BRKsEDU e LOUD Coringa tinham a fala espalhada em pedaços curtos. Entraram no ciclo,
    não renderam Short nem trecho do Top, o Gameplayrj ficou sem Short e o ciclo terminou com 2 Shorts e sem o Top 5.
    """

    # 50 s de fala no total, mas em pedaços de 5 s a cada 35 s: não há momento seguido para Short nem para o Top
    ESPALHADA = [{"start": 5.0 + i * 35, "end": 10.0 + i * 35, "text": "fala"} for i in range(10)]

    def test_video_com_fala_espalhada_e_trocado_pelo_proximo(self):
        self.m["transcrever_audio"].side_effect = [self.ESPALHADA, self.ESPALHADA] + [self.segmentos] * 10
        self.assertTrue(worker.executar_ciclo_producao())
        criadores = {c for c, _ in self.m["roteiro_compilacao"].call_args.args[0]}
        self.assertEqual(criadores, {f"Criador {i}" for i in range(2, 7)}, "o Top 5 fecha com o próximo viral")
        self.assertEqual(self.m["renderizar_short"].call_count, 4)
        self.assertIn("v1", self._historico(), "o vídeo sem momento não volta na próxima busca")
        memoria = json.loads((self.raiz / "trechos_sem_fala.json").read_text(encoding="utf-8"))
        self.assertEqual(set(memoria["v1"]), {"360", "1800"})
        self.assertTrue(all("espalhada" in m["motivo"] for m in memoria["v1"].values()))

    def test_short_passa_para_o_proximo_video_quando_um_nao_tem_momento(self):
        """Um vídeo com trecho bom para o Top, mas sem momento para Short, entra só no Top."""
        so_top = [dict(s, text="so para o top") for s in self.segmentos]
        self.m["transcrever_audio"].side_effect = [so_top] + [self.segmentos] * 10
        original = worker._corte_do_short
        with mock.patch.object(worker, "_corte_do_short",
                               side_effect=lambda falas, bloqueios: [] if falas and falas[0]["text"] == "so para o top"
                               else original(falas, bloqueios)):
            self.assertTrue(worker.executar_ciclo_producao())
        streamers = [c.kwargs["streamer"] for c in self.m["renderizar_short"].call_args_list]
        self.assertEqual(streamers, [f"Criador {i}" for i in range(2, 6)], "o 5º vídeo ganhou a vaga do Short")
        criadores = {c for c, _ in self.m["roteiro_compilacao"].call_args.args[0]}
        self.assertEqual(criadores, {f"Criador {i}" for i in range(1, 6)})

    def test_trecho_do_top_usado_na_conferencia_e_o_do_top_completo(self):
        self.assertAlmostEqual(worker.TRECHO_DO_TOP_S, 102.0)


class TestMemoriaDosTrechosSemFala(BaseCiclo):
    """
    Regressão: o começo do vídeo do BRKsEDU não tinha fala dele e o meio chegou cortado. No ciclo seguinte o começo
    foi baixado e transcrito de novo (25 min na internet lenta) para dar os mesmos 12 s de fala.
    """

    def _memoria(self):
        caminho = self.raiz / "trechos_sem_fala.json"
        return json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else {}

    def _trechos_baixados(self):
        return [c.kwargs["trecho"] for c in self.m["baixar_video"].call_args_list]

    def test_trecho_sem_fala_nao_e_baixado_de_novo_no_proximo_ciclo(self):
        def baixar(url, **kw):
            if kw["trecho"][0] == 1800.0:
                raise RuntimeError("conexão caiu")
            return self._baixar(url, **kw)

        self.m["baixar_video"].side_effect = baixar
        self.m["transcrever_audio"].return_value = []
        with self.assertRaises(RuntimeError):
            worker._preparar_fonte(viral(1), 1, 5)
        self.assertEqual(self._trechos_baixados(), [(360.0, 360.0), (1800.0, 360.0)])

        self.m["baixar_video"].reset_mock()
        self.m["baixar_video"].side_effect = self._baixar
        self.m["transcrever_audio"].return_value = self.segmentos
        fonte = worker._preparar_fonte(viral(1), 1, 5)
        self.assertIsNotNone(fonte, "o meio do vídeo tem fala e é aproveitado")
        self.assertEqual(self._trechos_baixados(), [(1800.0, 360.0)], "o começo sem fala não desce de novo")

    def test_trecho_guardado_com_o_motivo_e_a_data(self):
        # Começo do v1 sem fala e meio em outro idioma: o v1 sai e os outros cinco fecham o ciclo
        self.m["transcrever_audio"].side_effect = [[]] + [self.segmentos] * 10
        self.m["e_audio_em_portugues"].side_effect = [True, False] + [True] * 10
        self.assertTrue(worker.executar_ciclo_producao())
        memoria = self._memoria()
        self.assertEqual(set(memoria), {"v1"}, "trecho com fala boa não é guardado")
        self.assertEqual({inicio: m["motivo"] for inicio, m in memoria["v1"].items()},
                         {"360": "pouca fala aproveitável", "1800": "áudio fora do português"})
        self.assertRegex(memoria["v1"]["360"]["em"], r"^\d{4}-\d{2}-\d{2}$")

    def test_falha_no_download_nao_marca_o_trecho(self):
        self.m["baixar_video"].side_effect = RuntimeError("conexão caiu")
        with self.assertRaises(RuntimeError):
            worker._preparar_fonte(viral(1), 1, 5)
        self.assertEqual(self._memoria(), {})

    def test_video_com_todos_os_trechos_sem_fala_nem_e_baixado(self):
        worker.guardar_trecho_sem_fala("v1", 360.0, "pouca fala aproveitável")
        worker.guardar_trecho_sem_fala("v1", 1800.0, "áudio fora do português")
        self.assertIsNone(worker._preparar_fonte(viral(1), 1, 5))
        self.m["baixar_video"].assert_not_called()

    def test_registro_de_mais_de_um_mes_e_esquecido(self):
        antigo = (worker.datetime.now() - worker.timedelta(days=worker.DIAS_MEMORIA_TRECHOS + 1)).strftime("%Y-%m-%d")
        (self.raiz / "trechos_sem_fala.json").write_text(json.dumps(
            {"v1": {"360": {"motivo": "pouca fala aproveitável", "em": antigo}},
             "v9": {"500": {"motivo": "pouca fala aproveitável", "em": antigo}}}), encoding="utf-8")
        self.assertEqual(worker.trechos_sem_fala("v1"), {})
        self.assertIsNotNone(worker._preparar_fonte(viral(1), 1, 5))
        self.assertEqual(self._trechos_baixados(), [(360.0, 360.0)])
        worker.guardar_trecho_sem_fala("v2", 360.0, "pouca fala aproveitável")
        self.assertEqual(list(self._memoria()), ["v2"], "os registros antigos saem do arquivo")

    def test_arquivo_estragado_nao_para_a_producao(self):
        (self.raiz / "trechos_sem_fala.json").write_text("{ isto não é json", encoding="utf-8")
        self.assertEqual(worker.trechos_sem_fala("v1"), {})
        self.assertIsNotNone(worker._preparar_fonte(viral(1), 1, 5))


class TestEstoque(BaseCiclo):

    def test_estoque_cheio_nao_baixa_nada(self):
        self._criar_estoque(shorts=worker.VIDEO_SPECS["limite_shorts"], longos=worker.VIDEO_SPECS["limite_longos"])
        self.assertFalse(worker.executar_ciclo_producao())
        self.m["buscar_videos_virais"].assert_not_called()
        self.m["baixar_video"].assert_not_called()

    def test_com_os_shorts_no_limite_so_monta_o_top(self):
        self._criar_estoque(shorts=worker.VIDEO_SPECS["limite_shorts"])
        worker.executar_ciclo_producao()
        self.m["renderizar_short"].assert_not_called()
        self.assertEqual(self.m["renderizar_longo"].call_count, 1)

    def test_com_os_longos_no_limite_so_faz_shorts(self):
        self._criar_estoque(longos=worker.VIDEO_SPECS["limite_longos"])
        worker.executar_ciclo_producao()
        self.m["renderizar_longo"].assert_not_called()
        self.assertEqual(self.m["renderizar_short"].call_count, 4)
        self.assertEqual(self.m["baixar_video"].call_count, 4, "sem o Top, baixa só o que vira Short")

    def test_nunca_passa_do_limite_do_estoque(self):
        self._criar_estoque(shorts=worker.VIDEO_SPECS["limite_shorts"] - 1, longos=worker.VIDEO_SPECS["limite_longos"] - 1)
        self.assertEqual(worker.calcular_vagas(), (1, 1))


class TestIntervaloComercial(BaseCiclo):
    """Telas pretas e comerciais nunca aparecem nos vídeos entregues."""

    def test_short_recebe_o_comercial_para_retirar(self):
        self.m["detectar_intervalos_comerciais"].return_value = [(300.0, 340.0)]
        worker.executar_ciclo_producao()
        self.assertIn((300.0, 340.0), self.m["renderizar_short"].call_args.kwargs["bloqueios"])

    def test_trecho_do_top_nao_pega_tela_preta(self):
        self.m["detectar_telas_pretas"].return_value = [(0.0, 120.0)]
        worker.executar_ciclo_producao()
        for _, inicio, _ in self.m["montar_compilacao"].call_args.args[0]:
            self.assertGreaterEqual(inicio, 120.0)


class TestCanalDark(BaseCiclo):
    """Cada vídeo ganha narração própria, título e gancho escritos para o canal. Não existe mais o formato antigo."""

    def test_short_usa_gancho_narracao_e_titulo_do_roteiro(self):
        worker.executar_ciclo_producao()
        chamada = self.m["renderizar_short"].call_args.kwargs
        self.assertEqual(chamada["gancho"], "A FUGA MAIS ABSURDA")
        self.assertEqual(chamada["narracao_roteiro"], ROTEIRO_SHORT["narracao"])
        titulos = [v["titulo"] for k, v in self._metadados().items() if k.startswith("short-")]
        self.assertIn("Ele achou que ia escapar #Shorts", titulos)

    def test_gancho_que_nao_coube_usa_o_automatico_e_mantem_a_narracao(self):
        self.m["roteiro_short"].return_value = {**ROTEIRO_SHORT, "gancho": None}
        worker.executar_ciclo_producao()
        chamada = self.m["renderizar_short"].call_args.kwargs
        self.assertTrue(chamada["gancho"])
        self.assertEqual(chamada["narracao_roteiro"], ROTEIRO_SHORT["narracao"])

    def test_top_ganha_abertura_e_uma_narracao_por_trecho(self):
        worker.executar_ciclo_producao()
        chamada = self.m["renderizar_longo"].call_args.kwargs
        self.assertTrue(chamada["abertura"].startswith("Hoje"))
        instantes = [instante for instante, _ in chamada["narracoes"]]
        self.assertEqual(len(instantes), 5)
        self.assertEqual(instantes, sorted(instantes))
        self.assertEqual(instantes[0], 0.0, "o primeiro trecho é narrado logo depois da abertura")
        self.assertEqual(instantes, [ini for ini, _, _ in chamada["creditos"]])

    def test_roteiro_do_top_recebe_o_que_foi_falado_em_cada_trecho(self):
        worker.executar_ciclo_producao()
        self.assertTrue(all("fala" in texto for _, texto in self.m["roteiro_compilacao"].call_args.args[0]))

    def test_todo_video_pronto_sai_no_formato_dark(self):
        self.assertTrue(worker.executar_ciclo_producao())
        metadados = self._metadados()
        self.assertEqual(len(metadados), 5)
        self.assertTrue(all(v["formato"] == "dark" and v["roteiro"] for v in metadados.values()))
        self.assertTrue(all(c.kwargs["narracao_roteiro"] for c in self.m["renderizar_short"].call_args_list))
        self.assertTrue(self.m["renderizar_longo"].call_args.kwargs["abertura"])

    def test_corte_sem_roteiro_valido_nao_vira_video(self):
        """Regressão: quando a IA errava o roteiro, o vídeo saía no formato antigo, sem narração própria."""
        self.m["roteiro_short"].return_value = None
        self.assertTrue(worker.executar_ciclo_producao(), "o Top sai narrado")
        self.m["renderizar_short"].assert_not_called()
        # A vaga de cada Short sem roteiro passa para o próximo vídeo: os 5 vídeos do ciclo são tentados
        self.assertEqual(self.m["roteiro_short"].call_count, 5 * roteiro.TENTATIVAS_ROTEIRO)
        self.assertEqual(self.m["renderizar_longo"].call_count, 1)
        self.assertFalse(any(k.startswith("short-") for k in self._metadados()))

    def test_ia_fora_do_ar_nenhum_video_sai_sem_narracao(self):
        """Regressão: com a IA em 503, longos do ZoiooGamer e do Tonhão saíram sem narração própria."""
        def ia_caiu(*_):
            roteiro._ia["pausada_ate"] = time.monotonic() + roteiro.ESPERA_MAXIMA_ROTEIRO_S + 60
            return None

        self.m["roteiro_short"].side_effect = ia_caiu
        self.assertFalse(worker.executar_ciclo_producao())
        self.m["renderizar_short"].assert_not_called()
        self.m["roteiro_compilacao"].assert_not_called()
        self.m["renderizar_longo"].assert_not_called()
        self.assertEqual(self._status()["erro"]["categoria"], "ia_roteiro")
        self.assertEqual(self._metadados(), {})
        self.m["registrar_historico"].assert_not_called()

    def test_top_sem_roteiro_nao_sai_no_formato_antigo(self):
        self.m["roteiro_compilacao"].side_effect = None
        self.m["roteiro_compilacao"].return_value = None
        self.assertTrue(worker.executar_ciclo_producao(), "os Shorts saem narrados")
        self.m["renderizar_longo"].assert_not_called()
        self.assertFalse(any(k.startswith("longo-") for k in self._metadados()))

    def test_espera_a_ia_voltar_e_narra_o_video(self):
        chamadas = []

        def instavel(*_):
            chamadas.append(1)
            if len(chamadas) == 1:
                roteiro._ia["pausada_ate"] = time.monotonic() + 120
                return None
            return ROTEIRO_SHORT

        self.m["roteiro_short"].side_effect = instavel
        with mock.patch.object(roteiro.time, "sleep") as esperar:
            self.assertTrue(worker.executar_ciclo_producao())
        self.assertTrue(any(c.args and c.args[0] > 100 for c in esperar.call_args_list), "esperou a pausa da IA")
        self.assertEqual(self.m["renderizar_short"].call_count, 4)
        self.assertTrue(all(c.kwargs["narracao_roteiro"] for c in self.m["renderizar_short"].call_args_list))

    def test_sem_ia_nem_comeca_a_baixar(self):
        self.m["ia_respondendo"].return_value = False
        self.assertFalse(worker.executar_ciclo_producao())
        self.m["buscar_videos_virais"].assert_not_called()
        self.m["baixar_video"].assert_not_called()
        self.assertIn("IA de roteiro", json.dumps(self._status(), ensure_ascii=False))

    def test_nenhum_roteiro_valido_aparece_no_painel(self):
        self.m["roteiro_short"].return_value = None
        self.m["roteiro_compilacao"].side_effect = None
        self.m["roteiro_compilacao"].return_value = None
        self.assertFalse(worker.executar_ciclo_producao())
        self.assertEqual(self._status()["erro"]["categoria"], "sem_roteiro")


class TestSobrasDaDiretoria(BaseCiclo):

    def test_video_rejeitado_que_ficou_no_disco_e_apagado_no_ciclo(self):
        sobra = self.export_dir / "short-x-corte9.mp4"
        sobra.write_bytes(b"x" * 200_000)
        (self.raiz / "descartados.json").write_text(json.dumps([sobra.name]), encoding="utf-8")
        worker.executar_ciclo_producao()
        self.assertFalse(sobra.exists())

    def test_video_ja_enviado_que_ficou_no_disco_e_apagado_no_ciclo(self):
        sobra = self.export_dir / "longo-x-parte1.mp4"
        sobra.write_bytes(b"x" * 200_000)
        self.agendados_file.write_text(json.dumps([{"filename": sobra.name, "youtube_id": "yt1"}]), encoding="utf-8")
        worker.executar_ciclo_producao()
        self.assertFalse(sobra.exists())

    def test_video_agendado_sem_envio_concluido_continua_no_disco(self):
        pendente = self.export_dir / "longo-x-parte1.mp4"
        pendente.write_bytes(b"x" * 200_000)
        self.agendados_file.write_text(json.dumps([{"filename": pendente.name, "youtube_id": None}]), encoding="utf-8")
        worker.limpar_sobras_da_diretoria()
        self.assertTrue(pendente.exists())

    def test_sobra_rejeitada_nao_conta_no_estoque(self):
        sobra = self.export_dir / "short-x-corte9.mp4"
        sobra.write_bytes(b"x" * 200_000)
        (self.raiz / "descartados.json").write_text(json.dumps([sobra.name]), encoding="utf-8")
        self.assertEqual(worker.contar_estoque(), (0, 0))


class TestBloqueioDoYoutube(BaseCiclo):

    ERRO = "Sign in to confirm you're not a bot"

    def test_bloqueio_no_download_para_o_ciclo_e_pausa_o_youtube(self):
        self.m["baixar_video"].side_effect = RuntimeError(self.ERRO)
        self.assertFalse(worker.executar_ciclo_producao())
        self.assertEqual(self.m["baixar_video"].call_count, 1, "não insiste nos outros vídeos")
        self.assertGreater(searcher._fontes["youtube_pausado_ate"], time.monotonic())
        self.assertEqual(self._status()["erro"]["espera_s"], worker.ESPERA_APOS_BLOQUEIO_S)

    def test_bloqueio_durante_a_busca_tambem_pausa_o_youtube(self):
        self.m["buscar_videos_virais"].side_effect = RuntimeError(self.ERRO)
        worker.executar_ciclo_producao()
        self.assertGreater(searcher._fontes["youtube_pausado_ate"], time.monotonic())


class TestNaoGravaMaisLives(unittest.TestCase):

    def test_ciclo_nao_tem_mais_gravacao_de_live(self):
        for nome in ("buscar_melhor_live", "_amostra_mostra_gta6", "_gravar_proxima", "_adiantar_proxima", "_proxima"):
            self.assertFalse(hasattr(worker, nome), nome)


class TestLoopDoVigia(BaseCiclo):

    def test_espera_cresce_e_tem_teto(self):
        self.assertEqual(worker.calcular_espera(0), 30)
        self.assertEqual(worker.calcular_espera(1), 60)
        self.assertEqual(worker.calcular_espera(2), 120)
        self.assertEqual(worker.calcular_espera(20), worker.ESPERA_MAXIMA_S)
        self.assertEqual(worker.calcular_espera(1, espera_minima=900), 900)

    def test_caos_excecao_inesperada_nao_mata_o_loop(self):
        with mock.patch.object(worker, "_aguardar"), \
             mock.patch.object(worker, "executar_ciclo_producao", side_effect=[RuntimeError("boom"), True]) as ciclo:
            worker.loop_vigia_continuo(max_iteracoes=2)
        self.assertEqual(ciclo.call_count, 2)

    def test_loop_aguarda_ciclo_manual_sem_repetir_aviso(self):
        trava = estado.TravaCiclo()
        self.assertTrue(trava.adquirir())
        self.addCleanup(trava.liberar)
        with mock.patch.object(worker, "_aguardar"), \
             mock.patch.object(worker, "executar_ciclo_producao") as ciclo:
            worker.loop_vigia_continuo(max_iteracoes=2)
        ciclo.assert_not_called()

    def test_pausa_impede_novo_ciclo(self):
        estado.definir_producao_ativa(False)
        with mock.patch.object(worker, "_aguardar"), \
             mock.patch.object(worker, "executar_ciclo_producao") as ciclo:
            worker.loop_vigia_continuo(max_iteracoes=2)
        ciclo.assert_not_called()


class TestJanelaDeTranscricao(unittest.TestCase):

    def test_janelas(self):
        self.assertEqual(transcriber.calcular_janela_transcricao(3600), (360.0, 1260.0))
        self.assertEqual(transcriber.calcular_janela_transcricao(300), (0.0, None))
        self.assertEqual(transcriber.calcular_janela_transcricao(0), (0.0, 1260.0))

    def test_janela_de_6_min_dos_videos_virais(self):
        self.assertEqual(transcriber.calcular_janela_transcricao(40815, janela=360), (4081.5, 360.0))
        self.assertEqual(transcriber.calcular_janela_transcricao(600, janela=360), (60.0, 360.0))
        self.assertEqual(transcriber.calcular_janela_transcricao(300, janela=360), (0.0, None))

    def test_timestamps_voltam_para_a_posicao_real_do_video(self):
        modelo = mock.Mock()
        modelo.transcribe.return_value = {"segments": [{"start": 1.0, "end": 2.0, "text": "oi"}]}
        with mock.patch.object(transcriber, "_obter_modelo", return_value=modelo):
            segmentos = transcriber.transcrever_audio("a.wav", deslocamento=360.0)
        self.assertEqual((segmentos[0]["start"], segmentos[0]["end"]), (361.0, 362.0))

    def test_extracao_recorta_a_janela(self):
        with mock.patch.object(transcriber, "executar_ffmpeg") as ffmpeg:
            transcriber.extrair_audio_wav("v.webm", "a.wav", inicio=360.0, duracao=480.0)
        args = ffmpeg.call_args.args[0]
        self.assertEqual(args[args.index("-ss") + 1], "360.0")
        self.assertEqual(args[args.index("-t") + 1], "480.0")


class TestWhisperNaPlacaDeVideo(unittest.TestCase):

    def setUp(self):
        for patcher in (mock.patch.dict(transcriber._modelos, clear=True),
                        mock.patch.object(transcriber, "log_terminal")):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _modelo(self, dispositivo):
        modelo = mock.Mock()
        modelo.device.type = dispositivo
        modelo.transcribe.return_value = {"segments": []}
        return modelo

    def _com_placa(self, disponivel, **kw):
        return (mock.patch.object(transcriber.torch.cuda, "is_available", return_value=disponivel),
                mock.patch.object(transcriber.whisper, "load_model", **kw))

    def test_usa_a_placa_quando_ela_esta_disponivel(self):
        placa, carregar = self._com_placa(True, return_value=self._modelo("cuda"))
        with placa, carregar as load:
            transcriber._obter_modelo("small")
        self.assertEqual(load.call_args.kwargs["device"], "cuda")

    def test_sem_placa_compativel_usa_o_processador(self):
        placa, carregar = self._com_placa(False, return_value=self._modelo("cpu"))
        with placa, carregar as load:
            transcriber._obter_modelo("small")
        self.assertEqual(load.call_args.kwargs["device"], "cpu")

    def test_placa_sem_memoria_ao_carregar_cai_para_o_processador(self):
        placa, carregar = self._com_placa(True, side_effect=[RuntimeError("CUDA out of memory"), self._modelo("cpu")])
        with placa, carregar as load:
            modelo = transcriber._obter_modelo("small")
        self.assertEqual(modelo.device.type, "cpu")
        self.assertEqual(load.call_args.kwargs["device"], "cpu")

    def test_na_placa_transcreve_em_meia_precisao(self):
        modelo = self._modelo("cuda")
        with mock.patch.object(transcriber, "_obter_modelo", return_value=modelo):
            transcriber.transcrever_audio("a.wav")
        self.assertTrue(modelo.transcribe.call_args.kwargs["fp16"])

    def test_no_processador_transcreve_em_precisao_normal(self):
        modelo = self._modelo("cpu")
        with mock.patch.object(transcriber, "_obter_modelo", return_value=modelo):
            transcriber.transcrever_audio("a.wav")
        self.assertFalse(modelo.transcribe.call_args.kwargs["fp16"])

    def test_memoria_acaba_no_meio_e_refaz_no_processador(self):
        na_placa = self._modelo("cuda")
        na_placa.transcribe.side_effect = RuntimeError("CUDA out of memory")
        no_processador = self._modelo("cpu")
        with mock.patch.object(transcriber, "_obter_modelo", return_value=na_placa), \
                mock.patch.object(transcriber.whisper, "load_model", return_value=no_processador), \
                mock.patch.object(transcriber.torch.cuda, "empty_cache"):
            self.assertEqual(transcriber.transcrever_audio("a.wav"), [])
        no_processador.transcribe.assert_called_once()

    def test_outros_erros_nao_sao_escondidos(self):
        modelo = self._modelo("cuda")
        modelo.transcribe.side_effect = RuntimeError("arquivo corrompido")
        with mock.patch.object(transcriber, "_obter_modelo", return_value=modelo):
            with self.assertRaises(RuntimeError):
                transcriber.transcrever_audio("a.wav")


if __name__ == "__main__":
    unittest.main()
