var dadosServidor = {};

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

function atualizarTudo() {
  fetch('/api/data').then(function(r) { return r.json(); }).then(function(d) {
    dadosServidor = d || {};
    var pend = d.videos || d.pendentes || d.exportacao || [];
    var ag = d.agendados || d.fila || [];
    document.getElementById('m-est').innerText = pend.length;
    document.getElementById('m-env').innerText = ag.length + '/42';
    document.getElementById('b-dir').innerHTML = 'Diretoria<br>(' + pend.length + ')';
    document.getElementById('b-fila').innerHTML = 'Fila YouTube<br>(' + ag.length + ')';
    document.getElementById('g-pct').innerText = Math.min(100, Math.round((pend.length / 60) * 100)) + '%';
  }).catch(function() {});
}

function abrirAvaliacao() { verModal('Diretoria', 'Base da Parte 1 funcionando! Vamos adicionar o player na Parte 2.'); }
function abrirCuradoriaTop() { verModal('Curadoria Top', 'Base da Parte 1 funcionando!'); }
function abrirFila() { verModal('Fila YouTube', 'Base da Parte 1 funcionando!'); }
function abrirNivel() { verModal('Nivel 6 Estrelas', 'Base da Parte 1 funcionando!'); }
function abrirSuporteTI() { verModal('Suporte T.I.', 'Base da Parte 1 funcionando!'); }
function abrirReuniao() { verModal('Reuniao', 'Protocolo de Curadoria ativo.'); }
function toggleVarredura() { verModal('Varredura', 'Status alterado.'); }

atualizarTudo();
var listaPendentes = [];
var idxAtual = 0;

function abrirAvaliacao() {
  verModal('Curadoria & Aprovação (Ciclo de Hoje)', '<div class="card">Carregando vídeos da fila...</div>');
  fetch('/api/data').then(function(r) { return r.json(); }).then(function(d) {
    dadosServidor = d || {};
    listaPendentes = d.videos || d.pendentes || d.exportacao || [];
    idxAtual = 0;
    renderizarPlayer();
  }).catch(function() {
    document.getElementById('m-txt').innerHTML = '<div class="card">Nenhum vídeo encontrado na fila.</div>';
  });
}

function renderizarPlayer() {
  if (!listaPendentes.length || idxAtual >= listaPendentes.length) {
    document.getElementById('m-txt').innerHTML = '<div class="card" style="text-align:center;">Nenhum vídeo pendente na fila no momento.</div>';
    return;
  }
  var item = listaPendentes[idxAtual];
  var nome = (typeof item === 'string') ? item : (item.filename || item.arquivo || item.nome);
  var tit = (typeof item === 'object' && item.titulo) ? item.titulo : nome.replace('.mp4', '').replace(/_/g, ' ');
  var desc = (typeof item === 'object' && item.descricao) ? item.descricao : 'Inscreva-se no canal Viela Vice! #GTA6 #GTARP #Shorts';

  document.getElementById('m-txt').innerHTML =
    '<div style="font-size:11px; color:#94a3b8; margin-bottom:8px;">Arquivo (' + (idxAtual + 1) + '/' + listaPendentes.length + '): <b>' + nome + '</b></div>' +
    '<video id="player-review" controls autoplay playsinline style="width:100%; max-height:240px; background:#000; border-radius:8px; border:1px solid #334155;" src="/exportacao/' + encodeURIComponent(nome) + '"></video>' +
    '<select id="sel-canal">' +
      '<option value="1">1. Viela Vice (Principal - GTA 6)</option>' +
      '<option value="2">2. Viela Vice RP (Policia e Fugas)</option>' +
      '<option value="3">3. Viela Vice Clipes (Memes e Zueira)</option>' +
      '<option value="4">4. Viela Vice Stories (Historias)</option>' +
      '<option value="5">5. Viela Vice Underground (Favela)</option>' +
      '<option value="6">6. Viela Vice News (Vazamentos GTA 6)</option>' +
      '<option value="7">7. Viela Vice Best Moments</option>' +
    '</select>' +
    '<input id="inp-tit" value="' + tit.replace(/"/g, '&quot;') + '">' +
    '<textarea id="inp-desc" rows="2">' + desc + '</textarea>' +
    '<div class="row-btns">' +
      '<button class="act-btn" style="background:#16a34a;" onclick="aprovarVideo(\'' + nome + '\')">Aprovar &amp; Enviar Hoje</button>' +
      '<button class="act-btn" style="background:#d97706;" onclick="idxAtual++; renderizarPlayer();">Pular / Guardar</button>' +
      '<button class="act-btn" style="background:#dc2626;" onclick="negarVideo(\'' + nome + '\')">Rejeitar / Falha</button>' +
    '</div>';
}

function aprovarVideo(nome) {
  var vid = document.getElementById('player-review');
  if (vid) { vid.pause(); vid.removeAttribute('src'); vid.load(); }
  fetch('/api/aprovar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      filename: nome, arquivo: nome,
      canal: document.getElementById('sel-canal').value,
      titulo: document.getElementById('inp-tit').value,
      descricao: document.getElementById('inp-desc').value
    })
  }).then(function() {
    listaPendentes.splice(idxAtual, 1);
    renderizarPlayer();
    atualizarTudo();
  }).catch(function() { renderizarPlayer(); });
}

function negarVideo(nome) {
  if (!confirm('Rejeitar video e remover da exportacao?')) return;
  var vid = document.getElementById('player-review');
  if (vid) { vid.pause(); vid.removeAttribute('src'); vid.load(); }
  setTimeout(function() {
    fetch('/api/negar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: nome, arquivo: nome })
    }).then(function() {
      listaPendentes.splice(idxAtual, 1);
      renderizarPlayer();
      atualizarTudo();
    }).catch(function() { listaPendentes.splice(idxAtual, 1); renderizarPlayer(); });
  }, 300);
}

function abrirCuradoriaTop() {
  var total = (dadosServidor.videos || dadosServidor.pendentes || dadosServidor.exportacao || []).length;
  verModal('Curadoria Top', '<div style="text-align:center; padding:20px;"><div style="margin-bottom:14px;">' + total + ' videos validados na fila.</div><button onclick="abrirAvaliacao()" style="background:#2563eb; color:#fff; border:none; padding:10px 22px; border-radius:8px; font-weight:700; cursor:pointer;">Abrir Avaliacao</button></div>');
}
var varreduraAtiva = true;

function abrirFila() {
  var ag = dadosServidor.agendados || dadosServidor.fila || [];
  if (!ag.length) {
    verModal('Fila Programada de Hoje', '<div class="card" style="text-align:center;">Nenhum video enviado na fila de hoje ainda.</div>');
    return;
  }
  var h = '';
  for (var i = 0; i < ag.length; i++) {
    var v = ag[i];
    var tit = v.titulo || v.title || v.filename || v;
    h += '<div class="card"><b>' + tit + '</b></div>';
  }
  verModal('Fila Programada de Hoje (' + ag.length + '/42)', h);
}

function abrirNivel() {
  var canais = [
    '1. Viela Vice (Principal - GTA 6)',
    '2. Viela Vice RP (Policia e Fugas)',
    '3. Viela Vice Clipes (Memes e Zueira)',
    '4. Viela Vice Stories (Historias)',
    '5. Viela Vice Underground (Favela)',
    '6. Viela Vice News (Vazamentos GTA 6)',
    '7. Viela Vice Best Moments'
  ];
  var html = '';
  for (var i = 0; i < canais.length; i++) {
    html += '<div class="card" style="display:flex; justify-content:space-between; align-items:center;"><div><b>' + canais[i] + '</b><div style="font-size:11px; color:#94a3b8;">Cota Diaria: 0/6</div></div><div style="color:#facc15; font-size:15px;">★★★★★</div></div>';
  }
  verModal('★ Nivel de Procurado (Cota Diaria 6/6)', html);
}

function abrirSuporteTI() {
  verModal('Painel de Manutencao T.I.',
    '<div class="card" style="text-align:center;">' +
      '<p style="margin-bottom:12px;"><b>Controle de Qualidade e Purga:</b> Videos rejeitados pela Diretoria sao deletados. Use o botao abaixo para limpar residuos da exportacao.</p>' +
      '<button onclick="purgarTI()" style="background:#dc2626; color:#fff; border:none; padding:10px 20px; border-radius:8px; font-weight:700; cursor:pointer;">Purgar Fila e Arquivos Invalidos</button>' +
    '</div>'
  );
}

function purgarTI() {
  if (!confirm('Deseja realmente purgar a fila e limpar arquivos invalidos?')) return;
  fetch('/api/ti/purge', { method: 'POST' }).then(function() {
    alert('Manutencao de T.I. concluida!');
    atualizarTudo();
  }).catch(function() { alert('Manutencao de T.I. concluida!'); });
}

function toggleVarredura() {
  varreduraAtiva = !varreduraAtiva;
  var b = document.getElementById('b-var');
  var m = document.getElementById('g-msg');
  b.className = varreduraAtiva ? 'btn btn-red' : 'btn';
  b.innerHTML = varreduraAtiva ? 'Stop<br>Varredura' : 'Iniciar<br>Varredura';
  m.innerText = varreduraAtiva ? 'Varredura ativa e gerando estoque...' : 'Varredura pausada.';
  if (varreduraAtiva) { fetch('/api/buscar_lives', { method: 'POST' }).catch(function() {}); }
}

setInterval(atualizarTudo, 5000);
function obterInicioCiclo5AM() {
  var agora = new Date();
  var inicio = new Date(agora.getFullYear(), agora.getMonth(), agora.getDate(), 5, 0, 0, 0);
  if (agora.getHours() < 5) {
    inicio.setDate(inicio.getDate() - 1);
  }
  return inicio.getTime();
}

function contarEnviosCanalHoje(canalId) {
  var ag = dadosServidor.agendados || dadosServidor.enviados_hoje || dadosServidor.fila || [];
  var inicioCiclo = obterInicioCiclo5AM();
  var qtd = 0;
  for (var i = 0; i < ag.length; i++) {
    var item = ag[i];
    var itemCanal = String(item.canal || item.channel || '1');
    if (itemCanal.indexOf(String(canalId)) === 0) {
      var ts = item.timestamp ? Number(item.timestamp) * 1000 : (item.data_envio ? Date.parse(item.data_envio) : Date.now());
      if (isNaN(ts) || ts >= inicioCiclo) {
        qtd++;
      }
    }
  }
  return qtd > 6 ? 6 : qtd;
}

function verificarTravaCanal() {
  var sel = document.getElementById('sel-canal');
  var btn = document.getElementById('btn-enviar-hoje');
  if (!sel || !btn) return;
  var qtd = contarEnviosCanalHoje(sel.value);
  if (qtd >= 6) {
    btn.disabled = true;
    btn.style.background = '#475569';
    btn.style.cursor = 'not-allowed';
    btn.innerText = 'Bloqueado (6/6 Estrelas - Libera 5h AM)';
  } else {
    btn.disabled = false;
    btn.style.background = '#16a34a';
    btn.style.cursor = 'pointer';
    btn.innerHTML = 'Aprovar &amp; Enviar Hoje (' + qtd + '/6)';
  }
}

var renderizarPlayerOriginal = renderizarPlayer;
renderizarPlayer = function() {
  renderizarPlayerOriginal();
  var sel = document.getElementById('sel-canal');
  var botoes = document.querySelectorAll('.act-btn');
  if (sel && botoes.length > 0) {
    botoes.id = 'btn-enviar-hoje';
    sel.onchange = verificarTravaCanal;
    verificarTravaCanal();
  }
};

var aprovarVideoOriginal = aprovarVideo;
aprovarVideo = function(nome) {
  var sel = document.getElementById('sel-canal');
  if (sel && contarEnviosCanalHoje(sel.value) >= 6) {
    alert('Este canal ja atingiu o limite diario de 6 estrelas! Novos envios liberam as 05:00 AM.');
    return;
  }
  aprovarVideoOriginal(nome);
};
function obterInicioCiclo5AM() {
  var agora = new Date();
  var inicio = new Date(agora.getFullYear(), agora.getMonth(), agora.getDate(), 5, 0, 0, 0);
  if (agora.getHours() < 5) {
    inicio.setDate(inicio.getDate() - 1);
  }
  return inicio.getTime();
}

function contarEnviosCanalHoje(canalId) {
  var ag = dadosServidor.agendados || dadosServidor.enviados_hoje || dadosServidor.fila || [];
  var inicioCiclo = obterInicioCiclo5AM();
  var qtd = 0;
  for (var i = 0; i < ag.length; i++) {
    var item = ag[i];
    var itemCanal = String(item.canal || item.channel || '1');
    if (itemCanal.indexOf(String(canalId)) === 0) {
      var ts = item.timestamp ? Number(item.timestamp) * 1000 : (item.data_envio ? Date.parse(item.data_envio) : Date.now());
      if (isNaN(ts) || ts >= inicioCiclo) {
        qtd++;
      }
    }
  }
  return qtd > 6 ? 6 : qtd;
}

function abrirNivel() {
  var canais = [
    { id: '1', nome: '1. Viela Vice (Principal - GTA 6)' },
    { id: '2', nome: '2. Viela Vice RP (Policia e Fugas)' },
    { id: '3', nome: '3. Viela Vice Clipes (Memes e Zueira)' },
    { id: '4', nome: '4. Viela Vice Stories (Historias)' },
    { id: '5', nome: '5. Viela Vice Underground (Favela)' },
    { id: '6', nome: '6. Viela Vice News (Vazamentos GTA 6)' },
    { id: '7', nome: '7. Viela Vice Best Moments' }
  ];
  var html = '<div style="font-size:11px; color:#94a3b8; margin-bottom:10px;">Limite API Gratuita YouTube: <b>6 videos/dia por canal</b> (reseta as 05:00 AM).</div>';
  for (var i = 0; i < canais.length; i++) {
    var c = canais[i];
    var qtd = contarEnviosCanalHoje(c.id);
    var estrelas = '';
    for (var s = 1; s <= 6; s++) {
      estrelas += (s <= qtd) ? '<span style="color:#facc15;">★</span>' : '<span style="color:#334155;">☆</span>';
    }
    var statusCota = (qtd >= 6) ? '<span style="color:#ef4444; font-weight:700;">Cota Diaria: 6/6 (BLOQUEADO ATE 5H AM)</span>' : 'Cota Diaria: ' + qtd + '/6';
    html += '<div class="card" style="display:flex; justify-content:space-between; align-items:center; padding:10px 14px;">' +
              '<div><b>' + c.nome + '</b><div style="font-size:11px; color:#94a3b8;">' + statusCota + '</div></div>' +
              '<div style="font-size:16px; letter-spacing:2px;">' + estrelas + '</div>' +
            '</div>';
  }
  verModal('★ Nivel de Procurado (Controle API YouTube 6/6)', html);
}

function verificarTravaCanal() {
  var sel = document.getElementById('sel-canal');
  var btn = document.getElementById('btn-enviar-hoje');
  if (!sel || !btn) return;
  var qtd = contarEnviosCanalHoje(sel.value);
  if (qtd >= 6) {
    btn.disabled = true;
    btn.style.background = '#475569';
    btn.style.cursor = 'not-allowed';
    btn.innerText = 'Bloqueado (6/6 Estrelas - Libera 5h AM)';
  } else {
    btn.disabled = false;
    btn.style.background = '#16a34a';
    btn.style.cursor = 'pointer';
    btn.innerHTML = 'Aprovar &amp; Enviar Hoje (' + qtd + '/6)';
  }
}

var renderizarPlayerBase = renderizarPlayer;
renderizarPlayer = function() {
  renderizarPlayerBase();
  var sel = document.getElementById('sel-canal');
  var botoes = document.querySelectorAll('.act-btn');
  if (sel && botoes.length > 0) {
    botoes.id = 'btn-enviar-hoje';
    sel.onchange = verificarTravaCanal;
    verificarTravaCanal();
  }
};

var aprovarVideoBase = aprovarVideo;
aprovarVideo = function(nome) {
  var sel = document.getElementById('sel-canal');
  if (sel && contarEnviosCanalHoje(sel.value) >= 6) {
    alert('Canal atingiu o limite diario de 6 estrelas! Novos envios liberam as 05:00 AM.');
    return;
  }
  aprovarVideoBase(nome);
};
function atualizarLogsAoVivo() {
  fetch('/api/logs_vigia').then(function(r) { return r.json(); }).then(function(d) {
    if (d.etapa) {
      document.getElementById('g-msg').innerText = d.etapa;
    }
    if (d.logs && d.logs.length) {
      var ult = d.logs.slice(-6);
      var h = '';
      for (var i = 0; i < ult.length; i++) {
        var cor = ult[i].indexOf('ERRO') !== -1 ? '#fca5a5' : (ult[i].indexOf('SUCESSO') !== -1 ? '#86efac' : '#93c5fd');
        h += '<div style="color:' + cor + '; margin-bottom:3px;">' + ult[i] + '</div>';
      }
      document.getElementById('logs').innerHTML = h;
    }
  }).catch(function() {});
}
setInterval(atualizarLogsAoVivo, 3000);
atualizarLogsAoVivo();
