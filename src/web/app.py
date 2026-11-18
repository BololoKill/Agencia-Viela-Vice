"""
Servidor Web Flask da Agência Viela Vice.
Expõe o Escritório Virtual e a suíte completa de APIs REST para a Diretoria, Curadoria e Suporte de T.I.
"""
import os
import glob
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, jsonify, request, send_file, send_from_directory
from src.config import (
    BASE_DIR, EXPORT_DIR, VIDEO_BRUTO_DIR, SPRITES_DIR, IMAGE_PATH,
    STATE_FILE, AFILIADOS_FILE, AGENDADOS_FILE, DESCARTADOS_FILE,
    MEMORIA_FILE, FINANCEIRO_FILE, NOTICIAS_FILE, HISTORICO_FILE,
    DEFAULT_HORARIOS, CANAIS_VIELA_VICE
)
from src.utils import load_json_safe, save_json_safe
from src.youtube.uploader import enviar_video_agendado
from src.pipeline.worker import executar_ciclo_producao

app = Flask(__name__, static_folder=str(BASE_DIR))

def calcular_proximo_horario(agendados, horarios_config):
    """Calcula a próxima data/horário desocupado para a grade de postagens."""
    if not horarios_config:
        horarios_config = DEFAULT_HORARIOS
    ocupados = set((item.get("data"), item.get("horario")) for item in agendados)
    agora = datetime.now()
    for offset in range(30):
        dia = agora + timedelta(days=offset)
        data_str = dia.strftime("%Y-%m-%d")
        for h in horarios_config:
            if (data_str, h) not in ocupados:
                return data_str, h
    return agora.strftime("%Y-%m-%d"), horarios_config[0]

@app.route('/')
def index():
    """Entrega a interface do escritório virtual."""
    html_path = BASE_DIR / "painel_vice.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return "Painel Viela Vice não encontrado.", 404

@app.route('/painel.js')
def serve_js():
    """Entrega a lógica de animações e modais do escritório."""
    js_path = BASE_DIR / "painel.js"
    if js_path.exists():
        return js_path.read_text(encoding="utf-8"), 200, {'Content-Type': 'application/javascript'}
    return "", 404

@app.route('/tema_agencia.css')
def serve_css():
    """Entrega o tema escuro estilizado."""
    css_path = BASE_DIR / "tema_agencia.css"
    if css_path.exists():
        return css_path.read_text(encoding="utf-8"), 200, {'Content-Type': 'application/css'}
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

    pendentes = []
    for v in novos_videos:
        nome_limpo = v.replace(".mp4", "").replace("-", " ").title()
        pendentes.append({
            "arquivo": v,
            "filename": v,
            "titulo": f"{nome_limpo} | GTA RP Brasil #Shorts",
            "descricao": "Inscreva-se no canal Viela Vice! Os melhores momentos do GTA RP brasileiro. #GTA6 #GTARP #Shorts"
        })

    agendados = load_json_safe(AGENDADOS_FILE, [])
    financeiro = load_json_safe(FINANCEIRO_FILE, {
        "adsense": 1420.50,
        "afiliados": 680.00,
        "videos_mes": 42,
        "postados_mes": len(agendados)
    })

    return jsonify({
        "videos": pendentes,
        "pendentes": pendentes,
        "agendados": agendados,
        "fila": agendados,
        "financeiro": financeiro,
        "total_estoque": len(novos_videos)
    })

@app.route('/api/aprovar', methods=['POST'])
def api_aprovar():
    """Aprova e agenda publicação no YouTube."""
    data = request.get_json(silent=True) or {}
    filename = data.get("arquivo") or data.get("filename")
    titulo = data.get("titulo") or "Momento Épico GTA RP #Shorts"
    descricao = data.get("descricao") or ""
    canal_id = str(data.get("canal") or "1")

    if not filename:
        return jsonify({"success": False, "error": "Nome do arquivo não fornecido"}), 400

    video_path = EXPORT_DIR / filename
    if not video_path.exists():
        return jsonify({"success": False, "error": "Arquivo não encontrado"}), 404

    agendados = load_json_safe(AGENDADOS_FILE, [])
    afiliados = load_json_safe(AFILIADOS_FILE, {})
    horarios = afiliados.get("horarios", DEFAULT_HORARIOS)
    data_agenda, hora_agenda = calcular_proximo_horario(agendados, horarios)

    # Dispara agendamento no YouTube API v3
    ok_yt, msg_yt, vid_id = enviar_video_agendado(
        video_path=video_path,
        titulo=titulo,
        descricao=descricao,
        data_agenda=data_agenda,
        hora_agenda=hora_agenda,
        canal_id=canal_id
    )

    novo_registro = {
        "id": len(agendados) + 1,
        "filename": filename,
        "titulo": titulo,
        "canal": canal_id,
        "canal_nome": CANAIS_VIELA_VICE.get(canal_id, {}).get("nome", "Viela Vice"),
        "data": data_agenda,
        "horario": hora_agenda,
        "youtube_id": vid_id,
        "status": msg_yt if ok_yt else f"Fila Local ({msg_yt})",
        "aprovado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    agendados.append(novo_registro)
    save_json_safe(AGENDADOS_FILE, agendados)

    # Registro histórico
    try:
        with open(HISTORICO_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Aprovado: {titulo} ({filename})\n")
    except Exception:
        pass

    # Se enviado ao YouTube, remove do disco para economizar espaço
    if ok_yt:
        try:
            video_path.unlink()
        except Exception:
            pass

    return jsonify({"success": True, "message": f"Vídeo aprovado e agendado para {data_agenda} às {hora_agenda}!"})

@app.route('/api/negar', methods=['POST'])
def api_negar():
    """Descarta e exclui um vídeo rejeitado."""
    data = request.get_json(silent=True) or {}
    filename = data.get("arquivo") or data.get("filename")
    if not filename:
        return jsonify({"success": False, "error": "Nome ausente"}), 400

    video_path = EXPORT_DIR / filename
    if video_path.exists():
        try:
            video_path.unlink()
        except Exception:
            pass

    descartados = load_json_safe(DESCARTADOS_FILE, [])
    if filename not in descartados:
        descartados.append(filename)
        save_json_safe(DESCARTADOS_FILE, descartados)

    return jsonify({"success": True, "message": f"Vídeo {filename} rejeitado e excluído."})

@app.route('/api/buscar_lives', methods=['POST'])
def api_buscar_lives():
    """Gatilha um ciclo de varredura imediato."""
    import threading
    threading.Thread(target=executar_ciclo_producao, daemon=True).start()
    return jsonify({"success": True, "message": "Ciclo de busca e corte iniciado pelo Olheiro!"})

@app.route('/api/ti_terminal')
def api_ti_terminal():
    """Retorna logs recentes da produção para o console da interface."""
    from collections import deque
    log_file = BASE_DIR / "log_producao.txt"
    if not log_file.exists():
        return jsonify({"log": "Aguardando início do log de produção..."})
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            ultimas = "".join(deque(f, maxlen=35))
        return jsonify({"log": ultimas})
    except Exception:
        return jsonify({"log": "Lendo logs..."})

@app.route('/api/ti_diagnostico')
def api_ti_diagnostico():
    """Monitora recursos da máquina do usuário."""
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    disco_livre_gb = round(psutil.disk_usage(str(BASE_DIR)).free / (1024**3), 1)

    brutos = list(VIDEO_BRUTO_DIR.glob("*")) if VIDEO_BRUTO_DIR.exists() else []
    prontos = list(EXPORT_DIR.glob("*.mp4")) if EXPORT_DIR.exists() else []

    return jsonify({
        "cpu": cpu,
        "ram": ram,
        "disco_livre_gb": disco_livre_gb,
        "qtd_brutos": len(brutos),
        "qtd_prontos": len(prontos),
        "status": "Operação Estável (FFmpeg + Whisper Ativos)"
    })

@app.route('/api/ti/purge', methods=['POST'])
def api_ti_purge():
    """Limpa resíduos e arquivos corrompidos na pasta temporária."""
    removidos = 0
    if VIDEO_BRUTO_DIR.exists():
        for f in VIDEO_BRUTO_DIR.iterdir():
            try:
                f.unlink()
                removidos += 1
            except Exception:
                pass
    return jsonify({"success": True, "removidos": removidos})

def iniciar_servidor(host: str = "0.0.0.0", port: int = 8501):
    """Executa o servidor Flask."""
    app.run(host=host, port=port, debug=False)
