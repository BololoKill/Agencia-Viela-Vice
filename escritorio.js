// Escritório virtual desenhado em código: piso isométrico, móveis com colisão e personagens com rotas reais
var emReuniao = false;

var COLUNAS = 50;
var COLUNAS_CAMERA = 40;
var FUNDO_GREEN_ROOM = 12;
var LINHAS = 24;
var LIMITE_FRENTE = 46;
var MEIO_L = 28;
var MEIO_A = 14;
var ALTURA_PAREDE = 190;
var ALTURA_LAJE = 34;
var ALTURA_TORRE = 900;
var AFASTAMENTO_CAMERA = 0.8;
var ZOOM_MINIMO = 0.8;
var ZOOM_MAXIMO = 3;
var MUNDO = { x: -1000, y: -950, l: 2900, a: 1950 };
var MURAL_LOGO = { c: 3.6, z: 190, l: 256, a: 143 };
var AREA_LETREIROS = { x: 0, y: -250, l: 1500, a: 900 };
var VERSAO_ARTE = 'realista4';
var MARGEM_INFERIOR = 78;
var Z_MEZANINO = 262;
var FUNDO_MEZANINO = 3.2;
var ALTURA_PERSONAGEM = 108;
var ALTURA_ARTE = 206;
var VELOCIDADE = 1.55;
var PASSADA = 0.42;
var ESPERA_DIAGONAL_S = 3;
var ESPERA_MAXIMA_S = 8;
var MAXIMO_EM_PE = 4;
var MAXIMO_BALOES = 3;

var CORES = {
  madeira: '#5a2733', madeiraClara: '#74343f', madeiraEscura: '#3a1824',
  grafite: '#1d1b2e', grafiteClaro: '#2f2c48', grafiteEscuro: '#110f1e',
  rosa: '#ff2fa8', ciano: '#22e6ff', amarelo: '#ffc94d', roxo: '#8b5cf6', verde: '#3dff8f', ouro: '#f5c542'
};

// ---------- Planta do escritório ----------
var MOVEIS = [];

function movel(tipo, c, r, l, p, extra) {
  var item = { tipo: tipo, c: c, r: r, l: l, p: p };
  for (var chaveExtra in extra || {}) item[chaveExtra] = extra[chaveExtra];
  MOVEIS.push(item);
  return item;
}

function estacao(c, r, dono, executiva) {
  movel('cadeira', c, r, 1, 1, { dono: dono });
  movel(executiva ? 'mesaExecutiva' : 'mesa', c + 1, r - 1, 2, 3);
}

// Equipe de criação
estacao(6, 6, 'lucas');
estacao(6, 10, 'bruno');
estacao(6, 14, 'mariana');
estacao(13, 6, 'camila');
estacao(13, 10, 'thiago');
estacao(13, 14, 'caio');
estacao(20, 4, 'beatriz');

// Sala da diretoria com vidro
estacao(8, 21, 'dr_ricardo', true);
movel('divisoria', 0, 17, 13, 1, { rotulo: 'EXEC' });
movel('divisoria', 12, 18, 1, 1);
movel('divisoria', 12, 22, 1, 2);
movel('poltrona', 10, 23, 1, 1);
movel('poltrona', 11, 23, 1, 1);
movel('planta', 11, 21, 1, 1);
movel('planta', 11, 22, 1, 1);
movel('estante', 1, 18, 2, 1);
movel('aparador', 4, 23, 4, 1);
movel('planta', 0, 23, 1, 1);
movel('planta', 0, 18, 1, 1);

// Sala de reunião com vidro
movel('divisoria', 18, 14, 9, 1, { rotulo: 'WAR ROOM' });
movel('divisoria', 18, 15, 1, 1);
movel('divisoria', 18, 18, 1, 3);
movel('divisoria', 19, 20, 6, 1);
movel('divisoria', 26, 15, 1, 4);
movel('mesaReuniao', 21, 16, 3, 2);
movel('consoleWar', 20, 19, 5, 1);

// Recepção, café e parede principal
movel('aparador', 1, 0, 4, 1);
movel('aparador', 5, 0, 4, 1);
movel('balcao', 10, 0, 5, 1);
movel('planta', 15, 0, 1, 1);
movel('planta', 20, 0, 1, 1);
movel('rack', 25, 0, 1, 1);
movel('rack', 26, 0, 1, 1);

// Lounge VIP do Gordão
movel('divisoriaLounge', 27, 0, 1, 7);
movel('divisoriaLounge', 27, 11, 1, 3);
movel('freezer', 28, 0, 2, 1);
movel('prateleiraBar', 30, 0, 4, 1);
movel('caixaSom', 34, 0, 1, 1);
movel('sofa', 35, 0, 5, 2);
movel('balcaoBar', 30, 2, 5, 1);
movel('banqueta', 31, 3, 1, 1);
movel('banqueta', 33, 3, 1, 1);
movel('mesaCentro', 36, 3, 3, 1);
movel('lavaLamp', 34, 1, 1, 1);
movel('jukebox', 40, 0, 1, 1);
movel('erva', 40, 1, 1, 1);
movel('sofaVip', 41, 0, 5, 2);
movel('mesaCentro', 42, 2, 3, 1);
movel('caixaSom', 46, 0, 1, 1);
movel('poker', 46, 1, 3, 2);
movel('erva', 49, 0, 1, 1);
movel('caixaSom', 47, 0, 1, 1);
movel('lavaLamp', 48, 0, 1, 1);
movel('planta', 49, 1, 1, 1);
movel('planta', 49, 2, 1, 1);
movel('planta', 47, 7, 1, 1);
movel('planta', 39, 10, 1, 1);
movel('arcade', 28, 4, 1, 1, { cor: CORES.rosa });
movel('arcade', 28, 5, 1, 1, { cor: CORES.verde });
movel('sinuca', 30, 6, 4, 2);
movel('toca', 35, 6, 3, 1);
movel('caixaSom', 38, 5, 1, 1);
movel('pebolim', 30, 10, 3, 2);
movel('lowrider', 20, 9, 6, 3);

// Vice na decoração
movel('palmeira', 0, 2, 1, 1);
movel('palmeira', 0, 11, 1, 1);
movel('palmeira', 16, 23, 1, 1);
movel('palmeira', 26, 13, 1, 1);
movel('flamingo', 3, 3, 1, 1);
movel('prancha', 0, 4, 1, 1, { cor: CORES.rosa });
movel('prancha', 0, 5, 1, 1, { cor: CORES.ciano });
movel('planta', 0, 15, 1, 1);
movel('planta', 17, 12, 1, 1);

// Terraço com piscina em frente ao escritório
var EXTERNOS = [];

function externo(tipo, c, r, l, p, extra) {
  var item = { tipo: tipo, c: c, r: r, l: l, p: p };
  for (var chaveExtra in extra || {}) item[chaveExtra] = extra[chaveExtra];
  EXTERNOS.push(item);
}

externo('palmeira', 1, 25, 1, 1);
externo('palmeira', 17, 25, 1, 1);
externo('palmeira', 5, 31, 1, 1);
externo('espreguicadeira', 2.4, 26.4, 2, 1);
externo('espreguicadeira', 3.4, 28, 2, 1);
externo('guardaSol', 4.5, 26.5, 1, 1, { cor: CORES.rosa });
externo('espreguicadeira', 16.2, 27, 2, 1);
externo('guardaSol', 16, 28.4, 1, 1, { cor: CORES.ciano });
externo('barTiki', 9, 31.2, 3, 1.4);
externo('palmeira', -3, 26, 1, 1);
externo('palmeira', -6, 29, 1, 1);
externo('guardaSol', -1, 29, 1, 1, { cor: CORES.amarelo });
externo('espreguicadeira', 0.4, 30, 2, 1);

var bloqueadas = {};
MOVEIS.forEach(function(m) {
  for (var c = m.c; c < m.c + m.l; c++) {
    for (var r = m.r; r < m.r + m.p; r++) bloqueadas[chave(c, r)] = true;
  }
});

// Cada pessoa da equipe é uma etapa real da produção; o painel explica a função ao clicar nela
var AGENTES = [
  { id: 'dr_ricardo', nome: 'Dr. Ricardo', cargo: 'Diretoria (sua aprovação)', assento: [8, 21] },
  { id: 'camila', nome: 'Camila', cargo: 'Curadoria e Auditoria', assento: [13, 6] },
  { id: 'bruno', nome: 'Bruno', cargo: 'Olheiro de Virais', assento: [6, 10] },
  { id: 'lucas', nome: 'Lucas', cargo: 'Editor de Shorts', assento: [6, 6] },
  { id: 'mariana', nome: 'Mariana', cargo: 'Editora do Top 5', assento: [6, 14] },
  { id: 'caio', nome: 'Caio', cargo: 'T.I. e Downloads', assento: [13, 14] },
  { id: 'beatriz', nome: 'Beatriz', cargo: 'Publicação e Horários', assento: [20, 4] },
  { id: 'thiago', nome: 'Thiago', cargo: 'Roteirista e Narrador', assento: [13, 10] }
];

// Etapa da produção (texto do painel) -> quem está trabalhando nela
var TAREFAS = [
  { padrao: /Buscando os vídeos/i, agente: 'bruno', fala: '🔎 Procurando os vídeos de GTA 6 mais vistos da semana...' },
  { padrao: /Baixando o trecho/i, agente: 'caio', fala: '⬇️ Baixando só 6 min do vídeo viral, imagem e som separados.' },
  { padrao: /Conferindo o jogo/i, agente: 'camila', fala: '🔍 Conferindo se é GTA 6 de verdade na imagem.' },
  { padrao: /Transcrevendo/i, agente: 'thiago', fala: '📝 Ouvindo a fala do criador para escrever o roteiro.' },
  { padrao: /Esperando a IA/i, agente: 'thiago', fala: '⏳ A IA de roteiro caiu; esperando ela voltar. Sem narração, nada sai.' },
  { padrao: /Renderizando Short/i, agente: 'lucas', fala: '🎬 Editando o Short: gancho, legenda, narração e marca.' },
  { padrao: /Montando o Top/i, agente: 'mariana', fala: '🏆 Montando o Top 5 da semana em contagem regressiva.' },
  { padrao: /Ciclo concluído/i, agente: 'camila', fala: '✅ Auditoria feita: os vídeos novos estão na Diretoria.' },
  { padrao: /Estoque completo/i, agente: 'dr_ricardo', fala: '🔔 Estoque cheio: aprove ou rejeite os vídeos para a produção voltar.' }
];
var ultimaTarefa = '';

var PONTOS = {
  cafe: [[11, 1], [13, 1]],
  celular: [[2, 8], [3, 13], [17, 3], [24, 3], [15, 20], [29, 10], [25, 8]],
  danca: [[42, 4], [43, 5], [40, 5]],
  conversa: [[[10, 3], [11, 4]], [[17, 8], [18, 9]], [[22, 7], [23, 7]], [[14, 18], [15, 18]]],
  reuniao: [[20, 16], [20, 17], [21, 15], [22, 15], [23, 15], [21, 18], [22, 18], [23, 18]]
};

var FALAS = {
  trabalho: ['Escolhendo o melhor momento do vídeo viral.', 'Escrevendo o roteiro do próximo Short.', 'Gravando a narração do canal.',
    'Conferindo o crédito do criador na descrição.', 'Ajustando o gancho dos 3 segundos.', 'Montando a contagem do Top 5.'],
  cafe: ['☕ Um expresso duplo, por favor!', '☕ Pausa rápida pro café.', '☕ Recarregando as energias.'],
  celular: ['📱 Vendo as métricas do último Short.', '📱 Respondendo o grupo da equipe.', '📱 Olha esse meme de GTA 6!'],
  conversa: ['Essa narração ficou brabíssima!', 'Esse roteiro vai viralizar!', 'Qual foi a retenção de ontem?', 'Esse vídeo passou de 10 milhões!'],
  danca: ['🕺 Bateu a meta do dia!', '💃 Hoje tem Short viral!'],
  sinuca: ['🎱 Essa bola é minha, parceiro.', '🎱 Mesa boa é mesa ganha.', '🎱 Olha a tacada!'],
  freezer: ['🍺 Bem gelada, do jeito certo.', '🍺 Freezer do patrão nunca fica vazio.'],
  bar: ['🍹 Capricha nesse drink, chefia!', '🍹 O de sempre, por favor.'],
  dj: ['🎧 Solta o grave!', '🎧 Essa aqui é pra Vice City inteira.', '🎧 Agora a pista é minha.'],
  arcade: ['🕹️ Recorde da casa é meu.', '🕹️ Mais uma ficha!'],
  pebolim: ['⚽ Gol do Gordão!', '⚽ Segura essa, parceiro.'],
  poker: ['🃏 Pago pra ver, parceiro.', '🃏 Essa mão é minha.'],
  dancaGordao: ['🕺 Hoje o VIP tá on!', '🕺 Dança do patrão!'],
  sofa: ['💨 De boa na Green Room...', '📱 Só vendo os cortes, tranquilão.', '💨 Criatividade em dia, parceiro.', '📱 Esse Short ficou brabo!', '🎶 Abaixa o som não, tá no grave certo.']
};

var FALAS_REUNIAO = {
  dr_ricardo: 'Nada vai ao ar sem a aprovação da Diretoria.',
  camila: 'Confiro idioma, jogo e a qualidade de cada vídeo.',
  thiago: 'Transcrevo, escrevo o roteiro com a IA e narro.',
  bruno: 'Pego os vídeos de GTA 6 mais vistos da semana.',
  lucas: 'Shorts de 45 a 60 s, um por vídeo viral.',
  mariana: 'Top 5 da semana com 8min30 narrados.',
  caio: 'Baixo só 6 min de cada vídeo e cuido do computador.',
  beatriz: '1 longo às 17h e 2 Shorts às 12h e às 19h.'
};

// ---------- Rotas ----------
function chave(c, r) { return c + ',' + r; }

function dentroDoPiso(c, r) {
  if (c < 0 || r < 0 || c >= COLUNAS || r >= LINHAS) return false;
  return c < COLUNAS_CAMERA && c + r <= LIMITE_FRENTE - 2 || c >= LIMITE_FRENTE - FUNDO_GREEN_ROOM - 2 && r < FUNDO_GREEN_ROOM;
}

function celulaLivre(c, r, evitar) {
  var k = chave(c, r);
  return dentroDoPiso(c, r) && !bloqueadas[k] && !(evitar && evitar[k]);
}

// Busca o menor caminho sem atravessar móveis nem cortar quinas
function calcularRota(origem, destino, evitar) {
  var inicio = chave(origem[0], origem[1]);
  var fim = chave(destino[0], destino[1]);
  if (inicio === fim) return [];

  function estimativa(c, r) {
    var dc = Math.abs(c - destino[0]);
    var dr = Math.abs(r - destino[1]);
    return Math.max(dc, dr) + 0.414 * Math.min(dc, dr);
  }

  var abertos = [{ c: origem[0], r: origem[1], f: estimativa(origem[0], origem[1]) }];
  var custo = {};
  var veioDe = {};
  custo[inicio] = 0;

  while (abertos.length) {
    var melhor = 0;
    for (var i = 1; i < abertos.length; i++) if (abertos[i].f < abertos[melhor].f) melhor = i;
    var atual = abertos.splice(melhor, 1)[0];
    var chaveAtual = chave(atual.c, atual.r);
    if (chaveAtual === fim) {
      var rota = [];
      for (var k = fim; k !== inicio; k = veioDe[k]) rota.unshift(k.split(',').map(Number));
      return rota;
    }
    for (var dc = -1; dc <= 1; dc++) {
      for (var dr = -1; dr <= 1; dr++) {
        if (!dc && !dr) continue;
        var c = atual.c + dc;
        var r = atual.r + dr;
        var k2 = chave(c, r);
        if (k2 !== fim && !celulaLivre(c, r, evitar)) continue;
        if (!dentroDoPiso(c, r)) continue;
        if (dc && dr && (!celulaLivre(atual.c + dc, atual.r, evitar) || !celulaLivre(atual.c, atual.r + dr, evitar))) continue;
        var novoCusto = custo[chaveAtual] + (dc && dr ? 1.414 : 1);
        if (custo[k2] === undefined || novoCusto < custo[k2]) {
          custo[k2] = novoCusto;
          veioDe[k2] = chaveAtual;
          abertos.push({ c: c, r: r, f: novoCusto + estimativa(c, r) });
        }
      }
    }
  }
  return [];
}

function acessoDoAssento(ag) { return [ag.assento[0] - 1, ag.assento[1]]; }

// ---------- Comportamento ----------
var reservas = {};
var pontosReservados = {};

function sortear(lista) { return lista[Math.floor(Math.random() * lista.length)]; }

function prepararAgente(ag) {
  ag.celula = ag.assento.slice();
  ag.c = ag.assento[0] + 0.5;
  ag.r = ag.assento[1] + 0.5;
  ag.sentado = true;
  ag.ocupado = false;
  ag.rota = null;
  ag.quadro = 1;
  ag.passada = 0;
  ag.espera = 0;
  ag.paciencia = 0.8;
  ag.esperaTotal = 0;
  ag.salto = 0;
  ag.esquerda = false;
  ag.dancando = false;
  ag.balao = null;
}

function caminhar(ag, rota, aoChegar) {
  ag.sentado = false;
  ag.rota = rota;
  ag.destino = rota.length ? rota[rota.length - 1] : ag.celula;
  ag.aoChegar = aoChegar;
  ag.entrando = false;
  ag.espera = 0;
  ag.quadro = 3;
  if (!rota.length) terminarCaminhada(ag);
}

function terminarCaminhada(ag) {
  var aoChegar = ag.aoChegar;
  ag.rota = null;
  ag.aoChegar = null;
  ag.salto = 0;
  ag.quadro = 3;
  if (aoChegar) aoChegar();
}

// No passo em diagonal, as duas casas vizinhas também precisam estar livres para ninguém se cruzar
function passagemLivre(ag, proxima) {
  if (ag.esperaTotal > ESPERA_MAXIMA_S) return true;
  var dc = proxima[0] - ag.celula[0];
  var dr = proxima[1] - ag.celula[1];
  var casas = [chave(proxima[0], proxima[1])];
  if (dc && dr && ag.esperaTotal <= ESPERA_DIAGONAL_S) {
    casas.push(chave(ag.celula[0] + dc, ag.celula[1]), chave(ag.celula[0], ag.celula[1] + dr));
  }
  return casas.every(function(casa) { return !reservas[casa] || reservas[casa] === ag.id; });
}

function atualizarAgente(ag, segundos) {
  if (!ag.rota) return;
  var proxima = ag.rota[0];
  var chaveProxima = chave(proxima[0], proxima[1]);

  if (!ag.entrando) {
    if (!passagemLivre(ag, proxima)) {
      ag.espera += segundos;
      ag.esperaTotal += segundos;
      if (ag.espera > ag.paciencia) {
        ag.espera = 0;
        ag.paciencia = 0.5 + Math.random() * 0.9;
        var evitar = {};
        Object.keys(reservas).forEach(function(casa) {
          if (reservas[casa] !== ag.id) evitar[casa] = true;
        });
        var alternativa = calcularRota(ag.celula, ag.destino, evitar);
        if (alternativa.length) ag.rota = alternativa;
      }
      return;
    }
    reservas[chaveProxima] = ag.id;
    ag.entrando = true;
    ag.espera = 0;
    ag.esperaTotal = 0;
  }

  var alvoC = proxima[0] + 0.5;
  var alvoR = proxima[1] + 0.5;
  var dc = alvoC - ag.c;
  var dr = alvoR - ag.r;
  var distancia = Math.hypot(dc, dr);
  var passo = VELOCIDADE * segundos;
  if (Math.abs(dc - dr) > 0.01) ag.esquerda = dc - dr < 0;

  // A troca de pernas acompanha a distância percorrida para os pés não deslizarem
  ag.passada += Math.min(passo, distancia);
  if (ag.passada >= PASSADA) {
    ag.passada -= PASSADA;
    ag.quadro = ag.quadro === 3 ? 4 : 3;
  }
  ag.salto = Math.abs(Math.sin(ag.passada / PASSADA * Math.PI)) * 2.5;

  if (distancia <= passo) {
    ag.c = alvoC;
    ag.r = alvoR;
    var anterior = chave(ag.celula[0], ag.celula[1]);
    if (reservas[anterior] === ag.id) delete reservas[anterior];
    ag.celula = proxima;
    ag.rota.shift();
    ag.entrando = false;
    if (!ag.rota.length) terminarCaminhada(ag);
  } else {
    ag.c += dc / distancia * passo;
    ag.r += dr / distancia * passo;
  }
}

function irPara(ag, ponto, aoChegar) {
  caminhar(ag, calcularRota(ag.celula, ponto), aoChegar);
}

function sentar(ag, aoSentar) {
  if (ag.sentado) {
    if (aoSentar) aoSentar();
    return;
  }
  var rota = calcularRota(ag.celula, acessoDoAssento(ag));
  rota.push(ag.assento.slice());
  caminhar(ag, rota, function() {
    var k = chave(ag.celula[0], ag.celula[1]);
    if (reservas[k] === ag.id) delete reservas[k];
    ag.sentado = true;
    ag.quadro = 1;
    ag.esquerda = false;
    if (aoSentar) aoSentar();
  });
}

var ATIVIDADES_GORDAO = [
  { id: 'sinuca', ponto: [34, 7], quadros: ['sinuca1', 'sinuca1', 'sinuca2'], virar: true, duracao: 12, ritmo: 0.8 },
  { id: 'freezer', ponto: [29, 1], quadros: ['pegar', 'beber2', 'beber1', 'beber2', 'beber1'], virar: true, duracao: 8, ritmo: 1.5 },
  { id: 'dj', ponto: [36, 5], quadros: ['dj1', 'dj1', 'dj2'], duracao: 14, ritmo: 0.5 },
  { id: 'bar', ponto: [32, 3], quadros: ['beber2', 'beber1'], virar: true, duracao: 9, ritmo: 1.6 },
  { id: 'arcade', ponto: [29, 4], quadros: ['jogar1', 'jogar2'], virar: true, duracao: 9, ritmo: 0.35 },
  { id: 'pebolim', ponto: [31, 12], quadros: ['jogar1', 'jogar2'], duracao: 9, ritmo: 0.3 },
  { id: 'poker', ponto: [45, 2], quadros: ['jogar1', 'jogar2'], duracao: 10, ritmo: 0.9 },
  { id: 'dancaGordao', ponto: [42, 5], quadros: ['dj2', 'dj1'], dancar: true, duracao: 9, ritmo: 0.45 }
];
var SAIDAS_POR_PASSEIO = 3;
var TEMPO_NO_SOFA_S = 16;
var FORA_DA_GREEN = {};
for (var colunaFora = 0; colunaFora < 28; colunaFora++) {
  for (var linhaFora = 0; linhaFora < LINHAS; linhaFora++) FORA_DA_GREEN[chave(colunaFora, linhaFora)] = true;
}

function prepararGordao() {
  sofa.fase = 'deitado';
  sofa.deitado = true;
  sofa.tempo = TEMPO_NO_SOFA_S;
  sofa.indiceAtividade = 0;
  sofa.saidas = 0;
  sofa.atividade = null;
  sofa.acao = null;
  sofa.rota = null;
  sofa.celula = sofa.assento.slice();
  sofa.sentado = false;
  sofa.quadro = 3;
  sofa.passada = 0;
  sofa.salto = 0;
  sofa.espera = 0;
  sofa.paciencia = 0.8;
  sofa.esperaTotal = 0;
  sofa.dancando = false;
  sofa.esquerda = false;
  sofa.c = SOFA_C;
  sofa.r = SOFA_R;
}

function gordaoCaminhar(destino, aoChegar) {
  sofa.fase = 'andando';
  sofa.acao = null;
  sofa.dancando = false;
  caminhar(sofa, calcularRota(sofa.celula, destino, FORA_DA_GREEN), aoChegar);
}

function gordaoLevantar() {
  sofa.deitado = false;
  sofa.c = sofa.assento[0] + 0.5;
  sofa.r = sofa.assento[1] + 0.5;
  sofa.celula = sofa.assento.slice();
  reservas[chave(sofa.celula[0], sofa.celula[1])] = sofa.id;
  gordaoProximaAtividade();
}

function gordaoDeitar() {
  var k = chave(sofa.celula[0], sofa.celula[1]);
  if (reservas[k] === sofa.id) delete reservas[k];
  sofa.fase = 'deitado';
  sofa.deitado = true;
  sofa.atividade = null;
  sofa.tempo = TEMPO_NO_SOFA_S;
  sofa.saidas = 0;
  sofa.c = SOFA_C;
  sofa.r = SOFA_R;
  sofa.esquerda = false;
}

function gordaoProximaAtividade() {
  if (sofa.saidas >= SAIDAS_POR_PASSEIO) {
    sofa.atividade = null;
    gordaoCaminhar(sofa.assento, gordaoDeitar);
    return;
  }
  var atividade = ATIVIDADES_GORDAO[sofa.indiceAtividade % ATIVIDADES_GORDAO.length];
  sofa.indiceAtividade++;
  sofa.saidas++;
  sofa.atividade = atividade;
  gordaoCaminhar(atividade.ponto, function() {
    sofa.fase = 'acao';
    sofa.tempo = atividade.duracao;
    sofa.relogio = 0;
    sofa.esquerda = !!atividade.virar;
    sofa.dancando = !!atividade.dancar;
    falar(sofa, sortear(FALAS[atividade.id]), 3600, true);
  });
}

function atualizarGordao(segundos) {
  if (sofa.fase === 'deitado') {
    sofa.tempo -= segundos;
    if (sofa.tempo <= 0) gordaoLevantar();
  } else if (sofa.rota) {
    atualizarAgente(sofa, segundos);
  } else if (sofa.fase === 'acao') {
    sofa.tempo -= segundos;
    sofa.relogio += segundos;
    sofa.acao = sofa.atividade.quadros[Math.floor(sofa.relogio / sofa.atividade.ritmo) % sofa.atividade.quadros.length];
    if (sofa.tempo <= 0) {
      sofa.acao = null;
      sofa.dancando = false;
      gordaoProximaAtividade();
    }
  }
}

function falar(ag, texto, duracaoMs, prioridade) {
  var agora = performance.now();
  var ativos = AGENTES.concat([sofa]).filter(function(o) { return o.balao && o.balao.ate > agora; });
  var vizinho = ativos.some(function(o) { return o !== ag && Math.hypot(o.c - ag.c, o.r - ag.r) < 4.5; });
  if (!prioridade && (ativos.length >= MAXIMO_BALOES || vizinho)) return;
  ag.balao = { texto: texto, ate: agora + (duracaoMs || 4200) };
}

function reservarPonto(opcoes) {
  var livres = opcoes.filter(function(p) { return !pontosReservados[chave(p[0], p[1])]; });
  if (!livres.length) return null;
  var ponto = sortear(livres);
  pontosReservados[chave(ponto[0], ponto[1])] = true;
  return ponto;
}

function liberarPonto(ponto) {
  if (ponto) delete pontosReservados[chave(ponto[0], ponto[1])];
}

function agendar(ag, minimoMs, maximoMs) {
  clearTimeout(ag.proximaAcao);
  ag.proximaAcao = setTimeout(function() { agir(ag); }, minimoMs + Math.random() * (maximoMs - minimoMs));
}

function concluirAtividade(ag, ponto) {
  liberarPonto(ponto);
  ag.ocupado = false;
  ag.dancando = false;
  agendar(ag, 500, 1800);
}

function atividadeNoPonto(ag, opcoes, falas, duracaoMs, dancar) {
  var ponto = reservarPonto(opcoes);
  if (!ponto) {
    agendar(ag, 3000, 7000);
    return;
  }
  ag.ocupado = true;
  irPara(ag, ponto, function() {
    falar(ag, sortear(falas), duracaoMs - 500);
    ag.dancando = !!dancar;
    setTimeout(function() { concluirAtividade(ag, ponto); }, duracaoMs);
  });
}

function conversar(ag) {
  var parceiros = AGENTES.filter(function(o) { return o !== ag && !o.ocupado && o.sentado; });
  var livres = PONTOS.conversa.filter(function(par) {
    return !pontosReservados[chave(par[0][0], par[0][1])] && !pontosReservados[chave(par[1][0], par[1][1])];
  });
  if (!parceiros.length || !livres.length) {
    atividadeNoPonto(ag, PONTOS.celular, FALAS.celular, 5500);
    return;
  }
  var parceiro = sortear(parceiros);
  var par = sortear(livres);
  var chegaram = 0;
  ag.ocupado = parceiro.ocupado = true;
  pontosReservados[chave(par[0][0], par[0][1])] = pontosReservados[chave(par[1][0], par[1][1])] = true;

  function chegou() {
    chegaram++;
    if (chegaram < 2) return;
    ag.esquerda = (ag.c - ag.r) > (parceiro.c - parceiro.r);
    parceiro.esquerda = !ag.esquerda;
    falar(ag, sortear(FALAS.conversa), 3200, true);
    setTimeout(function() { falar(parceiro, sortear(FALAS.conversa), 3200, true); }, 3300);
    setTimeout(function() {
      concluirAtividade(ag, par[0]);
      concluirAtividade(parceiro, par[1]);
    }, 7000);
  }
  irPara(ag, par[0], chegou);
  irPara(parceiro, par[1], chegou);
}

function escolherAtividade(ag) {
  var sorteio = Math.random();
  if (sorteio < 0.28) atividadeNoPonto(ag, PONTOS.cafe, FALAS.cafe, 5500);
  else if (sorteio < 0.52) atividadeNoPonto(ag, PONTOS.celular, FALAS.celular, 6000);
  else if (sorteio < 0.82) conversar(ag);
  else atividadeNoPonto(ag, PONTOS.danca, FALAS.danca, 6000, true);
}

function pessoasEmPe() {
  return AGENTES.filter(function(ag) { return !ag.sentado; }).length;
}

function agir(ag) {
  if (ag.ocupado || ag.rota) {
    agendar(ag, 1500, 3000);
    return;
  }
  if (emReuniao) {
    participarDaReuniao(ag);
    return;
  }
  if (!ag.sentado) {
    if (Math.random() < 0.65) sentar(ag, function() { agendar(ag, 7000, 15000); });
    else escolherAtividade(ag);
    return;
  }
  var pendentes = (dadosServidor.pendentes || []).length;
  if (ag.id === 'dr_ricardo' && pendentes > 0 && Math.random() < 0.5) {
    falar(ag, '🔔 ' + pendentes + ' vídeo(s) aguardando aprovação!', 4500);
  }
  if (pessoasEmPe() < MAXIMO_EM_PE && Math.random() < 0.42) {
    escolherAtividade(ag);
    return;
  }
  if (Math.random() < 0.3) falar(ag, sortear(FALAS.trabalho));
  agendar(ag, 7000, 15000);
}

function participarDaReuniao(ag) {
  var ponto = reservarPonto(PONTOS.reuniao);
  if (!ponto) {
    agendar(ag, 3000, 5000);
    return;
  }
  ag.ocupado = true;
  irPara(ag, ponto, function() {
    var espera = setInterval(function() {
      if (emReuniao) return;
      clearInterval(espera);
      liberarPonto(ponto);
      ag.ocupado = false;
      sentar(ag, function() { agendar(ag, 6000, 12000); });
    }, 600);
  });
}

function abrirReuniao() {
  if (emReuniao) return;
  emReuniao = true;
  AGENTES.forEach(function(ag) {
    if (!ag.ocupado && !ag.rota) participarDaReuniao(ag);
  });
  AGENTES.forEach(function(ag, ordem) {
    setTimeout(function() { falar(ag, FALAS_REUNIAO[ag.id], 2400, true); }, 7000 + ordem * 2600);
  });
  if (typeof abrirGuiaDaEquipe === 'function') abrirGuiaDaEquipe(true);
  setTimeout(function() { emReuniao = false; }, 7000 + AGENTES.length * 2600 + 1500);
}

function abrirPainelDoAgente(id) {
  if (typeof abrirFuncaoDoAgente === 'function') abrirFuncaoDoAgente(id);
}

// O painel avisa a etapa atual: quem cuida dela conta na hora o que está fazendo
function anunciarTarefa(etapa) {
  var tarefa = TAREFAS.filter(function(t) { return t.padrao.test(etapa || ''); })[0];
  if (!tarefa || etapa === ultimaTarefa) return tarefa ? tarefa.agente : null;
  ultimaTarefa = etapa;
  var ag = AGENTES.filter(function(a) { return a.id === tarefa.agente; })[0];
  if (ag && typeof falar === 'function' && ag.balao !== undefined) falar(ag, tarefa.fala, 6500, true);
  return tarefa.agente;
}

function agenteDaEtapa(etapa) {
  var tarefa = TAREFAS.filter(function(t) { return t.padrao.test(etapa || ''); })[0];
  return tarefa ? tarefa.agente : null;
}

// ---------- Desenho ----------
var cena = { largura: 1, altura: 1, escala: 1, x: 0, y: 0, dpr: 1, tempo: 0, zoom: 1, escalaBase: 1, xBase: 0, yBase: 0, fatorArte: 1 };
var SOFA_C = 37.5;
var SOFA_R = 1.2;
var sofa = { id: 'gordao', nome: 'Gordão', cargo: 'Dono da Green Room', c: SOFA_C, r: SOFA_R, assento: [37, 2], deitado: true, fase: 'deitado', quadros: [1, 1, 2, 3, 2, 3, 2, 3], indice: 0, balao: null };
var fumacas = [];
var imagens = { poses: {}, sofa: {}, carro: {} };
var ponteiro = null;
var movimentoReduzido = false;
var ORIGEM_FUMACA = { 1: { x: -62, y: -43 }, 2: { x: -57, y: -13 }, 3: { x: -57, y: -13 } };
var ALTURA_DO_MOVEL = { freezer: 120, prateleiraBar: 130, balcaoBar: 80, pebolim: 60, guardaSol: 110, barTiki: 120, palmeira: 190, divisoria: 110, divisoriaLounge: 110, estante: 120, lowrider: 90, caixaSom: 110, arcade: 100, jukebox: 100, rack: 110, flamingo: 100, prancha: 120, erva: 90 };

function iso(c, r, z) {
  return { x: (c - r) * MEIO_L, y: (c + r) * MEIO_A - (z || 0) };
}

function poligono(ctx, pontos, cor, contorno, largura) {
  ctx.beginPath();
  pontos.forEach(function(p, i) { if (i) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y); });
  ctx.closePath();
  if (cor) { ctx.fillStyle = cor; ctx.fill(); }
  if (contorno) { ctx.strokeStyle = contorno; ctx.lineWidth = largura || 1; ctx.stroke(); }
}

function faceTopo(c, r, l, p, z) {
  return [iso(c, r, z), iso(c + l, r, z), iso(c + l, r + p, z), iso(c, r + p, z)];
}

function faceFrente(c, r, l, z, a) {
  return [iso(c, r, z), iso(c + l, r, z), iso(c + l, r, z + a), iso(c, r, z + a)];
}

function faceLado(c, r, p, z, a) {
  return [iso(c, r, z), iso(c, r + p, z), iso(c, r + p, z + a), iso(c, r, z + a)];
}

// Bloco com contorno escuro e aresta iluminada, no acabamento dos móveis isométricos
function bloco(ctx, c, r, l, p, z, altura, cores) {
  var topo = z + altura;
  poligono(ctx, faceFrente(c, r + p, l, z, altura), cores[1], 'rgba(8,4,16,0.6)', 0.8);
  poligono(ctx, faceLado(c + l, r, p, z, altura), cores[2], 'rgba(8,4,16,0.6)', 0.8);
  poligono(ctx, faceTopo(c, r, l, p, topo), cores[0], 'rgba(8,4,16,0.6)', 0.8);
  ctx.beginPath();
  var a = iso(c, r + p, topo), b = iso(c + l, r + p, topo), d = iso(c + l, r, topo);
  ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.lineTo(d.x, d.y);
  ctx.strokeStyle = 'rgba(255,255,255,0.2)';
  ctx.lineWidth = 0.8;
  ctx.stroke();
}

function brilho(ctx, cor, forca, desenhar) {
  ctx.save();
  ctx.shadowColor = cor;
  ctx.shadowBlur = forca * cena.fatorArte;
  desenhar();
  ctx.restore();
}

function linhaNeon(ctx, pontos, cor, largura) {
  brilho(ctx, cor, 12, function() {
    ctx.beginPath();
    pontos.forEach(function(p, i) { if (i) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y); });
    ctx.strokeStyle = cor;
    ctx.lineWidth = largura || 2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.stroke();
  });
}

function gerador(semente) {
  var valor = semente;
  return function() {
    valor = (valor * 16807) % 2147483647;
    return (valor - 1) / 2147483646;
  };
}

function elipse(ctx, x, y, rx, ry, cor, contorno) {
  ctx.beginPath();
  ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
  if (cor) { ctx.fillStyle = cor; ctx.fill(); }
  if (contorno) { ctx.strokeStyle = contorno; ctx.lineWidth = 1; ctx.stroke(); }
}

// Planos das paredes: x anda ao longo da parede e y desce em pixels
function noPlanoPrincipal(ctx, c, z, desenhar) {
  var p = iso(c, 0, z);
  ctx.save();
  ctx.transform(1, 0.5, 0, 1, p.x, p.y);
  desenhar();
  ctx.restore();
}

function noPlanoVidro(ctx, r, z, desenhar) {
  var p = iso(0, r, z);
  ctx.save();
  ctx.transform(1, -0.5, 0, 1, p.x, p.y);
  desenhar();
  ctx.restore();
}

function textoNeon(ctx, texto, x, y, fonte, cor, alinhamento) {
  ctx.font = fonte;
  ctx.textAlign = alinhamento || 'left';
  ctx.lineJoin = 'round';
  ctx.shadowColor = cor;
  ctx.shadowBlur = 20 * cena.fatorArte;
  ctx.strokeStyle = cor;
  ctx.lineWidth = 3.5;
  ctx.strokeText(texto, x, y);
  ctx.shadowBlur = 7 * cena.fatorArte;
  ctx.fillStyle = '#fff6fc';
  ctx.fillText(texto, x, y);
  ctx.shadowBlur = 0;
  ctx.textAlign = 'left';
}

function molduraNeon(ctx, x, y, l, a, raio, cor) {
  ctx.shadowColor = cor;
  ctx.shadowBlur = 16 * cena.fatorArte;
  ctx.strokeStyle = cor;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.roundRect(x, y, l, a, raio);
  ctx.stroke();
  ctx.shadowBlur = 0;
}

function palmeiraNeon(ctx, x, y, escala, cor) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(escala, escala);
  ctx.shadowColor = cor;
  ctx.shadowBlur = 14 * cena.fatorArte;
  ctx.strokeStyle = cor;
  ctx.lineWidth = 3.4;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(-6, 62);
  ctx.quadraticCurveTo(-12, 22, 4, -8);
  [[-44, 8], [-34, -24], [-8, -38], [28, -32], [46, -4], [38, 18]].forEach(function(f) {
    ctx.moveTo(4, -8);
    ctx.quadraticCurveTo((4 + f[0]) / 2, f[1] - 18, f[0], f[1]);
  });
  ctx.stroke();
  ctx.restore();
}

function folhaNeon(ctx, x, y, raio, cor) {
  ctx.save();
  ctx.translate(x, y);
  ctx.shadowColor = cor;
  ctx.shadowBlur = 16 * cena.fatorArte;
  ctx.strokeStyle = cor;
  ctx.lineWidth = 2.6;
  ctx.lineJoin = 'round';
  [[0, 1], [-34, 0.86], [34, 0.86], [-70, 0.66], [70, 0.66], [-108, 0.4], [108, 0.4]].forEach(function(lobo) {
    ctx.save();
    ctx.rotate(lobo[0] * Math.PI / 180);
    var comprimento = raio * lobo[1];
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.quadraticCurveTo(comprimento * 0.2, -comprimento * 0.55, 0, -comprimento);
    ctx.quadraticCurveTo(-comprimento * 0.2, -comprimento * 0.55, 0, 0);
    ctx.stroke();
    ctx.restore();
  });
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(0, raio * 0.42);
  ctx.stroke();
  ctx.restore();
}

// ---------- Céu e cidade ----------
function nuvem(ctx, x, y, l, cor) {
  ctx.fillStyle = cor;
  for (var i = 0; i < 5; i++) ctx.fillRect(x + i * l * 0.1, y - i * 3, l - i * l * 0.2, 4);
  for (var j = 1; j < 3; j++) ctx.fillRect(x + j * l * 0.08, y + j * 4, l - j * l * 0.16, 4);
}

function silhuetaPalmeira(ctx, x, y, altura, cor) {
  ctx.strokeStyle = cor;
  ctx.fillStyle = cor;
  ctx.lineCap = 'round';
  ctx.lineWidth = altura * 0.035;
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.quadraticCurveTo(x - altura * 0.12, y - altura * 0.55, x + altura * 0.06, y - altura);
  ctx.stroke();
  var topoX = x + altura * 0.06, topoY = y - altura;
  for (var i = 0; i < 9; i++) {
    var angulo = -Math.PI * (i + 0.5) / 9 * 1.25 + Math.PI * 0.12;
    var pontaX = topoX + Math.cos(angulo) * altura * 0.42;
    var pontaY = topoY + Math.sin(angulo) * altura * 0.2 + altura * 0.16;
    ctx.beginPath();
    ctx.moveTo(topoX, topoY);
    ctx.quadraticCurveTo((topoX + pontaX) / 2, Math.min(topoY, pontaY) - altura * 0.1, pontaX, pontaY);
    ctx.quadraticCurveTo((topoX + pontaX) / 2, Math.min(topoY, pontaY) - altura * 0.02, topoX, topoY);
    ctx.fill();
  }
}

function predio(ctx, x, base, l, a, aleatorio) {
  var corpo = aleatorio() > 0.5 ? '#2a1252' : '#1e0d42';
  var degraus = 1 + Math.floor(aleatorio() * 3);
  ctx.fillStyle = corpo;
  ctx.fillRect(x, base - a, l, a);
  for (var d = 1; d <= degraus; d++) ctx.fillRect(x + l * d * 0.12, base - a - d * 10, l - l * d * 0.24, 10);
  ctx.fillRect(x + l / 2 - 1, base - a - degraus * 10 - 16, 2, 16);
  var neon = ['rgba(255,47,168,0.85)', 'rgba(34,230,255,0.85)', 'rgba(255,201,77,0.8)'][Math.floor(aleatorio() * 3)];
  ctx.fillStyle = neon;
  ctx.fillRect(x, base - a, l, 2);
  ctx.fillRect(x, base - a, 2, a);
  var janela = aleatorio() > 0.5 ? 'rgba(255,214,130,0.8)' : 'rgba(120,226,255,0.7)';
  ctx.fillStyle = janela;
  for (var jx = x + 6; jx < x + l - 6; jx += 8) {
    for (var jy = base - a + 8; jy < base - 6; jy += 10) {
      if (aleatorio() > 0.55) ctx.fillRect(jx, jy, 4, 5);
    }
  }
}

function desenharCeu(ctx) {
  var L = cena.largura, A = cena.altura;
  var ceu = ctx.createLinearGradient(0, 0, 0, A * 0.46);
  ceu.addColorStop(0, '#120c38');
  ceu.addColorStop(0.3, '#46177a');
  ceu.addColorStop(0.58, '#c42a86');
  ceu.addColorStop(0.82, '#ff7a4d');
  ceu.addColorStop(1, '#ffc85e');
  ctx.fillStyle = ceu;
  ctx.fillRect(0, 0, L, A);

  var aleatorio = gerador(77);
  ctx.fillStyle = 'rgba(255,255,255,0.75)';
  for (var e = 0; e < 90; e++) ctx.fillRect(aleatorio() * L, aleatorio() * A * 0.3, 1.5, 1.5);

  var solX = L * 0.25, solY = A * 0.27, raio = A * 0.13;
  var sol = ctx.createLinearGradient(0, solY - raio, 0, solY + raio);
  sol.addColorStop(0, '#fff3a6');
  sol.addColorStop(0.55, '#ff9d4d');
  sol.addColorStop(1, '#ff2f8f');
  ctx.fillStyle = sol;
  ctx.beginPath();
  ctx.arc(solX, solY, raio, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#e8467f';
  for (var f = 0; f < 6; f++) ctx.fillRect(solX - raio, solY + raio * (0.1 + f * 0.15), raio * 2, 2 + f * 1.3);

  for (var n = 0; n < 12; n++) {
    nuvem(ctx, aleatorio() * L, A * (0.04 + aleatorio() * 0.3), 70 + aleatorio() * 150,
      n % 2 ? 'rgba(255,150,190,0.3)' : 'rgba(120,50,150,0.4)');
  }

  var horizonte = A * 0.46;
  for (var x = -10; x < L; ) {
    var largura = 30 + aleatorio() * 52;
    predio(ctx, x, horizonte, largura, A * (0.04 + aleatorio() * aleatorio() * 0.24), aleatorio);
    x += largura + 2 + aleatorio() * 8;
  }

  var mar = ctx.createLinearGradient(0, horizonte, 0, A);
  mar.addColorStop(0, '#7a2384');
  mar.addColorStop(0.5, '#34145f');
  mar.addColorStop(1, '#0d0a26');
  ctx.fillStyle = mar;
  ctx.fillRect(0, horizonte, L, A - horizonte);
  ctx.fillStyle = 'rgba(255,170,90,0.42)';
  for (var y = horizonte + 5; y < A; y += 8) {
    var meia = raio * 0.95 * (1 - (y - horizonte) / (A - horizonte)) + aleatorio() * 10;
    ctx.fillRect(solX - meia, y, meia * 2, 2);
  }
  silhuetaPalmeira(ctx, L * 0.012, A, A * 0.42, '#0f0720');
  silhuetaPalmeira(ctx, L * 0.15, A, A * 0.3, '#160a2b');
}

function desenharDirigivel(ctx) {
  var L = cena.largura, A = cena.altura;
  var x = ((cena.tempo * 9) % (L + 360)) - 180;
  var y = A * 0.14 + Math.sin(cena.tempo * 0.5) * 6;
  ctx.fillStyle = '#1b1238';
  ctx.beginPath();
  ctx.moveTo(x - 62, y);
  ctx.lineTo(x - 88, y - 16);
  ctx.lineTo(x - 88, y + 16);
  ctx.fill();
  elipse(ctx, x, y, 72, 21, '#2b1a55', '#ff2fa8');
  ctx.fillStyle = '#ffc94d';
  ctx.fillRect(x - 12, y + 19, 24, 6);
  ctx.font = '900 13px "Segoe UI", Arial, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillStyle = '#22e6ff';
  ctx.fillText('VIELA VICE', x, y + 5);
  ctx.textAlign = 'left';
}

// ---------- Piso e paredes ----------
function contornoDoPiso(z) {
  return [iso(0, 0, z), iso(COLUNAS, 0, z), iso(COLUNAS, FUNDO_GREEN_ROOM, z), iso(LIMITE_FRENTE - FUNDO_GREEN_ROOM, FUNDO_GREEN_ROOM, z),
    iso(LIMITE_FRENTE - LINHAS, LINHAS, z), iso(0, LINHAS, z)];
}

function tapete(ctx, c, r, l, p, fundo, borda) {
  poligono(ctx, faceTopo(c + 0.08, r + 0.1, l, p, 0), 'rgba(0,0,0,0.3)');
  poligono(ctx, faceTopo(c, r, l, p, 1), fundo, 'rgba(0,0,0,0.5)');
  poligono(ctx, faceTopo(c + 0.3, r + 0.3, l - 0.6, p - 0.6, 1), null, borda, 1.6);
  poligono(ctx, faceTopo(c + 0.5, r + 0.5, l - 1, p - 1, 1), null, borda, 0.7);
}

function desenharTerraco(ctx) {
  var z = -ALTURA_LAJE;
  poligono(ctx, [iso(-60, 24, z), iso(0, 24, z), iso(0, 0, z), iso(110, 0, z), iso(110, 90, z), iso(-60, 90, z)], '#1d0f38');
  for (var c = -26; c < 70; c++) {
    for (var r = 0; r < 62; r++) {
      if ((c < 0 && r < 24) || c + r > 64) continue;
      poligono(ctx, faceTopo(c, r, 1, 1, z), (c + r) % 2 ? '#2a1548' : '#351a5c', 'rgba(255,47,168,0.2)', 0.7);
    }
  }
  poligono(ctx, faceTopo(5.7, 25.7, 9.6, 4.6, z), '#43205f', 'rgba(255,47,168,0.5)', 1);
  var agua = ctx.createLinearGradient(iso(6, 26, z).x, iso(6, 26, z).y, iso(15, 30, z).x, iso(15, 30, z).y);
  agua.addColorStop(0, '#1fe0e8');
  agua.addColorStop(1, '#0a7fd0');
  poligono(ctx, faceTopo(6.2, 26.2, 8.6, 3.6, z), agua);
  linhaNeon(ctx, faceTopo(5.7, 25.7, 9.6, 4.6, z).concat([iso(5.7, 25.7, z)]), CORES.rosa, 2.2);
  EXTERNOS.forEach(function(m) {
    poligono(ctx, faceTopo(m.c + 0.15, m.r + 0.2, m.l, m.p, z), 'rgba(6,2,16,0.42)');
  });
}

function desenharPiso(ctx) {
  var fim = LIMITE_FRENTE;
  desenharTerraco(ctx);
  var canto = LIMITE_FRENTE - FUNDO_GREEN_ROOM;
  poligono(ctx, [iso(0, LINHAS, 0), iso(fim - LINHAS, LINHAS, 0), iso(fim - LINHAS, LINHAS, -ALTURA_LAJE), iso(0, LINHAS, -ALTURA_LAJE)], '#1b0e30');
  poligono(ctx, [iso(fim - LINHAS, LINHAS, 0), iso(canto, FUNDO_GREEN_ROOM, 0), iso(canto, FUNDO_GREEN_ROOM, -ALTURA_LAJE), iso(fim - LINHAS, LINHAS, -ALTURA_LAJE)], '#241238');
  poligono(ctx, [iso(canto, FUNDO_GREEN_ROOM, 0), iso(COLUNAS, FUNDO_GREEN_ROOM, 0), iso(COLUNAS, FUNDO_GREEN_ROOM, -ALTURA_LAJE), iso(canto, FUNDO_GREEN_ROOM, -ALTURA_LAJE)], '#1b0e30');
  ctx.fillStyle = 'rgba(255,214,130,0.75)';
  for (var q = 1; q < 24; q++) {
    var ponto = iso(fim - LINHAS + q * (canto - fim + LINHAS) / 24, LINHAS - q * (LINHAS - FUNDO_GREEN_ROOM) / 24, -22);
    if (q % 3) ctx.fillRect(ponto.x, ponto.y, 12, 8);
  }

  ctx.save();
  poligono(ctx, contornoDoPiso(0), '#4a1f2d');
  ctx.clip();

  var aleatorio = gerador(31);
  var tons = ['#6a2c3a', '#722f3e', '#622837', '#7b3443', '#5c2634', '#6f2e3d'];
  for (var faixa = 0; faixa < LINHAS * 2; faixa++) {
    var c = -aleatorio() * 4;
    while (c < COLUNAS) {
      var tamanho = 2.5 + aleatorio() * 3.5;
      poligono(ctx, faceTopo(c, faixa / 2, tamanho, 0.5, 0), tons[Math.floor(aleatorio() * tons.length)], 'rgba(24,8,16,0.55)', 0.7);
      c += tamanho;
    }
  }

  // Lounge com carpete roxo e losangos verdes
  poligono(ctx, faceTopo(27, 0, COLUNAS - 27, 14, 0), '#2a1244');
  ctx.strokeStyle = 'rgba(61,255,143,0.13)';
  ctx.lineWidth = 1;
  for (var d = 0; d < 40; d++) {
    var a = iso(27 + d, 0, 0), b = iso(27, d, 0), e = iso(27 + d, 14, 0), g = iso(COLUNAS, d, 0);
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.moveTo(e.x, e.y); ctx.lineTo(g.x, g.y); ctx.stroke();
  }
  // Diretoria em madeira escura e sala de reunião em porcelanato azul
  poligono(ctx, faceTopo(0, 18, 12, 6, 0), '#3a1c1a');
  for (var v = 0; v < 12; v += 1.5) poligono(ctx, faceTopo(v, 18, 1.5, 6, 0), v % 3 ? '#42211d' : '#351917', 'rgba(0,0,0,0.3)', 0.6);
  for (var mc = 19; mc < 26; mc++) {
    for (var mr = 15; mr < 20; mr++) poligono(ctx, faceTopo(mc, mr, 1, 1, 0), (mc + mr) % 2 ? '#0a1322' : '#0e1a2e', 'rgba(34,230,255,0.24)', 0.7);
  }

  tapete(ctx, 4.4, 3.6, 13.2, 13.6, 'rgba(36,18,66,0.62)', 'rgba(34,230,255,0.55)');
  tapete(ctx, 34.7, 2.1, 5, 3.3, 'rgba(18,70,48,0.9)', CORES.ouro);
  tapete(ctx, 29, 5.2, 6, 3.6, 'rgba(70,20,60,0.75)', CORES.rosa);
  poligono(ctx, faceTopo(39.8, 2.8, 6.4, 5.4, 1), '#0c0818', CORES.verde, 2.5);
  tapete(ctx, 1.6, 18.6, 8.4, 4.6, 'rgba(60,18,30,0.9)', CORES.ouro);
  var anelWar = [];
  for (var ia = 0; ia <= 48; ia++) anelWar.push(iso(22.5 + Math.cos(ia / 48 * Math.PI * 2) * 3, 17 + Math.sin(ia / 48 * Math.PI * 2) * 1.9, 1));
  linhaNeon(ctx, anelWar, CORES.ciano, 1.8);

  // Plataforma do carro
  poligono(ctx, faceTopo(19.7, 8.7, 6.6, 3.6, 1), '#17102c', CORES.rosa, 2);

  // Luz do pôr do sol entrando pelo vidro
  [2.5, 7, 12.5].forEach(function(r0) {
    var a0 = iso(0, r0, 0), b0 = iso(20, r0, 0);
    var luz = ctx.createLinearGradient(a0.x, a0.y, b0.x, b0.y);
    luz.addColorStop(0, 'rgba(255,170,90,0.34)');
    luz.addColorStop(1, 'rgba(255,120,190,0)');
    poligono(ctx, faceTopo(0, r0, 20, 2.1, 0), luz);
  });
  [[1, 12, 'rgba(255,47,168,0.2)'], [14, 13, 'rgba(34,230,255,0.13)'], [27, 13, 'rgba(61,255,143,0.16)']].forEach(function(f) {
    var a1 = iso(f[0], 0, 0), b1 = iso(f[0], 3, 0);
    var reflexo = ctx.createLinearGradient(a1.x, a1.y, b1.x, b1.y);
    reflexo.addColorStop(0, f[2]);
    reflexo.addColorStop(1, 'rgba(0,0,0,0)');
    poligono(ctx, faceTopo(f[0], 0, f[1], 3, 0), reflexo);
  });

  // Sombra de contato dos móveis
  MOVEIS.forEach(function(m) {
    if (m.tipo === 'cadeira' || m.tipo.indexOf('divisoria') === 0) return;
    poligono(ctx, faceTopo(m.c + 0.12, m.r + 0.16, m.l, m.p, 0), 'rgba(6,2,14,0.34)');
  });
  ctx.restore();

  linhaNeon(ctx, [iso(0, LINHAS, 0), iso(fim - LINHAS, LINHAS, 0), iso(canto, FUNDO_GREEN_ROOM, 0), iso(COLUNAS, FUNDO_GREEN_ROOM, 0)], CORES.rosa, 3);
  linhaNeon(ctx, [iso(0, LINHAS, -ALTURA_LAJE), iso(fim - LINHAS, LINHAS, -ALTURA_LAJE), iso(canto, FUNDO_GREEN_ROOM, -ALTURA_LAJE), iso(COLUNAS, FUNDO_GREEN_ROOM, -ALTURA_LAJE)], CORES.ciano, 2);
}

function discoDeOuro(ctx, x, y) {
  ctx.fillStyle = '#1a1020';
  ctx.fillRect(x - 25, y - 25, 50, 50);
  ctx.strokeStyle = CORES.ouro;
  ctx.lineWidth = 2.5;
  ctx.strokeRect(x - 25, y - 25, 50, 50);
  elipse(ctx, x, y, 19, 19, '#e5b53a', '#8a6410');
  elipse(ctx, x, y, 12, 12, null, '#a97f1d');
  elipse(ctx, x, y, 5, 5, '#3dff8f');
}

function rodaLowrider(ctx, x, y) {
  elipse(ctx, x, y, 34, 34, '#0e0a18', '#3a3350');
  elipse(ctx, x, y, 25, 25, '#d9dde8');
  ctx.strokeStyle = '#8a8fa5';
  ctx.lineWidth = 1;
  for (var i = 0; i < 18; i++) {
    var angulo = i * Math.PI / 9;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + Math.cos(angulo) * 25, y + Math.sin(angulo) * 25);
    ctx.stroke();
  }
  elipse(ctx, x, y, 7, 7, CORES.ouro, '#7a5a10');
}

// Pé-direito duplo: janelas altas e mezanino preenchem a tela até o topo
function desenharAndarDeCima(ctx) {
  var z = Z_MEZANINO;
  var parede = ctx.createLinearGradient(0, iso(20, 0, ALTURA_TORRE).y, 0, iso(20, 0, ALTURA_PAREDE).y);
  parede.addColorStop(0, '#1b0f38');
  parede.addColorStop(1, '#43205f');
  poligono(ctx, [iso(0, 0, ALTURA_PAREDE), iso(COLUNAS + 40, 0, ALTURA_PAREDE), iso(COLUNAS + 40, 0, ALTURA_TORRE), iso(0, 0, ALTURA_TORRE)], parede);

  noPlanoPrincipal(ctx, 0, z, function() {
    for (var i = 0; i < 17; i++) {
      var x = (4 + i * 3) * MEIO_L;
      var ceu = ctx.createLinearGradient(0, -340, 0, -40);
      ceu.addColorStop(0, '#3d1a78');
      ceu.addColorStop(0.55, '#e0337f');
      ceu.addColorStop(1, '#ffb45c');
      ctx.fillStyle = ceu;
      ctx.fillRect(x, -340, 2.3 * MEIO_L, 300);
      ctx.fillStyle = 'rgba(14,6,30,0.75)';
      ctx.fillRect(x, -92, 2.3 * MEIO_L, 52);
      ctx.fillStyle = 'rgba(255,214,130,0.8)';
      for (var j = 0; j < 7; j++) ctx.fillRect(x + 6 + j * 8, -84 + (j * 5) % 26, 4, 5);
      ctx.strokeStyle = '#2b1a44';
      ctx.lineWidth = 3;
      ctx.strokeRect(x, -340, 2.3 * MEIO_L, 300);
      ctx.beginPath();
      ctx.moveTo(x + 1.15 * MEIO_L, -340);
      ctx.lineTo(x + 1.15 * MEIO_L, -40);
      ctx.moveTo(x, -190);
      ctx.lineTo(x + 2.3 * MEIO_L, -190);
      ctx.stroke();
    }
  });

  // Piso do mezanino
  poligono(ctx, faceFrente(0, FUNDO_MEZANINO, COLUNAS, z - 16, 16), '#1b0f30');
  poligono(ctx, faceTopo(0, 0, COLUNAS, FUNDO_MEZANINO, z), '#6a2c3a', 'rgba(24,8,16,0.6)', 0.8);
  for (var c = 0; c < COLUNAS; c += 2) poligono(ctx, faceTopo(c, 0, 1, FUNDO_MEZANINO, z), '#74303f');
  linhaNeon(ctx, [iso(0, FUNDO_MEZANINO, z - 16), iso(COLUNAS, FUNDO_MEZANINO, z - 16)], CORES.rosa, 2.5);
  bloco(ctx, 25, 0.2, 4, 1, z, 14, ['#7238ad', '#4a1f78', '#401a68']);
  bloco(ctx, 25, 0.2, 4, 0.35, z + 14, 18, ['#5f2a94', '#3f1a66', '#34145a']);
  bloco(ctx, 33, 0.2, 3, 0.8, z, 30, ['#7a3a48', '#4d2230', '#3f1b27']);
  bloco(ctx, 17, 0.25, 0.7, 0.7, z, 18, ['#1ea765', '#e2559f', '#b83d80']);
  noPlanoPrincipal(ctx, 18.5, z + 205, function() {
    ctx.fillStyle = 'rgba(18,8,36,0.88)';
    ctx.fillRect(0, 0, 268, 46);
    molduraNeon(ctx, 0, 0, 268, 46, 10, CORES.amarelo);
    textoNeon(ctx, 'VICE PENTHOUSE', 134, 32, '900 25px "Segoe UI", Arial, sans-serif', CORES.amarelo, 'center');
  });
}

function desenharGradeDoMezanino(ctx) {
  var z = Z_MEZANINO;
  poligono(ctx, faceFrente(0, FUNDO_MEZANINO, COLUNAS, z, 46), 'rgba(170,235,255,0.16)');
  for (var c = 0; c <= COLUNAS; c += 2) bloco(ctx, c, FUNDO_MEZANINO - 0.05, 0.1, 0.1, z, 46, ['#b9bdd2', '#71758e', '#868aa3']);
  bloco(ctx, 0, FUNDO_MEZANINO - 0.05, COLUNAS, 0.1, z + 46, 3, ['#e8ecf5', '#9aa0b5', '#b6bbcd']);
}

function desenharParedes(ctx) {
  // Parede de vidro com as palmeiras do lado de fora
  var vidro = [iso(0, 0, 0), iso(0, LINHAS, 0), iso(0, LINHAS, ALTURA_TORRE), iso(0, 0, ALTURA_TORRE)];
  ctx.save();
  poligono(ctx, vidro, 'rgba(60,20,90,0.14)');
  ctx.clip();
  noPlanoVidro(ctx, 24, 0, function() {
    silhuetaPalmeira(ctx, 120, -2, 330, 'rgba(14,6,30,0.88)');
    silhuetaPalmeira(ctx, 360, -6, 430, 'rgba(14,6,30,0.88)');
    silhuetaPalmeira(ctx, 590, -2, 300, 'rgba(14,6,30,0.88)');
    ctx.fillStyle = 'rgba(255,255,255,0.07)';
    for (var i = 0; i < 7; i++) {
      ctx.beginPath();
      ctx.moveTo(i * 100 + 20, 0);
      ctx.lineTo(i * 100 + 60, 0);
      ctx.lineTo(i * 100 + 420, -700);
      ctx.lineTo(i * 100 + 380, -700);
      ctx.fill();
    }
  });
  ctx.restore();
  for (var r = 0; r <= LINHAS; r += 3) bloco(ctx, -0.14, r - 0.07, 0.14, 0.14, 0, ALTURA_TORRE, ['#34205a', '#20123a', '#3a2358']);
  [300, 410, 520].forEach(function(z) {
    poligono(ctx, [iso(0, 0, z), iso(0, LINHAS, z), iso(0, LINHAS, z + 5), iso(0, 0, z + 5)], '#2b1a44');
  });
  poligono(ctx, [iso(0, 0, 0), iso(0, LINHAS, 0), iso(0, LINHAS, 14), iso(0, 0, 14)], '#2b1a44');
  poligono(ctx, [iso(0, 0, 96), iso(0, LINHAS, 96), iso(0, LINHAS, 100), iso(0, 0, 100)], '#2b1a44');
  poligono(ctx, [iso(0, 0, ALTURA_PAREDE - 12), iso(0, LINHAS, ALTURA_PAREDE - 12), iso(0, LINHAS, ALTURA_PAREDE), iso(0, 0, ALTURA_PAREDE)], '#2b1a44');
  linhaNeon(ctx, [iso(0, LINHAS, ALTURA_PAREDE), iso(0, 0, ALTURA_PAREDE)], CORES.ciano, 2);
  desenharAndarDeCima(ctx);

  // Parede principal em concreto queimado
  var parede = ctx.createLinearGradient(0, iso(0, 0, ALTURA_PAREDE).y, 0, iso(27, 0, 0).y);
  parede.addColorStop(0, '#3a2054');
  parede.addColorStop(1, '#5c3268');
  poligono(ctx, [iso(0, 0, 0), iso(27, 0, 0), iso(27, 0, ALTURA_PAREDE), iso(0, 0, ALTURA_PAREDE)], parede);
  noPlanoPrincipal(ctx, 0, 0, function() {
    var ruido = gerador(19);
    for (var i = 0; i < 900; i++) {
      ctx.fillStyle = ruido() > 0.5 ? 'rgba(255,255,255,0.025)' : 'rgba(0,0,0,0.05)';
      ctx.fillRect(ruido() * 27 * MEIO_L, -ruido() * ALTURA_PAREDE, 3 + ruido() * 9, 2);
    }
    ctx.strokeStyle = 'rgba(10,4,20,0.28)';
    ctx.lineWidth = 1;
    for (var x = 4; x < 27; x += 4) {
      ctx.beginPath(); ctx.moveTo(x * MEIO_L, 0); ctx.lineTo(x * MEIO_L, -ALTURA_PAREDE); ctx.stroke();
    }
    // Prateleira de troféus sobre o aparador
    ctx.fillStyle = '#2b1420';
    ctx.fillRect(0.5 * MEIO_L, -58, 2.9 * MEIO_L, 5);
    [0.9, 1.6, 2.3, 3].forEach(function(t, i) {
      ctx.fillStyle = CORES.ouro;
      ctx.fillRect(t * MEIO_L - 5, -80 - (i % 2) * 4, 10, 12);
      ctx.fillRect(t * MEIO_L - 2, -68, 4, 7);
      ctx.fillRect(t * MEIO_L - 6, -62, 12, 4);
    });
  });

  // Área da Green Room com veludo, discos de ouro e roda cromada
  var veludo = ctx.createLinearGradient(0, iso(27, 0, ALTURA_PAREDE).y, 0, iso(COLUNAS, 0, 0).y);
  veludo.addColorStop(0, '#1d0f38');
  veludo.addColorStop(1, '#3a1460');
  poligono(ctx, [iso(27, 0, 0), iso(COLUNAS, 0, 0), iso(COLUNAS, 0, ALTURA_PAREDE), iso(27, 0, ALTURA_PAREDE)], veludo);
  noPlanoPrincipal(ctx, 27, 0, function() {
    ctx.strokeStyle = 'rgba(245,197,66,0.12)';
    ctx.lineWidth = 1;
    for (var u = -190; u < (COLUNAS - 27) * MEIO_L; u += 26) {
      ctx.beginPath(); ctx.moveTo(u, 0); ctx.lineTo(u + 190, -190); ctx.moveTo(u + 190, 0); ctx.lineTo(u, -190); ctx.stroke();
    }
    discoDeOuro(ctx, 30, -126);
    discoDeOuro(ctx, 30, -70);
    ctx.save();
    ctx.translate(336, -132);
    ctx.scale(0.72, 0.72);
    rodaLowrider(ctx, 0, 0);
    ctx.restore();
    discoDeOuro(ctx, 410, -128);
    discoDeOuro(ctx, 470, -128);
    discoDeOuro(ctx, 530, -128);
  });

  // Fachada do prédio à direita do escritório
  poligono(ctx, [iso(COLUNAS, 0, -ALTURA_LAJE), iso(COLUNAS + 40, 0, -ALTURA_LAJE), iso(COLUNAS + 40, 0, ALTURA_PAREDE), iso(COLUNAS, 0, ALTURA_PAREDE)], '#2a1548');
  noPlanoPrincipal(ctx, COLUNAS, 0, function() {
    for (var v = 0; v < 12; v++) {
      var vitrine = ctx.createLinearGradient(0, -170, 0, -30);
      vitrine.addColorStop(0, '#22e6ff');
      vitrine.addColorStop(1, '#7c2d92');
      ctx.fillStyle = vitrine;
      ctx.fillRect(14 + v * 96, -170, 74, 140);
      ctx.strokeStyle = CORES.rosa;
      ctx.lineWidth = 2;
      ctx.strokeRect(14 + v * 96, -170, 74, 140);
    }
  });

  // Porta da Ideas Room
  poligono(ctx, [iso(16.5, 0, 0), iso(19.5, 0, 0), iso(19.5, 0, 118), iso(16.5, 0, 118)], '#150c28');
  poligono(ctx, [iso(17, 0, 0), iso(19, 0, 0), iso(19, 0, 108), iso(17, 0, 108)], '#2a1648', 'rgba(255,47,168,0.5)');
  linhaNeon(ctx, [iso(16.5, 0, 0), iso(16.5, 0, 118), iso(19.5, 0, 118), iso(19.5, 0, 0)], CORES.rosa, 2);

  // Moldura do painel de vídeo
  poligono(ctx, [iso(20.8, 0, 30), iso(24.9, 0, 30), iso(24.9, 0, 132), iso(20.8, 0, 132)], '#0a0614', '#3a3350', 3);

  poligono(ctx, [iso(0, 0, 0), iso(COLUNAS, 0, 0), iso(COLUNAS, 0, 14), iso(0, 0, 14)], '#20112f');
  linhaNeon(ctx, [iso(0, 0, 14), iso(27, 0, 14)], 'rgba(34,230,255,0.7)', 1.5);
  linhaNeon(ctx, [iso(27, 0, 14), iso(COLUNAS, 0, 14)], 'rgba(61,255,143,0.8)', 1.5);
  poligono(ctx, [iso(COLUNAS, 0, 0), iso(COLUNAS, 0.3, 0), iso(COLUNAS, 0.3, ALTURA_PAREDE), iso(COLUNAS, 0, ALTURA_PAREDE)], '#1a0d2e');
}

// Logo oficial do canal em destaque na parede principal
function desenharMuralDaLogo(ctx) {
  var img = imagens.logo;
  if (!img || !img.complete || !img.naturalWidth) return;
  noPlanoPrincipal(ctx, MURAL_LOGO.c, MURAL_LOGO.z, function() {
    ctx.save();
    ctx.beginPath();
    ctx.roundRect(0, 0, MURAL_LOGO.l, MURAL_LOGO.a, 5);
    ctx.clip();
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(img, 0, 0, MURAL_LOGO.l, MURAL_LOGO.a);
    ctx.restore();
  });
}

function desenharLetreiros(ctx) {
  noPlanoPrincipal(ctx, MURAL_LOGO.c, MURAL_LOGO.z, function() {
    molduraNeon(ctx, -4, -4, MURAL_LOGO.l + 8, MURAL_LOGO.a + 8, 8, CORES.ciano);
    molduraNeon(ctx, -9, -9, MURAL_LOGO.l + 18, MURAL_LOGO.a + 18, 12, CORES.rosa);
  });
  noPlanoPrincipal(ctx, 12.9, 170, function() {
    molduraNeon(ctx, 0, 0, 96, 28, 6, CORES.ciano);
    textoNeon(ctx, 'INNOVATION', 48, 19, '800 12px "Segoe UI", Arial, sans-serif', CORES.ciano, 'center');
  });
  noPlanoPrincipal(ctx, 16.7, 170, function() {
    molduraNeon(ctx, 0, 0, 74, 42, 6, CORES.rosa);
    textoNeon(ctx, 'IDEAS', 37, 18, '800 14px "Segoe UI", Arial, sans-serif', CORES.rosa, 'center');
    textoNeon(ctx, 'ROOM', 37, 35, '800 14px "Segoe UI", Arial, sans-serif', CORES.rosa, 'center');
  });
  noPlanoPrincipal(ctx, 21, 164, function() {
    textoNeon(ctx, '● VIRAIS', 0, 18, '900 18px "Segoe UI", Arial, sans-serif', '#ff3b3b');
  });
  noPlanoPrincipal(ctx, 28.4, 182, function() {
    folhaNeon(ctx, 84, 36, 24, CORES.verde);
    textoNeon(ctx, 'Green Room', 112, 42, 'italic 900 27px "Segoe Script", "Brush Script MT", cursive', CORES.verde);
    textoNeon(ctx, 'VIP LOUNGE', 116, 62, '800 12px "Segoe UI", Arial, sans-serif', CORES.ouro);
  });
  noPlanoPrincipal(ctx, 41.5, 178, function() {
    molduraNeon(ctx, 0, 0, 150, 40, 8, CORES.roxo);
    textoNeon(ctx, 'DANCE FLOOR', 75, 27, '900 19px "Segoe UI", Arial, sans-serif', CORES.roxo, 'center');
  });
}

// ---------- Móveis ----------
function desenharMesaFixa(ctx, m) {
  var executiva = m.tipo === 'mesaExecutiva';
  var tampo = executiva ? ['#8a4a1f', '#5d2f12', '#4c250e'] : ['#7a3a48', '#4d2230', '#3f1b27'];
  var corpo = executiva ? ['#5d2f12', '#4c250e', '#3d1d0a'] : [CORES.madeira, CORES.madeiraEscura, '#31131d'];
  bloco(ctx, m.c + 0.1, m.r + 0.1, m.l - 0.2, 0.75, 0, 24, corpo);
  bloco(ctx, m.c + 0.1, m.r + m.p - 0.85, m.l - 0.2, 0.75, 0, 24, corpo);
  for (var g = 0; g < 3; g++) {
    poligono(ctx, faceFrente(m.c + 0.25 + g * 0.55, m.r + m.p - 0.1, 0.42, 5, 15), null, 'rgba(255,255,255,0.14)', 0.7);
  }
  bloco(ctx, m.c, m.r, m.l, m.p, 24, 4, tampo);
  linhaNeon(ctx, [iso(m.c, m.r + m.p, 24), iso(m.c + m.l, m.r + m.p, 24), iso(m.c + m.l, m.r, 24)], executiva ? CORES.ouro : CORES.ciano, 1.3);

  poligono(ctx, faceTopo(m.c + 0.08, m.r + 0.92, 0.9, 1.9, 28.3), '#0e0e16', 'rgba(255,255,255,0.14)', 0.6);
  bloco(ctx, m.c + 0.2, m.r + 1.02, 0.42, 1.05, 28.3, 1.8, ['#1a1a24', '#0b0b11', '#101018']);
  bloco(ctx, m.c + 0.3, m.r + 2.32, 0.2, 0.3, 28.3, 2.4, ['#22222e', '#0f0f16', '#15151e']);
  bloco(ctx, m.c + 1.45, m.r + 2.45, 0.22, 0.22, 28, 8, ['#2a1f3d', '#f1f5f9', '#cbd5e1']);
  // Gabinete gamer com lateral de vidro
  bloco(ctx, m.c + 1.18, m.r + 1.02, 0.66, 1.2, 28, 44, ['#1b1b26', '#0e0e15', '#13131c']);
  poligono(ctx, faceLado(m.c + 1.84, m.r + 1.1, 1.04, 33, 35), '#06060e', 'rgba(170,235,255,0.55)', 0.8);
  poligono(ctx, faceFrente(m.c + 1.26, m.r + 2.22, 0.5, 34, 32), '#0a0a12', 'rgba(255,255,255,0.12)', 0.6);

  [0.1, 1].forEach(function(desvio) {
    bloco(ctx, m.c + desvio + 0.32, m.r + 0.22, 0.26, 0.22, 28, 12, [CORES.grafiteClaro, CORES.grafite, CORES.grafiteEscuro]);
    bloco(ctx, m.c + desvio, m.r + 0.34, 0.9, 0.07, 38, 30, [CORES.grafiteClaro, CORES.grafite, CORES.grafiteEscuro]);
  });
  if (executiva) bloco(ctx, m.c + 1.05, m.r + 2.5, 0.28, 0.28, 28, 13, [CORES.ouro, '#d6a92e', '#b8912a']);
}

function telaGamer(ctx, c, r, z, l, a, semente) {
  var ceu = ctx.createLinearGradient(0, iso(c, r, z + a).y, 0, iso(c, r, z).y);
  ceu.addColorStop(0, '#2b1a6b');
  ceu.addColorStop(0.6, '#e0337f');
  ceu.addColorStop(1, '#ffb45c');
  poligono(ctx, faceFrente(c, r, l, z, a), ceu, '#22e6ff', 0.6);
  for (var i = 0; i < 4; i++) {
    poligono(ctx, faceFrente(c + l * (0.06 + i * 0.24), r, l * 0.15, z + a * 0.28, a * (0.16 + ((i * 37 + semente) % 5) * 0.06)), '#231445');
  }
  poligono(ctx, faceFrente(c, r, l, z, a * 0.3), '#17102c');
  var carro = (cena.tempo * 0.22 + semente * 0.37) % 1;
  poligono(ctx, faceFrente(c + l * carro * 0.84, r, l * 0.14, z + a * 0.09, a * 0.1), semente % 2 ? '#22e6ff' : '#ff2fa8');
  poligono(ctx, faceFrente(c + l * 0.06, r, l * 0.3, z + a * 0.85, a * 0.07), '#3dff8f');
  for (var e = 0; e < 3; e++) poligono(ctx, faceFrente(c + l * (0.72 + e * 0.08), r, l * 0.05, z + a * 0.84, a * 0.09), CORES.amarelo);
}

function desenharMesaViva(ctx, m) {
  var matiz = (cena.tempo * 70 + m.c * 30 + m.r * 17) % 360;
  function rgb(desvio) { return 'hsl(' + ((matiz + desvio) % 360).toFixed(0) + ',100%,60%)'; }
  telaGamer(ctx, m.c + 0.15, m.r + 0.42, 41, 0.8, 24, m.c + m.r);
  telaGamer(ctx, m.c + 1.05, m.r + 0.42, 41, 0.8, 24, m.c + m.r + 3);
  for (var linhaTecla = 0; linhaTecla < 3; linhaTecla++) {
    for (var coluna = 0; coluna < 5; coluna++) {
      poligono(ctx, faceTopo(m.c + 0.25 + linhaTecla * 0.11, m.r + 1.07 + coluna * 0.19, 0.09, 0.16, 30.2), rgb(coluna * 34 + linhaTecla * 22));
    }
  }
  poligono(ctx, faceTopo(m.c + 0.36, m.r + 2.42, 0.08, 0.1, 30.8), rgb(120));
  poligono(ctx, faceTopo(m.c + 0.08, m.r + 0.92, 0.9, 1.9, 28.4), null, rgb(60), 1);
  // Ventoinhas e placa de vídeo dentro do gabinete
  [1.34, 1.64, 1.94].forEach(function(r, i) {
    var p = iso(m.c + 1.84, m.r + r, 56);
    ctx.strokeStyle = rgb(i * 50);
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.ellipse(p.x, p.y, 3.8, 5, 0, 0, Math.PI * 2);
    ctx.stroke();
    var giro = cena.tempo * 9 + i;
    ctx.lineWidth = 0.9;
    ctx.beginPath();
    ctx.moveTo(p.x - Math.cos(giro) * 3, p.y - Math.sin(giro) * 4);
    ctx.lineTo(p.x + Math.cos(giro) * 3, p.y + Math.sin(giro) * 4);
    ctx.stroke();
  });
  poligono(ctx, faceLado(m.c + 1.84, m.r + 1.2, 0.84, 39, 4), rgb(200));
  [40, 49, 58].forEach(function(z, i) {
    var p = iso(m.c + 1.51, m.r + 2.22, z);
    ctx.strokeStyle = rgb(i * 40 + 90);
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.ellipse(p.x, p.y, 4.4, 4, 0, 0, Math.PI * 2);
    ctx.stroke();
  });
  // Fita de LED embaixo da mesa
  var a = iso(m.c, m.r + m.p, 23), b = iso(m.c + m.l, m.r + m.p, 23), d = iso(m.c + m.l, m.r, 23);
  ctx.strokeStyle = rgb(0);
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.moveTo(a.x, a.y);
  ctx.lineTo(b.x, b.y);
  ctx.lineTo(d.x, d.y);
  ctx.stroke();
}

function telaFrontal(ctx, c, r, z, l, altura, cor) {
  poligono(ctx, faceFrente(c, r, l, z, altura), '#07142b', cor, 0.8);
  ctx.lineWidth = 1.3;
  ctx.strokeStyle = cor;
  ctx.globalAlpha = 0.9;
  for (var i = 1; i <= 4; i++) {
    var fase = (Math.sin(cena.tempo * 1.2 + i * 2.1 + c * 3) + 1) / 2;
    var a = iso(c + l * 0.1, r, z + altura - i * altura / 5.2);
    var b = iso(c + l * (0.3 + 0.58 * fase), r, z + altura - i * altura / 5.2);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  ctx.globalAlpha = 1;
}

function desenharCadeira(ctx, m) {
  var centro = iso(m.c + 0.5, m.r + 0.5, 2);
  ctx.strokeStyle = '#2f2c48';
  ctx.lineWidth = 2.4;
  for (var i = 0; i < 5; i++) {
    var angulo = i * Math.PI * 0.4;
    ctx.beginPath();
    ctx.moveTo(centro.x, centro.y);
    ctx.lineTo(centro.x + Math.cos(angulo) * 15, centro.y + Math.sin(angulo) * 7.5);
    ctx.stroke();
  }
  bloco(ctx, m.c + 0.44, m.r + 0.44, 0.12, 0.12, 2, 14, [CORES.grafiteClaro, CORES.grafite, CORES.grafiteEscuro]);
  bloco(ctx, m.c + 0.18, m.r + 0.18, 0.64, 0.64, 16, 6, ['#4a3478', '#31225a', '#281c4a']);
  bloco(ctx, m.c + 0.12, m.r + 0.18, 0.13, 0.64, 22, 32, ['#4a3478', '#31225a', '#3d2b66']);
}

function desenharPoltrona(ctx, m) {
  bloco(ctx, m.c + 0.1, m.r + 0.1, 0.8, 0.8, 0, 16, ['#7a1f3d', '#54142a', '#451022']);
  bloco(ctx, m.c + 0.72, m.r + 0.1, 0.18, 0.8, 16, 24, ['#8f2849', '#5f1830', '#501226']);
  bloco(ctx, m.c + 0.1, m.r + 0.1, 0.62, 0.15, 16, 10, ['#8f2849', '#5f1830', '#501226']);
}

function vaso(ctx, m, cores) {
  bloco(ctx, m.c + 0.24, m.r + 0.24, 0.52, 0.52, 0, 18, cores);
  bloco(ctx, m.c + 0.2, m.r + 0.2, 0.6, 0.6, 18, 3, [ '#1b120e', cores[1], cores[2]]);
}

function desenharPlanta(ctx, m) {
  vaso(ctx, m, ['#f2e9dc', '#e2559f', '#b83d80']);
  var base = iso(m.c + 0.5, m.r + 0.5, 21);
  ctx.lineCap = 'round';
  for (var i = 0; i < 11; i++) {
    var angulo = -Math.PI / 2 + (i - 5) * 0.27;
    var comprimento = 26 + (i % 3) * 8;
    ctx.strokeStyle = i % 2 ? '#1ea765' : '#2fce7f';
    ctx.lineWidth = 4.5;
    ctx.beginPath();
    ctx.moveTo(base.x, base.y);
    ctx.quadraticCurveTo(base.x + Math.cos(angulo) * comprimento * 0.5, base.y + Math.sin(angulo) * comprimento,
      base.x + Math.cos(angulo) * comprimento, base.y + Math.sin(angulo) * comprimento * 0.9 + 8);
    ctx.stroke();
  }
}

function desenharErva(ctx, m) {
  vaso(ctx, m, ['#2a1a10', '#d9a520', '#a87c12']);
  var base = iso(m.c + 0.5, m.r + 0.5, 21);
  ctx.strokeStyle = '#1b7f43';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(base.x, base.y);
  ctx.lineTo(base.x, base.y - 58);
  ctx.stroke();
  [[-46, 14], [-34, 26], [-20, 18], [-58, 11]].forEach(function(nivel) {
    [-1, 1].forEach(function(lado) {
      var x = base.x + lado * nivel[1], y = base.y + nivel[0];
      for (var i = -2; i <= 2; i++) {
        ctx.strokeStyle = i % 2 ? '#2fce7f' : '#1ea765';
        ctx.lineWidth = 2.2;
        ctx.beginPath();
        ctx.moveTo(base.x, base.y + nivel[0] + 6);
        ctx.lineTo(x + lado * i * 3, y + Math.abs(i) * 3 - 4);
        ctx.stroke();
      }
    });
  });
}

function desenharPalmeira(ctx, m) {
  bloco(ctx, m.c + 0.14, m.r + 0.14, 0.72, 0.72, 0, 20, ['#2b2942', '#22d3ee', '#0e9fb8']);
  var base = iso(m.c + 0.5, m.r + 0.5, 20);
  var topo = { x: base.x + 10, y: base.y - 132 };
  for (var i = 0; i < 12; i++) {
    var t = i / 12, t2 = (i + 1) / 12;
    var x = base.x + 10 * t * t - 8 * Math.sin(t * Math.PI), y = base.y - 132 * t;
    var x2 = base.x + 10 * t2 * t2 - 8 * Math.sin(t2 * Math.PI), y2 = base.y - 132 * t2;
    ctx.strokeStyle = i % 2 ? '#7a4a30' : '#5e3722';
    ctx.lineWidth = 9 - t * 3;
    ctx.lineCap = 'butt';
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x2, y2); ctx.stroke();
  }
  ctx.lineCap = 'round';
  for (var f = 0; f < 11; f++) {
    var angulo = f / 11 * Math.PI * 2;
    var pontaX = topo.x + Math.cos(angulo) * 68;
    var pontaY = topo.y + Math.sin(angulo) * 22 + 30;
    ctx.strokeStyle = f % 2 ? '#0f8f52' : '#19c777';
    ctx.lineWidth = 7;
    ctx.beginPath();
    ctx.moveTo(topo.x, topo.y);
    ctx.quadraticCurveTo(topo.x + Math.cos(angulo) * 38, topo.y + Math.sin(angulo) * 12 - 24, pontaX, pontaY);
    ctx.stroke();
  }
  elipse(ctx, topo.x - 5, topo.y + 4, 5, 5, '#6b3f2a');
  elipse(ctx, topo.x + 6, topo.y + 5, 5, 5, '#7a4a30');
}

function desenharSofa(ctx, m) {
  bloco(ctx, m.c, m.r, m.l, m.p, 0, 18, ['#4b1d78', '#32124f', '#3e1760']);
  bloco(ctx, m.c, m.r, m.l, 0.55, 18, 36, ['#5f2a94', '#3f1a66', '#34145a']);
  for (var i = 0; i < 4; i++) bloco(ctx, m.c + 0.45 + i * 1.03, m.r + 0.55, 1, m.p - 0.6, 18, 6, ['#7238ad', '#4a1f78', '#401a68']);
  bloco(ctx, m.c, m.r + 0.55, 0.42, m.p - 0.55, 18, 16, ['#5f2a94', '#3f1a66', '#34145a']);
  bloco(ctx, m.c + m.l - 0.42, m.r + 0.55, 0.42, m.p - 0.55, 18, 16, ['#5f2a94', '#3f1a66', '#34145a']);
  bloco(ctx, m.c + 0.5, m.r + 0.6, 0.6, 0.65, 24, 8, ['#3dff8f', '#1f9d5c', '#178049']);
  linhaNeon(ctx, [iso(m.c, m.r + m.p, 1), iso(m.c + m.l, m.r + m.p, 1), iso(m.c + m.l, m.r, 1)], CORES.verde, 2.2);
  linhaNeon(ctx, [iso(m.c, m.r, 54), iso(m.c + m.l, m.r, 54)], CORES.ouro, 1.6);
}

function desenharGordao(ctx) {
  if (!sofa.deitado) return;
  var img = imagens.sofa[sofa.quadros[sofa.indice]];
  if (!img || !img.complete) return;
  var escala = ALTURA_PERSONAGEM / ALTURA_ARTE;
  var p = iso(SOFA_C, SOFA_R, 30);
  ctx.save();
  ctx.translate(p.x, p.y);
  ctx.rotate(Math.atan2(MEIO_A, MEIO_L));
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(img, -img.width * escala / 2, -(112 / 181) * img.height * escala, img.width * escala, img.height * escala);
  ctx.restore();
}

function desenharBalcao(ctx, m) {
  bloco(ctx, m.c, m.r, m.l, m.p, 0, 36, ['#f0ecf7', '#3a2552', '#2f1e45']);
  linhaNeon(ctx, [iso(m.c, m.r + m.p, 18), iso(m.c + m.l, m.r + m.p, 18)], CORES.ciano, 1.6);
  bloco(ctx, m.c + 1.1, m.r + 0.2, 0.9, 0.6, 36, 28, ['#30304a', '#c8ccdc', '#a2a6be']);
  bloco(ctx, m.c + 1.3, m.r + 0.65, 0.5, 0.16, 44, 5, ['#1b1a2b', '#1b1a2b', '#1b1a2b']);
  [2.6, 3, 3.4].forEach(function(x, i) {
    bloco(ctx, m.c + x, m.r + 0.35, 0.22, 0.22, 36, 9, ['#2a1f3d', ['#ff7ad9', '#22e6ff', '#ffc94d'][i], '#b98ab0']);
  });
}

function desenharBalcaoVivo(ctx, m) {
  var vapor = iso(m.c + 1.5, m.r + 0.5, 68);
  ctx.strokeStyle = 'rgba(255,255,255,0.45)';
  ctx.lineWidth = 2;
  for (var i = 0; i < 2; i++) {
    ctx.beginPath();
    ctx.moveTo(vapor.x + i * 8, vapor.y);
    ctx.quadraticCurveTo(vapor.x + i * 8 + Math.sin(cena.tempo * 2 + i) * 7, vapor.y - 10, vapor.x + i * 8, vapor.y - 20);
    ctx.stroke();
  }
}

function desenharEstante(ctx, m) {
  bloco(ctx, m.c, m.r, m.l, m.p, 0, 100, [CORES.madeiraClara, CORES.madeira, CORES.madeiraEscura]);
  var livros = ['#22e6ff', '#ff2fa8', '#ffc94d', '#8b5cf6', '#3dff8f', '#f97316'];
  for (var prateleira = 0; prateleira < 3; prateleira++) {
    var z = 12 + prateleira * 30;
    poligono(ctx, faceFrente(m.c + 0.1, m.r + m.p, m.l - 0.2, z, 24), '#1a0d18');
    for (var i = 0; i < 10; i++) {
      var inicio = m.c + 0.16 + i * 0.17;
      poligono(ctx, faceFrente(inicio, m.r + m.p, 0.13, z, 15 + (i * 7) % 7), livros[(i + prateleira * 2 + m.c) % livros.length]);
    }
  }
}

function desenharAparador(ctx, m) {
  bloco(ctx, m.c, m.r, m.l, m.p, 0, 30, ['#7a3a48', '#4d2230', '#3f1b27']);
  for (var i = 0; i < m.l; i++) poligono(ctx, faceFrente(m.c + i + 0.08, m.r + m.p, 0.84, 5, 21), null, 'rgba(245,197,66,0.45)', 0.8);
  bloco(ctx, m.c + 0.5, m.r + 0.3, 0.3, 0.3, 30, 16, [CORES.ouro, '#d6a92e', '#b8912a']);
  bloco(ctx, m.c + 2.2, m.r + 0.25, 0.9, 0.5, 30, 3, ['#ff2fa8', '#a81870', '#8d125d']);
}

function desenharArcade(ctx, m) {
  bloco(ctx, m.c + 0.08, m.r + 0.08, 0.84, 0.84, 0, 76, ['#2a1c46', '#33214f', '#21153a']);
  linhaNeon(ctx, [iso(m.c + 0.08, m.r + 0.92, 76), iso(m.c + 0.92, m.r + 0.92, 76), iso(m.c + 0.92, m.r + 0.08, 76)], m.cor, 1.8);
  bloco(ctx, m.c + 0.15, m.r + 0.92, 0.7, 0.14, 28, 5, ['#14101f', '#14101f', '#14101f']);
  elipse(ctx, iso(m.c + 0.3, m.r + 1, 33).x, iso(m.c + 0.3, m.r + 1, 33).y, 2.5, 1.5, '#ff3b3b');
}

function desenharRack(ctx, m) {
  bloco(ctx, m.c + 0.06, m.r + 0.05, 0.88, 0.9, 0, 96, [CORES.grafiteClaro, CORES.grafite, CORES.grafiteEscuro]);
  for (var i = 0; i < 7; i++) poligono(ctx, faceFrente(m.c + 0.14, m.r + 0.95, 0.72, 10 + i * 12, 9), '#0d0c18', 'rgba(255,255,255,0.08)', 0.6);
}

function desenharRackVivo(ctx, m) {
  for (var i = 0; i < 7; i++) {
    var aceso = Math.sin(cena.tempo * 3 + i * 1.9 + m.c) > -0.2;
    var p = iso(m.c + 0.2, m.r + 0.95, 13 + i * 12);
    ctx.fillStyle = aceso ? (i % 2 ? '#3dff8f' : '#22e6ff') : '#334155';
    ctx.fillRect(p.x, p.y, 7, 3);
  }
}

function desenharJukebox(ctx, m) {
  bloco(ctx, m.c + 0.08, m.r + 0.08, 0.84, 0.84, 0, 66, ['#7c2d92', '#5b1f70', '#4a185c']);
  poligono(ctx, faceFrente(m.c + 0.2, m.r + 0.92, 0.6, 26, 28), '#1a0d2e', CORES.ouro, 1);
}

function desenharJukeboxViva(ctx, m) {
  var cor = 'hsl(' + ((cena.tempo * 40) % 360) + ',95%,62%)';
  ctx.strokeStyle = cor;
  ctx.lineWidth = 2;
  poligono(ctx, faceFrente(m.c + 0.14, m.r + 0.92, 0.72, 8, 52), null, cor, 2);
}

function desenharCaixaSom(ctx, m) {
  bloco(ctx, m.c + 0.08, m.r + 0.08, 0.84, 0.84, 0, 92, ['#201a30', '#17121f', '#100c18']);
  poligono(ctx, faceFrente(m.c + 0.08, m.r + 0.92, 0.84, 0, 92), null, CORES.ouro, 1);
}

function desenharCaixaSomViva(ctx, m) {
  var tocando = sofa.fase === 'acao' && sofa.atividade && sofa.atividade.id === 'dj';
  var batida = 1 + Math.max(0, Math.sin(cena.tempo * (tocando ? 13 : 7.5))) * (tocando ? 0.2 : 0.09);
  [[0.5, 28, 15], [0.5, 66, 10]].forEach(function(cone) {
    var p = iso(m.c + cone[0], m.r + 0.92, cone[1]);
    elipse(ctx, p.x, p.y, cone[2] * batida * 0.82, cone[2] * batida, '#37304a', CORES.ouro);
    elipse(ctx, p.x, p.y, cone[2] * 0.3, cone[2] * 0.36, '#0d0a16');
  });
}

function desenharLavaLamp(ctx, m) {
  bloco(ctx, m.c + 0.34, m.r + 0.34, 0.32, 0.32, 0, 12, [CORES.ouro, '#b8912a', '#9a7720']);
}

function desenharLavaLampViva(ctx, m) {
  var p = iso(m.c + 0.5, m.r + 0.5, 12);
  var fundo = ctx.createLinearGradient(0, p.y - 44, 0, p.y);
  fundo.addColorStop(0, 'rgba(139,92,246,0.85)');
  fundo.addColorStop(1, 'rgba(61,255,143,0.85)');
  ctx.fillStyle = fundo;
  ctx.beginPath();
  ctx.roundRect(p.x - 8, p.y - 44, 16, 44, 7);
  ctx.fill();
  [0, 1.7, 3.4].forEach(function(fase) {
    var y = p.y - 22 + Math.sin(cena.tempo * 0.8 + fase + m.c) * 16;
    elipse(ctx, p.x + Math.sin(fase) * 2, y, 4.5, 6, 'rgba(255,240,140,0.9)');
  });
}

function desenharMesaCentro(ctx, m) {
  bloco(ctx, m.c + 0.25, m.r + 0.2, m.l - 0.5, m.p - 0.4, 0, 12, ['#3b2a18', '#2a1d10', '#21170c']);
  bloco(ctx, m.c, m.r, m.l, m.p, 12, 3, ['rgba(255,214,120,0.5)', '#b8912a', '#9a7720']);
  var cinzeiro = iso(m.c + 0.8, m.r + 0.5, 15);
  elipse(ctx, cinzeiro.x, cinzeiro.y, 11, 6, '#0f0b16', CORES.ouro);
  ctx.fillStyle = '#f4f0e2';
  ctx.fillRect(cinzeiro.x - 3, cinzeiro.y - 2, 9, 2);
  bloco(ctx, m.c + 1.7, m.r + 0.3, 0.3, 0.3, 15, 12, [CORES.ouro, '#d6a92e', '#b8912a']);
  bloco(ctx, m.c + 2.25, m.r + 0.28, 0.5, 0.42, 15, 2, ['#3dff8f', '#1f9d5c', '#178049']);
}

function desenharSinuca(ctx, m) {
  [[0.1, 0.1], [m.l - 0.4, 0.1], [0.1, m.p - 0.4], [m.l - 0.4, m.p - 0.4]].forEach(function(p) {
    bloco(ctx, m.c + p[0], m.r + p[1], 0.3, 0.3, 0, 22, ['#3a1a10', '#2a120a', '#210e08']);
  });
  bloco(ctx, m.c, m.r, m.l, m.p, 22, 8, ['#5d2f12', '#4c250e', '#3d1d0a']);
  poligono(ctx, faceTopo(m.c + 0.2, m.r + 0.2, m.l - 0.4, m.p - 0.4, 30), '#128a55');
  [['#ffc94d', 1, 0.6], ['#ff2fa8', 1.7, 1.2], ['#22e6ff', 2.4, 0.8], ['#fff', 3.1, 1.3], ['#111', 2.1, 1.5]].forEach(function(b) {
    var p = iso(m.c + b[1], m.r + b[2], 32);
    elipse(ctx, p.x, p.y, 3.2, 2.4, b[0], 'rgba(0,0,0,0.5)');
  });
}

function desenharToca(ctx, m) {
  bloco(ctx, m.c, m.r, m.l, m.p, 0, 30, ['#201a30', '#17121f', '#100c18']);
  linhaNeon(ctx, [iso(m.c, m.r + m.p, 16), iso(m.c + m.l, m.r + m.p, 16)], CORES.roxo, 1.6);
  bloco(ctx, m.c + 0.1, m.r + 0.1, m.l - 0.2, m.p - 0.2, 30, 3, ['#2f2c48', '#1b1a2b', '#11101d']);
}

function desenharTocaViva(ctx, m) {
  [0.7, 2.3].forEach(function(x) {
    var p = iso(m.c + x, m.r + 0.5, 33);
    elipse(ctx, p.x, p.y, 15, 7.5, '#0a0812', '#555070');
    var angulo = cena.tempo * 3 + x;
    ctx.strokeStyle = CORES.verde;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
    ctx.lineTo(p.x + Math.cos(angulo) * 13, p.y + Math.sin(angulo) * 6.5);
    ctx.stroke();
  });
}

function desenharDivisoria(ctx, m) {
  var aoLongo = m.l >= m.p;
  var c = m.c + (aoLongo ? 0 : 0.42), r = m.r + (aoLongo ? 0.42 : 0);
  var l = aoLongo ? m.l : 0.16, p = aoLongo ? 0.16 : m.p;
  var cor = m.tipo === 'divisoriaLounge' ? CORES.verde : CORES.ciano;
  bloco(ctx, c, r, l, p, 0, 7, ['#2f2c48', '#1d1b2e', '#141222']);
  var pontos = aoLongo ? faceFrente(c, r + p, l, 7, 72) : faceLado(c + l, r, p, 7, 72);
  poligono(ctx, pontos, 'rgba(170,235,255,0.14)');
  bloco(ctx, c, r, l, p, 79, 3, ['#d8dcef', '#8c90aa', '#a7abc4']);
  var total = aoLongo ? m.l : m.p;
  for (var i = 0; i <= total; i += 2) {
    if (aoLongo) bloco(ctx, c + Math.min(i, total - 0.1), r, 0.1, p, 7, 72, ['#b9bdd2', '#71758e', '#868aa3']);
    else bloco(ctx, c, r + Math.min(i, total - 0.1), l, 0.1, 7, 72, ['#b9bdd2', '#71758e', '#868aa3']);
  }
  linhaNeon(ctx, aoLongo ? [iso(c, r + p, 7), iso(c + l, r + p, 7)] : [iso(c + l, r, 7), iso(c + l, r + p, 7)], cor, 1.4);
  if (m.rotulo) {
    var p0 = iso(c + 0.5, r + p, 72);
    ctx.save();
    ctx.transform(1, 0.5, 0, 1, p0.x, p0.y);
    textoNeon(ctx, m.rotulo, 0, 0, '900 22px "Segoe UI", Arial, sans-serif', m.rotulo === 'EXEC' ? CORES.ouro : CORES.ciano);
    ctx.restore();
  }
}

function desenharMesaReuniao(ctx, m) {
  bloco(ctx, m.c + 0.8, m.r + 0.45, m.l - 1.6, m.p - 0.9, 0, 22, ['#1b2238', '#0e1424', '#121a2e']);
  bloco(ctx, m.c - 0.14, m.r - 0.14, m.l + 0.28, m.p + 0.28, 22, 6, ['#172036', '#0a1020', '#0e1528']);
  poligono(ctx, faceTopo(m.c, m.r, m.l, m.p, 28.4), '#04101d', CORES.ciano, 1.2);
  var z = 28.6;
  for (var g = 1; g < 6; g++) poligono(ctx, [iso(m.c + g * m.l / 6, m.r, z), iso(m.c + g * m.l / 6, m.r + m.p, z)], null, 'rgba(34,230,255,0.22)', 0.6);
  for (var h = 1; h < 4; h++) poligono(ctx, [iso(m.c, m.r + h * m.p / 4, z), iso(m.c + m.l, m.r + h * m.p / 4, z)], null, 'rgba(34,230,255,0.22)', 0.6);
  poligono(ctx, [iso(m.c + 0.35, m.r + 0.3, z), iso(m.c + 1.2, m.r + 0.18, z), iso(m.c + 1.55, m.r + 0.75, z), iso(m.c + 1.05, m.r + 1.55, z), iso(m.c + 0.45, m.r + 1.25, z)], 'rgba(61,255,143,0.32)', CORES.verde, 0.9);
  poligono(ctx, [iso(m.c + 1.95, m.r + 0.5, z), iso(m.c + 2.65, m.r + 0.42, z), iso(m.c + 2.75, m.r + 1.2, z), iso(m.c + 2.15, m.r + 1.55, z)], 'rgba(255,47,168,0.3)', CORES.rosa, 0.9);
  [0.5, 1.5, 2.5].forEach(function(x) {
    bloco(ctx, m.c + x - 0.16, m.r + m.p - 0.02, 0.32, 0.12, 28, 1.2, ['#7fe9ff', '#1b2238', '#1b2238']);
    bloco(ctx, m.c + x - 0.16, m.r - 0.1, 0.32, 0.12, 28, 1.2, ['#7fe9ff', '#1b2238', '#1b2238']);
  });
  linhaNeon(ctx, faceTopo(m.c - 0.14, m.r - 0.14, m.l + 0.28, m.p + 0.28, 28).concat([iso(m.c - 0.14, m.r - 0.14, 28)]), CORES.ciano, 1.6);
}

function desenharMesaReuniaoViva(ctx, m) {
  var centro = iso(m.c + m.l / 2, m.r + m.p / 2, 29);
  var pulso = 0.55 + Math.sin(cena.tempo * 2) * 0.2;
  [[0.8, 0.8], [1.2, 1.2], [2.3, 0.9], [2.45, 1.3], [0.7, 0.45]].forEach(function(b, i) {
    var p = iso(m.c + b[0], m.r + b[1], 29);
    var fase = (cena.tempo * 0.8 + i * 0.27) % 1;
    ctx.strokeStyle = 'rgba(255,201,77,' + (1 - fase).toFixed(3) + ')';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.ellipse(p.x, p.y, 2 + fase * 9, 1 + fase * 4.5, 0, 0, Math.PI * 2);
    ctx.stroke();
    elipse(ctx, p.x, p.y, 1.8, 1.1, CORES.amarelo);
  });
  var feixe = ctx.createLinearGradient(0, centro.y - 62, 0, centro.y);
  feixe.addColorStop(0, 'rgba(34,230,255,0)');
  feixe.addColorStop(1, 'rgba(34,230,255,' + (pulso * 0.42).toFixed(3) + ')');
  ctx.fillStyle = feixe;
  ctx.beginPath();
  ctx.moveTo(centro.x - 12, centro.y);
  ctx.lineTo(centro.x - 26, centro.y - 62);
  ctx.lineTo(centro.x + 26, centro.y - 62);
  ctx.lineTo(centro.x + 12, centro.y);
  ctx.fill();
  [0, 1, 2].forEach(function(i) {
    var y = centro.y - 22 - i * 15 + Math.sin(cena.tempo * 1.5 + i) * 2;
    ctx.strokeStyle = 'rgba(127,233,255,' + (0.75 - i * 0.18).toFixed(3) + ')';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.ellipse(centro.x, y, 13 + i * 5, 4 + i * 1.6, 0, cena.tempo * (i % 2 ? 1 : -1), cena.tempo * (i % 2 ? 1 : -1) + 4.6);
    ctx.stroke();
  });
  ctx.font = '900 21px "Segoe UI", Arial, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillStyle = 'rgba(255,240,170,' + (pulso + 0.35).toFixed(3) + ')';
  ctx.fillText('6★', centro.x, centro.y - 36 + Math.sin(cena.tempo * 1.4) * 3);
  ctx.textAlign = 'left';
}

function painelWar(ctx, c, r, l, tipo) {
  var z = 14, a = 50;
  poligono(ctx, faceFrente(c - 0.05, r, l + 0.1, z - 2, a + 4), '#1b2238', '#475569', 0.8);
  poligono(ctx, faceFrente(c, r, l, z, a), '#050d1c', CORES.ciano, 0.8);
  var i;
  if (tipo === 'mapa') {
    for (i = 1; i < 6; i++) poligono(ctx, [iso(c + l * i / 6, r, z), iso(c + l * i / 6, r, z + a)], null, 'rgba(34,230,255,0.25)', 0.5);
    for (i = 1; i < 4; i++) poligono(ctx, [iso(c, r, z + a * i / 4), iso(c + l, r, z + a * i / 4)], null, 'rgba(34,230,255,0.25)', 0.5);
    poligono(ctx, [iso(c + l * 0.2, r, z + a * 0.3), iso(c + l * 0.42, r, z + a * 0.78), iso(c + l * 0.68, r, z + a * 0.66), iso(c + l * 0.8, r, z + a * 0.22)], 'rgba(61,255,143,0.3)', CORES.verde, 0.9);
    var alvo = iso(c + l * (0.5 + Math.sin(cena.tempo * 0.7) * 0.22), r, z + a * (0.5 + Math.cos(cena.tempo * 0.9) * 0.18));
    elipse(ctx, alvo.x, alvo.y, 2.4, 2.4, '#ff3b3b');
  } else if (tipo === 'dados') {
    for (i = 0; i < 8; i++) {
      var altura = a * (0.22 + (Math.sin(cena.tempo * 1.2 + i * 0.8) + 1) * 0.28);
      poligono(ctx, faceFrente(c + l * (0.07 + i * 0.112), r, l * 0.075, z + 4, altura), i % 2 ? CORES.ciano : CORES.rosa);
    }
  } else {
    poligono(ctx, faceFrente(c + l * 0.08, r, l * 0.84, z + a * 0.3, a * 0.56), '#2a1148', '#ff3b3b', 0.8);
    for (i = 0; i < 3; i++) poligono(ctx, faceFrente(c + l * 0.08, r, l * (0.35 + ((i * 3 + Math.floor(cena.tempo)) % 5) * 0.1), z + 3 + i * 4.4, 2), '#7fe9ff');
    if (Math.sin(cena.tempo * 5) > -0.4) {
      var ao = iso(c + l * 0.16, r, z + a * 0.76);
      elipse(ctx, ao.x, ao.y, 2.6, 2.6, '#ff3b3b');
    }
  }
}

function desenharDivisoriaViva(ctx, m) {
  if (m.rotulo !== 'WAR ROOM') return;
  painelWar(ctx, 19.3, m.r + 0.95, 2.1, 'mapa');
  painelWar(ctx, 21.75, m.r + 0.95, 1.9, 'dados');
  painelWar(ctx, 24, m.r + 0.95, 1.9, 'aovivo');
}

function desenharConsoleWar(ctx, m) {
  bloco(ctx, m.c, m.r + 0.1, m.l, m.p - 0.15, 0, 30, ['#172036', '#0a1020', '#0e1528']);
  linhaNeon(ctx, [iso(m.c, m.r + m.p - 0.05, 6), iso(m.c + m.l, m.r + m.p - 0.05, 6)], CORES.ciano, 1.4);
}

function desenharConsoleWarVivo(ctx, m) {
  for (var i = 0; i < m.l; i++) telaFrontal(ctx, m.c + i + 0.1, m.r + m.p - 0.04, 10, 0.8, 16, i % 2 ? CORES.ciano : CORES.verde);
}

function desenharFlamingo(ctx, m) {
  var p = iso(m.c + 0.5, m.r + 0.5, 0);
  bloco(ctx, m.c + 0.3, m.r + 0.3, 0.4, 0.4, 0, 5, ['#2f2c48', '#1d1b2e', '#141222']);
  ctx.save();
  ctx.translate(p.x, p.y - 6);
  ctx.shadowColor = CORES.rosa;
  ctx.shadowBlur = 12 * cena.fatorArte;
  ctx.strokeStyle = '#ff6fc0';
  ctx.lineWidth = 3;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(-3, 0); ctx.lineTo(-3, -30);
  ctx.moveTo(3, 0); ctx.lineTo(3, -18); ctx.lineTo(-3, -30);
  ctx.moveTo(-16, -40);
  ctx.quadraticCurveTo(-4, -26, 12, -40);
  ctx.quadraticCurveTo(0, -54, -16, -40);
  ctx.moveTo(10, -42);
  ctx.bezierCurveTo(26, -52, 2, -62, 12, -76);
  ctx.quadraticCurveTo(20, -82, 25, -72);
  ctx.stroke();
  ctx.restore();
}

function desenharPrancha(ctx, m) {
  var a = iso(m.c + 0.5, m.r + 0.5, 0);
  ctx.save();
  ctx.translate(a.x, a.y);
  ctx.rotate(-0.1);
  ctx.fillStyle = m.cor;
  ctx.strokeStyle = 'rgba(8,4,16,0.7)';
  ctx.beginPath();
  ctx.ellipse(0, -48, 11, 48, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = 'rgba(255,255,255,0.75)';
  ctx.fillRect(-1.5, -94, 3, 90);
  ctx.restore();
}

function desenharPlataformaCarro(ctx, m) {
  bloco(ctx, m.c + 0.6, m.r + 0.5, m.l - 1.2, m.p - 1, 1, 8, ['#17121f', '#0e0b14', '#17121f']);
}

function desenharFreezer(ctx, m) {
  bloco(ctx, m.c + 0.04, m.r + 0.08, m.l - 0.08, m.p - 0.12, 0, 104, ['#dfe4ee', '#aeb5c6', '#c5cbd9']);
  poligono(ctx, faceFrente(m.c + 0.12, m.r + m.p - 0.04, m.l - 0.24, 8, 84), '#0a2b3d', '#8df0ff', 1.4);
  var bebidas = ['#22c55e', '#ef4444', '#f59e0b', '#38bdf8', '#e879f9', '#facc15', '#f8fafc'];
  for (var n = 0; n < 4; n++) {
    var z = 13 + n * 20;
    poligono(ctx, faceFrente(m.c + 0.16, m.r + m.p - 0.04, m.l - 0.32, z - 2, 1.6), '#cfefff');
    for (var i = 0; i < 10; i++) {
      var x = m.c + 0.2 + i * 0.158;
      var altura = 11 + (i * 3 + n) % 5;
      poligono(ctx, faceFrente(x, m.r + m.p - 0.04, 0.11, z, altura), bebidas[(i + n * 2) % bebidas.length], 'rgba(0,0,0,0.35)', 0.4);
      poligono(ctx, faceFrente(x + 0.03, m.r + m.p - 0.04, 0.05, z + altura, 3), '#e5e7eb');
    }
  }
  poligono(ctx, faceFrente(m.c + 0.12, m.r + m.p - 0.04, m.l - 0.24, 92, 10), '#14532d', CORES.verde, 1);
}

function desenharFreezerVivo(ctx, m) {
  var pulso = 0.1 + Math.sin(cena.tempo * 2) * 0.04;
  poligono(ctx, faceFrente(m.c + 0.12, m.r + m.p - 0.04, m.l - 0.24, 8, 84), 'rgba(141,240,255,' + pulso.toFixed(3) + ')');
  if (sofa.fase === 'acao' && sofa.atividade && sofa.atividade.id === 'freezer') {
    var x = m.c + m.l - 0.12;
    poligono(ctx, [iso(x, m.r + m.p, 8), iso(x + 0.1, m.r + m.p + 1.2, 8), iso(x + 0.1, m.r + m.p + 1.2, 92), iso(x, m.r + m.p, 92)], 'rgba(170,240,255,0.32)', '#dff7ff', 1.4);
  }
}

function desenharPrateleiraBar(ctx, m) {
  bloco(ctx, m.c, m.r + 0.1, m.l, m.p - 0.15, 0, 36, ['#4a2a16', '#3a2010', '#2f1a0d']);
  bloco(ctx, m.c, m.r + 0.1, m.l, 0.3, 36, 84, ['#2a1710', '#1e1009', '#1a0e08']);
  var cores = ['#14532d', '#7c2d12', '#b45309', '#1e3a8a', '#6b21a8', '#be123c', '#047857'];
  [46, 72, 98].forEach(function(z, prateleira) {
    linhaNeon(ctx, [iso(m.c + 0.1, m.r + 0.42, z - 2), iso(m.c + m.l - 0.1, m.r + 0.42, z - 2)], prateleira === 1 ? CORES.rosa : CORES.verde, 1.2);
    for (var i = 0; i < 16; i++) {
      var x = m.c + 0.15 + i * 0.235;
      poligono(ctx, faceFrente(x, m.r + 0.42, 0.13, z, 13), cores[(i + prateleira * 3) % cores.length], 'rgba(255,255,255,0.3)', 0.5);
      poligono(ctx, faceFrente(x + 0.04, m.r + 0.42, 0.05, z + 13, 7), '#d4b483');
    }
  });
}

function desenharBalcaoBar(ctx, m) {
  bloco(ctx, m.c, m.r + 0.1, m.l, m.p - 0.2, 0, 38, ['#3f2513', '#2b180c', '#22130a']);
  bloco(ctx, m.c - 0.08, m.r, m.l + 0.16, m.p, 38, 4, ['#8a5a2e', '#5e3b1d', '#4c2f17']);
  linhaNeon(ctx, [iso(m.c, m.r + m.p - 0.1, 12), iso(m.c + m.l, m.r + m.p - 0.1, 12)], CORES.verde, 1.8);
  linhaNeon(ctx, [iso(m.c, m.r + m.p - 0.1, 30), iso(m.c + m.l, m.r + m.p - 0.1, 30)], CORES.ouro, 1.2);
  [1, 1.45, 1.9].forEach(function(x) {
    bloco(ctx, m.c + x, m.r + 0.4, 0.12, 0.12, 42, 18, ['#e8ecf5', '#9aa0b5', '#b6bbcd']);
    bloco(ctx, m.c + x - 0.08, m.r + 0.34, 0.28, 0.1, 58, 4, [CORES.ouro, '#b8912a', '#9a7720']);
  });
  [3, 3.5, 4].forEach(function(x, i) {
    bloco(ctx, m.c + x, m.r + 0.4, 0.2, 0.2, 42, 10, ['#fde68a', ['#f59e0b', '#22d3ee', '#ec4899'][i], '#e8c56a']);
  });
}

function desenharBanqueta(ctx, m) {
  bloco(ctx, m.c + 0.44, m.r + 0.44, 0.12, 0.12, 0, 26, ['#c8ccd8', '#868aa3', '#a1a5bd']);
  bloco(ctx, m.c + 0.25, m.r + 0.25, 0.5, 0.5, 0, 2, ['#a1a5bd', '#71758e', '#868aa3']);
  bloco(ctx, m.c + 0.16, m.r + 0.16, 0.68, 0.68, 26, 6, ['#1f9d5c', '#14703f', '#178049']);
}

function desenharPebolim(ctx, m) {
  [[0.1, 0.1], [m.l - 0.3, 0.1], [0.1, m.p - 0.3], [m.l - 0.3, m.p - 0.3]].forEach(function(p) {
    bloco(ctx, m.c + p[0], m.r + p[1], 0.2, 0.2, 0, 22, ['#3a2010', '#2a170b', '#211208']);
  });
  bloco(ctx, m.c, m.r, m.l, m.p, 22, 12, ['#7c4a21', '#5e3717', '#4c2c12']);
  poligono(ctx, faceTopo(m.c + 0.14, m.r + 0.14, m.l - 0.28, m.p - 0.28, 34), '#178a4a', '#e8f5e9', 1);
  poligono(ctx, [iso(m.c + m.l / 2, m.r + 0.14, 34), iso(m.c + m.l / 2, m.r + m.p - 0.14, 34)], null, '#e8f5e9', 1);
  for (var i = 0; i < 6; i++) {
    var x = m.c + 0.35 + i * 0.46;
    var a = iso(x, m.r - 0.25, 38), b = iso(x, m.r + m.p + 0.25, 38);
    ctx.strokeStyle = '#d9dde8';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
    for (var j = 0; j < 3; j++) {
      var boneco = iso(x, m.r + 0.5 + j * 0.5, 40);
      ctx.fillStyle = i % 2 ? '#ef4444' : '#2563eb';
      ctx.fillRect(boneco.x - 2, boneco.y - 3, 4, 7);
    }
  }
}

function desenharPoker(ctx, m) {
  bloco(ctx, m.c + 1, m.r + 0.5, 1, 1, 0, 24, ['#2a170b', '#1e1009', '#1a0e08']);
  bloco(ctx, m.c, m.r, m.l, m.p, 24, 6, ['#6e4626', '#4c2f1a', '#5c3a20']);
  poligono(ctx, faceTopo(m.c + 0.2, m.r + 0.2, m.l - 0.4, m.p - 0.4, 30), '#0f6b42', CORES.ouro, 1);
  [[0.7, 0.6], [1.5, 1.2], [2.3, 0.7]].forEach(function(f, i) {
    var p = iso(m.c + f[0], m.r + f[1], 31);
    ctx.fillStyle = ['#ef4444', '#f8fafc', '#2563eb'][i];
    for (var n = 0; n < 4; n++) ctx.fillRect(p.x - 4, p.y - n * 2, 8, 2);
  });
  poligono(ctx, faceTopo(m.c + 1.2, m.r + 0.7, 0.5, 0.35, 31), '#f8fafc', '#94a3b8', 0.6);
}

function desenharPistaViva(ctx) {
  for (var c = 40; c < 46; c++) {
    for (var r = 3; r < 8; r++) {
      var onda = Math.sin(cena.tempo * 2.2 + c * 0.9 + r * 1.3);
      var matiz = (cena.tempo * 45 + (c + r) * 28) % 360;
      poligono(ctx, faceTopo(c + 0.04, r + 0.04, 0.92, 0.92, 1), 'hsla(' + matiz.toFixed(0) + ',95%,58%,' + (0.42 + onda * 0.3).toFixed(3) + ')');
    }
  }
}

function desenharNotasDoDj(ctx) {
  if (!(sofa.fase === 'acao' && sofa.atividade && sofa.atividade.id === 'dj')) return;
  ctx.font = '700 15px "Segoe UI", Arial, sans-serif';
  ctx.textAlign = 'center';
  for (var i = 0; i < 5; i++) {
    var fase = (cena.tempo * 0.45 + i / 5) % 1;
    var p = iso(36.5 + Math.sin(i * 2.1) * 1.6, 6, 70 + fase * 70);
    ctx.fillStyle = 'rgba(61,255,143,' + (1 - fase).toFixed(3) + ')';
    ctx.fillText(i % 2 ? '♪' : '♫', p.x + Math.sin(cena.tempo * 2 + i) * 6, p.y);
  }
  ctx.textAlign = 'left';
}

function desenharEspreguicadeira(ctx, m) {
  bloco(ctx, m.c, m.r + 0.1, m.l, m.p - 0.2, 4, 5, ['#f5efe0', '#c9b98f', '#d8caa3']);
  bloco(ctx, m.c, m.r + 0.1, 0.7, m.p - 0.2, 9, 8, ['#ff7ab8', '#c94b86', '#d85c96']);
}

function desenharGuardaSol(ctx, m) {
  var base = iso(m.c + 0.5, m.r + 0.5, 0);
  ctx.strokeStyle = '#e8e2d2';
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(base.x, base.y);
  ctx.lineTo(base.x, base.y - 74);
  ctx.stroke();
  for (var i = 0; i < 8; i++) {
    var a1 = i / 8 * Math.PI * 2, a2 = (i + 1) / 8 * Math.PI * 2;
    ctx.fillStyle = i % 2 ? m.cor : '#fff4e6';
    ctx.beginPath();
    ctx.moveTo(base.x, base.y - 92);
    ctx.lineTo(base.x + Math.cos(a1) * 44, base.y - 66 + Math.sin(a1) * 20);
    ctx.lineTo(base.x + Math.cos(a2) * 44, base.y - 66 + Math.sin(a2) * 20);
    ctx.closePath();
    ctx.fill();
  }
}

function desenharBarTiki(ctx, m) {
  bloco(ctx, m.c, m.r, m.l, m.p, 0, 34, ['#8a5a32', '#5c3a20', '#6e4626']);
  linhaNeon(ctx, [iso(m.c, m.r + m.p, 20), iso(m.c + m.l, m.r + m.p, 20)], CORES.rosa, 1.6);
  [[0.1, 0.1], [m.l - 0.3, 0.1]].forEach(function(poste) {
    bloco(ctx, m.c + poste[0], m.r + poste[1], 0.2, 0.2, 34, 56, ['#6e4626', '#4c2f1a', '#5c3a20']);
  });
  bloco(ctx, m.c - 0.3, m.r - 0.3, m.l + 0.6, m.p + 0.6, 90, 10, ['#d9a441', '#a8772a', '#bb8833']);
  [0.6, 1.2, 1.8, 2.4].forEach(function(x, i) {
    bloco(ctx, m.c + x, m.r + 0.5, 0.14, 0.14, 34, 12, ['#fff', ['#ff2fa8', '#22e6ff', '#ffc94d', '#3dff8f'][i], '#ccc']);
  });
}

function desenharExterno(ctx, m) {
  var limites = limitesDoMovel(m);
  var imagem = imagemGuardada(m, 'fixo', limites, function(c) { FIXOS[m.tipo](c, m); });
  ctx.save();
  ctx.translate(0, ALTURA_LAJE);
  ctx.drawImage(imagem, limites.x, limites.y, limites.l, limites.a);
  ctx.restore();
}

function desenharPiscinaViva(ctx) {
  ctx.save();
  poligono(ctx, faceTopo(6.2, 26.2, 8.6, 3.6, -ALTURA_LAJE));
  ctx.clip();
  ctx.strokeStyle = 'rgba(255,255,255,0.42)';
  ctx.lineWidth = 1.4;
  for (var i = 0; i < 12; i++) {
    var r = 26.5 + i * 0.3;
    ctx.beginPath();
    for (var c = 6; c <= 15; c += 0.5) {
      var p = iso(c, r + Math.sin(cena.tempo * 1.3 + c * 1.7 + i) * 0.1, -ALTURA_LAJE);
      if (c === 6) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
  }
  ctx.restore();
}

// Móveis parados ficam guardados em imagem e só as partes animadas são redesenhadas
var FIXOS = {
  mesa: desenharMesaFixa, mesaExecutiva: desenharMesaFixa, cadeira: desenharCadeira, poltrona: desenharPoltrona,
  planta: desenharPlanta, erva: desenharErva, palmeira: desenharPalmeira, sofa: desenharSofa, balcao: desenharBalcao,
  estante: desenharEstante, aparador: desenharAparador, arcade: desenharArcade, rack: desenharRack, jukebox: desenharJukebox,
  caixaSom: desenharCaixaSom, lavaLamp: desenharLavaLamp, mesaCentro: desenharMesaCentro, sinuca: desenharSinuca,
  toca: desenharToca, divisoria: desenharDivisoria, divisoriaLounge: desenharDivisoria, mesaReuniao: desenharMesaReuniao,
  flamingo: desenharFlamingo, prancha: desenharPrancha, lowrider: desenharPlataformaCarro,
  consoleWar: desenharConsoleWar, sofaVip: desenharSofa, poker: desenharPoker, freezer: desenharFreezer, prateleiraBar: desenharPrateleiraBar, balcaoBar: desenharBalcaoBar, banqueta: desenharBanqueta, pebolim: desenharPebolim,
  espreguicadeira: desenharEspreguicadeira, guardaSol: desenharGuardaSol, barTiki: desenharBarTiki
};
var VIVOS = {
  mesa: desenharMesaViva, mesaExecutiva: desenharMesaViva, balcao: desenharBalcaoVivo, rack: desenharRackVivo,
  jukebox: desenharJukeboxViva, caixaSom: desenharCaixaSomViva, lavaLamp: desenharLavaLampViva, toca: desenharTocaViva,
  mesaReuniao: desenharMesaReuniaoViva, sofa: desenharGordao, lowrider: desenharCarroVivo, freezer: desenharFreezerVivo, divisoria: desenharDivisoriaViva, consoleWar: desenharConsoleWarVivo
};

function limitesDoMovel(m) {
  var altura = ALTURA_DO_MOVEL[m.tipo] || 90;
  var x1 = (m.c - m.r - m.p) * MEIO_L - 90, x2 = (m.c + m.l - m.r) * MEIO_L + 90;
  var y1 = (m.c + m.r) * MEIO_A - altura - 70, y2 = (m.c + m.l + m.r + m.p) * MEIO_A + 30;
  return { x: x1, y: y1, l: x2 - x1, a: y2 - y1 };
}

function imagemGuardada(dono, chaveImagem, limites, desenhar) {
  dono.imagens = dono.imagens || {};
  if (dono.imagens[chaveImagem] && dono.imagens[chaveImagem].versao === cena.versao) return dono.imagens[chaveImagem];
  var fator = cena.fatorArte;
  var tela = document.createElement('canvas');
  tela.width = Math.max(1, Math.ceil(limites.l * fator));
  tela.height = Math.max(1, Math.ceil(limites.a * fator));
  var ctx = tela.getContext('2d');
  ctx.setTransform(fator, 0, 0, fator, -limites.x * fator, -limites.y * fator);
  desenhar(ctx);
  tela.versao = cena.versao;
  dono.imagens[chaveImagem] = tela;
  return tela;
}

function desenharCarroVivo(ctx, m) {
  var corpo = imagens.carro.corpo, rodas = imagens.carro.rodas;
  if (!corpo || !corpo.complete || !corpo.naturalWidth) return;
  var origem = iso(m.c, m.r, 0);
  var salto = Math.max(0, Math.sin(cena.tempo * 1.6)) * 5;
  var inclinacao = Math.sin(cena.tempo * 3.2) * 0.01 * (salto > 0.5 ? 1 : 0);
  var centro = iso(m.c + m.l / 2, m.r + m.p / 2, 20);
  var luz = iso(m.c + m.l / 2, m.r + m.p / 2, 1);
  elipse(ctx, luz.x, luz.y, 118, 44, 'rgba(255,47,168,' + (0.2 + salto * 0.02).toFixed(3) + ')');
  ctx.save();
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  ctx.save();
  ctx.translate(centro.x, centro.y - salto);
  ctx.rotate(inclinacao);
  ctx.translate(-centro.x, -centro.y);
  ctx.drawImage(corpo, origem.x - 104, origem.y - 75, 292, 226);
  ctx.restore();
  ctx.drawImage(rodas, origem.x - 104, origem.y - 75, 292, 226);
  ctx.restore();
}

function desenharMovel(ctx, m) {
  if (m.tipo === 'cadeira') {
    var dono = AGENTES.filter(function(a) { return a.id === m.dono; })[0];
    if (dono && dono.sentado) return;
  }
  var limites = limitesDoMovel(m);
  var imagem = imagemGuardada(m, 'fixo', limites, function(c) { FIXOS[m.tipo](c, m); });
  ctx.drawImage(imagem, limites.x, limites.y, limites.l, limites.a);
  if (VIVOS[m.tipo]) VIVOS[m.tipo](ctx, m);
}

function desenharPainelDeVideo(ctx) {
  noPlanoPrincipal(ctx, 21, 128, function() {
    var l = 104, a = 94;
    ctx.fillStyle = '#0a1026';
    ctx.fillRect(0, 0, l, a);
    for (var i = 0; i < 9; i++) {
      var altura = 18 + (Math.sin(cena.tempo * 1.3 + i * 0.9) + 1) * 20 + i * 2;
      ctx.fillStyle = i % 2 ? CORES.ciano : CORES.rosa;
      ctx.fillRect(6 + i * 10.6, a - 20 - altura, 7, altura);
    }
    ctx.fillStyle = '#ff2fa8';
    ctx.fillRect(0, a - 16, l, 16);
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, a - 16, l, 16);
    ctx.clip();
    ctx.fillStyle = '#fff';
    ctx.font = '800 11px "Segoe UI", Arial, sans-serif';
    ctx.fillText('GTA 6 NARRADO  •  VIRAIS DA SEMANA  •  TOP 5  •  CANAL DARK', 104 - (cena.tempo * 22) % 300, a - 4);
    ctx.restore();
  });
}

function spriteDoAgente(ag, pose) {
  var img = imagens.poses[ag.id + pose];
  return img && img.complete && img.naturalWidth ? img : null;
}

function retanguloDoAgente(ag) {
  var p = iso(ag.c, ag.r, ag.z || 0);
  var largura = ALTURA_PERSONAGEM * 132 / ALTURA_ARTE;
  return { x: p.x - largura * (ag.sentado ? 0.37 : 0.5), y: p.y - ALTURA_PERSONAGEM + (ag.sentado ? 8 : 4), l: largura, a: ALTURA_PERSONAGEM };
}

function desenharAgente(ctx, ag) {
  var sprite = spriteDoAgente(ag, ag.acao || (ag.sentado ? (Math.floor(cena.tempo * 1.6 + ag.c) % 2 ? 1 : 2) : ag.quadro));
  if (!sprite) return;
  var caixaSprite = retanguloDoAgente(ag);
  var pe = iso(ag.c, ag.r, ag.z || 0);
  if (!ag.sentado) elipse(ctx, pe.x, pe.y, 19, 9, 'rgba(0,0,0,0.32)');
  var salto = ag.dancando ? Math.abs(Math.sin(cena.tempo * 7)) * 11 : ag.salto;
  var virar = ag.dancando ? Math.sin(cena.tempo * 3.5) < 0 : (ag.esquerda && !ag.sentado);
  ctx.save();
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  if (virar) {
    ctx.translate(caixaSprite.x + caixaSprite.l, caixaSprite.y - salto);
    ctx.scale(-1, 1);
    ctx.drawImage(sprite, 0, 0, caixaSprite.l, caixaSprite.a);
  } else {
    ctx.drawImage(sprite, caixaSprite.x, caixaSprite.y - salto, caixaSprite.l, caixaSprite.a);
  }
  ctx.restore();
}

// Objetos de trás são desenhados primeiro para os móveis cobrirem corretamente os personagens
function ordenarProfundidade(itens) {
  var saida = [];
  function atras(a, b) { return a.c2 <= b.c1 || a.r2 <= b.r1; }
  function visitar(item) {
    if (item.visitado) return;
    item.visitado = true;
    itens.forEach(function(outro) {
      if (outro !== item && atras(outro, item) && !atras(item, outro)) visitar(outro);
    });
    saida.push(item);
  }
  itens.forEach(visitar);
  return saida;
}

function itensDaCena() {
  var itens = MOVEIS.map(function(m) {
    return { tipo: 'movel', ref: m, c1: m.c, c2: m.c + m.l, r1: m.r, r2: m.r + m.p };
  });
  EXTERNOS.forEach(function(m) {
    itens.push({ tipo: 'externo', ref: m, c1: m.c, c2: m.c + m.l, r1: m.r, r2: m.r + m.p });
  });
  AGENTES.concat(sofa.deitado ? [] : [sofa]).forEach(function(ag) {
    itens.push({ tipo: 'agente', ref: ag, c1: ag.c - 0.3, c2: ag.c + 0.3, r1: ag.r - 0.3, r2: ag.r + 0.3 });
  });
  return ordenarProfundidade(itens);
}

function desenharFumaca(ctx, segundos) {
  fumacas = fumacas.filter(function(f) { return f.vida > 0; });
  fumacas.forEach(function(f) {
    f.vida -= segundos / 2.6;
    f.x += (8 + Math.sin(f.vida * 9) * 8) * segundos;
    f.y -= 25 * segundos;
    ctx.fillStyle = 'rgba(214,255,226,' + (Math.max(f.vida, 0) * 0.34).toFixed(3) + ')';
    ctx.beginPath();
    ctx.arc(f.x, f.y, 1.5 + (1 - f.vida) * 11, 0, Math.PI * 2);
    ctx.fill();
  });
}

function soltarFumaca() {
  if (!sofa.deitado) return;
  sofa.indice = (sofa.indice + 1) % sofa.quadros.length;
  var origem = ORIGEM_FUMACA[sofa.quadros[sofa.indice]];
  var escala = ALTURA_PERSONAGEM / ALTURA_ARTE;
  var angulo = Math.atan2(MEIO_A, MEIO_L);
  var p = iso(SOFA_C, SOFA_R, 30);
  fumacas.push({
    x: p.x + (origem.x * Math.cos(angulo) - origem.y * Math.sin(angulo)) * escala,
    y: p.y + (origem.x * Math.sin(angulo) + origem.y * Math.cos(angulo)) * escala,
    vida: 1
  });
}

function quebrarTexto(ctx, texto, largura) {
  var linhas = [];
  var atual = '';
  texto.split(' ').forEach(function(palavra) {
    var teste = atual ? atual + ' ' + palavra : palavra;
    if (ctx.measureText(teste).width > largura && atual) {
      linhas.push(atual);
      atual = palavra;
    } else {
      atual = teste;
    }
  });
  if (atual) linhas.push(atual);
  return linhas;
}

function paraTela(p) {
  return { x: cena.x + p.x * cena.escala, y: cena.y + p.y * cena.escala };
}

function desenharBalao(ctx, dono, topo) {
  var agora = performance.now();
  if (!dono.balao || dono.balao.ate < agora) return;
  ctx.font = '600 12px "Segoe UI", Arial, sans-serif';
  var linhas = quebrarTexto(ctx, dono.nome + ': ' + dono.balao.texto, 172);
  var largura = Math.max.apply(null, linhas.map(function(l) { return ctx.measureText(l).width; })) + 20;
  var altura = linhas.length * 16 + 12;
  var x = Math.max(8, Math.min(cena.largura - largura - 8, topo.x - largura / 2));
  var y = Math.max(8, topo.y - altura - 12);
  ctx.fillStyle = '#ffffff';
  ctx.strokeStyle = '#111827';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.roundRect(x, y, largura, altura, 10);
  ctx.fill();
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(topo.x - 6, y + altura - 1);
  ctx.lineTo(topo.x, y + altura + 8);
  ctx.lineTo(topo.x + 6, y + altura - 1);
  ctx.fill();
  ctx.stroke();
  ctx.fillRect(topo.x - 5, y + altura - 3, 10, 3);
  ctx.fillStyle = '#111827';
  ctx.textAlign = 'center';
  linhas.forEach(function(l, i) { ctx.fillText(l, x + largura / 2, y + 19 + i * 16); });
  ctx.textAlign = 'left';
}

function desenharEtiqueta(ctx, nome, cargo, ponto) {
  var texto = nome + ' • ' + cargo;
  ctx.font = '700 11px "Segoe UI", Arial, sans-serif';
  var largura = ctx.measureText(texto).width + 14;
  ctx.fillStyle = 'rgba(2,6,23,0.9)';
  ctx.beginPath();
  ctx.roundRect(ponto.x - largura / 2, ponto.y + 6, largura, 20, 5);
  ctx.fill();
  ctx.fillStyle = '#e2e8f0';
  ctx.fillText(texto, ponto.x - largura / 2 + 7, ponto.y + 20);
}

function desenharInterface(ctx) {
  ctx.setTransform(cena.dpr, 0, 0, cena.dpr, 0, 0);
  AGENTES.forEach(function(ag) {
    var r = retanguloDoAgente(ag);
    desenharBalao(ctx, ag, paraTela({ x: r.x + r.l / 2, y: r.y }));
  });
  desenharBalao(ctx, sofa, paraTela(iso(sofa.c, sofa.r, 90)));
  var alvo = agenteNoPonteiro();
  if (alvo) desenharEtiqueta(ctx, alvo.nome, alvo.cargo, paraTela(iso(alvo.c, alvo.r, 0)));
}

function coordenadaMundo(x, y) {
  return { x: (x - cena.x) / cena.escala, y: (y - cena.y) / cena.escala };
}

function agenteNoPonteiro() {
  if (!ponteiro) return null;
  var p = coordenadaMundo(ponteiro.x, ponteiro.y);
  var lista = AGENTES.slice().sort(function(a, b) { return (b.c + b.r) - (a.c + a.r); });
  for (var i = 0; i < lista.length; i++) {
    var r = retanguloDoAgente(lista[i]);
    if (p.x >= r.x && p.x <= r.x + r.l && p.y >= r.y && p.y <= r.y + r.a) return lista[i];
  }
  var s = iso(sofa.c, sofa.r, 30);
  return Math.abs(p.x - s.x) < 60 && Math.abs(p.y - s.y) < 40 ? sofa : null;
}

function novaTela() {
  var tela = document.createElement('canvas');
  tela.width = cena.largura * cena.dpr;
  tela.height = cena.altura * cena.dpr;
  return tela;
}

function telaDoMundo(area) {
  var tela = document.createElement('canvas');
  tela.width = Math.ceil(area.l * cena.fatorArte);
  tela.height = Math.ceil(area.a * cena.fatorArte);
  var ctx = tela.getContext('2d');
  ctx.setTransform(cena.fatorArte, 0, 0, cena.fatorArte, -area.x * cena.fatorArte, -area.y * cena.fatorArte);
  return { tela: tela, ctx: ctx };
}

function montarFundo() {
  var ceu = novaTela();
  var ctxCeu = ceu.getContext('2d');
  ctxCeu.setTransform(cena.dpr, 0, 0, cena.dpr, 0, 0);
  desenharCeu(ctxCeu);
  cena.ceu = ceu;

  var sala = telaDoMundo(MUNDO);
  desenharPiso(sala.ctx);
  desenharParedes(sala.ctx);
  cena.sala = sala.tela;

  var letreiros = telaDoMundo(AREA_LETREIROS);
  desenharLetreiros(letreiros.ctx);
  cena.letreiros = letreiros.tela;
}

// Copia só o pedaço do cenário que está visível na câmera
function desenharCamada(ctx, imagem, area) {
  var x0 = Math.max(area.x, -cena.x / cena.escala);
  var y0 = Math.max(area.y, -cena.y / cena.escala);
  var x1 = Math.min(area.x + area.l, (cena.largura - cena.x) / cena.escala);
  var y1 = Math.min(area.y + area.a, (cena.altura - cena.y) / cena.escala);
  if (x1 <= x0 || y1 <= y0) return;
  var f = cena.fatorArte;
  ctx.drawImage(imagem, (x0 - area.x) * f, (y0 - area.y) * f, (x1 - x0) * f, (y1 - y0) * f, x0, y0, x1 - x0, y1 - y0);
}

// ---------- Câmera: zoom e arraste ----------
function limitarCamera() {
  var xMinimo = cena.largura - (MUNDO.x + MUNDO.l) * cena.escala;
  var xMaximo = -MUNDO.x * cena.escala;
  var yMinimo = cena.altura - (MUNDO.y + MUNDO.a) * cena.escala;
  var yMaximo = -MUNDO.y * cena.escala;
  cena.x = xMinimo > xMaximo ? (xMinimo + xMaximo) / 2 : Math.min(xMaximo, Math.max(xMinimo, cena.x));
  cena.y = yMinimo > yMaximo ? (yMinimo + yMaximo) / 2 : Math.min(yMaximo, Math.max(yMinimo, cena.y));
}

function definirZoom(zoom, telaX, telaY) {
  var mundoX = (telaX - cena.x) / cena.escala;
  var mundoY = (telaY - cena.y) / cena.escala;
  cena.zoom = Math.min(ZOOM_MAXIMO, Math.max(ZOOM_MINIMO, zoom));
  cena.escala = cena.escalaBase * cena.zoom;
  cena.x = telaX - mundoX * cena.escala;
  cena.y = telaY - mundoY * cena.escala;
  limitarCamera();
}

function moverCamera(dx, dy) {
  cena.x += dx;
  cena.y += dy;
  limitarCamera();
}

function zoomCentral(fator) {
  definirZoom(cena.zoom * fator, cena.largura / 2, cena.altura / 2);
}

function restaurarCamera() {
  cena.zoom = 1;
  cena.escala = cena.escalaBase;
  cena.x = cena.xBase;
  cena.y = cena.yBase;
}

var cameraArrastada = false;

function ligarCamera(canvas) {
  var dedos = {};
  var percurso = 0;
  var distanciaPinca = 0;

  function posicao(e) {
    var caixa = canvas.getBoundingClientRect();
    return { x: e.clientX - caixa.left, y: e.clientY - caixa.top };
  }

  canvas.style.touchAction = 'none';
  canvas.addEventListener('wheel', function(e) {
    e.preventDefault();
    var p = posicao(e);
    definirZoom(cena.zoom * Math.exp(-e.deltaY * 0.0014), p.x, p.y);
  }, { passive: false });

  canvas.addEventListener('pointerdown', function(e) {
    canvas.setPointerCapture(e.pointerId);
    dedos[e.pointerId] = posicao(e);
    percurso = 0;
    distanciaPinca = 0;
    cameraArrastada = false;
  });

  canvas.addEventListener('pointermove', function(e) {
    if (!dedos[e.pointerId]) return;
    var p = posicao(e);
    var anterior = dedos[e.pointerId];
    dedos[e.pointerId] = p;
    var ids = Object.keys(dedos);
    if (ids.length === 1) {
      percurso += Math.abs(p.x - anterior.x) + Math.abs(p.y - anterior.y);
      if (percurso > 5) {
        cameraArrastada = true;
        canvas.style.cursor = 'grabbing';
        moverCamera(p.x - anterior.x, p.y - anterior.y);
      }
    } else if (ids.length === 2) {
      cameraArrastada = true;
      var a = dedos[ids[0]], b = dedos[ids[1]];
      var distancia = Math.hypot(a.x - b.x, a.y - b.y);
      if (distanciaPinca) definirZoom(cena.zoom * distancia / distanciaPinca, (a.x + b.x) / 2, (a.y + b.y) / 2);
      distanciaPinca = distancia;
    }
  });

  function soltar(e) {
    delete dedos[e.pointerId];
    distanciaPinca = 0;
    canvas.style.cursor = 'grab';
  }
  canvas.addEventListener('pointerup', soltar);
  canvas.addEventListener('pointercancel', soltar);
  canvas.addEventListener('dblclick', restaurarCamera);
}

function ajustarEscala() {
  var palco = document.getElementById('stage');
  var canvas = document.getElementById('cena');
  if (!palco.clientWidth || !palco.clientHeight) return;
  if (palco.clientWidth === cena.largura && palco.clientHeight === cena.altura && cena.sala) return;
  cena.dpr = Math.min(window.devicePixelRatio || 1, 2);
  cena.largura = palco.clientWidth;
  cena.altura = palco.clientHeight;
  cena.versao = (cena.versao || 0) + 1;
  canvas.width = Math.round(cena.largura * cena.dpr);
  canvas.height = Math.round(cena.altura * cena.dpr);

  var larguraMundo = (COLUNAS_CAMERA + LINHAS) * MEIO_L;
  var alturaPiso = LIMITE_FRENTE * MEIO_A;
  cena.escalaBase = Math.min(cena.largura / larguraMundo, (cena.altura - 40) / alturaPiso) * AFASTAMENTO_CAMERA;
  cena.xBase = cena.largura / 2 - (COLUNAS_CAMERA - LINHAS) * MEIO_L / 2 * cena.escalaBase;
  cena.yBase = cena.altura - alturaPiso * cena.escalaBase - MARGEM_INFERIOR;
  cena.fatorArte = Math.min(1.3, cena.escalaBase * cena.dpr * 1.6);
  restaurarCamera();
  montarFundo();
}

var ultimoQuadro = 0;
function lacoAnimacao(agora) {
  var segundos = Math.min(0.1, (agora - ultimoQuadro) / 1000);
  ultimoQuadro = agora;
  if (!movimentoReduzido) cena.tempo += segundos;
  AGENTES.forEach(function(ag) { atualizarAgente(ag, segundos); });
  atualizarGordao(segundos);
  if (!cena.sala) {
    requestAnimationFrame(lacoAnimacao);
    return;
  }

  var canvas = document.getElementById('cena');
  var ctx = canvas.getContext('2d');
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.drawImage(cena.ceu, 0, 0);
  ctx.setTransform(cena.dpr, 0, 0, cena.dpr, 0, 0);
  desenharDirigivel(ctx);
  ctx.setTransform(cena.dpr * cena.escala, 0, 0, cena.dpr * cena.escala, cena.dpr * cena.x, cena.dpr * cena.y);
  desenharCamada(ctx, cena.sala, MUNDO);
  desenharMuralDaLogo(ctx);
  ctx.globalAlpha = Math.sin(cena.tempo * 11) > 0.985 ? 0.72 : 0.94 + Math.sin(cena.tempo * 2.2) * 0.06;
  desenharCamada(ctx, cena.letreiros, AREA_LETREIROS);
  ctx.globalAlpha = 1;
  desenharPainelDeVideo(ctx);
  desenharGradeDoMezanino(ctx);
  desenharPiscinaViva(ctx);
  desenharPistaViva(ctx);
  itensDaCena().forEach(function(item) {
    if (item.tipo === 'movel') desenharMovel(ctx, item.ref);
    else if (item.tipo === 'externo') desenharExterno(ctx, item.ref);
    else desenharAgente(ctx, item.ref);
  });
  desenharFumaca(ctx, segundos);
  desenharNotasDoDj(ctx);
  desenharInterface(ctx);
  requestAnimationFrame(lacoAnimacao);
}

function carregarImagens() {
  var elenco = AGENTES.concat([sofa]);
  function carregar(id, nome, arquivo) {
    var img = new Image();
    img.src = '/sprites/personagens/' + id + '_' + arquivo + '.png?v=' + VERSAO_ARTE;
    imagens.poses[id + nome] = img;
  }
  elenco.forEach(function(pessoa) {
    [1, 2, 3, 4].forEach(function(pose) { carregar(pessoa.id, pose, 'pose' + pose); });
    (pessoa.quadros && pessoa !== sofa ? pessoa.quadros : []).forEach(function(nome) { carregar(pessoa.id, nome, nome); });
  });
  ATIVIDADES_GORDAO.forEach(function(atividade) {
    atividade.quadros.forEach(function(nome) { carregar(sofa.id, nome, nome); });
  });
  imagens.logo = new Image();
  imagens.logo.src = '/sprites/logo_mural.jpg?v=' + VERSAO_ARTE;
  ['corpo', 'rodas'].forEach(function(parte) {
    imagens.carro[parte] = new Image();
    imagens.carro[parte].src = '/sprites/carro_' + parte + '.png?v=' + VERSAO_ARTE;
  });
  [1, 2, 3].forEach(function(quadro) {
    var img = new Image();
    img.src = '/sprites/sofa_quadro' + quadro + '.png?v=' + VERSAO_ARTE;
    imagens.sofa[quadro] = img;
  });
}

function iniciarEscritorio() {
  var canvas = document.getElementById('cena');
  movimentoReduzido = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  carregarImagens();
  AGENTES.forEach(prepararAgente);
  prepararGordao();
  ajustarEscala();
  window.addEventListener('resize', ajustarEscala);
  if (window.ResizeObserver) new ResizeObserver(ajustarEscala).observe(document.getElementById('stage'));

  canvas.addEventListener('mousemove', function(e) {
    var caixa = canvas.getBoundingClientRect();
    ponteiro = { x: e.clientX - caixa.left, y: e.clientY - caixa.top };
    var alvo = agenteNoPonteiro();
    if (canvas.style.cursor !== 'grabbing') canvas.style.cursor = alvo && alvo !== sofa ? 'pointer' : 'grab';
  });
  canvas.addEventListener('mouseleave', function() { ponteiro = null; });
  ligarCamera(canvas);
  canvas.addEventListener('click', function() {
    if (cameraArrastada) {
      cameraArrastada = false;
      return;
    }
    var alvo = agenteNoPonteiro();
    if (alvo && alvo !== sofa) abrirPainelDoAgente(alvo.id);
  });

  requestAnimationFrame(function(agora) {
    ultimoQuadro = agora;
    lacoAnimacao(agora);
  });
  setInterval(soltarFumaca, 950);
  setInterval(function() { if (sofa.deitado) falar(sofa, sortear(FALAS.sofa), 4200); }, 17000);
  AGENTES.forEach(function(ag) { agendar(ag, 1500, 9000); });
}

if (typeof module !== 'undefined') {
  module.exports = { AGENTES: AGENTES, MOVEIS: MOVEIS, PONTOS: PONTOS, COLUNAS: COLUNAS, LINHAS: LINHAS, LIMITE_FRENTE: LIMITE_FRENTE,
    calcularRota: calcularRota, celulaLivre: celulaLivre, dentroDoPiso: dentroDoPiso, acessoDoAssento: acessoDoAssento, bloqueadas: bloqueadas,
    prepararAgente: prepararAgente, atualizarAgente: atualizarAgente, irPara: irPara, sentar: sentar, reservas: reservas, sofa: sofa,
    cena: cena, definirZoom: definirZoom, moverCamera: moverCamera, restaurarCamera: restaurarCamera, ZOOM_MINIMO: ZOOM_MINIMO, ZOOM_MAXIMO: ZOOM_MAXIMO,
    FIXOS: FIXOS, EXTERNOS: EXTERNOS, ATIVIDADES_GORDAO: ATIVIDADES_GORDAO, prepararGordao: prepararGordao, atualizarGordao: atualizarGordao, TAREFAS: TAREFAS, agenteDaEtapa: agenteDaEtapa, anunciarTarefa: anunciarTarefa, FALAS_REUNIAO: FALAS_REUNIAO };
}
