# Agencia Viela Vice

Sistema automatizado de gestao, edicao e publicacao de video com painel interativo.

## Arquitetura do Projeto

O projeto adota uma estrutura modular em Python dividida em:

- **`src/config.py`**: Parametros operacionais, canais, lista de criadores e caminhos.
- **`src/utils.py`**: Persistencia JSON segura, sanitizacao de texto e logs.
- **`src/pipeline/`**:
  - `searcher.py`: Descoberta de conteudos com yt-dlp.
  - `downloader.py`: Ingestao e download de video bruto.
  - `transcriber.py`: Transcricao de audio via Whisper e geracao de SRT.
  - `renderer.py`: Composicao e exportacao de video vertical com FFmpeg direto.
  - `quality.py`: Auditoria tecnica de duracao e formato via ffprobe.
  - `worker.py`: Loop autonomo de monitoramento e producao.
- **`src/youtube/`**: Autenticacao OAuth2 e agendamento de upload via YouTube API v3.
- **`src/web/`**: Servidor Flask que serve a interface e rotas REST.
- **`src/governance/`**: Registro de atas e diretrizes operacionais.

## Execucao

O ponto de entrada unico e o `main.py`:

```bash
# Executar servidor web e worker concorrentemente
python main.py run

# Executar apenas o servidor web
python main.py server --port 8501

# Executar apenas o worker de producao
python main.py worker

# Executar auditoria de qualidade da fila
python main.py curadoria
```

## Seguranca

Arquivos de configuracao sensiveis (`.env`), tokens de autenticacao (`token*.json`) e credenciais de cliente (`client_secret*.json`) sao ignorados pelo `.gitignore` e nunca devem ser versionados.
