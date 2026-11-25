"""
Diretoria: aprovar um vídeo não trava a curadoria enquanto ele sobe para o YouTube.
O painel.js roda no Node com uma página simulada, sem tocar no YouTube.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

PAINEL = Path(__file__).resolve().parent.parent / "painel.js"

SIMULACAO = r"""
const fs = require('fs'), vm = require('vm');
const elementos = {};
function el(id) {
  if (!elementos[id]) {
    elementos[id] = { id, innerHTML: '', innerText: '', textContent: '', className: '', value: id === 'sel-canal' ? '1' : '',
      style: {}, dataset: {}, disabled: false, pause() {}, removeAttribute() {}, load() {}, setAttribute() {},
      getAttribute: () => null, appendChild() {}, classList: { add() {}, remove() {}, toggle() {}, contains: () => false } };
  }
  return elementos[id];
}
const documento = { getElementById: el, querySelectorAll: () => [], addEventListener() {}, hidden: false };
let pendentes = ['a.mp4', 'b.mp4', 'c.mp4', 'd.mp4', 'longo-e.mp4'].map(n => ({ arquivo: n, filename: n, titulo: n,
  descricao: '', formato: 'dark', roteiro: { narracao: 'Narração de ' + n } }));
pendentes[0].roteiro = { narracao: 'Ele achou que <ia> escapar.' };
pendentes[3].formato = 'padrao';
pendentes[3].roteiro = null;
pendentes[4].tipo = 'longo';
// O canal 1 já recebeu o vídeo longo de hoje; os Shorts continuam livres
const cotas = { '1': { usados: 1, limite: 3, verificado: true, bloqueado: false,
  por_tipo: { longo: { usados: 1, limite: 1 }, short: { usados: 0, limite: 2 } } } };
// Já publicado, ainda vai ao ar e envio que não chegou ao YouTube
const historico = [
  { filename: 'short-velho.mp4', titulo: 'Short velho', youtube_id: 'yt0', data: '2020-01-01', horario: '12:00', canal: '1' },
  { filename: 'longo-novo-parte1.mp4', titulo: 'Longo novo', youtube_id: 'yt1', data: '2099-01-01', horario: '17:00', canal: '1', canal_nome: 'Viela Vice' },
  { filename: 'short-falhou.mp4', titulo: 'Short falhou', youtube_id: null, data: '2099-01-01', horario: '12:00', canal: '1' }
];
const aprovacoes = [];
function resposta(status, corpo) { return { ok: status < 400, status, json: () => Promise.resolve(corpo) }; }
function buscar(url, cfg) {
  if (url === '/api/data') return Promise.resolve(resposta(200, { videos: pendentes, cotas, cota_por_tipo: { longo: 1, short: 2 },
    agendados: historico, enviando: [] }));
  if (url === '/api/aprovar') return new Promise(r => aprovacoes.push({ nome: JSON.parse(cfg.body).filename, responder: r }));
  return Promise.resolve(resposta(200, {}));
}
const contexto = { document: documento, fetch: buscar, AbortController, console, JSON, Promise, Object, Date, Math,
  setTimeout: () => 0, clearTimeout() {}, setInterval: () => 0, clearInterval() {}, confirm: () => true,
  navigator: {}, window: {}, iniciarEscritorio() {} };
vm.createContext(contexto);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), contexto);
const esperar = () => new Promise(r => setImmediate(r));
const tela = () => el('m-txt').innerHTML;
(async () => {
  const r = {};
  contexto.abrirAvaliacao(); await esperar(); await esperar();
  r.inicio = tela().includes('<b>a.mp4</b>');
  r.selo_dark = tela().includes('Formato dark') && tela().includes('Ele achou que &lt;ia&gt; escapar.');
  contexto.aprovarVideo('a.mp4');
  r.proximo_na_tela = tela().includes('<b>b.mp4</b>');
  r.status_mostra_envio = tela().includes('envios-status') && el('envios-status').innerHTML.includes('a.mp4');
  r.botao_do_proximo_livre = !el('btn-enviar-hoje').disabled;
  contexto.aprovarVideo('b.mp4');
  r.dois_envios_juntos = aprovacoes.length === 2 && el('envios-status').innerHTML.includes('b.mp4');
  aprovacoes[0].responder(resposta(409, { success: false, em_andamento: true, error: 'Este vídeo já está sendo enviado.' }));
  await esperar(); await esperar();
  r.duplicado_e_so_aviso = el('aviso').className === 'aviso';
  r.a_nao_volta = !JSON.stringify(vm.runInContext('listaPendentes', contexto)).includes('a.mp4');
  aprovacoes[1].responder(resposta(500, { success: false, error: 'falhou' }));
  await esperar(); await esperar();
  r.falha_e_erro = el('aviso').className === 'erro';
  r.b_volta_para_a_lista = JSON.stringify(vm.runInContext('listaPendentes', contexto)).includes('b.mp4');
  r.status_limpo = !el('envios-status').innerHTML.includes('mp4');
  contexto.aprovarVideo('c.mp4');
  // O próximo é do formato antigo: aviso vermelho e aprovação travada
  r.selo_fora_do_padrao = tela().includes('<b>d.mp4</b>') && tela().includes('Fora do padrão dark');
  r.botao_travado_fora_do_padrao = el('btn-enviar-hoje').disabled === true && el('btn-enviar-hoje').textContent.includes('Fora do padrão');
  aprovacoes[2].responder(resposta(200, { success: true, enviado_youtube: true, message: 'Vídeo aprovado e agendado!' }));
  await esperar(); await esperar();
  r.sucesso_e_ok = el('aviso').className === 'ok';
  r.c_saiu = !JSON.stringify(vm.runInContext('listaPendentes', contexto)).includes('c.mp4');
  // Pula para o longo: o canal 1 já tem o longo do dia
  vm.runInContext('idxAtual++; renderizarPlayer();', contexto);
  r.longo_na_tela = tela().includes('<b>longo-e.mp4</b>');
  r.longo_travado_no_canal_completo = el('btn-enviar-hoje').disabled === true &&
    el('btn-enviar-hoje').textContent.includes('1/1 vídeo longo');
  r.canais_mostram_cada_tipo = tela().includes('longo 1/1 · Shorts 0/2');
  contexto.atualizarTudo(); await esperar(); await esperar();
  r.fila_conta_so_o_que_vai_ao_ar = el('b-fila').innerHTML.includes('(1)');
  contexto.abrirFila();
  r.fila_mostra_o_agendado = tela().includes('Longo novo') && tela().includes('Vídeo longo') && !tela().includes('Short velho');
  r.fila_conta_os_publicados = tela().includes('1 vídeo(s) já publicado(s)');
  console.log(JSON.stringify(r));
})();
"""


@unittest.skipUnless(shutil.which("node"), "Node.js não está disponível")
class TestAprovacaoNaDiretoria(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        saida = subprocess.check_output(["node", "-e", SIMULACAO, str(PAINEL)], text=True, encoding="utf-8", timeout=60)
        cls.r = json.loads(saida.strip().splitlines()[-1])

    def test_abre_no_primeiro_video(self):
        self.assertTrue(self.r["inicio"])

    def test_diretoria_mostra_a_narracao_do_formato_dark(self):
        self.assertTrue(self.r["selo_dark"])

    def test_video_do_formato_antigo_fica_travado(self):
        self.assertTrue(self.r["selo_fora_do_padrao"])
        self.assertTrue(self.r["botao_travado_fora_do_padrao"])

    def test_canal_que_ja_tem_o_longo_do_dia_nao_recebe_outro(self):
        self.assertTrue(self.r["longo_na_tela"])
        self.assertTrue(self.r["longo_travado_no_canal_completo"])
        self.assertTrue(self.r["canais_mostram_cada_tipo"])

    def test_aprovar_mostra_o_proximo_video_na_hora(self):
        self.assertTrue(self.r["proximo_na_tela"])
        self.assertTrue(self.r["botao_do_proximo_livre"])

    def test_envio_em_andamento_fica_visivel(self):
        self.assertTrue(self.r["status_mostra_envio"])
        self.assertTrue(self.r["dois_envios_juntos"])

    def test_clique_repetido_nao_vira_erro(self):
        self.assertTrue(self.r["duplicado_e_so_aviso"])
        self.assertTrue(self.r["a_nao_volta"])

    def test_falha_devolve_o_video_para_a_diretoria(self):
        self.assertTrue(self.r["falha_e_erro"])
        self.assertTrue(self.r["b_volta_para_a_lista"])
        self.assertTrue(self.r["status_limpo"])

    def test_fila_do_youtube_mostra_so_o_que_vai_ao_ar(self):
        """Regressão: a Fila mostrava 74 vídeos que já tinham sido publicados dias antes."""
        self.assertTrue(self.r["fila_conta_so_o_que_vai_ao_ar"])
        self.assertTrue(self.r["fila_mostra_o_agendado"])
        self.assertTrue(self.r["fila_conta_os_publicados"])

    def test_sucesso_confirma_e_tira_da_lista(self):
        self.assertTrue(self.r["sucesso_e_ok"])
        self.assertTrue(self.r["c_saiu"])


if __name__ == "__main__":
    unittest.main()
