"""
SPEC-004: os personagens só andam pelo piso livre e nunca atravessam os móveis.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ESCRITORIO = Path(__file__).resolve().parent.parent / "escritorio.js"

VERIFICACAO = r"""
const e = require(process.argv[1]);
const erros = { semRota: [], atravessaMovel: [], cortaQuina: [], pontoBloqueado: [], acessoBloqueado: [] };
const pontos = [];
e.PONTOS.cafe.concat(e.PONTOS.celular, e.PONTOS.danca, e.PONTOS.reuniao).forEach(p => pontos.push(p));
e.PONTOS.conversa.forEach(par => par.forEach(p => pontos.push(p)));
pontos.forEach(p => { if (!e.celulaLivre(p[0], p[1])) erros.pontoBloqueado.push(p); });

const acessos = e.AGENTES.map(a => e.acessoDoAssento(a));
acessos.forEach(p => { if (!e.celulaLivre(p[0], p[1])) erros.acessoBloqueado.push(p); });

const lugares = pontos.concat(acessos);
lugares.forEach(origem => lugares.forEach(destino => {
  if (origem[0] === destino[0] && origem[1] === destino[1]) return;
  const rota = e.calcularRota(origem, destino);
  if (!rota.length) { erros.semRota.push([origem, destino]); return; }
  let anterior = origem;
  rota.forEach(p => {
    if (!e.celulaLivre(p[0], p[1])) erros.atravessaMovel.push(p);
    const dc = p[0] - anterior[0], dr = p[1] - anterior[1];
    if (dc && dr && (!e.celulaLivre(anterior[0] + dc, anterior[1]) || !e.celulaLivre(anterior[0], anterior[1] + dr))) {
      erros.cortaQuina.push([anterior, p]);
    }
    anterior = p;
  });
}));

e.AGENTES.forEach(a => {
  const rota = e.calcularRota(a.assento, [13, 8]);
  if (!rota.length) erros.semRota.push([a.id, 'levantar']);
});
const livres = [];
for (let c = 0; c < e.COLUNAS; c++) for (let r = 0; r < e.LINHAS; r++) if (e.celulaLivre(c, r)) livres.push([c, r]);
const vistos = new Set([livres[0].join(',')]);
const fila = [livres[0]];
while (fila.length) {
  const [c, r] = fila.pop();
  [[1, 0], [-1, 0], [0, 1], [0, -1]].forEach(([dc, dr]) => {
    const k = (c + dc) + ',' + (r + dr);
    if (e.celulaLivre(c + dc, r + dr) && !vistos.has(k)) { vistos.add(k); fila.push([c + dc, r + dr]); }
  });
}
const ocupadas = {};
const sobrepostos = [], foraDoPiso = [], semDesenho = [];
e.MOVEIS.forEach(m => {
  if (!e.FIXOS[m.tipo]) semDesenho.push(m.tipo);
  for (let c = m.c; c < m.c + m.l; c++) for (let r = m.r; r < m.r + m.p; r++) {
    const k = c + ',' + r;
    if (ocupadas[k]) sobrepostos.push(m.tipo + '@' + k + ' x ' + ocupadas[k]);
    ocupadas[k] = m.tipo;
    if (!e.dentroDoPiso(c, r)) foraDoPiso.push(m.tipo + '@' + k);
  }
});
const externosNoPiso = e.EXTERNOS.filter(m => e.dentroDoPiso(Math.floor(m.c), Math.floor(m.r))).map(m => m.tipo);
const sofa = e.MOVEIS.find(m => m.tipo === 'sofa');
console.log(JSON.stringify({ erros, agentes: e.AGENTES.length,
  assentos: new Set(e.AGENTES.map(a => a.assento.join(','))).size,
  gordaoNoSofa: !!e.bloqueadas[Math.floor(e.sofa.c) + ',' + Math.floor(e.sofa.r)]
    && e.sofa.c > sofa.c && e.sofa.c < sofa.c + sofa.l,
  areaLivre: livres.length, alcancaveis: vistos.size, sobrepostos, foraDoPiso, semDesenho,
  externosNoPiso, figurantes: e.MOVEIS.filter(m => m.tipo === 'npc').length + (e.PASSANTES || []).length,
  externosSemDesenho: e.EXTERNOS.filter(m => !e.FIXOS[m.tipo]).map(m => m.tipo) }));
"""


SIMULACAO = r"""
const e = require(process.argv[1]);
let semente = 4242;
Math.random = () => { semente = (semente * 16807) % 2147483647; return (semente - 1) / 2147483646; };
e.AGENTES.forEach(e.prepararAgente);

const livres = [];
for (let c = 0; c < e.COLUNAS; c++) for (let r = 0; r < e.LINHAS; r++) if (e.celulaLivre(c, r)) livres.push([c, r]);
const estados = e.AGENTES.map(a => ({ a, pausa: Math.random() * 2, chegadas: 0, ultima: 0 }));
const dt = 1 / 60;
const duracao = 600;
const sobreMovel = new Set();
const colisoes = new Set();
const presos = new Set();
let maiorPasso = 0;

for (let quadro = 0; quadro < duracao * 60; quadro++) {
  const tempo = quadro * dt;
  estados.forEach(s => {
    const a = s.a;
    if (!a.rota) {
      s.pausa -= dt;
      if (s.pausa <= 0) {
        let destino = livres[Math.floor(Math.random() * livres.length)];
        while (e.reservas[destino.join(',')]) destino = livres[Math.floor(Math.random() * livres.length)];
        e.irPara(a, destino, () => { s.chegadas++; s.ultima = tempo; s.pausa = Math.random() * 2; });
      }
    }
    const antes = [a.c, a.r];
    e.atualizarAgente(a, dt);
    maiorPasso = Math.max(maiorPasso, Math.hypot(a.c - antes[0], a.r - antes[1]));
    const celula = [Math.floor(a.c), Math.floor(a.r)];
    const propria = celula[0] === a.assento[0] && celula[1] === a.assento[1];
    if (e.bloqueadas[celula.join(',')] && !propria) sobreMovel.add(a.id + '@' + celula.join(','));
    if (tempo - s.ultima > 120) presos.add(a.id);
  });
  for (let i = 0; i < estados.length; i++) for (let j = i + 1; j < estados.length; j++) {
    const a = estados[i].a, b = estados[j].a;
    if (Math.hypot(a.c - b.c, a.r - b.r) < 0.45) colisoes.add(a.id + 'x' + b.id);
  }
}

let voltaram = 0;
const pediram = new Set();
for (let quadro = 0; quadro < 60 * 240 && voltaram < e.AGENTES.length; quadro++) {
  e.AGENTES.forEach(a => {
    if (!a.rota && !pediram.has(a.id)) {
      pediram.add(a.id);
      e.sentar(a, () => voltaram++);
    }
    e.atualizarAgente(a, dt);
  });
}
console.log(JSON.stringify({ sobreMovel: [...sobreMovel], colisoes: [...colisoes], presos: [...presos],
  chegadas: Math.min(...estados.map(s => s.chegadas)), maiorPasso, voltaram }));
"""


@unittest.skipUnless(shutil.which("node"), "Node.js não está disponível")
class TestCaminhadaSimulada(unittest.TestCase):
    """Simula 10 minutos de movimentação dos 8 personagens andando ao mesmo tempo."""

    @classmethod
    def setUpClass(cls):
        saida = subprocess.check_output(
            ["node", "-e", SIMULACAO, str(ESCRITORIO)], text=True, encoding="utf-8", timeout=120)
        cls.resultado = json.loads(saida)

    def test_ninguem_pisa_em_movel(self):
        self.assertEqual(self.resultado["sobreMovel"], [])

    def test_personagens_nao_atravessam_uns_aos_outros(self):
        self.assertEqual(self.resultado["colisoes"], [])

    def test_ninguem_fica_preso(self):
        self.assertEqual(self.resultado["presos"], [])
        self.assertGreater(self.resultado["chegadas"], 10)

    def test_movimento_e_continuo_sem_saltos(self):
        self.assertLess(self.resultado["maiorPasso"], 0.05)

    def test_todos_voltam_para_a_cadeira(self):
        self.assertEqual(self.resultado["voltaram"], 8)


@unittest.skipUnless(shutil.which("node"), "Node.js não está disponível")
class TestPlantaDoEscritorio(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        saida = subprocess.check_output(["node", "-e", VERIFICACAO, str(ESCRITORIO)], text=True, encoding="utf-8")
        cls.resultado = json.loads(saida)

    def test_rotas_nunca_atravessam_moveis(self):
        self.assertEqual(self.resultado["erros"]["atravessaMovel"], [])

    def test_rotas_nao_cortam_quinas_dos_moveis(self):
        self.assertEqual(self.resultado["erros"]["cortaQuina"], [])

    def test_todos_os_lugares_sao_alcancaveis(self):
        self.assertEqual(self.resultado["erros"]["semRota"], [])

    def test_pontos_de_atividade_ficam_no_piso_livre(self):
        self.assertEqual(self.resultado["erros"]["pontoBloqueado"], [])
        self.assertEqual(self.resultado["erros"]["acessoBloqueado"], [])

    def test_cada_personagem_tem_a_propria_cadeira(self):
        self.assertEqual(self.resultado["agentes"], 8)
        self.assertEqual(self.resultado["assentos"], 8)

    def test_sofa_do_gordao_nao_e_caminho(self):
        self.assertTrue(self.resultado["gordaoNoSofa"])

    def test_escritorio_ampliado_tem_espaco_para_circular(self):
        self.assertGreaterEqual(self.resultado["areaLivre"], 450)

    def test_todo_o_piso_livre_e_alcancavel(self):
        self.assertEqual(self.resultado["alcancaveis"], self.resultado["areaLivre"])

    def test_moveis_nao_se_sobrepoem_nem_saem_do_piso(self):
        self.assertEqual(self.resultado["sobrepostos"], [])
        self.assertEqual(self.resultado["foraDoPiso"], [])

    def test_todo_movel_tem_desenho(self):
        self.assertEqual(self.resultado["semDesenho"], [])
        self.assertEqual(self.resultado["externosSemDesenho"], [])

    def test_terraco_fica_fora_do_piso_do_escritorio(self):
        self.assertEqual(self.resultado["externosNoPiso"], [])

    def test_escritorio_nao_tem_mais_figurantes(self):
        """Pedido de 24/11: ficam só as pessoas que cobrem uma função; os figurantes de volume saíram."""
        self.assertEqual(self.resultado["figurantes"], 0)


@unittest.skipUnless(shutil.which("node"), "Node.js não está disponível")
class TestElencoSemRepeticao(unittest.TestCase):
    """Cada pessoa do escritório tem arte própria, em vez de um mesmo boneco com outra cor."""

    PASTA = ESCRITORIO.parent / "sprites" / "personagens"

    @classmethod
    def setUpClass(cls):
        codigo = "const e=require(process.argv[1]);console.log(JSON.stringify(e.AGENTES.map(p=>p.id)))"
        cls.ids = json.loads(subprocess.check_output(["node", "-e", codigo, str(ESCRITORIO)], text=True, encoding="utf-8"))

    def test_todos_tem_as_quatro_poses(self):
        faltando = [f"{i}_pose{n}" for i in self.ids for n in (1, 2, 3, 4) if not (self.PASTA / f"{i}_pose{n}.png").exists()]
        self.assertEqual(faltando, [])

    def test_ninguem_tem_identificador_repetido(self):
        self.assertEqual(len(self.ids), len(set(self.ids)))

    def test_nenhum_boneco_e_recoloracao_de_outro(self):
        """Compara a silhueta: bonecos só recoloridos teriam exatamente o mesmo contorno."""
        from PIL import Image
        silhuetas = {}
        for pessoa in self.ids:
            alfa = Image.open(self.PASTA / f"{pessoa}_pose3.png").convert("RGBA").getchannel("A").point(lambda v: 255 if v else 0)
            silhuetas.setdefault(alfa.tobytes(), []).append(pessoa)
        repetidos = [nomes for nomes in silhuetas.values() if len(nomes) > 1]
        self.assertEqual(repetidos, [])


TAREFAS = r"""
const e = require(process.argv[1]);
const etapas = {
  busca: 'Buscando os vídeos de GTA 6 mais virais da semana...',
  download: 'Baixando o trecho do vídeo viral 2/5 (alanzoka)...',
  jogo: 'Conferindo o jogo no vídeo viral 2/5 (alanzoka)...',
  fala: 'Transcrevendo o vídeo viral 2/5 (alanzoka)...',
  ia: 'Esperando a IA de roteiro voltar para narrar o Short 1 (até 5 min)...',
  short: 'Renderizando Short 1/4 (alanzoka)...',
  top: 'Montando o Top 5 da semana...',
  fim: 'Ciclo concluído: 4 Short(s) e 1 vídeo(s) longo(s) pronto(s)!',
  estoque: 'Estoque completo (9/9). Em pausa.',
  outra: 'Robô Vigia iniciado.'
};
const quem = {};
Object.keys(etapas).forEach(k => { quem[k] = e.agenteDaEtapa(etapas[k]); });
const falas = [];
e.AGENTES.forEach(a => { a.balao = null; });
global.falar = (ag, texto) => falas.push(ag.id + ':' + texto);
e.anunciarTarefa(etapas.download);
e.anunciarTarefa(etapas.download);
console.log(JSON.stringify({ quem, cargos: e.AGENTES.map(a => a.cargo), reuniao: Object.keys(e.FALAS_REUNIAO).sort(),
  ids: e.AGENTES.map(a => a.id).sort() }));
"""


@unittest.skipUnless(shutil.which("node"), "Node.js não está disponível")
class TestCadaEtapaTemQuemCuide(unittest.TestCase):
    """Cada pessoa da equipe é uma etapa real da produção; o painel mostra quem está trabalhando agora."""

    @classmethod
    def setUpClass(cls):
        saida = subprocess.check_output(["node", "-e", TAREFAS, str(ESCRITORIO)], text=True, encoding="utf-8")
        cls.r = json.loads(saida.strip().splitlines()[-1])

    def test_cada_etapa_aponta_quem_cuida_dela(self):
        self.assertEqual(self.r["quem"], {
            "busca": "bruno", "download": "caio", "jogo": "camila", "fala": "thiago", "ia": "thiago",
            "short": "lucas", "top": "mariana", "fim": "camila", "estoque": "dr_ricardo", "outra": None})

    def test_cargos_falam_do_modelo_novo(self):
        cargos = " ".join(self.r["cargos"])
        for funcao in ("Olheiro de Virais", "Downloads", "Roteirista", "Shorts", "Top 5", "Publicação", "Diretoria"):
            self.assertIn(funcao, cargos)
        self.assertNotIn("CTR", cargos)

    def test_todos_explicam_a_funcao_na_reuniao(self):
        self.assertEqual(self.r["reuniao"], self.r["ids"])


SIMULACAO_GORDAO = r"""
const e = require(process.argv[1]);
globalThis.performance = globalThis.performance || { now: () => Date.now() };
e.prepararGordao();
const g = e.sofa;
const feitas = new Set(), acoes = new Set();
const foraDaSala = new Set(), sobreMovel = new Set();
let deitadas = 0, antes = true, maiorPasso = 0;
for (let q = 0; q < 60 * 60 * 15; q++) {
  const c0 = g.c, r0 = g.r, estava = g.deitado;
  e.atualizarGordao(1 / 60);
  if (estava === g.deitado && !g.deitado) maiorPasso = Math.max(maiorPasso, Math.hypot(g.c - c0, g.r - r0));
  if (g.deitado && !antes) deitadas++;
  antes = g.deitado;
  if (g.deitado) continue;
  if (g.fase === 'acao') { feitas.add(g.atividade.id); if (g.acao) acoes.add(g.acao); }
  const celula = [Math.floor(g.c), Math.floor(g.r)];
  if (celula[0] < 28) foraDaSala.add(celula.join(','));
  if (e.bloqueadas[celula.join(',')]) sobreMovel.add(celula.join(','));
}
console.log(JSON.stringify({ feitas: [...feitas], acoes: [...acoes], foraDaSala: [...foraDaSala], sobreMovel: [...sobreMovel],
  deitadas, maiorPasso, esperadas: e.ATIVIDADES_GORDAO.map(a => a.id),
  pontosLivres: e.ATIVIDADES_GORDAO.every(a => e.celulaLivre(a.ponto[0], a.ponto[1])),
  moveis: e.MOVEIS.map(m => m.tipo) }));
"""


@unittest.skipUnless(shutil.which("node"), "Node.js não está disponível")
class TestGordaoNaGreenRoom(unittest.TestCase):
    """Simula 15 minutos do Gordão aproveitando tudo o que existe na Green Room."""

    @classmethod
    def setUpClass(cls):
        saida = subprocess.check_output(["node", "-e", SIMULACAO_GORDAO, str(ESCRITORIO)], text=True, encoding="utf-8", timeout=120)
        cls.r = json.loads(saida.strip().splitlines()[-1])

    def test_faz_todas_as_atividades(self):
        self.assertEqual(sorted(self.r["feitas"]), sorted(self.r["esperadas"]))
        for atividade in ("sinuca", "freezer", "dj", "bar"):
            self.assertIn(atividade, self.r["feitas"])

    def test_volta_para_o_sofa_entre_os_passeios(self):
        self.assertGreaterEqual(self.r["deitadas"], 3)

    def test_nunca_sai_da_green_room(self):
        self.assertEqual(self.r["foraDaSala"], [])

    def test_nao_atravessa_moveis(self):
        self.assertEqual(self.r["sobreMovel"], [])
        self.assertTrue(self.r["pontosLivres"])

    def test_anda_sem_teleportar(self):
        self.assertLess(self.r["maiorPasso"], 0.05)

    def test_sala_tem_bar_freezer_e_jogos(self):
        for movel in ("freezer", "balcaoBar", "prateleiraBar", "sinuca", "toca", "pebolim", "arcade", "sofa"):
            self.assertIn(movel, self.r["moveis"])

    def test_todas_as_acoes_tem_imagem(self):
        pasta = ESCRITORIO.parent / "sprites" / "personagens"
        faltando = [a for a in self.r["acoes"] if not (pasta / f"gordao_{a}.png").exists()]
        self.assertEqual(faltando, [])


CAMERA = r"""
const e = require(process.argv[1]);
const c = e.cena;
Object.assign(c, { largura: 1850, altura: 802, escalaBase: 0.826, xBase: 740, yBase: 192 });
e.restaurarCamera();
const mundo = (x, y) => [(x - c.x) / c.escala, (y - c.y) / c.escala];
const antes = mundo(900, 400);
e.definirZoom(2, 900, 400);
const depois = mundo(900, 400);
const ancora = Math.hypot(antes[0] - depois[0], antes[1] - depois[1]);
e.definirZoom(99, 900, 400);
const maximo = c.zoom;
e.definirZoom(0.01, 900, 400);
const minimo = c.zoom;
e.definirZoom(2, 900, 400);
e.moverCamera(1e6, 1e6);
const canto = [c.x, c.y];
e.moverCamera(-120, -80);
const moveu = canto[0] - c.x;
e.restaurarCamera();
console.log(JSON.stringify({ ancora, maximo, minimo, limiteMaxMin: [e.ZOOM_MAXIMO, e.ZOOM_MINIMO], canto, moveu,
  inicial: [c.zoom, c.escala, c.x, c.y] }));
"""


@unittest.skipUnless(shutil.which("node"), "Node.js não está disponível")
class TestCameraDoEscritorio(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.r = json.loads(subprocess.check_output(["node", "-e", CAMERA, str(ESCRITORIO)], text=True, encoding="utf-8"))

    def test_zoom_mantem_o_ponto_sob_o_mouse(self):
        self.assertLess(self.r["ancora"], 0.001)

    def test_zoom_respeita_os_limites(self):
        self.assertEqual([self.r["maximo"], self.r["minimo"]], self.r["limiteMaxMin"])

    def test_arrastar_nao_deixa_o_cenario_sair_da_tela(self):
        self.assertLess(self.r["canto"][0], 1e5)
        self.assertLess(self.r["canto"][1], 1e5)
        self.assertAlmostEqual(self.r["moveu"], 120, places=3)

    def test_botao_volta_para_a_visao_inicial(self):
        self.assertEqual(self.r["inicial"], [1, 0.826, 740, 192])

    def test_logo_do_canal_esta_na_parede(self):
        self.assertTrue((ESCRITORIO.parent / "sprites" / "logo_mural.jpg").exists())
        self.assertIn("/sprites/logo_mural.jpg", ESCRITORIO.read_text(encoding="utf-8"))

    def test_carro_realista_existe(self):
        for parte in ("corpo", "rodas"):
            self.assertTrue((ESCRITORIO.parent / "sprites" / f"carro_{parte}.png").exists())

    def test_painel_tem_botoes_de_zoom(self):
        html = (ESCRITORIO.parent / "painel_vice.html").read_text(encoding="utf-8")
        for trecho in ("zoomCentral(1.25)", "zoomCentral(0.8)", "restaurarCamera()"):
            self.assertIn(trecho, html)


class TestGordao(unittest.TestCase):
    """O Gordão segue o porte dos outros bonecos: o nome é apelido, não o corpo do personagem."""

    def test_sprite_tem_a_mesma_escala_dos_outros_personagens(self):
        from PIL import Image
        pasta = ESCRITORIO.parent / "sprites"
        referencia = Image.open(pasta / "personagens" / "dr_ricardo_pose3.png").convert("RGBA").getchannel("A").getbbox()
        altura_em_pe = referencia[3] - referencia[1]
        largura_em_pe = referencia[2] - referencia[0]
        for quadro in (1, 2, 3):
            caixa = Image.open(pasta / f"sofa_quadro{quadro}.png").convert("RGBA").getchannel("A").getbbox()
            self.assertLessEqual(caixa[2] - caixa[0], altura_em_pe + 16, "comprimento deitado igual à altura em pé")
            tronco = Image.open(pasta / f"sofa_quadro{quadro}.png").convert("RGBA").crop((122, 0, 130, 181)).getchannel("A").getbbox()
            self.assertLessEqual(tronco[3] - tronco[1], largura_em_pe + 16, "sem corpo mais largo que o dos outros bonecos")


if __name__ == "__main__":
    unittest.main()
