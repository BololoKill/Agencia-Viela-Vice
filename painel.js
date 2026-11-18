var dadosServidor = {};

// Gerenciamento de Janelas Modais
function verModal(titulo, html) {
  document.getElementById('m-tit').innerText = titulo;
  document.getElementById('m-txt').innerHTML = html;
  document.getElementById('modal').style.display = 'flex';
}

function fecharModal() {
  var vid = document.getElementById('player-review');
  if (vid) { vid.pause(); vid.removeAttribute('src'); vid.load(); }
  document.getElementById('modal').style.display = 'none';
}

// Sincronização geral de dados com a API
function atualizarTudo() {
  fetch('/api/data').then(function(r) { return r.json(); }).then(function(d) {
    dadosServidor = d || {};
    var pend = d.videos || d.pendentes || [];
    var ag = d.agendados || d.fila || [];
    document.getElementById('m-est').innerText = pend.length;
    var envios = d.envios_hoje || 0;
    var limiteEnvios = d.limite_envios || 42;
    document.getElementById('m-env').innerText = envios + '/' + limiteEnvios;
    document.getElementById('b-niv').innerHTML = '★ Estrelas<br>' + envios + '/' + limiteEnvios;
    verificarTravaCanal();
    document.getElementById('b-dir').innerHTML = 'Diretoria<br>(' + pend.length + ')';
    document.getElementById('b-fila').innerHTML = 'Fila YouTube<br>(' + ag.length + ')';
    document.getElementById('g-pct').innerText = Math.min(100, Math.round((pend.length / 60) * 100)) + '%';
  }).catch(function() {});
}

// Player de Avaliação da Diretoria
var listaPendentes = [];
var idxAtual = 0;

function abrirAvaliacao() {
  verModal('Curadoria & Aprovação da Diretoria', '<div class="card">Carregando vídeos da fila...</div>');
  fetch('/api/data').then(function(r) { return r.json(); }).then(function(d) {
    dadosServidor = d || {};
    listaPendentes = d.videos || d.pendentes || [];
    idxAtual = 0;
    renderizarPlayer();
  }).catch(function() {
    document.getElementById('m-txt').innerHTML = '<div class="card">Nenhum vídeo encontrado na fila.</div>';
  });
}

function renderizarPlayer() {
  if (!listaPendentes.length || idxAtual >= listaPendentes.length) {
    document.getElementById('m-txt').innerHTML = '<div class="card" style="text-align:center;">Nenhum vídeo pendente na fila no momento.<br>A equipe está cuidando dos próximos cortes!</div>';
    return;
  }
  var item = listaPendentes[idxAtual];
  var nome = (typeof item === 'string') ? item : (item.filename || item.arquivo || item.nome);
  var tit = (typeof item === 'object' && item.titulo) ? item.titulo : nome.replace('.mp4', '').replace(/_/g, ' ');
  var desc = (typeof item === 'object' && item.descricao) ? item.descricao : 'Inscreva-se no canal Viela Vice! #GTA6 #GTARP #Shorts';

  document.getElementById('m-txt').innerHTML =
    '<div style="font-size:11px; color:#94a3b8; margin-bottom:8px;">Arquivo (' + (idxAtual + 1) + '/' + listaPendentes.length + '): <b>' + nome + '</b></div>' +
    '<video id="player-review" controls autoplay playsinline style="width:100%; max-height:240px; background:#000; border-radius:8px; border:1px solid #334155;" src="/exportacao/' + encodeURIComponent(nome) + '"></video>' +
    '<select id="sel-canal" onchange="verificarTravaCanal()">' + montarOpcoesCanais() + '</select>' +
    '<div id="estrelas-canal"></div>' +
    '<input id="inp-tit" value="' + tit.replace(/"/g, '&quot;') + '">' +
    '<textarea id="inp-desc" rows="2">' + desc + '</textarea>' +
    '<div class="row-btns">' +
      '<button class="act-btn" id="btn-enviar-hoje" style="background:#16a34a;" onclick="aprovarVideo(\'' + nome + '\')">Aprovar &amp; Enviar Hoje</button>' +
      '<button class="act-btn" style="background:#d97706;" onclick="idxAtual++; renderizarPlayer();">Pular / Guardar</button>' +
      '<button class="act-btn" style="background:#dc2626;" onclick="negarVideo(\'' + nome + '\')">Rejeitar / Excluir</button>' +
    '</div>';
  verificarTravaCanal();
}

// Estrelas: cada canal pode receber 6 envios por ciclo, que reinicia às 05:00
var CANAIS_PAINEL = [
  { id: '1', nome: '1. Viela Vice (Principal - GTA 6)' },
  { id: '2', nome: '2. Viela Vice RP (Policia e Fugas)' },
  { id: '3', nome: '3. Viela Vice Clipes (Memes e Zueira)' },
  { id: '4', nome: '4. Viela Vice Stories (Historias)' },
  { id: '5', nome: '5. Viela Vice Underground (Favela)' },
  { id: '6', nome: '6. Viela Vice News (Vazamentos GTA 6)' },
  { id: '7', nome: '7. Viela Vice Best Moments' }
];

function cotaDoCanal(canalId) {
  var cotas = dadosServidor.cotas || {};
  return cotas[canalId] || { usados: 0, limite: 6, bloqueado: false, verificado: false };
}

function desenharEstrelas(usados, limite) {
  var html = '<span class="estrelas" aria-hidden="true">';
  for (var i = 1; i <= limite; i++) {
    html += i <= usados ? '<span class="estrela-cheia">★</span>' : '<span class="estrela-vazia">☆</span>';
  }
  return html + '</span>';
}

function montarOpcoesCanais() {
  var html = '';
  CANAIS_PAINEL.forEach(function(canal) {
    var cota = cotaDoCanal(canal.id);
    html += '<option value="' + canal.id + '">' + canal.nome + ' (' + cota.usados + '/' + cota.limite + ')</option>';
  });
  return html;
}

function verificarTravaCanal() {
  var sel = document.getElementById('sel-canal');
  var btn = document.getElementById('btn-enviar-hoje');
  var painel = document.getElementById('estrelas-canal');
  if (!sel || !btn || !painel) return;

  var cota = cotaDoCanal(sel.value);
  var situacao = cota.verificado ? 'Envios neste ciclo: ' + cota.usados + '/' + cota.limite : 'Confirmando envios no YouTube...';
  painel.innerHTML = '<span>' + situacao + ' · reinicia às 05:00</span>' + desenharEstrelas(cota.usados, cota.limite);
  if (btn.dataset.enviando === '1') return;

  btn.disabled = !!cota.bloqueado;
  btn.style.background = cota.bloqueado ? '#475569' : '#16a34a';
  btn.style.cursor = cota.bloqueado ? 'not-allowed' : 'pointer';
  btn.textContent = cota.bloqueado
    ? 'Bloqueado (' + cota.usados + '/' + cota.limite + ') · Libera às 05:00'
    : 'Aprovar & Enviar Hoje (' + cota.usados + '/' + cota.limite + ')';
}

function bloquearAcoes(bloquear) {
  var botoes = document.querySelectorAll('#m-txt .act-btn');
  for (var i = 0; i < botoes.length; i++) {
    botoes[i].disabled = bloquear;
    botoes[i].dataset.enviando = bloquear ? '1' : '';
  }
}

function aprovarVideo(nome) {
  var vid = document.getElementById('player-review');
  if (vid) { vid.pause(); vid.removeAttribute('src'); vid.load(); }
  var corpo = {
    filename: nome, arquivo: nome,
    canal: document.getElementById('sel-canal').value,
    titulo: document.getElementById('inp-tit').value,
    descricao: document.getElementById('inp-desc').value
  };
  bloquearAcoes(true);
  mostrarAviso('Enviando vídeo ao YouTube...', '');
  enviarJson('/api/aprovar', corpo, LIMITE_ENVIO_MS).then(function(d) {
    mostrarAviso(d.message || 'Vídeo aprovado!', d.enviado_youtube === false ? 'aviso' : 'ok');
    listaPendentes.splice(idxAtual, 1);
    renderizarPlayer();
    atualizarTudo();
  }).catch(function(e) {
    mostrarAviso('Não foi possível aprovar: ' + e.message, 'erro');
    renderizarPlayer();
  });
}

function negarVideo(nome) {
  if (!confirm('Rejeitar vídeo e remover da exportação?')) return;
  var vid = document.getElementById('player-review');
  if (vid) { vid.pause(); vid.removeAttribute('src'); vid.load(); }
  bloquearAcoes(true);
  enviarJson('/api/negar', { filename: nome, arquivo: nome }).then(function(d) {
    mostrarAviso(d.message || 'Vídeo rejeitado.', 'ok');
    listaPendentes.splice(idxAtual, 1);
    renderizarPlayer();
    atualizarTudo();
  }).catch(function(e) {
    mostrarAviso('Não foi possível rejeitar: ' + e.message, 'erro');
    renderizarPlayer();
  });
}

function abrirCuradoriaTop() {
  var total = (dadosServidor.videos || dadosServidor.pendentes || []).length;
  verModal('Curadoria de Qualidade & Top 6', '<div style="text-align:center; padding:20px;"><div style="margin-bottom:14px; font-size:14px;"><b>' + total + '</b> vídeos auditados e sem bugs na fila.</div><button onclick="abrirAvaliacao()" style="background:#2563eb; color:#fff; border:none; padding:10px 22px; border-radius:8px; font-weight:700; cursor:pointer;">Avaliar Fila Agora</button></div>');
}

function abrirFila() {
  var ag = dadosServidor.agendados || dadosServidor.fila || [];
  if (!ag.length) {
    verModal('Fila Programada no YouTube', '<div class="card" style="text-align:center;">Nenhum vídeo agendado na fila ainda hoje.</div>');
    return;
  }
  var h = '';
  for (var i = 0; i < ag.length; i++) {
    var v = ag[i];
    var tit = v.titulo || v.title || v.filename || v;
    var hora = v.horario || v.data || "Hoje";
    h += '<div class="card"><b>' + tit + '</b><div style="font-size:11px; color:#38bdf8; margin-top:4px;">Agendado para: ' + hora + '</div></div>';
  }
  verModal('Fila Programada no YouTube (' + ag.length + ')', h);
}

function abrirNivel() {
  var html = '<div style="font-size:11px; color:#94a3b8; margin-bottom:10px;">Limite de <b>6 vídeos por canal</b> em cada ciclo. As estrelas só reiniciam às 05:00.</div>';
  CANAIS_PAINEL.forEach(function(canal) {
    var cota = cotaDoCanal(canal.id);
    var situacao = cota.bloqueado
      ? '<span style="color:#f87171; font-weight:700;">Bloqueado até as 05:00 (' + cota.usados + '/' + cota.limite + ')</span>'
      : (cota.verificado ? 'Envios neste ciclo: ' + cota.usados + '/' + cota.limite : 'Confirmando envios no YouTube...');
    html += '<div class="card" style="display:flex; justify-content:space-between; align-items:center; gap:12px;">' +
      '<div><b>' + canal.nome + '</b><div style="font-size:11px; color:#94a3b8;">' + situacao + '</div></div>' +
      desenharEstrelas(cota.usados, cota.limite) +
    '</div>';
  });
  verModal('★ Sistema 6 Estrelas (Cotas dos Canais)', html);
}

function abrirSuporteTI() {
  verModal('Suporte Técnico & Manutenção T.I.',
    '<div class="card" style="text-align:center;">' +
      '<p style="margin-bottom:12px;">Caio e Beatriz monitoram CPU, temperatura e disco. Limpe os temporários com 1 clique abaixo:</p>' +
      '<button onclick="purgarTI()" style="background:#dc2626; color:#fff; border:none; padding:10px 20px; border-radius:8px; font-weight:700; cursor:pointer;">Limpar Resíduos e Temporários (Purga)</button>' +
    '</div>'
  );
}

function purgarTI() {
  enviarJson('/api/ti/purge', {}).then(function(d) {
    mostrarAviso(d.removidos + ' arquivo(s) temporário(s) removido(s).', 'ok');
    atualizarTudo();
  }).catch(function(e) { mostrarAviso(e.message, 'aviso'); });
}

// Comunicação com o servidor
var LIMITE_PADRAO_MS = 8000;
var LIMITE_ENVIO_MS = 900000;

function requisitarJson(url, opcoes, limiteMs) {
  var cfg = opcoes || {};
  var controle = new AbortController();
  var relogio = setTimeout(function() { controle.abort(); }, limiteMs || LIMITE_PADRAO_MS);
  cfg.signal = controle.signal;
  return fetch(url, cfg).then(function(r) {
    return r.json().catch(function() { return {}; }).then(function(d) {
      if (!r.ok) throw new Error(d.error || d.message || ('Servidor respondeu ' + r.status));
      return d;
    });
  }).then(function(d) {
    clearTimeout(relogio);
    return d;
  }, function(e) {
    clearTimeout(relogio);
    throw e.name === 'AbortError' ? new Error('O servidor demorou para responder.') : e;
  });
}

function enviarJson(url, corpo, limiteMs) {
  return requisitarJson(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(corpo)
  }, limiteMs);
}

var relogioAviso = null;
function mostrarAviso(texto, tipo) {
  var el = document.getElementById('aviso');
  el.textContent = texto;
  el.className = tipo || '';
  el.style.display = 'block';
  clearTimeout(relogioAviso);
  relogioAviso = setTimeout(function() { el.style.display = 'none'; }, 7000);
}

// Console de T.I. e saúde da produção
var INTERVALO_CONSOLE_MS = 2500;
var INTERVALO_MAXIMO_MS = 30000;
var falhasConsole = 0;
var consoleOcupado = false;
var relogioConsole = null;
var ultimoLog = null;
var varreduraAtiva = true;

var SELOS_SAUDE = {
  produzindo: { texto: '● PRODUZINDO', cor: '#22c55e' },
  ocioso: { texto: '● ONLINE', cor: '#22c55e' },
  pausado: { texto: '❚❚ PAUSADO', cor: '#fbbf24' },
  erro: { texto: '▲ COM ERRO', cor: '#f87171' },
  travado: { texto: '▲ TRAVADO', cor: '#f87171' },
  parado: { texto: '○ ROBÔ DESLIGADO', cor: '#94a3b8' },
  offline: { texto: '○ OFFLINE', cor: '#f87171' }
};

function classeDaLinha(linha) {
  if (/\[ERRO|\[QUARENTENA/.test(linha)) return 'log-linha log-erro';
  if (/\[AVISO|\[AGUARDANDO|\[PAINEL/.test(linha)) return 'log-linha log-aviso';
  if (/\[SUCESSO|\[100%\]/.test(linha)) return 'log-linha log-ok';
  return 'log-linha';
}

function renderizarConsole(linhas) {
  var assinatura = linhas.join('\n');
  if (assinatura === ultimoLog) return;
  ultimoLog = assinatura;

  var caixa = document.getElementById('logs');
  var noFim = caixa.scrollHeight - caixa.scrollTop - caixa.clientHeight < 24;
  caixa.textContent = '';
  if (!linhas.length) {
    caixa.textContent = 'Aguardando o primeiro registro da produção...';
    return;
  }
  linhas.forEach(function(linha) {
    var item = document.createElement('div');
    item.className = classeDaLinha(linha);
    item.textContent = linha;
    caixa.appendChild(item);
  });
  if (noFim) caixa.scrollTop = caixa.scrollHeight;
}

function copiarTextoAlternativo(texto) {
  return new Promise(function(resolve, reject) {
    var campo = document.createElement('textarea');
    campo.value = texto;
    campo.setAttribute('readonly', '');
    campo.style.position = 'fixed';
    campo.style.opacity = '0';
    document.body.appendChild(campo);
    campo.select();
    var copiou = false;
    try { copiou = document.execCommand('copy'); } catch (e) { copiou = false; }
    document.body.removeChild(campo);
    if (copiou) resolve();
    else reject(new Error('Cópia bloqueada pelo navegador.'));
  });
}

function copiarTexto(texto) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(texto).catch(function() {
      return copiarTextoAlternativo(texto);
    });
  }
  return copiarTextoAlternativo(texto);
}

var relogioCopia = null;
function sinalizarCopia(texto, classe) {
  var botao = document.getElementById('btn-copiar-console');
  botao.textContent = texto;
  botao.className = classe;
  clearTimeout(relogioCopia);
  relogioCopia = setTimeout(function() {
    botao.textContent = 'Copiar console';
    botao.className = '';
  }, 2000);
}

function copiarConsole() {
  if (!ultimoLog) {
    mostrarAviso('O console ainda não tem registros para copiar.', 'aviso');
    return;
  }
  copiarTexto(ultimoLog).then(function() {
    sinalizarCopia('✓ Copiado', 'copiado');
  }).catch(function() {
    sinalizarCopia('Não copiado', 'falhou');
    mostrarAviso('O navegador bloqueou a cópia. Selecione o texto do console e use Ctrl+C.', 'erro');
  });
}

function aplicarSelo(saude, mensagem) {
  var selo = SELOS_SAUDE[saude] || SELOS_SAUDE.ocioso;
  var el = document.getElementById('console-status');
  el.textContent = selo.texto;
  el.style.color = selo.cor;

  var msg = document.getElementById('g-msg');
  msg.textContent = mensagem;
  msg.title = mensagem;
  msg.style.color = (saude === 'erro' || saude === 'travado' || saude === 'offline') ? '#fca5a5' : '#cbd5e1';
}

// Recarrega sozinho quando uma nova versão do painel é instalada
var versaoPainel = null;
function verificarVersaoPainel(versao) {
  if (!versao) return;
  if (versaoPainel === null) versaoPainel = versao;
  if (versao !== versaoPainel && document.getElementById('modal').style.display !== 'flex') location.reload();
}

function aplicarStatus(s) {
  verificarVersaoPainel(s.versao_painel);
  var mensagem = s.mensagem || '';
  if (s.saude === 'erro' && s.proxima_tentativa_em) mensagem += ' Nova tentativa às ' + s.proxima_tentativa_em + '.';
  aplicarSelo(s.saude, mensagem);

  var produzindo = s.saude === 'produzindo';
  document.getElementById('g-barra').style.display = produzindo ? 'block' : 'none';
  document.getElementById('g-barra-fill').style.width = (produzindo ? (s.progresso || 0) : 0) + '%';

  varreduraAtiva = s.ativo !== false;
  desenharBotaoVarredura(varreduraAtiva, varreduraAtiva && (s.saude === 'produzindo' || s.saude === 'ocioso'));
}

function desenharBotaoVarredura(ativa, noAr) {
  var b = document.getElementById('b-var');
  b.className = ativa ? 'btn btn-red' : 'btn';
  b.setAttribute('aria-label', ativa ? 'Pausar varredura' : 'Iniciar varredura');
  b.innerHTML = ativa
    ? '<span class="status-ao-vivo"><span class="ponto-ao-vivo' + (noAr ? '' : ' desligado') + '"></span>' +
      (noAr ? 'AO VIVO' : 'OFFLINE') + '</span>❚❚ Pausar'
    : '▶ Iniciar<br>Varredura';
}

function cicloConsole() {
  if (consoleOcupado) return;
  consoleOcupado = true;
  Promise.all([requisitarJson('/api/ti_terminal'), requisitarJson('/api/status')]).then(function(r) {
    var reconectou = falhasConsole > 0;
    falhasConsole = 0;
    renderizarConsole(r[0].linhas || []);
    aplicarStatus(r[1]);
    if (reconectou) atualizarTudo();
  }).catch(function() {
    falhasConsole++;
    desenharBotaoVarredura(varreduraAtiva, false);
    document.getElementById('g-barra').style.display = 'none';
    aplicarSelo('offline', 'Sem conexão com o servidor. Tentando reconectar...');
  }).then(function() {
    consoleOcupado = false;
    var espera = falhasConsole ? Math.min(INTERVALO_MAXIMO_MS, INTERVALO_CONSOLE_MS * Math.pow(2, falhasConsole)) : INTERVALO_CONSOLE_MS;
    clearTimeout(relogioConsole);
    relogioConsole = setTimeout(cicloConsole, espera);
  });
}

function toggleVarredura() {
  var b = document.getElementById('b-var');
  var ativar = !varreduraAtiva;
  b.disabled = true;
  enviarJson('/api/varredura', { ativo: ativar }).then(function(s) {
    aplicarStatus(s);
    mostrarAviso(ativar ? 'Varredura retomada.' : 'Varredura pausada. O ciclo atual termina normalmente.', 'ok');
    if (ativar) return enviarJson('/api/buscar_lives', {});
  }).catch(function(e) {
    mostrarAviso('Não foi possível alterar a varredura: ' + e.message, 'erro');
  }).then(function() { b.disabled = false; });
}

document.addEventListener('visibilitychange', function() {
  if (!document.hidden) {
    clearTimeout(relogioConsole);
    cicloConsole();
  }
});

// Inicialização
atualizarTudo();
iniciarEscritorio();
cicloConsole();
setInterval(atualizarTudo, 5000);
