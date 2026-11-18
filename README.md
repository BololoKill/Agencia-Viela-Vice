# 🏢 Agência Viela Vice — Operação Autônoma de Mídia

> Sistema inteligente e gamificado de curadoria, corte, edição e publicação autônoma de Shorts e resumos de **GTA RP e GTA 6** para o YouTube.

---

## 🎯 Visão do Produto

A **Agência Viela Vice** funciona como uma emissora de TV digital autônoma, operada por uma equipe de especialistas virtuais. O sistema rastreia as maiores transmissões ao vivo do cenário brasileiro de GTA RP, recorta os momentos de maior retenção, gera legendas sincronizadas, queima introduções narradas por inteligência artificial e entrega os melhores cortes prontos para aprovação e agendamento no YouTube.

---

## 👥 A Equipe Virtual

| Especialista | Função no Sistema | Módulo Técnico |
|---|---|---|
| **Dr. Ricardo** | Diretor Geral (Aprovação Final) | Interface de Avaliação (`painel_vice.html`) |
| **Camila** | Líder de Curadoria & Qualidade | Auditoria FFprobe & Ranking Top 6 (`src/pipeline/quality.py`) |
| **Bruno** | Olheiro de Tendências & GTA 6 | Rastreamento de Criadores via yt-dlp (`src/pipeline/searcher.py`) |
| **Lucas & Mariana** | Editores de Shorts e Longos | Fatiamento Whisper & FFmpeg (`src/pipeline/renderer.py`) |
| **Rafael** | Auditor Técnico & Proteção do Disco | Validação de Codec (yuv420p) e Limpeza Automática |
| **Caio & Beatriz** | Setor de T.I. & Otimização | Telemetria de CPU/RAM e Auto-diagnóstico |
| **Felipe** | Engenheiro de API do YouTube | Publicação Agendada e Gestão de Canais (`src/youtube/uploader.py`) |

---

## 📐 Padrões Técnicos Obrigatórios

- **Proporção:** 9:16 Vertical (1080x1920)
- **Taxa de Quadros:** 30 fps
- **Formato de Cor:** `yuv420p` (H.264)
- **Áudio:** AAC 192kbps (sem sobreposição de vozes)
- **Motor de Renderização:** **FFmpeg Direto** (O uso de MoviePy é estritamente proibido)
- **Transcrição:** OpenAI Whisper (`pt-BR`) com censura rigorosa de profanidades
- **Encerramento:** Banner e áudio de Call to Action (CTA) nos últimos 4 segundos

---

## 📁 Estrutura do Projeto

```
editor-de-video/
├── main.py                     # Ponto de entrada CLI do sistema
├── requirements.txt            # Dependências oficiais pinadas
├── .env.example                # Template de variáveis de ambiente
├── .gitignore                  # Proteção estrita de tokens e dados pesados
│
├── src/                        # Código-fonte modular
│   ├── config.py               # Constantes, canais e parâmetros centrais
│   ├── utils.py                # Persistência JSON e sanitização de texto
│   │
│   ├── pipeline/               # Motor de Produção de Vídeo
│   │   ├── searcher.py         # Varredura de lives no YouTube
│   │   ├── downloader.py       # Download eficiente em 720p
│   │   ├── transcriber.py      # Transcrição Whisper e fatiamento SRT
│   │   ├── renderer.py         # Renderização FFmpeg 9:16 com vinheta e CTA
│   │   ├── quality.py          # Auditoria técnica com FFprobe e Top 6
│   │   └── worker.py           # Loop contínuo de produção autônoma
│   │
│   ├── youtube/                # Integração com a API do YouTube
│   │   ├── auth.py             # Autenticação OAuth2 dos 7 canais
│   │   └── uploader.py         # Agendamento e publicação com publishAt
│   │
│   ├── web/                    # Servidor Web do Escritório Virtual
│   │   └── app.py              # Aplicação Flask e rotas de API
│   │
│   └── governance/             # Governança e Alinhamento
│       └── meetings.py         # Registro de atas executivas dos agentes
│
├── sprites/                    # Sprites dos 10 agentes em pixel art
├── painel_vice.html            # Interface visual do Escritório Virtual
├── painel.js                   # Animações, docking e chamadas de API
├── tema_agencia.css            # Estilo escuro futurista do painel
│
├── exportacao/                 # Fila de vídeos prontos para revisão
├── video-bruto/                # Pasta de arquivos temporários de edição
└── archive/                    # Backups antigos e scripts descartáveis organizados
```

---

## 🚀 Como Executar

### 1. Instalação das Dependências

Certifique-se de possuir o Python 3.10+ e o FFmpeg instalado e acessível no PATH:

```bash
pip install -r requirements.txt
```

### 2. Configuração de Variáveis de Ambiente

Copie o modelo de ambiente e insira suas credenciais:

```bash
cp .env.example .env
```

### 3. Modos de Inicialização

**Iniciar Sistema Completo (Servidor Web + Robô de Produção):**
```bash
python main.py run
```
Acesse o Escritório Virtual em: `http://localhost:8501`

**Iniciar Apenas o Escritório Virtual:**
```bash
python main.py server
```

**Iniciar Apenas o Robô Vigia em Segundo Plano:**
```bash
python main.py worker
```

**Executar Auditoria Técnica de Qualidade:**
```bash
python main.py curadoria
```

**Registrar Reunião Executiva de Governança:**
```bash
python main.py reuniao
```
