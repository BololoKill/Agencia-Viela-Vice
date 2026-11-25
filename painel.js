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
    var limiteEnvios = d.limite_envios || 3;
    document.getElementById('m-env').innerText = envios + '/' + limiteEnvios;
    document.getElementById('b-niv').innerHTML = 'Publicação<br>' + envios + '/' + limiteEnvios;
    var canal = d.canal || {};
    document.getElementById('m-canal').innerText = canal.inscritos != null ? Number(canal.inscritos).toLocaleString('pt-BR') : '—';
    document.getElementById('m-canal-sub').innerText = canal.visualizacoes != null
      ? 'inscritos · ' + Number(canal.visualizacoes).toLocaleString('pt-BR') + ' views' : 'inscritos';
    verificarTravaCanal();
    document.getElementById('b-dir').innerHTML = 'Diretoria<br>(' + pend.length + ')';
    document.getElementById('b-fila').innerHTML = 'Fila YouTube<br>(' + agendadosAPublicar(ag).length + ')';
    var limiteEstoque = d.limite_estoque || 9;
    document.getElementById('g-pct').innerText = Math.min(100, Math.round((pend.length / limiteEstoque) * 100)) + '%';
    atualizarStatusEnvios();
  }).catch(function() {});
}

// Player de Avaliação da Diretoria
var listaPendentes = [];
var idxAtual = 0;

function abrirAvaliacao() {
  verModal(TITULO_DIRETORIA, '<div class="card">Carregando os vídeos prontos...</div>');
  fetch('/api/data').then(function(r) { return r.json(); }).then(function(d) {
    dadosServidor = d || {};
    listaPendentes = d.videos || d.pendentes || [];
    idxAtual = 0;
    renderizarPlayer();
  }).catch(function() {
    document.getElementById('m-txt').innerHTML = '<div class="card">Nenhum vídeo encontrado na fila.</div>';
  });
}

// Envios ao YouTube em andamento: o vídeo sai da Diretoria na hora e a curadoria continua
var TITULO_DIRETORIA = 'Diretoria: aprovar ou rejeitar';
var QUADRO_ENVIOS = '<div id="envios-status" style="display:none; font-size:11px; color:#bae6fd; background:#0c4a6e; ' +
  'border:1px solid #0284c7; border-radius:8px; padding:8px 10px; margin-bottom:8px;"></div>';
var enviosEmAndamento = {};
var relogioEnvios = null;

function nomeDoItem(item) {
  return (typeof item === 'string') ? item : (item.filename || item.arquivo || item.nome);
}

function diretoriaAberta() {
  return document.getElementById('modal').style.display === 'flex' &&
    document.getElementById('m-tit').innerText === TITULO_DIRETORIA;
}

function tirarDaLista(nome) {
  for (var i = 0; i < listaPendentes.length; i++) {
    if (nomeDoItem(listaPendentes[i]) === nome) {
      var item = listaPendentes.splice(i, 1)[0];
      if (i < idxAtual) idxAtual--;
      return item;
    }
  }
  return null;
}

function tempoDecorrido(inicio) {
  var segundos = Math.max(0, Math.round((Date.now() - inicio) / 1000));
  return segundos < 60 ? segundos + ' s' : Math.floor(segundos / 60) + ' min ' + (segundos % 60) + ' s';
}

function atualizarStatusEnvios() {
  var nomes = Object.keys(enviosEmAndamento);
  (dadosServidor.enviando || []).forEach(function(n) { if (nomes.indexOf(n) < 0) nomes.push(n); });
  var quadro = document.getElementById('envios-status');
  if (quadro) {
    quadro.style.display = nomes.length ? 'block' : 'none';
    quadro.innerHTML = nomes.length ? nomes.map(function(n) {
      return 'Enviando ao YouTube: <b>' + n + '</b>' + (enviosEmAndamento[n] ? ' (' + tempoDecorrido(enviosEmAndamento[n]) + ')' : '');
    }).join('<br>') + '<div style="color:#94a3b8; margin-top:4px;">Vídeos longos levam alguns minutos. ' +
      'Pode continuar avaliando ou fechar esta janela: o envio continua.</div>' : '';
  }
  var ativos = Object.keys(enviosEmAndamento).length > 0;
  if (ativos && !relogioEnvios) relogioEnvios = setInterval(atualizarStatusEnvios, 1000);
  if (!ativos && relogioEnvios) { clearInterval(relogioEnvios); relogioEnvios = null; }
}

function concluirEnvio(nome) {
  delete enviosEmAndamento[nome];
  atualizarStatusEnvios();
  atualizarTudo();
}

function devolverParaLista(item) {
  if (!item) return;
  listaPendentes.push(item);
  if (diretoriaAberta() && idxAtual === listaPendentes.length - 1) renderizarPlayer();
}

function escaparHtml(texto) {
  return String(texto == null ? '' : texto).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Selo do formato: a Diretoria vê a narração do roteiro ou o aviso de que o vídeo saiu sem ela
function seloFormato(item) {
  if (typeof item !== 'object' || !item) return '';
  var roteiro = item.roteiro || {};
  if (item.formato === 'dark') {
    var fala = roteiro.narracao || roteiro.abertura || '';
    var extra = (roteiro.capitulos && roteiro.capitulos.length) ? ' (+ ' + roteiro.capitulos.length + ' capítulos narrados)' : '';
    return '<div class="card" style="border-color:#16a34a; font-size:11px; margin-bottom:8px;">' +
      '<b style="color:#4ade80;">🎙️ Formato dark: narração própria</b>' +
      '<div style="margin-top:4px; color:#cbd5e1;">' + escaparHtml(fala) + escaparHtml(extra) + '</div></div>';
  }
  return '<div class="card" style="border-color:#dc2626; font-size:11px; color:#fecaca; margin-bottom:8px;">' +
    '<b>⚠ Fora do padrão dark: sem narração própria.</b> O formato antigo não vai mais para o canal: rejeite este vídeo.</div>';
}

function tipoDoItem(item) {
  if (item && typeof item === 'object' && item.tipo) return item.tipo;
  return String(nomeDoItem(item) || '').indexOf('longo-') === 0 ? 'longo' : 'short';
}

function renderizarPlayer() {
  if (!listaPendentes.length || idxAtual >= listaPendentes.length) {
    document.getElementById('m-txt').innerHTML = QUADRO_ENVIOS + '<div class="card" style="text-align:center;">Nenhum vídeo esperando aprovação agora.<br>A equipe está produzindo os próximos!</div>';
    atualizarStatusEnvios();
    return;
  }
  var item = listaPendentes[idxAtual];
  var nome = nomeDoItem(item);
  var tit = (typeof item === 'object' && item.titulo) ? item.titulo : nome.replace('.mp4', '').replace(/_/g, ' ');
  var desc = (typeof item === 'object' && item.descricao) ? item.descricao : 'Inscreva-se no canal Viela Vice! #GTA6 #GTAVI #Shorts';

  document.getElementById('m-txt').innerHTML = QUADRO_ENVIOS +
    '<div style="font-size:11px; color:#94a3b8; margin-bottom:8px;">Arquivo (' + (idxAtual + 1) + '/' + listaPendentes.length + '): <b>' + nome + '</b></div>' +
    seloFormato(item) +
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
  atualizarStatusEnvios();
}

// Estrelas: no padrão dark o canal recebe 1 vídeo longo e 2 Shorts por ciclo, que reinicia às 05:00.
// Os canais ativos vêm do servidor; hoje a agência publica só no canal principal.
var CANAIS_PAINEL = [{ id: '1', nome: '1. Viela Vice (Principal - GTA 6)' }];

function canaisAtivos() {
  return (dadosServidor.canais && dadosServidor.canais.length) ? dadosServidor.canais : CANAIS_PAINEL;
}

function cotaDoCanal(canalId) {
  var cotas = dadosServidor.cotas || {};
  return cotas[canalId] || { usados: 0, limite: 3, bloqueado: false, verificado: false };
}

var NOMES_TIPO = { longo: 'vídeo longo', short: 'Shorts' };

function cotaDoTipo(cota, tipo) {
  var padrao = (dadosServidor.cota_por_tipo || { longo: 1, short: 2 })[tipo] || 0;
  return ((cota.por_tipo || {})[tipo]) || { usados: 0, limite: padrao };
}

function resumoDoCanal(cota) {
  var longo = cotaDoTipo(cota, 'longo'), shorts = cotaDoTipo(cota, 'short');
  return 'longo ' + longo.usados + '/' + longo.limite + ' · Shorts ' + shorts.usados + '/' + shorts.limite;
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
  canaisAtivos().forEach(function(canal) {
    var cota = cotaDoCanal(canal.id);
    html += '<option value="' + canal.id + '">' + escaparHtml(canal.nome) + ' (' + resumoDoCanal(cota) + ')</option>';
  });
  return html;
}

function verificarTravaCanal() {
  var sel = document.getElementById('sel-canal');
  var btn = document.getElementById('btn-enviar-hoje');
  var painel = document.getElementById('estrelas-canal');
  if (!sel || !btn || !painel) return;

  var item = listaPendentes[idxAtual];
  var tipo = tipoDoItem(item);
  var cota = cotaDoCanal(sel.value);
  var doTipo = cotaDoTipo(cota, tipo);
  var situacao = cota.verificado ? 'Hoje neste canal: ' + resumoDoCanal(cota) : 'Confirmando envios no YouTube...';
  painel.innerHTML = '<span>' + situacao + ' · reinicia às 05:00</span>' + desenharEstrelas(cota.usados, cota.limite);
  if (btn.dataset.enviando === '1') return;

  // Padrão dark: o formato antigo não sai, e cada canal recebe 1 longo e 2 Shorts por dia
  var foraDoPadrao = !!item && typeof item === 'object' && item.formato !== 'dark';
  var tipoCompleto = doTipo.usados >= doTipo.limite;
  var bloqueado = foraDoPadrao || !!cota.bloqueado || tipoCompleto;
  btn.disabled = bloqueado;
  btn.style.background = bloqueado ? '#475569' : '#16a34a';
  btn.style.cursor = bloqueado ? 'not-allowed' : 'pointer';
  btn.textContent = foraDoPadrao ? 'Fora do padrão dark · rejeite este vídeo'
    : cota.bloqueado ? 'Bloqueado (' + cota.usados + '/' + cota.limite + ') · Libera às 05:00'
    : tipoCompleto ? 'Canal já tem ' + doTipo.usados + '/' + doTipo.limite + ' ' + NOMES_TIPO[tipo] + ' hoje · libera às 05:00'
    : 'Aprovar & Enviar (' + NOMES_TIPO[tipo] + ' ' + doTipo.usados + '/' + doTipo.limite + ' hoje)';
}

function bloquearAcoes(bloquear) {
  var botoes = document.querySelectorAll('#m-txt .act-btn');
  for (var i = 0; i < botoes.length; i++) {
    botoes[i].disabled = bloquear;
    botoes[i].dataset.enviando = bloquear ? '1' : '';
  }
}

function aprovarVideo(nome) {
  if (enviosEmAndamento[nome]) return;
  var vid = document.getElementById('player-review');
  if (vid) { vid.pause(); vid.removeAttribute('src'); vid.load(); }
  var corpo = {
    filename: nome, arquivo: nome,
    canal: document.getElementById('sel-canal').value,
    titulo: document.getElementById('inp-tit').value,
    descricao: document.getElementById('inp-desc').value
  };
  // O envio segue sozinho: a Diretoria já mostra o próximo vídeo
  enviosEmAndamento[nome] = Date.now();
  var item = tirarDaLista(nome);
  renderizarPlayer();
  mostrarAviso('Envio iniciado: ' + nome + '. Ele entra na Fila do YouTube quando terminar.', '');
  enviarJson('/api/aprovar', corpo, LIMITE_ENVIO_MS).then(function(d) {
    concluirEnvio(nome);
    mostrarAviso(d.message || 'Vídeo aprovado!', d.enviado_youtube === false ? 'aviso' : 'ok');
  }).catch(function(e) {
    concluirEnvio(nome);
    if (e.dados && e.dados.em_andamento) {
      mostrarAviso(e.message, 'aviso');
      return;
    }
    devolverParaLista(item);
    mostrarAviso('Não foi possível aprovar ' + nome + ': ' + e.message + ' Ele voltou para a Diretoria.', 'erro');
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

// A fila mostra só o que ainda vai ao ar; o que já foi publicado fica no histórico
function horaDePublicacao(v) {
  return (v && v.data && v.horario) ? new Date(v.data + 'T' + v.horario + ':00') : null;
}

function agendadosAPublicar(ag) {
  var agora = new Date();
  return (ag || []).filter(function(v) {
    var quando = horaDePublicacao(v);
    return !!(v && v.youtube_id && quando && quando > agora);
  }).sort(function(a, b) { return horaDePublicacao(a) - horaDePublicacao(b); });
}

function abrirFila() {
  var ag = dadosServidor.agendados || dadosServidor.fila || [];
  var futuros = agendadosAPublicar(ag);
  var publicados = ag.filter(function(v) { return v && v.youtube_id; }).length - futuros.length;
  var rodape = publicados > 0 ? '<div style="font-size:11px; color:#94a3b8; margin-top:8px;">' + publicados +
    ' vídeo(s) já publicado(s) ficam fora da fila.</div>' : '';
  if (!futuros.length) {
    verModal('Fila Programada no YouTube', '<div class="card" style="text-align:center;">Nenhum vídeo agendado para ir ao ar.</div>' + rodape);
    return;
  }
  var h = '';
  futuros.forEach(function(v) {
    var tit = escaparHtml(v.titulo || v.title || v.filename);
    var tipo = tipoDoItem(v) === 'longo' ? 'Vídeo longo' : 'Short';
    h += '<div class="card"><b>' + tit + '</b><div style="font-size:11px; color:#38bdf8; margin-top:4px;">' + tipo +
      ' · vai ao ar em ' + v.data.split('-').reverse().join('/') + ' às ' + v.horario + ' · ' + escaparHtml(v.canal_nome || ('Canal ' + v.canal)) + '</div></div>';
  });
  verModal('Fila Programada no YouTube (' + futuros.length + ')', h + rodape);
}

function abrirNivel() {
  var porTipo = dadosServidor.cota_por_tipo || { longo: 1, short: 2 };
  var horarios = dadosServidor.horarios_por_tipo || { longo: ['17:00'], short: ['12:00', '19:00'] };
  var html = '<div class="card" style="font-size:12px;">A Beatriz agenda o que você aprova: <b>' + porTipo.longo + ' vídeo longo às ' +
    horarios.longo.join(' e ') + '</b> e <b>' + porTipo.short + ' Shorts às ' + horarios.short.join(' e às ') + '</b>, por dia. ' +
    'Cada estrela é um envio; elas reiniciam às 05:00.</div>';
  canaisAtivos().forEach(function(canal) {
    var cota = cotaDoCanal(canal.id);
    var situacao = cota.bloqueado
      ? '<span style="color:#f87171; font-weight:700;">Bloqueado até as 05:00 (' + cota.usados + '/' + cota.limite + ')</span>'
      : (cota.verificado ? 'Hoje: ' + resumoDoCanal(cota) : 'Confirmando envios no YouTube...');
    html += '<div class="card" style="display:flex; justify-content:space-between; align-items:center; gap:12px;">' +
      '<div><b>' + canal.nome + '</b><div style="font-size:11px; color:#94a3b8;">' + situacao + '</div></div>' +
      desenharEstrelas(cota.usados, cota.limite) +
    '</div>';
  });
  verModal('Publicação de hoje', html);
}

function situacaoDaIa(ia, nome) {
  if (!ia) return '<b>' + nome + ':</b> aparece após o próximo reinício do painel.';
  if (ia.sem_chave) return '<b>' + nome + ':</b> <span style="color:#fca5a5;">sem a chave do Google (GEMINI_API_KEY)</span>';
  if (ia.pausada_ate) return '<b>' + nome + ':</b> <span style="color:#fde68a;">fora do ar, nova tentativa às ' + escaparHtml(ia.pausada_ate) + '</span>';
  return '<b>' + nome + ':</b> <span style="color:#86efac;">disponível</span>';
}

function abrirSuporteTI() {
  var ia = dadosServidor.ia || {};
  verModal('Suporte T.I.',
    '<div class="card" style="font-size:12px;">O Caio cuida do computador e dos downloads. A IA do Google escreve os roteiros (Thiago) e confere o jogo na imagem (Camila); sem ela, a produção espera.</div>' +
    '<div class="card" id="ti-maquina" style="font-size:12px;">Medindo o computador...</div>' +
    '<div class="card" style="font-size:12px; line-height:1.8;">' + situacaoDaIa(ia.roteiro, 'IA de roteiro') + '<br>' + situacaoDaIa(ia.visao, 'IA que confere o jogo') + '</div>' +
    '<div class="card" style="text-align:center;"><p style="margin-bottom:10px; font-size:12px;">Os trechos baixados são apagados ao fim de cada ciclo. Se sobrar algo de um ciclo interrompido:</p>' +
      '<button onclick="purgarTI()" style="background:#dc2626; color:#fff; border:none; padding:10px 20px; border-radius:8px; font-weight:700; cursor:pointer;">Limpar temporários</button></div>'
  );
  requisitarJson('/api/ti_diagnostico').then(function(m) {
    var caixa = document.getElementById('ti-maquina');
    if (caixa) caixa.innerHTML = '<b>Processador:</b> ' + m.cpu + '% · <b>Memória:</b> ' + m.ram + '% · <b>Disco livre:</b> ' + m.disco_livre_gb +
      ' GB<br><b>Arquivos temporários:</b> ' + m.qtd_brutos + ' · <b>Vídeos prontos na pasta:</b> ' + m.qtd_prontos;
  }).catch(function() {
    var caixa = document.getElementById('ti-maquina');
    if (caixa) caixa.textContent = 'Não foi possível medir o computador agora.';
  });
}

function purgarTI() {
  enviarJson('/api/ti/purge', {}).then(function(d) {
    mostrarAviso(d.removidos + ' arquivo(s) temporário(s) removido(s).', 'ok');
    atualizarTudo();
  }).catch(function(e) { mostrarAviso(e.message, 'aviso'); });
}

// Comunicação com o servidor
var LIMITE_PADRAO_MS = 8000;
var LIMITE_ENVIO_MS = 3600000;  // Envios saem um por vez: a vez de um vídeo pode demorar

function requisitarJson(url, opcoes, limiteMs) {
  var cfg = opcoes || {};
  var controle = new AbortController();
  var relogio = setTimeout(function() { controle.abort(); }, limiteMs || LIMITE_PADRAO_MS);
  cfg.signal = controle.signal;
  return fetch(url, cfg).then(function(r) {
    return r.json().catch(function() { return {}; }).then(function(d) {
      if (!r.ok) {
        var erro = new Error(d.error || d.message || ('Servidor respondeu ' + r.status));
        erro.dados = d;
        throw erro;
      }
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
  statusAtual = s || {};
  verificarVersaoPainel(s.versao_painel);
  var quem = agenteTrabalhandoAgora();
  var caixaQuem = document.getElementById('g-quem');
  if (caixaQuem) caixaQuem.textContent = quem && FUNCOES[quem] ? 'Com: ' + nomeDoAgente(quem) + ' — ' + FUNCOES[quem].titulo : '';
  if (s.saude === 'produzindo' && typeof anunciarTarefa === 'function') anunciarTarefa(s.etapa);
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
  b.setAttribute('aria-label', ativa ? 'Pausar a produção' : 'Ligar a produção');
  b.innerHTML = ativa
    ? '<span class="status-ao-vivo"><span class="ponto-ao-vivo' + (noAr ? '' : ' desligado') + '"></span>' +
      (noAr ? 'PRODUZINDO' : 'PARADA') + '</span>❚❚ Pausar'
    : '▶ Ligar<br>Produção';
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
    mostrarAviso(ativar ? 'Produção ligada.' : 'Produção pausada. O vídeo em andamento termina normalmente.', 'ok');
    if (ativar) return enviarJson('/api/buscar_lives', {});
  }).catch(function(e) {
    mostrarAviso('Não foi possível ligar ou pausar a produção: ' + e.message, 'erro');
  }).then(function() { b.disabled = false; });
}

document.addEventListener('visibilitychange', function() {
  if (!document.hidden) {
    clearTimeout(relogioConsole);
    cicloConsole();
  }
});


// ---------- A equipe: cada pessoa do escritório é uma etapa real da produção ----------
var FUNCOES = {
  bruno: { etapa: 1, titulo: 'Busca dos vídeos virais',
    descricao: 'Procura no YouTube os vídeos de GTA 6 em português mais vistos da semana, com pelo menos 100 mil visualizações e um por criador. Vídeo em inglês, Short e reportagem de TV ficam de fora.',
    botao: ['Ver os virais da vez', 'abrirVirais()'] },
  caio: { etapa: 2, titulo: 'Download e computador',
    descricao: 'Baixa só 6 minutos de cada vídeo viral, imagem e som separados. Se o YouTube derrubar a conexão, continua de onde parou, e a parte que chegar cortada é baixada de novo sozinha. Se o trecho tiver pouca fala, tenta o meio do vídeo e guarda isso para não baixar o mesmo trecho de novo. Também cuida do disco e dos arquivos temporários.',
    botao: ['Abrir Suporte T.I.', 'abrirSuporteTI()'] },
  camila: { etapa: 3, titulo: 'Curadoria e auditoria',
    descricao: 'Confere com a IA de imagem se o vídeo é mesmo GTA 6 e se a fala é em português. No fim, faz a auditoria técnica de cada vídeo pronto (imagem, som e sincronia) antes de ele chegar à Diretoria.',
    botao: ['Ver os vídeos na Diretoria', 'abrirAvaliacao()'] },
  thiago: { etapa: 4, titulo: 'Roteiro e narração',
    descricao: 'Transcreve a fala do criador, escreve o roteiro com a IA do Google (título, gancho e narração) e grava a narração. Se a IA cair, a produção espera: nenhum vídeo sai sem narração própria.',
    botao: ['Ver a IA no Suporte T.I.', 'abrirSuporteTI()'] },
  lucas: { etapa: 5, titulo: 'Edição dos Shorts',
    descricao: 'Monta um Short de 45 a 60 segundos com o melhor momento de cada vídeo viral: gancho na tela, legendas, narração no começo, marca da Viela Vice e chamada final.',
    botao: ['Ver os vídeos na Diretoria', 'abrirAvaliacao()'] },
  mariana: { etapa: 6, titulo: 'Edição do Top 5 da semana',
    descricao: 'Monta o vídeo longo de 8min30 em contagem regressiva, com um trecho de cada vídeo viral, a narração apresentando cada um e o nome do criador na tela.',
    botao: ['Ver os vídeos na Diretoria', 'abrirAvaliacao()'] },
  dr_ricardo: { etapa: 7, titulo: 'Diretoria (a sua aprovação)',
    descricao: 'Representa você: todo vídeo pronto espera aqui. Só o que você aprovar vai para o YouTube; o que você rejeitar é apagado.',
    botao: ['Avaliar os vídeos', 'abrirAvaliacao()'] },
  beatriz: { etapa: 8, titulo: 'Publicação e horários',
    descricao: 'Agenda no YouTube o que foi aprovado: 1 vídeo longo às 17:00 e 2 Shorts, às 12:00 e às 19:00, por dia. Controla a cota do canal e o horário de cada vídeo.',
    botao: ['Ver a publicação de hoje', 'abrirNivel()'] }
};

var BOTOES_DO_PAINEL = [
  ['Diretoria', 'Assistir, aprovar ou rejeitar os vídeos prontos. Aprovar envia ao YouTube no próximo horário livre.'],
  ['Fila YouTube', 'Vídeos já enviados que ainda vão ao ar, com dia e hora.'],
  ['Publicação', 'Quantos vídeos o canal recebeu hoje: 1 longo e 2 Shorts por dia, cada um no seu horário.'],
  ['Virais da vez', 'Os vídeos de GTA 6 mais vistos escolhidos no último ciclo, com as visualizações.'],
  ['Suporte T.I.', 'Computador (processador, memória e disco), situação da IA do Google e limpeza de temporários.'],
  ['Produzindo / Pausar', 'Liga ou pausa a produção automática. O vídeo em andamento termina normalmente.'],
  ['Atualizar', 'Recarrega os números do painel.'],
  ['Equipe e funções', 'Este guia. Clique em qualquer pessoa do escritório para ver a função dela.']
];

var statusAtual = {};

function nomeDoAgente(id) {
  var lista = (typeof AGENTES !== 'undefined') ? AGENTES : [];
  var ag = lista.filter(function(a) { return a.id === id; })[0];
  return ag ? ag.nome : id;
}

function agenteTrabalhandoAgora() {
  if (statusAtual.saude !== 'produzindo') return null;
  return (typeof agenteDaEtapa === 'function') ? agenteDaEtapa(statusAtual.etapa) : null;
}

function cartaoDaFuncao(id, comBotao) {
  var f = FUNCOES[id];
  var agora = agenteTrabalhandoAgora() === id;
  var botao = comBotao && f.botao ? '<button class="botao-funcao" onclick="' + f.botao[1] + '">' + escaparHtml(f.botao[0]) + '</button>' : '';
  return '<div class="card funcao' + (agora ? ' agora' : '') + '"><div class="etapa">' + f.etapa + '</div><div>' +
    '<h4>' + escaparHtml(f.titulo) + '</h4><div class="quem">' + escaparHtml(nomeDoAgente(id)) + '</div>' +
    '<p>' + escaparHtml(f.descricao) + '</p>' +
    (agora ? '<div class="status-agora">● Trabalhando agora: ' + escaparHtml(statusAtual.etapa || '') + '</div>' : '') +
    botao + '</div></div>';
}

function abrirFuncaoDoAgente(id) {
  if (!FUNCOES[id]) return;
  verModal(nomeDoAgente(id) + ' — ' + FUNCOES[id].titulo, cartaoDaFuncao(id, true));
}

function abrirGuiaDaEquipe(emReuniao) {
  var ordem = Object.keys(FUNCOES).sort(function(a, b) { return FUNCOES[a].etapa - FUNCOES[b].etapa; });
  var html = (emReuniao ? '<div class="card" style="font-size:12px;">A equipe foi para a sala de reunião e cada um explica a sua parte. ' +
      'Um vídeo passa pelas 8 etapas abaixo, nesta ordem.</div>' : '') +
    '<div class="guia-secao">Como um vídeo nasce</div>' +
    ordem.map(function(id) { return cartaoDaFuncao(id, false); }).join('') +
    '<div class="guia-secao">Botões do painel</div><table class="guia-botoes" style="width:100%; border-collapse:collapse;">' +
    BOTOES_DO_PAINEL.map(function(b) { return '<tr><td>' + escaparHtml(b[0]) + '</td><td>' + escaparHtml(b[1]) + '</td></tr>'; }).join('') +
    '</table>';
  verModal('Equipe e funções', html);
}

function abrirVirais() {
  var virais = statusAtual.virais || [];
  var explicacao = '<div class="card" style="font-size:12px;">O Bruno pega os vídeos de GTA 6 em português mais vistos da semana ' +
    '(mínimo de 100 mil visualizações, um por criador). Cada vídeo rende no máximo 1 Short e 1 trecho do Top 5, com crédito e link do vídeo original.</div>';
  if (!virais.length) {
    verModal('Virais da vez', explicacao + '<div class="card" style="text-align:center;">A lista aparece aqui quando o próximo ciclo fizer a busca.</div>');
    return;
  }
  var linhas = virais.map(function(v, i) {
    return '<tr><td>' + (i + 1) + '. <b>' + escaparHtml(v.streamer) + '</b><div style="color:#94a3b8;">' + escaparHtml(v.titulo || '') +
      '</div></td><td>' + Number(v.visualizacoes || 0).toLocaleString('pt-BR') + ' views</td></tr>';
  }).join('');
  verModal('Virais da vez', explicacao + '<table class="tabela-virais" style="width:100%; border-collapse:collapse;">' + linhas + '</table>');
}

// Inicialização
atualizarTudo();
iniciarEscritorio();
cicloConsole();
setInterval(atualizarTudo, 5000);
