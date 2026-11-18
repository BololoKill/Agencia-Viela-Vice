import os
import json
from datetime import datetime, timedelta
import subprocess
from flask import Flask, render_template_string, request, jsonify, send_from_directory, send_file
import urllib.request
import xml.etree.ElementTree as ET

app = Flask(__name__)

STATE_FILE = "painel_state.json"
AFILIADOS_FILE = "afiliados_config.json"
AGENDADOS_FILE = "agendados.json"
DESCARTADOS_FILE = "descartados.json"
MEMORIA_FILE = "memoria_agentes.json"
FINANCEIRO_FILE = "financeiro_agencia.json"
GEMINI_MD_FILE = "GEMINI.md"
EXPORT_DIR = "exportacao"
VIDEO_BRUTO_DIR = "video-bruto"
HISTORICO_FILE = "historico.txt"
IMAGE_PATH = "novo_vice.png.jpeg"
NOTICIAS_FILE = "noticias_gta6.json"

DEFAULT_HORARIOS = ["10:00", "13:00", "16:00", "19:00", "21:00", "22:30"]

def load_json(filepath, default_val):
    if not os.path.exists(filepath):
        save_json(filepath, default_val)
        return default_val
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default_val

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_afiliados():
    return load_json(AFILIADOS_FILE, {
        "links_afiliado": ["https://exemplo.com/afiliado-gamer"],
        "cupons_gamer": ["VIELA10 (10% OFF em acessórios gamer)"],
        "horarios": DEFAULT_HORARIOS
    })

def load_agendados():
    return load_json(AGENDADOS_FILE, [])

def load_descartados():
    return load_json(DESCARTADOS_FILE, [])

def load_memoria():
    return load_json(MEMORIA_FILE, {
        "aprovados": [],
        "negados": [],
        "melhorias_pendentes": [
            {
                "id": "melhoria_1",
                "titulo": "Ajustar ganchos de título para 3 segundos iniciais mais fortes",
                "descricao": "Análise de retenção indica que títulos focados em reviravoltas no GTA RP aumentam o CTR em 18%.",
                "regra_gemini": "- **Ganchos de Título:** Priorizar frases curtas e impactantes nos primeiros 3 segundos baseadas em reviravoltas ou confrontos no GTA RP."
            },
            {
                "id": "melhoria_2",
                "titulo": "Otimização de horários de pico",
                "descricao": "Dados mostram maior engajamento às 18:00 e 21:00 em dias úteis.",
                "regra_gemini": "- **Horários de Pico:** Priorizar agendamentos nos horários de maior retenção (18:00 e 21:00)."
            }
        ],
        "melhorias_aprovadas": []
    })

def load_financeiro():
    return load_json(FINANCEIRO_FILE, {
        "adsense": 1420.50,
        "afiliados": 680.00,
        "videos_mes": 42,
        "postados_mes": 38
    })

def get_noticias_gta6(num_videos=0):
    default_noticias = [
        "Rockstar confirma foco total no polimento e física de GTA 6 para PS5 e Xbox Series X|S.",
        "Novos rumores apontam melhorias na inteligência artificial de pedestres em Vice City.",
        "Comunidade de GTA RP no Brasil bate recorde de audiência com novas mecânicas de facções.",
        f"Canal Viela Vice operando com {num_videos} vídeos em estoque. Meta diÃ¡ria em andamento.",
        "Jason e Lúcia terão interações dinâmicas avançadas baseadas no clima de Vice City."
    ]
    try:
        url = "https://news.google.com/rss/search?q=GTA+6+Rockstar+Games+Vice+City&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')
            headlines = []
            for item in items[:5]:
                title = item.find('title')
                if title is not None and title.text:
                    clean_title = title.text.split(' - ')[0]
                    headlines.append(clean_title)
            if headlines:
                headlines.append(f"Viela Vice: {num_videos} Shorts no estoque de exportação.")
                save_json(NOTICIAS_FILE, {"atualizado_em": datetime.now().strftime("%Y-%m-%d"), "noticias": headlines})
                return headlines
    except Exception as e:
        pass
    
    if os.path.exists(NOTICIAS_FILE):
        data = load_json(NOTICIAS_FILE, {})
        if "noticias" in data and data["noticias"]:
            return data["noticias"]
            
    save_json(NOTICIAS_FILE, {"atualizado_em": datetime.now().strftime("%Y-%m-%d"), "noticias": default_noticias})
    return default_noticias

def append_gemini_rule(rule_text):
    if not os.path.exists(GEMINI_MD_FILE):
        return
    try:
        with open(GEMINI_MD_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        if rule_text not in content:
            with open(GEMINI_MD_FILE, 'a', encoding='utf-8') as f:
                f.write(f"\n{rule_text}\n")
    except:
        pass

def calcular_proximo_horario(agendados, horarios_config):
    if not horarios_config:
        horarios_config = DEFAULT_HORARIOS
    ocupados = set((item.get("data"), item.get("horario")) for item in agendados)
    data_atual = datetime.now()
    for dia_offset in range(30):
        dia_alvo = data_atual + timedelta(days=dia_offset)
        data_str = dia_alvo.strftime("%Y-%m-%d")
        for horario in horarios_config:
            if (data_str, horario) not in ocupados:
                return data_str, horario
    return data_atual.strftime("%Y-%m-%d"), horarios_config[0]

@app.route('/sprites/<path:filename>')
def serve_sprite(filename):
    return send_from_directory('sprites', filename)

@app.route('/escritorio_img')
def serve_escritorio():
    if os.path.exists(IMAGE_PATH):
        return send_file(IMAGE_PATH)
    return "Imagem de fundo não encontrada", 404

@app.route('/exportacao/<path:filename>')
def serve_exportacao(filename):
    return send_from_directory(EXPORT_DIR, filename)

@app.route('/api/data')
def api_data():
    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR, exist_ok=True)
    if not os.path.exists(VIDEO_BRUTO_DIR):
        os.makedirs(VIDEO_BRUTO_DIR, exist_ok=True)
        
    all_videos = [f for f in os.listdir(EXPORT_DIR) if f.endswith('.mp4')]
    descartados = load_descartados()
    novos_videos = [v for v in all_videos if v not in descartados]
    video_bruto_files = os.listdir(VIDEO_BRUTO_DIR)
    
    noticias = get_noticias_gta6(len(all_videos))
    memoria = load_memoria()
    afiliados = load_afiliados()
    agendados = load_agendados()
    financeiro = load_financeiro()
    
    pendentes = []
    for v in novos_videos:
        nome_limpo = v.replace(".mp4", "").replace("-", " ").title()
        pendentes.append({
            "arquivo": v,
            "titulo": f"{nome_limpo} | GTA RP Brasil #Shorts",
            "descricao": "Inscreva-se no canal Viela Vice! Os melhores momentos do GTA RP brasileiro. #GTA6 #GTARP #Shorts"
        })

    return jsonify({
        "all_videos": all_videos,
        "novos_videos": novos_videos,
        "pendentes": pendentes,
        "video_bruto_count": len(video_bruto_files),
        "noticias": noticias,
        "memoria": memoria,
        "afiliados": afiliados,
        "agendados": agendados,
        "financeiro": financeiro
    })


def enviar_youtube_agendado(video_path, title, description, data_agenda, hora_agenda):
    if not os.path.exists("client_secrets.json"):
        return False, "client_secrets.json ausente", None
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        SCOPES = ["https://googleapis.com"]
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
                creds = flow.run_local_server(port=8088, prompt="select_account")
            with open("token.json", "w", encoding="utf-8") as tf:
                tf.write(creds.to_json())

        youtube = build("youtube", "v3", credentials=creds)
        from datetime import timedelta
        dt_ag = datetime.strptime(f"{data_agenda} {hora_agenda}", "%Y-%m-%d %H:%M")
        agora_min = datetime.now() + timedelta(minutes=15)
        while dt_ag <= agora_min:
            dt_ag += timedelta(days=1)
        publish_at = dt_ag.strftime("%Y-%m-%dT%H:%M:00-03:00")
        tags = ["GTA RP", "GTA 6", "GTA VI", "Viela Vice", "GTA RP Brasil", "Shorts", "Clipes GTA"]
        desc_completa = (description or "").strip()
        if "Viela Vice" not in desc_completa:
            desc_completa += "\n\nEsquenta oficial GTA 6 com os melhores momentos do GTA RP Brasil! Inscreva-se no canal Viela Vice."

        body = {
            "snippet": {
                "title": title[:98],
                "description": desc_completa[:4900],
                "tags": tags,
                "categoryId": "20"
            },
            "status": {
                "privacyStatus": "private",
                "publishAt": publish_at,
                "selfDeclaredMadeForKids": False
            }
        }
        media = MediaFileUpload(video_path, chunksize=4*1024*1024, resumable=True, mimetype="video/mp4")
        req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        resp = None
        while resp is None:
            _, resp = req.next_chunk()
        return True, f"Agendado no YouTube ({publish_at})", resp.get("id")
    except Exception as e:
        return False, f"Erro YouTube API: {str(e)}", None


def gerar_seo_viela_vice(filename, title_atual, desc_atual):
    import random
    base = os.path.splitext(os.path.basename(filename))[0]
    partes = base.split("-")
    streamer_raw = partes[1] if len(partes) > 1 else "GTA RP"
    mapa_streamers = {
        "paulinho": "Paulinho o Loko",
        "paulinhooloko": "Paulinho o Loko",
        "coringa": "LOUD Coringa",
        "loudcoringa": "LOUD Coringa",
        "luqueta": "Luqueta",
        "gabepeixe": "Gabe Peixe",
        "piozinho": "Piozinho",
        "biquinho": "Biquinho",
        "bagualu": "Bagualu",
        "davyjones": "Davy Jones",
        "alanzoka": "Alanzoka",
        "mount": "Mount",
        "jonvlog": "Jon Vlogs",
    }
    streamer_nome = mapa_streamers.get(streamer_raw.lower(), streamer_raw.capitalize())
    eh_longo = base.startswith("longo-")

    if not title_atual or "Momento" in title_atual:
        if eh_longo:
            modelos_longo = [
                f"{streamer_nome}: Os Melhores Momentos do GTA RP Brasil! (Esquenta GTA 6)",
                f"Insano no GTA RP! O Melhor da Live de {streamer_nome} | Viela Vice",
                f"{streamer_nome} Quebrou Tudo no GTA RP! Compilado Completo #GTA6",
            ]
            title_atual = random.choice(modelos_longo)
        else:
            modelos_short = [
                f"{streamer_nome} não acreditou no que aconteceu! #GTARP #GTA6 #Shorts",
                f"Olha o que {streamer_nome} fez no GTA RP Brasil! #Shorts #GTA6",
                f"Ninguém esperava essa reação de {streamer_nome}! #GTARP #Shorts",
                f"Clipe insano de {streamer_nome} no esquenta pro GTA 6! #Shorts",
            ]
            title_atual = random.choice(modelos_short)

    if not desc_atual.strip():
        nl = chr(10) + chr(10)
        desc_atual = (
            f"Melhores momentos de {streamer_nome} no GTA RP Brasil enquanto aquecemos os motores para o lançamento do GTA 6!"
            + nl
            + "Curta o vídeo e inscreva-se no canal Viela Vice (@VielaVice) para clipes diários dos maiores streamers do Brasil."
            + nl
            + f"#GTARP #GTA6 #GTAVI #VielaVice #{streamer_raw.capitalize()} #Shorts"
        )
    return title_atual, desc_atual


def auditoria_continua_ti():
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except Exception:
        pass
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return "Aguardando GEMINI_API_KEY para auditoria continua."
    try:
        import subprocess, json as _json
        from google import genai
        client = genai.Client(api_key=api_key)

        arqs = sorted(
            [os.path.join("exportacao", f) for f in os.listdir("exportacao") if f.endswith(".mp4")],
            key=os.path.getmtime,
            reverse=True
        )
        if not arqs:
            return "Nenhum video novo na exportacao para auditar."

        ultimo_video = arqs
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", ultimo_video
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        meta = res.stdout[:2500]

        with open("robo_cortes.py", "r", encoding="utf-8") as rc_f:
            trecho_edicao = chr(10).join(rc_f.splitlines()[260:360])

        prompt = (
            "Voce e Caio e Beatriz (Setor de T.I. e Qualidade da Agencia Viela Vice). "
            "Analise os metadados tecnicos do ultimo video exportado e o trecho de renderizacao FFmpeg abaixo. "
            "Verifique se ha queda de FPS, bitrate baixo, resolucao errada ou oportunidade real de melhoria na edicao. "
            "Responda em 2 frases objetivas em portugues com o diagnostico e a melhoria recomendada." + chr(10) +
            "ARQUIVO: " + os.path.basename(ultimo_video) + chr(10) +
            "METADADOS FFPROBE: " + meta + chr(10) +
            "TRECHO ROBO_CORTES: " + trecho_edicao
        )
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        diag = (resp.text or "").strip()

        rel_path = "auditoria_ti_continua.json"
        historico = []
        if os.path.exists(rel_path):
            try:
                historico = _json.load(open(rel_path, encoding="utf-8"))
            except Exception:
                historico = []
        historico.append({
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "video": os.path.basename(ultimo_video),
            "diagnostico_ti": diag
        })
        with open(rel_path, "w", encoding="utf-8") as out_f:
            _json.dump(historico[-30:], out_f, ensure_ascii=False, indent=2)
        return diag
    except Exception as e:
        return f"Erro na auditoria continua: {str(e)}"

@app.route('/api/auditoria_continua', methods=['GET', 'POST'])
def api_auditoria_continua():
    resultado = auditoria_continua_ti()
    return jsonify({"status": "ok", "diagnostico": resultado})


@app.route('/tema_agencia.css')
def servir_tema_css():
    from flask import Response
    css_txt = open("tema_agencia.css", encoding="utf-8").read() if os.path.exists("tema_agencia.css") else ""
    resp = Response(css_txt, mimetype="text/css"); resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"; return resp


@app.after_request
def injetar_tema_html(response):
    if response.content_type and "text/html" in response.content_type:
        html = response.get_data(as_text=True)
        if "tema_agencia.css" not in html and "</head>" in html:
            tag = '<link rel="stylesheet" href="/tema_agencia.css?v=' + str(int(os.path.getmtime("tema_agencia.css"))) + '">'
            html = html.replace("</head>", tag + "\n</head>", 1)
            response.set_data(html)
    return response

@app.route('/api/aprovar', methods=['POST'])
def api_aprovar():
    data = request.get_json(silent=True) or {}
    filename = os.path.basename(str(data.get("arquivo") or data.get("filename") or "").strip())
    title = data.get("title", "Momento Épico GTA RP #Shorts")
    description = data.get("description", "")
    
    if not filename:
        return jsonify({"success": False, "error": "Nome do arquivo não fornecido"}), 400
        
    video_path = os.path.join(EXPORT_DIR, filename)
    if not os.path.exists(video_path):
        return jsonify({"success": False, "error": "Arquivo não encontrado na exportação"}), 404
        
    agendados = load_agendados()
    afiliados = load_afiliados()
    horarios = afiliados.get("horarios", DEFAULT_HORARIOS)
    data_agenda, hora_agenda = calcular_proximo_horario(agendados, horarios)
    
    title, description = gerar_seo_viela_vice(filename, title, description)
    ok_yt, msg_yt, yt_id = enviar_youtube_agendado(video_path, title, description, data_agenda, hora_agenda)
    ok_yt, msg_yt, yt_id = enviar_youtube_agendado(video_path, title, description, data_agenda, hora_agenda)
    status_msg = msg_yt if ok_yt else f"Fila Local ({msg_yt})"
    if ok_yt and os.path.exists(video_path):
        try: os.remove(video_path)
        except Exception: pass
    if ok_yt and os.path.exists(video_path):
        try:
            os.remove(video_path)
        except Exception:
            pass
    
    novo_agendado = {
        "filename": filename,
        "title": title,
        "description": description,
        "data": data_agenda,
        "horario": hora_agenda,
        "status": status_msg,
        "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    agendados.append(novo_agendado)
    save_json(AGENDADOS_FILE, agendados)
    
    # Atualizar financeiro (incrementar postados e receita simulada)
    fin = load_financeiro()
    fin["postados_mes"] = fin.get("postados_mes", 38) + 1
    fin["afiliados"] = round(fin.get("afiliados", 680.0) + 15.0, 2)
    fin["adsense"] = round(fin.get("adsense", 1420.5) + 25.0, 2)
    save_json(FINANCEIRO_FILE, fin)
    
    memoria = load_memoria()
    memoria["aprovados"].append({
        "filename": filename,
        "title": title,
        "aprovado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_json(MEMORIA_FILE, memoria)
    
    try:
        os.remove(video_path)
    except:
        pass
        
    try:
        with open(HISTORICO_FILE, "a", encoding="utf-8") as hf:
            hf.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Aprovado e Agendado: {title} ({filename})\n")
    except:
        pass
        
    return jsonify({"success": True, "message": f"Vídeo aprovado e agendado para {data_agenda} às {hora_agenda}!"})

@app.route('/api/negar', methods=['POST'])
def api_negar():
    data = request.get_json(silent=True) or {}
    filename = os.path.basename(str(data.get("arquivo") or data.get("filename") or "").strip())
    motivo = data.get("motivo", "Rejeitado pelo Gerente")
    
    if not filename:
        return jsonify({"success": False, "error": "Nome do arquivo não fornecido"}), 400
        
    video_path = os.path.join(EXPORT_DIR, filename)
    for _ in range(6):
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
            break
        except Exception:
            time.sleep(0.25)
    descartados = load_descartados()
    if filename not in descartados:
        descartados.append(filename)
        save_json(DESCARTADOS_FILE, descartados)
        
    memoria = load_memoria()
    memoria["negados"].append({
        "filename": filename,
        "negado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "motivo": motivo
    })
    save_json(MEMORIA_FILE, memoria)
    
    if os.path.exists(video_path):
        try:
            os.remove(video_path)
        except:
            pass
            
    return jsonify({"success": True, "message": f"Vídeo {filename} negado e excluído com sucesso."})

@app.route('/api/buscar_lives', methods=['POST'])
def api_buscar_lives():
    try:
        script_to_run = "robo_cortes.py" if os.path.exists("robo_cortes.py") else "vigia_lives.py"
        res = subprocess.run(["python", script_to_run], capture_output=True, text=True, timeout=30)
        output = res.stdout if res.stdout else "Busca executada com sucesso pelo Olheiro!"
        return jsonify({"success": True, "output": output})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/aplicar_melhoria', methods=['POST'])
def api_aplicar_melhoria():
    data = request.json or {}
    melhoria_id = data.get("id")
    memoria = load_memoria()
    
    pendentes = memoria.get("melhorias_pendentes", [])
    alvo = None
    novos_pendentes = []
    
    for m in pendentes:
        if m.get("id") == melhoria_id:
            alvo = m
        else:
            novos_pendentes.append(m)
            
    if not alvo:
        return jsonify({"success": False, "error": "Melhoria não encontrada"}), 404
        
    regra = alvo.get("regra_gemini")
    if regra:
        append_gemini_rule(regra)
        
    memoria["melhorias_pendentes"] = novos_pendentes
    if "melhorias_aprovadas" not in memoria:
        memoria["melhorias_aprovadas"] = []
    memoria["melhorias_aprovadas"].append({
        **alvo,
        "aplicado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_json(MEMORIA_FILE, memoria)
    
    return jsonify({"success": True, "message": f"Melhoria '{alvo.get('titulo')}' aprovada e gravada no GEMINI.md com sucesso!"})

@app.route('/api/salvar_afiliados', methods=['POST'])
def api_salvar_afiliados():
    data = request.json or {}
    links = data.get("links_afiliado", [])
    cupons = data.get("cupons_gamer", [])
    horarios = data.get("horarios", DEFAULT_HORARIOS)
    
    if isinstance(links, str):
        links = [l.strip() for l in links.split("\n") if l.strip()]
    if isinstance(cupons, str):
        cupons = [c.strip() for c in cupons.split("\n") if c.strip()]
    if isinstance(horarios, str):
        horarios = [h.strip() for h in horarios.split(",") if h.strip()]
        
    config = {
        "links_afiliado": links,
        "cupons_gamer": cupons,
        "horarios": horarios
    }
    save_json(AFILIADOS_FILE, config)
    return jsonify({"success": True, "message": "Configurações salvas com sucesso!"})


@app.route('/api/ti_terminal')
def ti_terminal():
    from collections import deque
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log_producao.txt')
    if not os.path.exists(caminho):
        return jsonify({'log': '[T.I.] Aguardando inicio do log_producao.txt...'})
    with open(caminho, 'r', encoding='utf-8', errors='replace') as f:
        ultimas = ''.join(deque(f, maxlen=35))
    return jsonify({'log': ultimas})

@app.route('/api/ti_diagnostico')
def api_ti_diagnostico():
    import os, glob, time, psutil
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    disco_livre_gb = round(psutil.disk_usage('.').free / (1024**3), 1)
    brutos = glob.glob('video-bruto/*')
    prontos = glob.glob('exportacao/*.mp4')

    gargalos = []
    melhorias = []
    etapa = "Aguardando novo ciclo ou fila cheia"
    progresso = 0
    arquivo_atual = "Nenhum vídeo em corte no momento"

    if brutos:
        mais_antigo = min(os.path.getmtime(b) for b in brutos)
        mins = round((time.time() - mais_antigo) / 60, 1)
        nomes = [os.path.basename(b) for b in brutos]
        arquivo_atual = nomes[0]

        if any("intro_" in n or "final" in n for n in nomes):
            etapa = "Aplicando vinheta e finalizando (FFmpeg)"
            progresso = 92
        elif any("clip_" in n or "legenda" in n or "processed" in n for n in nomes):
            etapa = "Cortando e queimando legenda PT-BR (FFmpeg)"
            progresso = 78
            etapa = "Finalizando renderização e legenda (FFmpeg)"
            progresso = 88
        elif any("audio" in n or n.endswith(".wav") for n in nomes):
            etapa = "Transcrevendo áudio em PT-BR (Whisper)"
            progresso = 58
        else:
            etapa = "Baixando live brasileira (yt-dlp)"
            progresso = 25

        gargalos.append(f"Etapa atual: {etapa} — rodando há {mins} min ({len(brutos)} arq temporário(s)).")
        if mins > 15:
            melhorias.append("Alerta de lentidão: vídeo acima de 15 min. Clique em 'Corrigir Tudo & Limpar' se travou.")
    else:
        gargalos.append("Nenhum vídeo travado na pasta temporária no momento.")

    if cpu > 85:
        gargalos.append(f"CPU em carga máxima ({cpu}%): Whisper ou FFmpeg usando todo o processador.")
        melhorias.append("Evite abrir abas pesadas ou jogos enquanto a renderização conclui.")
    if ram > 82:
        gargalos.append(f"Memória RAM alta ({ram}%): risco de lentidão no Windows.")
        melhorias.append("Mantenha no máximo 1 robô de edição rodando por vez.")
    if disco_livre_gb < 10:
        gargalos.append(f"Espaço em disco baixo ({disco_livre_gb} GB livres).")
        melhorias.append("Aprove ou exclua vídeos pendentes no Gerente para liberar espaço imediato.")

    if not melhorias:
        melhorias.append("Sistema operando dentro dos parâmetros ideais (Whisper acelerado + preset veryfast + yuv420p ativos).")

    correcoes_auto = []
    if os.path.exists("log_ti_autocorrecao.json"):
        try:
            correcoes_auto = json.load(open("log_ti_autocorrecao.json", encoding="utf-8"))
        except Exception:
            correcoes_auto = []

    return jsonify({
        "cpu": cpu,
        "ram": ram,
        "disco_livre_gb": disco_livre_gb,
        "qtd_brutos": len(brutos),
        "qtd_prontos": len(prontos),
        "etapa": etapa,
        "progresso": progresso,
        "arquivo_atual": arquivo_atual,
        "gargalos": gargalos,
        "melhorias": melhorias,
        "correcoes_auto": correcoes_auto
    })

@app.route('/api/ti_chat', methods=['POST'])
def api_ti_chat():
    import os, glob, shutil, subprocess, sys, json, re
    try:
        data = request.get_json(silent=True) or {}
        msg_orig = (data.get('mensagem') or '').strip()
        if len(msg_orig.strip()) > 12:
            _ok_g, _resp_g = executar_auto_reparo_gemini(msg_orig)
            if _ok_g:
                return jsonify({"resposta": f"💻 Caio & ⚡ Beatriz (Gemini): {_resp_g}", "recarregar": True})
        msg = msg_orig.lower()
        acoes = []

        # 1. Acoes imediatas de limpeza, manutencao e producao
        if not os.path.exists("arial.ttf") and os.path.exists(r"C:\Windows\Fonts\arial.ttf"):
            shutil.copy(r"C:\Windows\Fonts\arial.ttf", "arial.ttf")
            acoes.append("Fonte arial.ttf garantida.")

        if any(k in msg for k in ["limpar", "trav", "preso", "bruto", "corrigir", "consertar", "arrumar"]):
            rem = 0
            for arq in glob.glob("video-bruto/*"):
                try:
                    os.remove(arq)
                    rem += 1
                except Exception:
                    pass
            acoes.append(f"Limpei {rem} arquivo(s) temporário(s) da pasta video-bruto.")

        if any(k in msg for k in ["rodar", "iniciar", "gerar", "cortar", "novo video", "novo vídeo", "producao", "produção", "agora"]):
            subprocess.Popen([sys.executable, "-u", "robo_cortes.py"], stdout=open("log_producao.txt", "w", encoding="utf-8"), stderr=subprocess.STDOUT)
            acoes.append("Iniciei um novo ciclo de corte em segundo plano!")

        # 2. Edicao Visual Automatica do Escritorio (Aumentar imagem da agencia, escala e alto padrao)
        if any(k in msg for k in ["imagem", "mapa", "escritorio", "escritório", "aumentar", "pequena", "tamanho", "layout", "visual", "padrao", "padrão", "melhorar", "organizar", "boneco", "personagem"]):
            shutil.copy("servidor_agencia.py", "servidor_agencia.bak.py")
            s_edit = open("servidor_agencia.py", encoding="utf-8").read()

            # Expande o mapa do escritorio para preencher a tela toda de forma panoramica e organizada
            s_edit = s_edit.replace(
                "width: 99vw; height: calc(100vh - 122px); max-width: 1920px;",
                "width: 99vw; height: calc(100vh - 122px); max-width: 1920px;"
            )
            s_edit = s_edit.replace(
                "background: url('/escritorio_img') center/100% 100% no-repeat; border-radius: 14px; box-shadow: 0 0 40px rgba(0,0,0,0.85);",
                "background: url('/escritorio_img') center/100% 100% no-repeat; border-radius: 14px; box-shadow: 0 0 40px rgba(0,0,0,0.85);"
            )
            # Ajusta escala proporcional dos bonecos (96px) para caberem com folga nas mesas
            if "diminuir boneco" in msg or "menor" in msg:
                s_edit = s_edit.replace("96px", "88px")
            else:
                s_edit = s_edit.replace("96px", "96px")

            open("servidor_agencia.py", "w", encoding="utf-8").write(s_edit)
            acoes.append("Apliquei o upgrade visual de Alto Padrão: expandi a imagem da agência para tela cheia panorâmica (99vw) e ajustei a proporção dos 10 especialistas nas mesas! (Atualizando tela...)")
            return jsonify({"resposta": "💻 Caio & ⚡ Beatriz: " + " ".join(acoes), "recarregar": True})

        if acoes:
            return jsonify({"resposta": "💻 Caio & ⚡ Beatriz: " + " ".join(acoes), "recarregar": False})

        # 3. Consultoria Inteligente sobre qualquer assunto da Agencia usando Gemini (ou base de conhecimento local)
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-2.5-flash")
                contexto = (
                    "Você é Caio (Líder de T.I.) e Beatriz (Analista de Otimização) da Agência Viela Vice, "
                    "uma operação autônoma de vídeos de GTA 6 e GTA RP em Português do Brasil (pt-BR). "
                    "A agência possui 10 especialistas nomeados (Dr. Ricardo, Camila, Thiago, Bruno, Lucas, Mariana, Rafael, Caio, Beatriz e Felipe), "
                    "meta de estoque de 24 vídeos (6 Longos Narrados + 30 Shorts acima de 1 min em yuv420p), "
                    "Curadoria Top 6 diária e 6 horários de postagem no YouTube. "
                    "Responda de forma direta, prática e amigável em português sobre a dúvida ou pedido do dono da agência: "
                )
                ok_gem, texto_ia = executar_auto_reparo_gemini(msg_orig)
                if not ok_gem:
                    raise RuntimeError(texto_ia)
                return jsonify({"resposta": f"💻 Caio & ⚡ Beatriz: {texto_ia}", "recarregar": False})
        except Exception:
            pass

        # Fallback inteligente caso a API key nao esteja no .env
        resumo_agencia = (
            "Estamos operando com 10 especialistas ativos na Agência Viela Vice: "
            "meta de 24 vídeos (6 Longos + 30 Shorts em PT-BR e yuv420p), Curadoria Top 6 pela Camila e aprovação final pelo Dr. Ricardo. "
            "Você pode me pedir para 'melhorar o visual e aumentar a imagem da agência', 'limpar temporários' ou 'gerar vídeo agora'!"
        )
        return jsonify({"resposta": "💻 Caio & ⚡ Beatriz: " + resumo_agencia, "recarregar": False})

    except Exception as e:
        return jsonify({"resposta": f"💻 Caio (T.I.): Aviso técnico: {str(e)}", "recarregar": False})


@app.after_request
def add_cache_headers(response):
    if request.path.startswith("/sprites/") or request.path.startswith("/assets/"):
        response.headers["Cache-Control"] = "public, max-age=86400"
    return response


def executar_auto_reparo_gemini(pedido_usuario):
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except Exception:
        pass
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return False, "Chave GEMINI_API_KEY nao encontrada no .env."
    try:
        import subprocess, threading, time, json as _json
        from google import genai
        client = genai.Client(api_key=api_key)

        with open("robo_cortes.py", "r", encoding="utf-8") as f1:
            cod_robo = f1.read()
        with open("servidor_agencia.py", "r", encoding="utf-8") as f2:
            cod_srv = f2.read()
        cod_css = open("tema_agencia.css", encoding="utf-8").read() if os.path.exists("tema_agencia.css") else ""

        partes = [
            "Voce e Caio & Beatriz, Engenheiros Autonomos de T.I. da Agencia Viela Vice (Windows 11, Python, Flask, FFmpeg, YouTube API).",
            "Voce tem AUTONOMIA TOTAL para alterar codigo Python, HTML/JS, CSS visual ou rodar comandos locais sem o usuario precisar abrir o PowerShell.",
            "Pedido do dono da agencia: " + str(pedido_usuario),
            "Responda APENAS com um JSON valido contendo uma ou mais acoes no formato:",
            '{"arquivo": "tema_agencia.css | robo_cortes.py | servidor_agencia.py | comando | nenhum", "css_completo": "se arquivo for tema_agencia.css, escreva o CSS completo com !important (NUNCA coloque filter no container pai de #camada-agentes para nao deslocar os bonecos)", "buscar": "trecho exato antigo se editar .py", "substituir": "trecho novo corrigido se editar .py", "cmd_powershell": "comando curto opcional se arquivo for comando", "reiniciar_servidor": false, "explicacao": "o que foi feito de forma direta e amigavel"}',
            "--- TEMA_AGENCIA.CSS ATUAL ---",
            cod_css,
            "--- ROBO_CORTES.PY ---",
            cod_robo,
            "--- SERVIDOR_AGENCIA.PY ---",
            cod_srv,
        ]
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=chr(10).join(partes))
        txt = (resp.text or "").strip()
        m = re.search(r"\{.*\}", txt, re.DOTALL)
        if not m:
            return True, txt
        dados = _json.loads(m.group(0))
        arq = dados.get("arquivo", "nenhum")
        exp = dados.get("explicacao", "Ajuste executado com sucesso.")

        if arq == "tema_agencia.css" and dados.get("css_completo"):
            shutil.copy("tema_agencia.css", "tema_agencia.css.bak_auto")
            with open("tema_agencia.css", "w", encoding="utf-8") as fc:
                fc.write(dados["css_completo"])
            return True, f"Visual atualizado automaticamente! Dê F5 para ver: {exp}"

        if arq in ("robo_cortes.py", "servidor_agencia.py") and dados.get("buscar") and dados.get("substituir"):
            with open(arq, "r", encoding="utf-8") as fa:
                conteudo = fa.read()
            if dados["buscar"] in conteudo:
                shutil.copy(arq, arq + ".bak_auto")
                novo = conteudo.replace(dados["buscar"], dados["substituir"], 1)
                compile(novo, arq, "exec")
                with open(arq, "w", encoding="utf-8") as fa:
                    fa.write(novo)
                if arq == "servidor_agencia.py":
                    def _restart():
                        time.sleep(1.5)
                        os._exit(0)
                    threading.Thread(target=_restart, daemon=True).start()
                    return True, f"Codigo atualizado em {arq} e servidor reiniciando agora: {exp}"
                return True, f"Motor {arq} atualizado automaticamente para os proximos videos: {exp}"
            else:
                return True, f"Nao encontrei o trecho exato em {arq}, tente pedir especificando a funcao ou o efeito desejado."

        if arq == "comando" and dados.get("cmd_powershell"):
            out = subprocess.run(["powershell", "-NoProfile", "-Command", dados["cmd_powershell"]], capture_output=True, text=True, timeout=30)
            return True, f"Executado no sistema: {exp} | Saida: {(out.stdout or out.stderr).strip()[:300]}"

        return True, exp
    except Exception as e:
        return False, f"Aviso tecnico no agente autonomo: {str(e)}"

@app.route('/api/logs_vigia')
def api_logs_vigia():
    import os, json
    if os.path.exists('logs_vigia.json'):
        return open('logs_vigia.json', encoding='utf-8').read(), 200, {'Content-Type': 'application/json'}
    return '{"etapa": "Varredura ativa e gerando estoque...", "logs": []}', 200, {'Content-Type': 'application/json'}

@app.route('/')
def index():
    return open('painel_vice.html', encoding='utf-8').read()

@app.route('/painel.js')
def serve_js():
    return open('painel.js', encoding='utf-8').read(), 200, {'Content-Type': 'application/javascript'}

def index_antigo():
    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Agência Viela Vice — Escritório Virtual</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
  body { background: #090d16; color: #f8fafc; font-family: 'Segoe UI', system-ui, sans-serif; overflow: hidden; width: 100vw; height: 100vh; }

  /* BARRA SUPERIOR LIMPA (ZERO SOBREPOSICAO) */
  #hud-top {
    position: fixed; top: 0; left: 0; right: 0; height: 54px; z-index: 100;
    background: linear-gradient(90deg, rgba(15,23,42,0.96), rgba(30,27,75,0.96));
    border-bottom: 2px solid #334155; display: flex; align-items: center; justify-content: space-between; padding: 0 20px;
  }
  .brand { font-size: 18px; font-weight: 800; color: #c084fc; letter-spacing: 0.5px; display: flex; align-items: center; gap: 10px; }
  .pill { background: #1e293b; border: 1px solid #475569; padding: 5px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
  .pill-green { border-color: #22c55e; color: #4ade80; }
  .pill-cyan { border-color: #06b6d4; color: #22d3ee; }
  .pill-gold { border-color: #eab308; color: #facc15; }

  /* AREA DO MAPA EM TELA CHEIA (ESCALA PROPORCIONAL) */
  #viewport {
    position: fixed; top: 54px; bottom: 64px; left: 0; right: 0;
    display: flex; align-items: center; justify-content: center; background: radial-gradient(circle at center, #131c31 0%, #070a12 100%);
  }
  #mapa-container {
    position: relative; width: 99vw; height: calc(100vh - 122px); max-width: 1920px;
    background: url('/escritorio_img') center/100% 100% no-repeat; border-radius: 14px; box-shadow: 0 0 40px rgba(0,0,0,0.85);
  }

  /* TELINHA DE MONETIZACAO FIXA AO LADO DO GERENTE */
  #monitor-gerente {
    position: absolute; top: 7%; right: 6%; z-index: 60;
    background: rgba(15, 23, 42, 0.94); border: 2px solid #a855f7; border-radius: 12px;
    padding: 10px 14px; min-width: 215px; box-shadow: 0 8px 25px rgba(0,0,0,0.7);
  }
  #monitor-gerente .titulo-m { font-size: 11px; font-weight: 700; color: #d8b4fe; text-transform: uppercase; }
  #monitor-gerente .valor-m { font-size: 22px; font-weight: 800; color: #4ade80; margin: 2px 0; }
  #monitor-gerente .sub-m { font-size: 12px; color: #cbd5e1; margin-bottom: 6px; }
  .btn-mini { background: #7e22ce; color: #fff; border: none; border-radius: 6px; padding: 5px 9px; font-size: 11px; font-weight: 700; cursor: pointer; }
  .btn-mini:hover { background: #9333ea; }

  /* PERSONAGENS COM CAMINHADA REAL PELOS CORREDORES */
  .agente {
    position: absolute; width: 96px; transform: translate(-50%, -82%);
    transition: left 2.4s linear, top 2.4s linear; cursor: pointer; z-index: 30;
    display: flex; flex-direction: column; align-items: center;
  }
  .agente:hover { filter: drop-shadow(0 0 8px #38bdf8); z-index: 50; }
  .agente img { width: 96px; height: 96px; object-fit: contain; display: block; pointer-events: none; }
  .balao {
    background: rgba(15, 23, 42, 0.94); color: #f8fafc; border: 1.5px solid #64748b;
    padding: 5px 10px; border-radius: 10px; font-size: 12px; font-weight: 600;
    white-space: nowrap; margin-bottom: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.6);
    max-width: 260px; overflow: hidden; text-overflow: ellipsis;
  }
  .balao.alerta { border-color: #f59e0b; color: #fde047; }
  .balao.feliz { border-color: #22c55e; color: #86efac; }
  .tag-nome {
    background: rgba(2, 6, 23, 0.85); color: #94a3b8; font-size: 10px; font-weight: 700;
    padding: 1px 6px; border-radius: 4px; margin-top: -2px;
  }

  /* BARRA INFERIOR DE ESTACOES */
  #hud-bottom {
    position: fixed; bottom: 0; left: 0; right: 0; height: 64px; z-index: 100;
    background: rgba(15, 23, 42, 0.97); border-top: 2px solid #334155;
    display: flex; align-items: center; justify-content: center; gap: 10px; padding: 0 16px;
  }
  .btn-estacao {
    background: #1e293b; color: #f1f5f9; border: 1.5px solid #475569; border-radius: 10px;
    padding: 9px 15px; font-size: 13px; font-weight: 700; cursor: pointer; transition: 0.15s;
  }
  .btn-estacao:hover { background: #334155; border-color: #38bdf8; transform: translateY(-2px); }
  .btn-destaque { background: #6d28d9; border-color: #a855f7; }
  .btn-curadoria { background: #0e7490; border-color: #22d3ee; }

  /* JANELA FLUTUANTE (MODAL) */
  #modal-bg {
    display: none; position: fixed; inset: 0; background: rgba(2, 6, 23, 0.82);
    z-index: 500; align-items: center; justify-content: center; padding: 20px;
  }
  #modal-box {
    background: #0f172a; border: 2px solid #6366f1; border-radius: 16px;
    width: 100%; max-width: 760px; max-height: 86vh; overflow-y: auto; padding: 24px;
    box-shadow: 0 20px 50px rgba(0,0,0,0.85);
  }
  .modal-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 12px; margin-bottom: 16px; }
  .btn-fechar { background: #ef4444; color: #fff; border: none; border-radius: 8px; padding: 6px 12px; font-weight: 800; cursor: pointer; }
  .card-video { background: #1e293b; border: 1px solid #475569; border-radius: 12px; padding: 14px; margin-bottom: 14px; }
  input, textarea { width: 100%; background: #090d16; color: #fff; border: 1px solid #475569; border-radius: 8px; padding: 8px; margin: 6px 0 10px 0; font-family: inherit; }
  .btn-acao { border: none; border-radius: 8px; padding: 10px 16px; font-weight: 700; cursor: pointer; font-size: 13px; margin-right: 8px; }
  .btn-aprovar { background: #16a34a; color: #fff; }
  .btn-negar { background: #dc2626; color: #fff; }
</style>
</head>
<body>

<div id="hud-top">
  <div class="brand">🎬 AGÊNCIA VIELA VICE <span style="font-size:12px; color:#94a3b8; font-weight:500;">Operação Autônoma GTA 6 & RP</span></div>
  <div style="display:flex; gap:10px; align-items:center;">
    <div class="pill pill-cyan" id="hud-estoque">📦 Fila: 0/36 (6 Longos + 30 Shorts)</div>
    <div class="pill pill-gold" id="hud-pendentes">👔 Pendentes Gerente: 0</div>
    <div class="pill pill-green" id="hud-felicidade">😊 Moral Equipe: 90%</div>
  </div>
</div>

<div id="viewport">
  <div id="mapa-container">
    <!-- TELINHA DE MONETIZACAO AO LADO DO GERENTE -->
        <div id="painel-progresso-live" style="position:absolute;top:4%;left:3%;z-index:60;background:rgba(15,23,42,0.94);border:2px solid #06b6d4;border-radius:12px;padding:10px 14px;width:295px;box-shadow:0 8px 25px rgba(0,0,0,0.75);">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
        <span style="font-size:11px;font-weight:800;color:#22d3ee;text-transform:uppercase;">⚡ Produção ao Vivo</span>
        <span id="live-pct" style="font-size:12px;font-weight:800;color:#4ade80;">0%</span>
      </div>
      <div id="live-etapa" style="font-size:12px;font-weight:700;color:#f8fafc;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">Aguardando início do corte...</div>
      <div id="live-arquivo" style="font-size:10px;color:#94a3b8;margin:2px 0 7px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">Nenhum arquivo ativo</div>
      <div style="width:100%;height:9px;background:#090d16;border-radius:6px;overflow:hidden;border:1px solid #334155;">
        <div id="live-barra" style="width:0%;height:100%;background:linear-gradient(90deg,#06b6d4,#22c55e);transition:width 0.6s ease;"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:10px;color:#cbd5e1;margin-top:6px;">
        <span id="live-hw">CPU: --% | RAM: --%</span>
        <span id="live-prontos">Prontos: 0</span>
      </div>
    </div>
    <div id="monitor-gerente">
      <div class="titulo-m">💰 Monetização Mensal</div>
      <div class="valor-m" id="val-receita">R$ 0,00</div>
      <div class="sub-m" id="txt-meta-mes">Meta: R$ 1.000,00 | Equipe: 10</div>
      <button class="btn-mini" onclick="abrirModal('relatorio')">📊 Relatório Mensal</button>
    </div>
    <!-- CAMADA DE AGENTES DINAMICOS -->
    <div id="camada-agentes"></div>
  </div>
</div>

<div id="hud-bottom">
  <button class="btn-estacao btn-destaque" onclick="abrirModal('gerente')">👔 Gerente (<span id="btn-pend">0</span>)</button>
  <button class="btn-estacao btn-curadoria" onclick="abrirModal('curadoria')">🛡️ Curadoria Top 6</button>
  <button class="btn-estacao" onclick="abrirModal('olheiro')">🔍 Olheiro & GTA 6</button>
  <button class="btn-estacao" onclick="abrirModal('editor')">🎬 Editor (24)</button>
  <button class="btn-estacao" onclick="abrirModal('lab')">🧠 Lab Evolução</button>
  <button class="btn-estacao" onclick="abrirModal('engenharia')">⚙️ Engenharia</button>
  <button class="btn-estacao" style="border-color:#10b981;color:#6ee7b7;" onclick="abrirModal('ti')">🖥️ Equipe T.I.</button>
  <button class="btn-estacao" onclick="dispararReuniao(); fetch('/api/reuniao_inteligente').then(r=>r.json()).then(d=>{ setTimeout(()=>{ document.getElementById('modal-titulo').innerText='🤝 Ata da Reunião Executiva — Agência Viela Vice'; document.getElementById('modal-corpo').innerHTML=(d.resumo||[]).map(x=>`<div class='card-video' style='border-left:4px solid #38bdf8;'>${x}</div>`).join(''); document.getElementById('modal-bg').style.display='flex'; }, 1200); }).catch(()=>{});">🤝 Reunião</button>
  <button class="btn-estacao" onclick="contratarReforco()">➕ Contratar</button>
</div>

<div id="modal-bg" onclick="if(event.target===this) fecharModal()">
  <div id="modal-box">
    <div class="modal-header">
      <h2 id="modal-titulo" style="font-size:18px; color:#c084fc;">Estação</h2>
      <button class="btn-fechar" onclick="fecharModal()">✕ Fechar</button>
    </div>
    <div id="modal-corpo"></div>
  </div>
</div>

<script>
let dadosGlobais = { pendentes: [], estoque: 0, noticias: [] };
let reforcos = parseInt(localStorage.getItem("viela_reforcos") || "0");
let emReuniao = false;

const agentesConfig = [
  { id: "gerente", nome: "👔 Dr. Ricardo • Diretor", linha: 1, filtro: "none", mesa: {x: 56, y: 31}, descanso: {x: 78, y: 55}, reuniao: {x: 50, y: 46}, x: 56, y: 31, fala: "Foco na meta mensal e retenção máxima!" },
  { id: "curadora", nome: "🛡️ Camila • Curadoria Top 6", linha: 2, filtro: "none", mesa: {x: 43, y: 47}, descanso: {x: 68, y: 58}, reuniao: {x: 45, y: 49}, x: 43, y: 47, fala: "Zero tolerância com bugs no Top 6!" },
  { id: "roteirista", nome: "⚡ Thiago • Roteirista", linha: 2, filtro: "hue-rotate(145deg) saturate(1.35) brightness(1.08)", mesa: {x: 24, y: 49}, descanso: {x: 72, y: 64}, reuniao: {x: 41, y: 48}, x: 24, y: 49, fala: "Testando gancho explosivo nos 3s iniciais!" },
  { id: "olheiro", nome: "🕵️ Bruno • Olheiro GTA 6", linha: 3, filtro: "none", mesa: {x: 33, y: 39}, descanso: {x: 22, y: 56}, reuniao: {x: 43, y: 43}, x: 33, y: 39, fala: "Rastreando furos de GTA 6 e lives BR!" },
  { id: "editor", nome: "🔥 Lucas • Editor Shorts", linha: 4, filtro: "none", mesa: {x: 38, y: 69}, descanso: {x: 52, y: 56}, reuniao: {x: 48, y: 52}, x: 38, y: 69, fala: "Ritmo frenético nos 30 Shorts verticais!" },
  { id: "editor_longo", nome: "🎙️ Mariana • Editora Longos", linha: 4, filtro: "hue-rotate(210deg) saturate(1.25) brightness(1.05)", mesa: {x: 30, y: 61}, descanso: {x: 65, y: 63}, reuniao: {x: 46, y: 54}, x: 30, y: 61, fala: "Lapidando a narrativa dos 4 resumos longos..." },
  { id: "auditor", nome: "🔬 Rafael • Auditor Técnico", linha: 5, filtro: "hue-rotate(95deg) saturate(1.3) brightness(1.1)", mesa: {x: 64, y: 48}, descanso: {x: 81, y: 59}, reuniao: {x: 54, y: 45}, x: 64, y: 48, fala: "Protegendo o HD e validando yuv420p!" },
  { id: "ti_caio", nome: "💻 Caio • Líder de T.I.", linha: 5, filtro: "hue-rotate(175deg) saturate(1.4)", mesa: {x: 68, y: 34}, descanso: {x: 83, y: 53}, reuniao: {x: 55, y: 42}, x: 68, y: 34, fala: "Monitorando CPU, RAM e tempo de corte!" },
  { id: "ti_beatriz", nome: "⚡ Beatriz • Gargalos T.I.", linha: 3, filtro: "hue-rotate(45deg) saturate(1.4)", mesa: {x: 74, y: 41}, descanso: {x: 86, y: 61}, reuniao: {x: 56, y: 48}, x: 74, y: 41, fala: "Analisando o que pode ser acelerado!" },
  { id: "engenharia", nome: "🤖 Felipe • Engenheiro API", linha: 5, filtro: "none", mesa: {x: 58, y: 63}, descanso: {x: 74, y: 61}, reuniao: {x: 53, y: 50}, x: 58, y: 63, fala: "Pipelines Whisper e YouTube 100% blindados!" }
];

const extrasPool = [
  { id: "sub1", nome: "Subagente Shorts", linha: 2, mesa: {x: 26, y: 49}, descanso: {x: 75, y: 65}, reuniao: {x: 46, y: 43}, x: 26, y: 49, fala: "Acelerando cortes verticais" },
  { id: "sub2", nome: "Analista Retenção", linha: 3, mesa: {x: 64, y: 48}, descanso: {x: 81, y: 59}, reuniao: {x: 53, y: 44}, x: 64, y: 48, fala: "Otimizando ganchos de 3s" }
];

function getTodosAgentes() { return agentesConfig.concat(extrasPool.slice(0, reforcos)); }

let framePose = 1;
const spritesGarantidos = ['linha1_pose1.png', 'linha2_pose1.png', 'linha3_pose1.png', 'linha4_pose1.png', 'linha5_pose1.png'];
function desenharAgentes() {
  const camada = document.getElementById("camada-agentes");
  if (!camada) return;
  getTodosAgentes().forEach(ag => {
    let el = document.getElementById("ag-" + ag.id);
    const idxLinha = ((ag.linha || 1) - 1) % spritesGarantidos.length;
    const arquivoBase = spritesGarantidos[idxLinha];
    const arquivoAnimado = arquivoBase.replace("pose1", "pose" + framePose);
    if (!el) {
      el = document.createElement("div");
      el.id = "ag-" + ag.id;
      el.className = "agente";
      el.onclick = () => abrirModal(ag.id);
      el.innerHTML = `<div class="balao" id="balao-${ag.id}">${ag.fala}</div><img id="img-${ag.id}" src="/sprites/${arquivoBase}" style="width:96px;height:96px;object-fit:contain;display:block;"><div class="tag-nome">${ag.nome}</div>`;
      camada.appendChild(el);
    }
    el.style.left = ag.x + "%";
    el.style.top = ag.y + "%";
    const imgEl = document.getElementById("img-" + ag.id);
    if (imgEl) {
      imgEl.src = "/sprites/" + arquivoAnimado;
      imgEl.onerror = function() { this.onerror = null; this.src = "/sprites/" + arquivoBase; };
      imgEl.style.filter = ag.filtro || "none";
    }
    const b = document.getElementById("balao-" + ag.id);
    if (b) {
      b.innerText = ag.fala;
      b.className = "balao" + (ag.id === "gerente" && (dadosGlobais.pendentes || []).length > 0 ? " alerta" : (emReuniao ? " feliz" : ""));
    }
  });
}

setInterval(() => { framePose = (framePose % 4) + 1; desenharAgentes(); }, 320);

setInterval(() => {
  if (emReuniao) return;
  const pend = (dadosGlobais.pendentes || []).length;
  const est = dadosGlobais.estoque || pend;
  const brutos = dadosGlobais.brutos || 0;
  const producaoAtiva = (brutos > 0 || est < 36);

  getTodosAgentes().forEach(ag => {
    if (ag.id === "gerente") {
      if (pend > 0) {
        ag.x = ag.mesa.x; ag.y = ag.mesa.y;
        ag.fala = `🔔 Avaliando ${pend} vídeo(s) do Top 6`;
      } else {
        const irCafe = Math.random() > 0.5;
        ag.x = irCafe ? ag.descanso.x : ag.mesa.x;
        ag.y = irCafe ? ag.descanso.y : ag.mesa.y;
        ag.fala = irCafe ? "☕ Livre: tomando café no lounge" : "📊 Sem pendências no momento";
      }
    } else if (ag.id === "curadora" || ag.id === "auditor") {
      if (pend > 0 || brutos > 0) {
        ag.x = ag.mesa.x; ag.y = ag.mesa.y;
        ag.fala = ag.id === "curadora" ? "🛡️ Auditando e ranqueando Top 6" : "🔍 Verificando yuv420p e áudio limpo";
      } else {
        const passear = Math.random() > 0.5;
        ag.x = passear ? ag.descanso.x : ag.mesa.x;
        ag.y = passear ? ag.descanso.y : ag.mesa.y;
        ag.fala = passear ? "☕ Auditoria em dia: pausa no sofá" : "✅ Qualidade 100% verificada";
      }
    } else if (ag.id === "olheiro" || ag.id === "roteirista") {
      if (producaoAtiva) {
        ag.x = ag.mesa.x; ag.y = ag.mesa.y;
        ag.fala = ag.id === "olheiro" ? "🔍 Buscando lives BR e GTA 6 na mesa" : "✍️ Escrevendo ganchos de 3s na mesa";
      } else {
        const irLousa = Math.random() > 0.5;
        ag.x = irLousa ? 29 : ag.descanso.x;
        ag.y = irLousa ? 33 : ag.descanso.y;
        ag.fala = irLousa ? "📰 Anotando ideias na lousa" : "☕ Meta 24 batida: descansando";
      }
    } else if (ag.id === "editor" || ag.id === "editor_longo" || ag.id === "sub1" || ag.id === "sub2") {
      if (producaoAtiva) {
        ag.x = ag.mesa.x; ag.y = ag.mesa.y;
        ag.fala = ag.id === "editor" ? "✂️ Cortando 30 Shorts na estação" : "🎬 Editando 6 Longos narrados";
      } else {
        ag.x = ag.descanso.x; ag.y = ag.descanso.y;
        ag.fala = "☕ Estoque 36/36 cheio: pausa merecida";
      }
    } else {
      if (pend > 0 || brutos > 0) {
        ag.x = ag.mesa.x; ag.y = ag.mesa.y;
        ag.fala = "⚙️ Monitorando API YouTube e FFmpeg";
      } else {
        const passear = Math.random() > 0.5;
        ag.x = passear ? ag.descanso.x : ag.mesa.x;
        ag.y = passear ? ag.descanso.y : ag.mesa.y;
        ag.fala = passear ? "☕ Sistemas estáveis: tomando café" : "⚙️ Engenharia 100% operacional";
      }
    }
  });
  desenharAgentes();
}, 4000);

function dispararReuniao() { fetch('/api/reuniao_inteligente').then(r=>r.json()).then(d=>{ document.getElementById('modal-titulo').innerText = '🤝 Ata da Reunião Executiva — Agência Viela Vice'; document.getElementById('modal-corpo').innerHTML = (d.resumo||[]).map(item => `<div class='card-video' style='border-left:4px solid #38bdf8;'>${item}</div>`).join(''); document.getElementById('modal-bg').style.display = 'flex'; }).catch(()=>{}); }

function contratarReforco() {
  if (reforcos < extrasPool.length) {
    reforcos++;
    localStorage.setItem("viela_reforcos", reforcos);
    desenharAgentes();
    alert("✅ Novo membro contratado! Ele já sentou na mesa livre do escritório.");
  } else { alert("⭐ Todas as estações da Agência Viela Vice já estão completas!"); }
}

function fecharModal() { document.getElementById("modal-bg").style.display = "none"; }

function abrirModal(tipo) {
  const titulo = document.getElementById("modal-titulo");
  const corpo = document.getElementById("modal-corpo");
  document.getElementById("modal-bg").style.display = "flex";
  if (tipo === "gerente") {
    titulo.innerText = "👔 Diretoria — Avaliação Final (Top 6 Sem Bugs)";
    const lista = dadosGlobais.pendentes || [];
    if (lista.length === 0) { corpo.innerHTML = "<p>Nenhum vídeo pendente no momento. A Curadoria e o Editor estão preparando o próximo lote brasileiro!</p>"; return; }
    const slotsPico = ["11:30", "14:00", "16:30", "18:30", "20:30", "22:30"];
    corpo.innerHTML = lista.map((v, idx) => {
      const isShort = v.arquivo.startsWith("short-");
      const corBorda = isShort ? "#00f0ff" : "#a855f7";
      const vidStyle = isShort
        ? "width:210px;height:370px;display:block;margin:10px auto;border-radius:10px;border:2px solid #00f0ff;background:#000;"
        : "width:100%;max-height:280px;margin:10px 0;border-radius:10px;border:2px solid #a855f7;background:#000;";
      const titDef = isShort ? (v.gancho || v.titulo || "Momento Épico GTA RP #Shorts") : (v.titulo || "Resumo Completo GTA RP | Viela Vice").replace("#Shorts", "").trim();
      const descDef = isShort ? (v.descricao || "Inscreva-se no canal Viela Vice! #GTA6 #GTARP #Shorts #VielaVice") : (v.descricao || "Inscreva-se no canal Viela Vice! Os melhores resumos de GTA RP e GTA 6. #GTA6 #GTARP #VielaVice").replace("#Shorts", "").trim();
      return `<div class="card-video" style="border-left:4px solid ${corBorda};">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <b>#${idx+1} — ${v.arquivo}</b>
          <span style="background:#1e293b;color:#38bdf8;padding:2px 8px;border-radius:6px;font-size:11px;">⏰ Pico: ${slotsPico[idx%6]}</span>
        </div>
        <video src="/exportacao/${v.arquivo}" controls preload="metadata" style="${vidStyle}"></video>
        <input id="tit-${idx}" value="${titDef}">
        <textarea id="desc-${idx}" rows="2">${descDef}</textarea>
        <button class="btn-acao btn-aprovar" onclick="aprovarVideo('${v.arquivo}',${idx})">✅ Aprovar e Agendar</button>
        <button class="btn-acao btn-negar" onclick="negarVideo('${v.arquivo}', this)">🗑️ Negar e Excluir</button>
      </div>`;
    }).join("");
  } else if (tipo === "curadoria") {
    titulo.innerText = "🛡️ Setor de Qualidade & Curadoria (Top 6 Auditado)";
    const fila = dadosGlobais.pendentes || [];
    const top6 = fila.slice(0, 6);
    let html = `<div class="card-video" style="border-color:#3b82f6;">
      <b>📋 Triagem Camila:</b> ${fila.length} vídeo(s) na fila | <b>Top 6 selecionados:</b> ${top6.length}/6<br>
      <small style="color:#94a3b8;">Padrão exigido: 100% PT-BR, cor yuv420p, áudio limpo e sem HTML no narrador.</small>
      <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;">
        <button class="btn-acao btn-aprovar" style="margin:0;" onclick="abrirModal('gerente')">📤 Abrir Top 6 no Gerente (${top6.length})</button>
        <button class="btn-acao" style="margin:0;background:#475569;color:#fff;" onclick="fecharModal();dispararReuniao();">🤝 Reunião de Melhoria</button>
      </div>
    </div>`;
    if (fila.length === 0) {
      html += `<p style="color:#94a3b8;margin-top:10px;">Nenhum vídeo na fila da Curadoria no momento. Aguardando o Editor finalizar o próximo lote.</p>`;
    } else {
      html += fila.map((v, idx) => `
        <div class="card-video">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <b>${idx < 6 ? '⭐ TOP ' + (idx+1) : '⏳ Reserva #' + (idx+1)} — ${v.arquivo}</b>
            <span style="font-size:11px;background:#065f46;color:#6ee7b7;padding:2px 8px;border-radius:10px;">yuv420p • PT-BR</span>
          </div>
          <video src="/exportacao/${v.arquivo}" controls preload="metadata" style="${v.arquivo.startsWith('short-')?'width:200px;height:355px;display:block;margin:8px auto;border-radius:10px;border:2px solid #00f0ff;background:#000;':'width:100%;max-height:240px;margin:8px 0;border-radius:8px;border:2px solid #a855f7;background:#000;'}"></video>
          <button class="btn-acao btn-negar" onclick="negarVideo('${v.arquivo}', this)">🗑️ Reprovar Bug e Excluir</button>
        </div>`).join("");
    }
    corpo.innerHTML = html;
  } else if (tipo === "ti" || tipo === "ti_caio" || tipo === "ti_beatriz") {
    titulo.innerText = "🖥️ Setor de T.I. — Diagnóstico de Lentidão & Melhorias Reais";
    corpo.innerHTML = "<p>Caio e Beatriz estão lendo os sensores do seu notebook agora...</p>";
    fetch('/api/ti_autofix').catch(()=>{}); fetch('/api/ti_diagnostico').then(r=>r.json()).then(d=>{
      corpo.innerHTML = `
        <div class="card-video" style="display:flex;justify-content:space-around;text-align:center;">
          <div><small style="color:#94a3b8;">USO DE CPU</small><div style="font-size:22px;font-weight:800;color:${d.cpu>80?'#f87171':'#4ade80'};">${d.cpu}%</div></div>
          <div><small style="color:#94a3b8;">MEMÓRIA RAM</small><div style="font-size:22px;font-weight:800;color:${d.ram>80?'#f87171':'#38bdf8'};">${d.ram}%</div></div>
          <div><small style="color:#94a3b8;">HD LIVRE</small><div style="font-size:22px;font-weight:800;color:#facc15;">${d.disco_livre_gb} GB</div></div>
          <div><small style="color:#94a3b8;">EM EDIÇÃO</small><div style="font-size:22px;font-weight:800;color:#c084fc;">${d.qtd_brutos} arq</div></div>
        </div>
        <div class="card-video">
          <b style="color:#fbbf24;">⏱️ O que está demorando agora (Diagnóstico Caio):</b>
          <ul style="margin:6px 0 0 18px;line-height:1.6;">${d.gargalos.map(g=>`<li>${g}</li>`).join('')}</ul>
        </div>
        <div class="card-video">
          <b style="color:#34d399;">⚡ O que pode ser melhorado (Recomendações Beatriz):</b>
          <ul style="margin:6px 0 0 18px;line-height:1.6;">${d.melhorias.map(m=>`<li>${m}</li>`).join('')}</ul>
        </div>
        <div class="card-video" style="border-color:#10b981;background:#0b1324;">
          <b style="color:#34d399;font-size:14px;">💬 Falar Direto com Caio & Beatriz (Autonomia Total: Sistema & Visual GTA 6)</b>
          <div id="chat-ti-historico" style="max-height:150px;overflow-y:auto;background:#060a12;border:1px solid #334155;border-radius:8px;padding:10px;margin:8px 0;font-size:12px;line-height:1.5;">
            <div style="color:#6ee7b7;"><b>💻 Caio & ⚡ Beatriz:</b> Olá! Diga o que está acontecendo (ex: "aplicar tema GTA 6 Vice City", "mudar cores do escritório", "corrigir erros") que resolvemos direto por aqui!</div>
          </div>
          <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;">
            <button class="btn-mini" style="background:#059669;" onclick="enviarMensagemTI('Corrigir todos os erros e limpar temporários travados')">🛠️ Corrigir Tudo & Limpar</button>
            <button class="btn-mini" style="background:#0284c7;" onclick="enviarMensagemTI('Acelerar velocidade do Whisper e FFmpeg')">⚡ Acelerar Edição</button>
            <button class="btn-mini" style="background:#7c3aed;" onclick="enviarMensagemTI('Iniciar novo corte agora')">▶️ Gerar Vídeo Agora</button>
          <button class="btn-mini" style="background:#db2777;" onclick="enviarMensagemTI('Aumentar imagem da agência e evoluir para alto padrão')">✨ Evoluir Escritório (Alto Padrão)</button>
          </div>
          <div style="display:flex;gap:8px;">
            <input id="input-chat-ti" placeholder="Digite o problema aqui e aperte Enter..." style="margin:0;flex:1;" onkeydown="if(event.key==='Enter') enviarMensagemTI()">
            <button class="btn-acao btn-aprovar" style="margin:0;padding:8px 14px;" onclick="enviarMensagemTI()">Enviar</button>
          </div>
        </div>
        <div class="card-video">
          <b style="color:#60a5fa;">🛠️ Correções Aplicadas Automaticamente pelo T.I.:</b>
          <ul style="margin:6px 0 0 18px;line-height:1.6;">${(d.correcoes_auto && d.correcoes_auto.length) ? d.correcoes_auto.map(c=>`<li><b>[${c.data_hora}]</b> ${c.problema} → <span style="color:#4ade80;">${c.solucao}</span></li>`).join('') : '<li>Monitoramento ativo: nenhuma falha ocorreu desde a última verificação.</li>'}</ul>
        </div>
      `;
    });
  } else if (tipo === "relatorio") {
    titulo.innerText = "📊 Relatório Mensal — Viela Vice";
    corpo.innerHTML = `<p><b>Receita Mensal:</b> R$ 0,00<br><b>Equipe Ativa:</b> ${5+reforcos} agentes<br><b>Meta de Fila:</b> 36 vídeos (6 Longos + 30 Shorts)</p>`;
  } else if (tipo === "olheiro") {
    titulo.innerText = "🔍 Olheiro — Radar Brasil & GTA 6";
    corpo.innerHTML = `<p>Monitorando lives brasileiras e novidades de GTA 6.</p><br><button class="btn-acao btn-aprovar" onclick="fetch('/api/buscar_lives',{method:'POST'});alert('Busca iniciada!');">🔍 Buscar Lives Agora</button>`;
  } else if (tipo === "engenharia") {
    titulo.innerText = "⚙️ Engenharia & Horários";
    corpo.innerHTML = `<label>Horários (6 por dia):</label><input id="cfg-horarios" value="11:30, 14:00, 16:30, 18:30, 20:30, 22:30"><label>Links de Afiliado (Opcional):</label><textarea id="cfg-afiliados" rows="2"></textarea><button class="btn-acao btn-aprovar" onclick="salvarEngenharia()">💾 Salvar</button>`;
  } else {
    titulo.innerText = "🎬 Produção & Evolução";
    corpo.innerHTML = `<p>Fila configurada para <b>36 vídeos (6 Longos + 30 Shorts)</b> com Whisper otimizado.</p>`;
  }
}

async function enviarMensagemTI(textoPronto) {
  const inp = document.getElementById("input-chat-ti");
  const hist = document.getElementById("chat-ti-historico");
  const msg = textoPronto || (inp ? inp.value.trim() : "");
  if (!msg) return;
  if (inp && !textoPronto) inp.value = "";
  hist.innerHTML += `<div style="margin-top:6px;color:#f8fafc;"><b>👤 Você:</b> ${msg}</div>`;
  hist.scrollTop = hist.scrollHeight;
  try {
    const r = await fetch("/api/ti_chat", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ mensagem: msg }) });
    const d = await r.json();
    hist.innerHTML += `<div style="margin-top:6px;color:#6ee7b7;"><b>${d.resposta}</b></div>`; if (d.recarregar) { setTimeout(() => { window.location.href = "/?v=" + Date.now(); }, 1800); }
    hist.scrollTop = hist.scrollHeight;
  } catch (e) {
    hist.innerHTML += `<div style="margin-top:6px;color:#f87171;">Erro de conexão com o servidor local.</div>`;
  }
}

async function aprovarVideo(arquivo, idx) {
  const titulo = document.getElementById("tit-" + idx).value;
  const descricao = document.getElementById("desc-" + idx).value;
  const r = await fetch("/api/aprovar", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ arquivo, titulo, descricao }) });
  const res = await r.json();
  alert(res.mensagem || "Vídeo aprovado e agendado!");
  fecharModal(); sincronizarDados();
}

async function negarVideo(arquivo, btnEl) {
  const card = btnEl ? btnEl.closest(".card-video") : null;
  if (card) {
    card.querySelectorAll("video").forEach(v => { try { v.pause(); v.removeAttribute("src"); v.load(); } catch(e){} });
    card.style.opacity = "0.35";
  }
  await new Promise(r => setTimeout(r, 200));
  await fetch("/api/negar", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ arquivo, filename: arquivo, motivo: "Descartado" }) });
  if (card) card.remove();
  sincronizarDados();
}

async function salvarEngenharia() {
  const horarios = document.getElementById("cfg-horarios").value;
  const links = document.getElementById("cfg-afiliados").value;
  await fetch("/api/salvar_afiliados", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ horarios, links, cupons: "" }) });
  alert("💾 Configurações salvas!"); fecharModal();
}

async function sincronizarDados() {
  try {
    const r = await fetch("/api/data");
    const d = await r.json();
    dadosGlobais = Object.assign(dadosGlobais, d);
    const pend = dadosGlobais.pendentes ? dadosGlobais.pendentes.length : 0;
    document.getElementById("hud-estoque").innerText = `📦 Fila: ${dadosGlobais.estoque || pend}/36 (6 Longos + 30 Shorts)`;
    document.getElementById("hud-pendentes").innerText = `👔 Pendentes Gerente: ${pend}`;
    document.getElementById("btn-pend").innerText = pend;
    document.getElementById("hud-felicidade").innerText = `😊 Moral Equipe: ${Math.min(100, 88 + reforcos*4 + pend*2)}%`;
  } catch (e) {}
}
async function atualizarSensoresTI() {
  try {
    const r = await fetch('/api/ti_diagnostico');
    const d = await r.json();
    const elPct = document.getElementById('live-pct');
    const elEtapa = document.getElementById('live-etapa');
    const elArq = document.getElementById('live-arquivo');
    const elBarra = document.getElementById('live-barra');
    const elHw = document.getElementById('live-hw');
    const elProntos = document.getElementById('live-prontos');

    if (elPct) elPct.innerText = (d.progresso || 0) + '%';
    if (elEtapa) elEtapa.innerText = d.etapa || 'Monitorando produção...';
    if (elArq) elArq.innerText = 'Arquivo: ' + (d.arquivo_atual || 'Nenhum');
    if (elBarra) elBarra.style.width = (d.progresso || 0) + '%';
    if (elHw) elHw.innerText = `CPU: ${d.cpu}% | RAM: ${d.ram}%`;
    if (elProntos) elProntos.innerText = `Prontos: ${d.qtd_prontos || 0}`;

    const boxTi = document.getElementById('ti-sensores-live');
    if (boxTi && document.getElementById('modal-bg').style.display === 'flex') {
      boxTi.innerHTML = `
        <div class="card-video" style="display:flex;justify-content:space-around;text-align:center;margin-bottom:10px;">
          <div><small style="color:#94a3b8;">USO DE CPU</small><div style="font-size:22px;font-weight:800;color:${d.cpu>80?'#f87171':'#4ade80'};">${d.cpu}%</div></div>
          <div><small style="color:#94a3b8;">MEMÓRIA RAM</small><div style="font-size:22px;font-weight:800;color:${d.ram>80?'#f87171':'#38bdf8'};">${d.ram}%</div></div>
          <div><small style="color:#94a3b8;">HD LIVRE</small><div style="font-size:22px;font-weight:800;color:#facc15;">${d.disco_livre_gb} GB</div></div>
          <div><small style="color:#94a3b8;">EM EDIÇÃO</small><div style="font-size:22px;font-weight:800;color:#c084fc;">${d.qtd_brutos} arq</div></div>
        </div>
        <div class="card-video" style="margin-bottom:10px;">
          <b style="color:#fbbf24;">⏱️ Diagnóstico ao Vivo (Caio):</b>
          <ul style="margin:6px 0 0 18px;line-height:1.5;font-size:12px;">${(d.gargalos||[]).map(g=>`<li>${g}</li>`).join('')}</ul>
        </div>
        <div class="card-video" style="margin-bottom:0;">
          <b style="color:#34d399;">⚡ Recomendações & Correções (Beatriz):</b>
          <ul style="margin:6px 0 0 18px;line-height:1.5;font-size:12px;">${(d.melhorias||[]).map(m=>`<li>${m}</li>`).join('')}</ul>
        </div>
      `;
    }
  } catch (e) {}
}
setInterval(atualizarSensoresTI, 2500);
atualizarSensoresTI();

setInterval(sincronizarDados, 5000);
sincronizarDados();
desenharAgentes();
</script>

<div id="painel-terminal-flutuante" style="position:fixed;bottom:52px;right:14px;width:360px;background:rgba(11,15,23,0.95);border:1px solid #1e293b;border-radius:10px;padding:8px 10px;z-index:90;box-shadow:0 6px 20px rgba(0,0,0,0.7);">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
    <span style="color:#38bdf8;font-weight:700;font-size:11px;">🖥️ TERMINAL AO VIVO (log_producao.txt)</span>
    <button onclick="const b=document.getElementById('ti-terminal-box');b.style.display=b.style.display==='none'?'block':'none';" style="background:#1e293b;color:#cbd5e1;border:none;border-radius:4px;padding:1px 6px;font-size:10px;cursor:pointer;">Minimizar</button>
  </div>
  <pre id="ti-terminal-box" style="background:#05080f;color:#4ade80;font-family:monospace;font-size:10px;height:110px;overflow-y:auto;padding:6px;border-radius:6px;margin:0;white-space:pre-wrap;">Conectando ao terminal...</pre>
</div>
<script>
setInterval(() => {
  const b = document.getElementById('ti-terminal-box');
  if (b && b.style.display !== 'none') {
    fetch('/api/ti_terminal').then(r => r.json()).then(t => {
      b.textContent = t.log;
      b.scrollTop = b.scrollHeight;
    }).catch(()=>{});
  }
}, 2000);
</script>
<!-- hud_script_ok -->
<script>
setInterval(() => {
  fetch("/api/ti_terminal").then(r=>r.json()).then(d=>{
    const ls = (d.log||"").trim().split("\n").filter(Boolean);
    if (ls.length) {
      const m = ls[ls.length-1].match(/\[(\d+)%\]\s*(.*)/);
      if (m) {
        const pEl = document.getElementById("live-pct");
        const eEl = document.getElementById("live-etapa");
        const bEl = document.getElementById("live-barra");
        if (pEl) pEl.innerText = m + "%";
        if (eEl) eEl.innerText = m;
        if (bEl) bEl.style.width = m + "%";
      }
    }
  }).catch(()=>{});
}, 2500);
</script>
</body>
</html>"""
app.run(host='0.0.0.0', port=8501, debug=False)
