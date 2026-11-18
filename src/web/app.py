"""
Servidor Web Flask da Agência Viela Vice.
Expõe o Escritório Virtual e a suíte completa de APIs REST para a Diretoria, Curadoria e Suporte de T.I.
"""
import re
import socket
import threading
import psutil
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_file, send_from_directory
from src.config import (
    BASE_DIR, EXPORT_DIR, VIDEO_BRUTO_DIR, SPRITES_DIR, IMAGE_PATH,
    AFILIADOS_FILE, AGENDADOS_FILE, DESCARTADOS_FILE,
    FINANCEIRO_FILE, HISTORICO_FILE, METADADOS_FILE,
    DEFAULT_HORARIOS, CANAIS_VIELA_VICE, COTA_DIARIA_CANAL
)
from src.utils import load_json_safe, save_json_safe, log_terminal, ler_ultimas_linhas
from src.youtube import cota
from src.youtube.uploader import enviar_video_agendado
from src.pipeline import estado
from src.pipeline.worker import executar_ciclo_producao

# static_folder=None impede que a raiz do projeto (com .env e tokens) seja publicada.
app = Flask(__name__, static_folder=None)

_NOME_VIDEO_VALIDO = re.compile(r"^[\w .()\[\]-]+\.mp4$")
_SEM_CACHE = {"Cache-Control": "no-store"}
MARGEM_AGENDAMENTO_MIN = 30
_aprovacoes_em_andamento = set()
_trava_aprovacoes = threading.Lock()


def _versao_painel() -> str:
    """Identifica a versão dos arquivos do painel para atualizar abas já abertas."""
    arquivos = [BASE_DIR / nome for nome in ("painel_vice.html", "painel.js", "escritorio.js")]
    return str(max((int(a.stat().st_mtime) for a in arquivos if a.exists()), default=0))


def _resolver_video(nome):
    """Aceita somente arquivos .mp4 diretamente dentro da pasta de exportação."""
    if not isinstance(nome, str) or not _NOME_VIDEO_VALIDO.match(nome):
        return None
    return EXPORT_DIR / nome


def calcular_proximo_horario(agendados, horarios_config, canal_id="1", agora: datetime = None):
    """Escolhe o próximo horário futuro livre na grade do próprio canal."""
    if not horarios_config:
        horarios_config = DEFAULT_HORARIOS
    agora = agora or datetime.now()
    minimo = agora + timedelta(minutes=MARGEM_AGENDAMENTO_MIN)
    ocupados = set(
        (item.get("data"), item.get("horario")) for item in agendados if str(item.get("canal")) == str(canal_id)
    )
    for offset in range(30):
        data_str = (agora + timedelta(days=offset)).strftime("%Y-%m-%d")
        for h in horarios_config:
            if (data_str, h) not in ocupados and datetime.strptime(f"{data_str} {h}", "%Y-%m-%d %H:%M") > minimo:
                return data_str, h
    return (agora + timedelta(days=30)).strftime("%Y-%m-%d"), horarios_config[0]


@app.route('/')
def index():
    """Entrega a interface do escritório virtual."""
    html_path = BASE_DIR / "painel_vice.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8"), 200, {"Content-Type": "text/html; charset=utf-8", **_SEM_CACHE}
    return "Painel Viela Vice não encontrado.", 404


@app.route('/painel.js')
def serve_js():
    """Entrega a lógica de animações e modais do escritório."""
    js_path = BASE_DIR / "painel.js"
    if js_path.exists():
        return js_path.read_text(encoding="utf-8"), 200, {"Content-Type": "application/javascript", **_SEM_CACHE}
    return "", 404


@app.route('/escritorio.js')
def serve_escritorio_js():
    """Entrega os personagens e a movimentação do escritório virtual."""
    js_path = BASE_DIR / "escritorio.js"
    if js_path.exists():
        return js_path.read_text(encoding="utf-8"), 200, {"Content-Type": "application/javascript", **_SEM_CACHE}
    return "", 404


@app.route('/tema_agencia.css')
def serve_css():
    """Entrega o tema escuro estilizado."""
    css_path = BASE_DIR / "tema_agencia.css"
    if css_path.exists():
        return css_path.read_text(encoding="utf-8"), 200, {'Content-Type': 'text/css'}
    return "", 404


@app.route('/sprites/<path:filename>')
def serve_sprite(filename):
    return send_from_directory(str(SPRITES_DIR), filename)


@app.route('/escritorio_img')
def serve_escritorio():
    if IMAGE_PATH.exists():
        return send_file(str(IMAGE_PATH))
    return "Imagem de fundo não encontrada", 404


@app.route('/exportacao/<path:filename>')
def serve_exportacao(filename):
    return send_from_directory(str(EXPORT_DIR), filename)


@app.route('/api/data')
def api_data():
    """Sincroniza o estado geral da agência para o HUD."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    all_videos = [f.name for f in EXPORT_DIR.glob("*.mp4")]
    descartados = load_json_safe(DESCARTADOS_FILE, [])
    novos_videos = [v for v in all_videos if v not in descartados]
    metadados = load_json_safe(METADADOS_FILE, {})
    metadados = metadados if isinstance(metadados, dict) else {}

    pendentes = []
    for v in novos_videos:
        nome_limpo = v.replace(".mp4", "").replace("-", " ").title()
        dados_corte = metadados.get(v) if isinstance(metadados.get(v), dict) else {}
        pendentes.append({
            "arquivo": v,
            "filename": v,
            "titulo": dados_corte.get("titulo") or f"{nome_limpo} | GTA RP Brasil #Shorts",
            "descricao": dados_corte.get("descricao") or "Inscreva-se no canal Viela Vice! Os melhores momentos do GTA RP brasileiro. #GTA6 #GTARP #Shorts"
        })

    agendados = load_json_safe(AGENDADOS_FILE, [])
    financeiro = load_json_safe(FINANCEIRO_FILE, {
        "adsense": 1420.50,
        "afiliados": 680.00,
        "videos_mes": 42,
        "postados_mes": len(agendados)
    })
    cotas = cota.resumo()

    return jsonify({
        "cotas": cotas,
        "envios_hoje": sum(c["usados"] for c in cotas.values()),
        "limite_envios": COTA_DIARIA_CANAL * len(CANAIS_VIELA_VICE),
        "videos": pendentes,
        "pendentes": pendentes,
        "agendados": agendados,
        "fila": agendados,
        "financeiro": financeiro,
        "total_estoque": len(novos_videos)
    })


def _reservar_agendamento(filename, titulo, canal_id):
    """Reserva o horário antes do envio para aprovações simultâneas não disputarem a mesma vaga."""
    with _trava_aprovacoes:
        agendados = load_json_safe(AGENDADOS_FILE, [])
        registro = next((item for item in agendados if item.get("filename") == filename), None)
        if registro is None:
            afiliados = load_json_safe(AFILIADOS_FILE, {})
            data_agenda, hora_agenda = calcular_proximo_horario(
                agendados, afiliados.get("horarios", DEFAULT_HORARIOS), canal_id)
            registro = {"id": len(agendados) + 1, "filename": filename, "data": data_agenda, "horario": hora_agenda}
            agendados.append(registro)
        registro.update({
            "titulo": titulo,
            "canal": canal_id,
            "canal_nome": CANAIS_VIELA_VICE.get(canal_id, {}).get("nome", "Viela Vice"),
            "status": "Enviando ao YouTube...",
            "aprovado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        save_json_safe(AGENDADOS_FILE, agendados)
        return registro["data"], registro["horario"]


def _concluir_agendamento(filename, youtube_id, status):
    with _trava_aprovacoes:
        agendados = load_json_safe(AGENDADOS_FILE, [])
        for item in agendados:
            if item.get("filename") == filename:
                item.update({"youtube_id": youtube_id, "status": status})
        save_json_safe(AGENDADOS_FILE, agendados)


def _processar_aprovacao(filename, video_path, titulo, descricao, canal_id):
    agendados = load_json_safe(AGENDADOS_FILE, [])
    existente = next((item for item in agendados if item.get("filename") == filename), None)
    if existente and existente.get("youtube_id"):
        return jsonify({
            "success": True, "ja_agendado": True, "enviado_youtube": True,
            "message": f"Vídeo já agendado para {existente.get('data')} às {existente.get('horario')}."
        })
    if not video_path.exists():
        return jsonify({"success": False, "error": "Arquivo não encontrado"}), 404

    try:
        cota.reservar_envio(canal_id)
    except cota.CotaEsgotada as e:
        return jsonify({"success": False, "cota_esgotada": True, "error": str(e)}), 409
    except cota.CotaNaoVerificada as e:
        log_terminal(f"[AVISO] Envio cancelado para {filename}: {e}")
        return jsonify({"success": False, "cota_nao_verificada": True, "error": str(e)}), 503

    ok_yt, msg_yt, vid_id = False, "Envio não iniciado", None
    try:
        data_agenda, hora_agenda = _reservar_agendamento(filename, titulo, canal_id)
        ok_yt, msg_yt, vid_id = enviar_video_agendado(
            video_path=video_path,
            titulo=titulo,
            descricao=descricao,
            data_agenda=data_agenda,
            hora_agenda=hora_agenda,
            canal_id=canal_id
        )
    except Exception as e:
        ok_yt, msg_yt, vid_id = False, f"Erro inesperado no envio: {e}", None
    finally:
        cota.concluir_envio(canal_id, vid_id if ok_yt else None)

    if not ok_yt and "quotaexceeded" in str(msg_yt).lower():
        cota.marcar_api_esgotada()

    _concluir_agendamento(filename, vid_id, msg_yt if ok_yt else f"Fila Local ({msg_yt})")

    try:
        with open(HISTORICO_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Aprovado: {titulo} ({filename})\n")
    except OSError:
        pass

    if not ok_yt:
        log_terminal(f"[AVISO] Envio ao YouTube não concluído para {filename}: {msg_yt}")
        return jsonify({
            "success": True, "enviado_youtube": False,
            "message": f"Vídeo mantido na fila local. YouTube: {msg_yt}"
        })

    # Enviado ao YouTube: remove do disco para economizar espaço
    try:
        video_path.unlink()
    except OSError:
        pass
    log_terminal(f"[SUCESSO] {filename} agendado para {data_agenda} às {hora_agenda}.")
    return jsonify({
        "success": True, "enviado_youtube": True,
        "message": f"Vídeo aprovado e agendado para {data_agenda} às {hora_agenda}!"
    })


@app.route('/api/aprovar', methods=['POST'])
def api_aprovar():
    """Aprova e agenda publicação no YouTube, sem duplicar envios."""
    data = request.get_json(silent=True) or {}
    filename = data.get("arquivo") or data.get("filename")
    if not filename:
        return jsonify({"success": False, "error": "Nome do arquivo não fornecido"}), 400

    video_path = _resolver_video(filename)
    if video_path is None:
        return jsonify({"success": False, "error": "Nome de arquivo inválido"}), 400

    with _trava_aprovacoes:
        if filename in _aprovacoes_em_andamento:
            return jsonify({"success": False, "error": "Este vídeo já está sendo enviado."}), 409
        _aprovacoes_em_andamento.add(filename)

    try:
        return _processar_aprovacao(
            filename, video_path,
            data.get("titulo") or "Momento Épico GTA RP #Shorts",
            data.get("descricao") or "",
            str(data.get("canal")) if str(data.get("canal")) in CANAIS_VIELA_VICE else "1",
        )
    finally:
        with _trava_aprovacoes:
            _aprovacoes_em_andamento.discard(filename)


def _remover_da_fila_local(filename):
    """Libera o horário de um vídeo rejeitado que não chegou ao YouTube."""
    with _trava_aprovacoes:
        agendados = load_json_safe(AGENDADOS_FILE, [])
        restantes = [item for item in agendados if item.get("filename") != filename or item.get("youtube_id")]
        if len(restantes) != len(agendados):
            save_json_safe(AGENDADOS_FILE, restantes)


@app.route('/api/negar', methods=['POST'])
def api_negar():
    """Descarta e exclui um vídeo rejeitado."""
    data = request.get_json(silent=True) or {}
    filename = data.get("arquivo") or data.get("filename")
    if not filename:
        return jsonify({"success": False, "error": "Nome ausente"}), 400

    video_path = _resolver_video(filename)
    if video_path is None:
        return jsonify({"success": False, "error": "Nome de arquivo inválido"}), 400

    with _trava_aprovacoes:
        if filename in _aprovacoes_em_andamento:
            return jsonify({"success": False, "error": "Este vídeo está sendo enviado ao YouTube."}), 409

    try:
        video_path.unlink(missing_ok=True)
    except OSError as e:
        return jsonify({"success": False, "error": f"Não foi possível excluir o vídeo: {e}"}), 500

    descartados = load_json_safe(DESCARTADOS_FILE, [])
    if filename not in descartados:
        descartados.append(filename)
        save_json_safe(DESCARTADOS_FILE, descartados)

    _remover_da_fila_local(filename)
    return jsonify({"success": True, "message": f"Vídeo {filename} rejeitado e excluído."})


@app.route('/api/buscar_lives', methods=['POST'])
def api_buscar_lives():
    """Gatilha um ciclo imediato. Repetir o pedido durante a produção não cria outro ciclo."""
    if estado.ciclo_em_andamento():
        return jsonify({"success": True, "iniciado": False, "message": "A produção já está em andamento."})
    threading.Thread(target=executar_ciclo_producao, daemon=True).start()
    return jsonify({"success": True, "iniciado": True, "message": "Ciclo de busca e corte iniciado pelo Olheiro!"})


@app.route('/api/varredura', methods=['POST'])
def api_varredura():
    """Pausa ou retoma a produção automática."""
    data = request.get_json(silent=True) or {}
    ativo = data.get("ativo")
    if not isinstance(ativo, bool):
        return jsonify({"success": False, "error": "Informe ativo como true ou false."}), 400
    estado.definir_producao_ativa(ativo)
    log_terminal("[PAINEL] Varredura retomada." if ativo else "[PAINEL] Varredura pausada.")
    return jsonify(estado.ler_status())


@app.route('/api/status')
def api_status():
    """Informa a situação real da produção e a versão instalada do painel."""
    return jsonify({**estado.ler_status(), "versao_painel": _versao_painel()})


@app.route('/api/ti_terminal')
def api_ti_terminal():
    """Retorna logs recentes da produção para o console da interface."""
    linhas = ler_ultimas_linhas(60)
    return jsonify({"log": "\n".join(linhas), "linhas": linhas})


@app.route('/api/ti_diagnostico')
def api_ti_diagnostico():
    """Monitora recursos da máquina do usuário."""
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    disco_livre_gb = round(psutil.disk_usage(str(BASE_DIR)).free / (1024**3), 1)

    brutos = list(VIDEO_BRUTO_DIR.glob("*")) if VIDEO_BRUTO_DIR.exists() else []
    prontos = list(EXPORT_DIR.glob("*.mp4")) if EXPORT_DIR.exists() else []
    situacao = estado.ler_status()

    return jsonify({
        "cpu": cpu,
        "ram": ram,
        "disco_livre_gb": disco_livre_gb,
        "qtd_brutos": len(brutos),
        "qtd_prontos": len(prontos),
        "saude": situacao["saude"],
        "status": situacao["mensagem"]
    })


@app.route('/api/ti/purge', methods=['POST'])
def api_ti_purge():
    """Limpa resíduos da pasta temporária, exceto durante a produção."""
    if estado.ciclo_em_andamento():
        return jsonify({"success": False, "error": "Produção em andamento. Tente novamente ao final do ciclo."}), 409
    removidos = 0
    if VIDEO_BRUTO_DIR.exists():
        for f in VIDEO_BRUTO_DIR.iterdir():
            try:
                f.unlink()
                removidos += 1
            except OSError:
                pass
    return jsonify({"success": True, "removidos": removidos})


def porta_em_uso(port: int, host: str = "127.0.0.1") -> bool:
    """Detecta outro servidor ativo: no Windows, dois processos conseguem escutar a mesma porta."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def iniciar_servidor(host: str = "127.0.0.1", port: int = 8501):
    """Executa o servidor Flask."""
    app.run(host=host, port=port, debug=False, threaded=True)
