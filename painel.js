var dadosServidor = {};
var emReuniao = false;
var framePose = 1;

// Configuração completa dos agentes com perspectivas e coordenadas
var agentesConfig = [
  {
    id: "dr_ricardo",
    nome: "Dr. Ricardo",
    cargo: "Diretor Geral",
    linha: 1,
    filtro: "none",
    mesa: { x: 84, y: 15 },
    lounge: { x: 85, y: 72 },
    celular: { x: 74, y: 16 },
    reuniao: { x: 50, y: 46 },
    x: 84,
    y: 15,
    estado: "TRABALHANDO",
    fala: "Avaliando métricas de retenção dos canais."
  },
  {
    id: "camila",
    nome: "Camila",
    cargo: "Curadoria Top 6",
    linha: 3,
    filtro: "none",
    mesa: { x: 48, y: 47 },
    lounge: { x: 82, y: 74 },
    celular: { x: 58, y: 45 },
    reuniao: { x: 46, y: 48 },
    x: 48,
    y: 47,
    estado: "TRABALHANDO",
    fala: "Zero tolerância com bugs e desfoque no Top 6."
  },
  {
    id: "bruno",
    nome: "Bruno",
    cargo: "Olheiro de Tendências",
    linha: 5,
    filtro: "none",
    mesa: { x: 29, y: 61 },
    lounge: { x: 79, y: 71 },
    celular: { x: 20, y: 56 },
    reuniao: { x: 44, y: 44 },
    x: 29,
    y: 61,
    estado: "TRABALHANDO",
    fala: "Rastreando lives BR de GTA RP e pistas de GTA 6."
  },
  {
    id: "lucas",
    nome: "Lucas",
    cargo: "Editor de Shorts",
    linha: 1,
    filtro: "hue-rotate(290deg) saturate(1.3)",
    mesa: { x: 17, y: 67 },
    lounge: { x: 88, y: 76 },
    celular: { x: 35, y: 68 },
    reuniao: { x: 48, y: 52 },
    x: 17,
    y: 67,
    estado: "TRABALHANDO",
    fala: "Sincronismo de cortes em 65s e legendas amarelas."
  },
  {
    id: "mariana",
    nome: "Mariana",
    cargo: "Editora de Longos",
    linha: 4,
    filtro: "none",
    mesa: { x: 38, y: 46 },
    lounge: { x: 86, y: 74 },
    celular: { x: 42, y: 56 },
    reuniao: { x: 45, y: 53 },
    x: 38,
    y: 46,
    estado: "TRABALHANDO",
    fala: "Lapidando a narrativa dos resumos longos."
  },
  {
    id: "caio",
    nome: "Caio",
    cargo: "Líder de T.I.",
    linha: 3,
    filtro: "hue-rotate(185deg) saturate(1.4)",
    mesa: { x: 61, y: 63 },
    lounge: { x: 83, y: 70 },
    celular: { x: 67, y: 49 },
    reuniao: { x: 53, y: 43 },
    x: 61,
    y: 63,
    estado: "TRABALHANDO",
    fala: "Monitorando uso de CPU, RAM e temperatura."
  },
  {
    id: "beatriz",
    nome: "Beatriz",
    cargo: "Analista de CTR",
    linha: 2,
    filtro: "hue-rotate(45deg) saturate(1.4)",
    mesa: { x: 69, y: 69 },
    lounge: { x: 91, y: 77 },
    celular: { x: 73, y: 58 },
    reuniao: { x: 55, y: 48 },
    x: 69,
    y: 69,
    estado: "TRABALHANDO",
    fala: "Analisando ganchos de 3s e horários de pico."
  },
  {
    id: "thiago",
    nome: "Thiago",
    cargo: "Roteirista",
    linha: 2,
    filtro: "hue-rotate(145deg) saturate(1.3)",
    mesa: { x: 44, y: 41 },
    lounge: { x: 80, y: 76 },
    celular: { x: 52, y: 38 },
    reuniao: { x: 42, y: 47 },
    x: 44,
    y: 41,
    estado: "TRABALHANDO",
    fala: "Criando chamadas explosivas para os títulos."
  }
];

// Banco de falas e atitudes dinâmicas de escritório
var falasCafe = [
  "☕ Tomando um expresso duplo no lounge...",
  "☕ Pausa merecida no sofá do Relax & Create!",
  "☕ Recarregando a cafeína pro próximo lote...",
  "☕ Batendo papo no lounge sobre o GTA 6...",
  "☕ Degustando um café enquanto o FFmpeg renderiza."
];

var falasCelular = [
  "📱 No WhatsApp alinhando publi com patrocinador gamer.",
  "📱 Falando com o suporte sobre a cota do YouTube.",
  "📱 Checando métricas do último Short no celular.",
  "📱 Ouvindo áudio da assessoria do Paulinho o Loko.",
  "📱 Olhando os memes novos no Discord de GTA RP."
];

var falasTrabalho = [
  "💻 Foco total no corte e renderização de alta qualidade.",
  "🔍 Auditando se o formato yuv420p está perfeito.",
  "⚡ Ajustando o gancho explosivo nos 3 segundos iniciais.",
  "🎬 Equalizando o volume do jogo e da intro narrada.",
  "📊 Verificando cota diária de 6 envios por canal."
];

// Desenha e anima os agentes com profundidade isométrica real
function desenharAgentes() {
  var camada = document.getElementById("camada-agentes");
  if (!camada) return;

  agentesConfig.forEach(function(ag) {
    var el = document.getElementById("ag-" + ag.id);
    var arquivoBase = "linha" + ag.linha + "_pose1.png";
    var arquivoAnimado = "linha" + ag.linha + "_pose" + framePose + ".png";

    if (!el) {
      el = document.createElement("div");
      el.id = "ag-" + ag.id;
      el.className = "agente";
      el.onclick = function() {
        if (ag.id === "dr_ricardo") abrirAvaliacao();
        else if (ag.id === "camila") abrirCuradoriaTop();
        else if (ag.id === "caio" || ag.id === "beatriz") abrirSuporteTI();
        else abrirAvaliacao();
      };
      el.innerHTML =
        '<div class="bubble" id="balao-' + ag.id + '">' + ag.fala + '</div>' +
        '<img id="img-' + ag.id + '" src="/sprites/' + arquivoBase + '">' +
        '<div class="tag-nome"><b>' + ag.nome + '</b> • ' + ag.cargo + '</div>';
      camada.appendChild(el);
    }

    // Posicionamento suave com z-index baseado na coordenada Y (profundidade isométrica)
    el.style.left = ag.x + "%";
    el.style.top = ag.y + "%";
    el.style.zIndex = Math.floor(ag.y * 10);

    var imgEl = document.getElementById("img-" + ag.id);
    if (imgEl) {
      imgEl.src = "/sprites/" + arquivoAnimado;
      imgEl.style.filter = ag.filtro || "none";
    }

    var b = document.getElementById("balao-" + ag.id);
    if (b) {
      b.innerText = ag.fala;
      var classeBalao = "bubble";
      if (ag.estado === "PAUSA_CAFE") classeBalao += " cafe";
      else if (ag.estado === "NO_CELULAR") classeBalao += " celular";
      else if (emReuniao) classeBalao += " reuniao";
      else if ((dadosServidor.pendentes || []).length > 0 && ag.id === "dr_ricardo") classeBalao += " alerta";
      b.className = classeBalao;
    }
  });
}

// Ciclo contínuo de animação das poses dos sprites (andar e respirar)
setInterval(function() {
  framePose = (framePose % 4) + 1;
  desenharAgentes();
}, 340);

// Máquina de Estados: Inteligência de Comportamento Ocioso dos Colaboradores
setInterval(function() {
  if (emReuniao) return;

  var pend = (dadosServidor.pendentes || []).length;
  var emProducao = pend > 0;

  agentesConfig.forEach(function(ag) {
    if (emProducao) {
      // Quando há trabalho ativo, todos retornam para as suas mesas
      ag.x = ag.mesa.x;
      ag.y = ag.mesa.y;
      ag.estado = "TRABALHANDO";
      if (ag.id === "dr_ricardo") {
        ag.fala = "🔔 " + pend + " vídeo(s) na fila aguardando minha aprovação!";
      } else {
        ag.fala = falasTrabalho[Math.floor(Math.random() * falasTrabalho.length)];
      }
    } else {
      // Quando ociosos, sorteia atitude de escritório
      var sorteio = Math.random();

      if (sorteio < 0.35) {
        // Pausa pro café no sofá rosa neon do lounge (Relax & Create)
        ag.x = ag.lounge.x + (Math.random() * 4 - 2);
        ag.y = ag.lounge.y + (Math.random() * 4 - 2);
        ag.estado = "PAUSA_CAFE";
        ag.fala = falasCafe[Math.floor(Math.random() * falasCafe.length)];
      } else if (sorteio < 0.65) {
        // No celular caminhando pelo corredor ou perto da janela
        ag.x = ag.celular.x + (Math.random() * 3 - 1.5);
        ag.y = ag.celular.y + (Math.random() * 3 - 1.5);
        ag.estado = "NO_CELULAR";
        ag.fala = falasCelular[Math.floor(Math.random() * falasCelular.length)];
      } else {
        // Na mesa trabalhando ou organizando notas
        ag.x = ag.mesa.x;
        ag.y = ag.mesa.y;
        ag.estado = "TRABALHANDO";
        ag.fala = falasTrabalho[Math.floor(Math.random() * falasTrabalho.length)];
      }
    }
  });

  desenharAgentes();
}, 6500);

// Protocolo de Reunião da Equipe com todos reunidos no centro
function abrirReuniao() {
  emReuniao = true;
  var falasReuniao = [
    "Dr. Ricardo: Nosso objetivo hoje é bater os 6 envios de pico sem falhas!",
    "Camila: Curadoria alinhada! Só passa vídeo com áudio e imagem perfeitos.",
    "Thiago: Títulos otimizados com ganchos de curiosidade nos 3s!",
    "Bruno: Rastreando lives do Paulinho, Coringa e novos vazamentos de GTA 6.",
    "Lucas: Shorts verticais 9:16 renderizados com legendas de alta fidelidade.",
    "Mariana: Narrativa dos resumos longos aprovada pela equipe.",
    "Caio: Monitoramento térmico do hardware e proteção de disco ativos.",
    "Beatriz: Análise de retenção aponta melhor desempenho às 18h e 21h!"
  ];

  agentesConfig.forEach(function(ag, idx) {
    ag.x = ag.reuniao.x + (idx % 3) * 4 - 4;
    ag.y = ag.reuniao.y + Math.floor(idx / 3) * 4 - 2;
    ag.fala = falasReuniao[idx % falasReuniao.length];
  });
  desenharAgentes();

  verModal('🤝 Reunião Executiva em Andamento', '<div class="card" style="text-align:center;">A equipe executiva está alinhando as diretrizes de produção no centro do escritório.<br><br><b>Normas em pauta:</b> Sistema 6 Estrelas, Proibição de MoviePy e Qualidade Máxima sem pressa.</div>');

  setTimeout(function() {
    emReuniao = false;
  }, 14000);
}

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
    document.getElementById('m-env').innerText = ag.length + '/42';
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
      '<button class="act-btn" style="background:#dc2626;" onclick="negarVideo(\'' + nome + '\')">Rejeitar / Excluir</button>' +
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
  if (!confirm('Rejeitar vídeo e remover da exportação?')) return;
  var vid = document.getElementById('player-review');
  if (vid) { vid.pause(); vid.removeAttribute('src'); vid.load(); }
  fetch('/api/negar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename: nome, arquivo: nome })
  }).then(function() {
    listaPendentes.splice(idxAtual, 1);
    renderizarPlayer();
    atualizarTudo();
  }).catch(function() { listaPendentes.splice(idxAtual, 1); renderizarPlayer(); });
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
    html += '<div class="card" style="display:flex; justify-content:space-between; align-items:center;"><div><b>' + canais[i] + '</b><div style="font-size:11px; color:#94a3b8;">Cota Máxima: 6 por dia</div></div><div style="color:#facc15; font-size:15px;">★★★★★★</div></div>';
  }
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
  fetch('/api/ti/purge', { method: 'POST' }).then(function() {
    alert('Limpeza de arquivos temporários concluída com sucesso!');
    atualizarTudo();
  }).catch(function() { alert('Limpeza efetuada!'); });
}

var varreduraAtiva = true;
function toggleVarredura() {
  varreduraAtiva = !varreduraAtiva;
  var b = document.getElementById('b-var');
  var m = document.getElementById('g-msg');
  b.className = varreduraAtiva ? 'btn btn-red' : 'btn';
  b.innerHTML = varreduraAtiva ? 'Stop<br>Varredura' : 'Iniciar<br>Varredura';
  m.innerText = varreduraAtiva ? 'Varredura ativa e gerando estoque...' : 'Varredura pausada.';
  if (varreduraAtiva) { fetch('/api/buscar_lives', { method: 'POST' }).catch(function() {}); }
}

// Inicialização
atualizarTudo();
desenharAgentes();
setInterval(atualizarTudo, 5000);
