# Diretrizes do Projeto

- Responda sempre em português simples e objetivo.
- **PROIBIDO O USO DE MOVIEPY:** Nunca utilizar a biblioteca MoviePy para edição ou processamento de vídeos (utilizar sempre FFmpeg direto via linha de comando para garantir estabilidade, nitidez e evitar corrupção de imagens/acentos).

## Padrão de Referência Técnico (Vídeos / YouTube Shorts)

Com base na análise dos vídeos de referência (`3yGYehFfUP8` e `zrre7u9a6qM`), os padrões técnicos recomendados são:

- **Proporção (Aspect Ratio):** 9:16 (Vertical)
- **Resoluções Comuns:** 
  - Full HD: 1080x1920 (ex: `3yGYehFfUP8.mp4`)
  - HD: 720x1280 (ex: `zrre7u9a6qM.mp4`)
- **Taxa de Quadros (Frame Rate):** 30 fps (`30/1`)
- **Duração Média:** Variável para Shorts (ex: ~24s a ~41s)
- **Regra de Monetização / Duração Alvo:** 65 a 75 segundos.

## Lista Oficial de Streamers de GTA RP (Busca Automática)

- **Brasil:**
  - Paulinho o Loko
  - LOUD Coringa
  - Luqueta
  - Piozinho
  - Gabi Peixe
  - Biquinho
  - Bagualu
  - Alanzoka
  - Davy Jones (Gameplayrj)

- **Internacionais:**
  - xQc
  - JLTomy
  - Chatterbox
  - Lord_Kebun
  - Bác Gấu
  - RDjavi

## Regras Avançadas, Segurança e Transparência - Canal Viela Vice

1. **Velocidade:** Uso do modelo `--model base` do Whisper para transcrição rápida em notebooks.
2. **Proteção Contra Strike (Monetização):** Inclusão automática de créditos (`"Créditos: Live de [Nome do Streamer]"`) e variação rotativa de hashtags para evitar detecção de spam.
3. **Segurança da API & Limite de Estoque (Rate Limiting & Storage):**
   - **Gerenciamento via `painel.py`:** Limitar o envio a no máximo 6 vídeos por dia (5 Shorts + 1 Resumo Longo), espaçados por intervalos de 3 horas.
   - **Limite de Estoque (2x a Meta Diária = 12 vídeos):** Antes de buscar ou baixar qualquer nova live, o sistema (`robo_cortes.py` e `vigia_lives.py`) verifica a pasta `exportacao`. Se já houver 12 ou mais vídeos `.mp4` prontos aguardando revisão, a criação é pausada imediatamente para evitar acúmulo no disco, retomando apenas quando o estoque cair abaixo de 12.
4. **Descoberta Dinâmica & Limpeza:** Monitoramento de novos criadores (`streamers_descobertos.json`) e limpeza automática da pasta `video-bruto`.
5. **Transparência Total (Afiliados e Cupons):** O `painel.py` gerencia links de afiliado e cupons gamer, incluindo automaticamente o aviso de transparência no final da descrição: `"Transparência: Links de afiliado oficiais. Comprando por aqui você apoia o canal sem pagar nada a mais."`.
6. **Áudio e Narração sem Sobreposição:** Nos vídeos, nunca coloque narração do edge-tts falando por cima da voz do streamer. O contexto é narrado em um intro com o primeiro quadro congelado (zoom leve e fundo escuro), liberando depois o áudio 100% limpo do streamer (baixando apenas a faixa de áudio principal para evitar dublagens automáticas).
7. **CTA Final Obrigatório:** Nos últimos 4 segundos de todos os Shorts (66s a 70s), o áudio `exportacao/cta.mp3` (gerado via edge-tts `pt-BR-AntonioNeural` com rate `+15%` falando *"Se você curtiu o vídeo, já deixa o like e se inscreva no canal!"*) entra com o som do jogo reduzido a 10% e o banner vermelho na tela `"CURTA E SE INSCREVA NO VIELA VICE!"`. As legendas são ocultadas nesses últimos 4 segundos (limite de corte em 66s) para evitar sobreposição.
8. **Estética Híbrida Viela Vice & Qualidade Máxima sem Pressa:**
   - **Base Visual:** Vídeo central nítido com fundo blur escuro, título no topo (sempre uma frase curta e chamativa baseada no momento do vídeo, nunca genérica) e encerramento com `exportacao/cta.mp3`.
   - **Qualidade Máxima (FFmpeg & Whisper):** Transcrição de alta precisão usando Whisper `--model small` (em vez de base). Renderização via FFmpeg com alta qualidade visual (`-crf 18 -preset medium`) e áudio limpo de alta fidelidade (`-b:a 192k`).
   - **Resfriamento do Sistema:** Pausas curtas (`time.sleep(5)`) entre processos pesados para evitar sobrecarga ou travamento do notebook.
   - **Ritmo e Legendas:** Corte dinâmico de silêncios/pausas, legendas modernas centralizadas de **até 3 palavras** por vez (com destaque em amarelo e box preto, terminando obrigatoriamente antes de 66s).
   - **Censura Rigorosa:** Filtragem automática de profanidades no Python (como "porra", "caralho", "viado", "merda", "puta", etc.) substituídas por asteriscos.
9. **Política Rigorosa de Economia de Espaço (Notebook):**
   - **No Robô (`robo_cortes.py`):** Limpeza automática de todos os arquivos pesados em `video-bruto` e intermediários (`.srt`, `.txt`, `.json`, `.wav`, `.mp3`) pós-renderização, preservando apenas os vídeos finais em `exportacao` e `exportacao/cta.mp3`.
   - **No Painel (`painel.py`):** Assim que o vídeo é autorizado/agendado, o arquivo `.mp4` correspondente é apagado da pasta `exportacao` para liberar espaço, registrando título e link/status em `historico.txt`.

- **Ganchos de Título:** Priorizar frases curtas e impactantes nos primeiros 3 segundos baseadas em reviravoltas ou confrontos no GTA RP.

- **Horários de Pico:** Priorizar agendamentos nos horários de maior retenção (18:00 e 21:00).


## NOVA ESTRUTURA DE PRODUCAO E SETOR DE CURADORIA (24 VIDEOS)
- META DE ESTOQUE TOTAL: 24 videos prontos na fila (exatamente 4 videos longos/resumos e 20 Shorts).
- SETOR DE CONTROLE DE QUALIDADE & CURADORIA (LIDER DE REUNIOES):
  1. Audita automaticamente 100% dos videos gerados antes de chegarem ao Gerente (checando codec yuv420p, audio sem falhas, idioma pt-BR, censura e duracao). Videos com bugs sao apagados automaticamente.
  2. Ranqueia os videos aprovados na auditoria e entrega ao Gerente apenas o TOP 6 DO DIA (1 Longo + 5 Shorts com maior potencial de retencao).
  3. Lidera as reunioes periodicas da agencia, ditando melhorias de automacao e atualizando as diretrizes da equipe conforme o desempenho.
