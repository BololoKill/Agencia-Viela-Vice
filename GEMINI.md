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

1. **Transcrição:** Whisper `small`, só nos 6 minutos baixados de cada vídeo viral.
2. **Proteção Contra Strike (Monetização):** Inclusão automática de créditos (`"Créditos: vídeo de [criador] — [link do vídeo original]"`) e variação rotativa de hashtags para evitar detecção de spam.
3. **Segurança da API & Limite de Estoque (Rate Limiting & Storage):**
   - **Padrão dark de publicação:** a agência publica num canal só (o principal). Por ciclo (que reinicia às 05:00) ele recebe 1 vídeo longo publicado às 17:00 e 2 Shorts publicados às 12:00 e às 19:00. A Diretoria bloqueia o 2º longo e o 3º Short do dia.
   - **Matéria-prima:** não se gravam mais lives. A busca pega os vídeos de GTA 6 em português mais vistos da semana (um por criador, com pelo menos 8 min) e baixa só 6 min de cada. Cada vídeo rende no máximo 1 Short e 1 trecho do Top 5 da semana, com crédito e link na descrição e o nome do criador na tela. Volume alto de vídeos parecidos é tratado pelo YouTube como conteúdo produzido em massa e pode tirar a monetização do canal inteiro.
   - **Download do trecho:** a imagem e o som descem separados e são juntados sem recodificar. Se o YouTube derruba a conexão, o FFmpeg continua de onde parou; a parte que chega cortada é baixada de novo sozinha (o som leva segundos, a imagem leva minutos). Um trecho já conferido sem fala do criador em português fica guardado por 30 dias e não é baixado de novo. Os downloads e os arquivos temporários ficam no SSD (`D:/VielaVice`), poupando o HD do Windows.
   - **Limite de Estoque (3 dias de publicação = 9 vídeos):** Antes de buscar ou baixar qualquer vídeo viral, o robô (`src/pipeline/worker.py`) verifica a pasta `exportacao`. Com 6 Shorts e 3 longos prontos esperando a Diretoria, a produção pausa e só volta quando o estoque baixar.
4. **Descoberta Dinâmica & Limpeza:** Monitoramento de novos criadores (`streamers_descobertos.json`) e limpeza automática da pasta `video-bruto`.
5. **Transparência Total (Afiliados e Cupons):** O `painel.py` gerencia links de afiliado e cupons gamer, incluindo automaticamente o aviso de transparência no final da descrição: `"Transparência: Links de afiliado oficiais. Comprando por aqui você apoia o canal sem pagar nada a mais."`.
6. **Canal dark com narração própria:** cada vídeo ganha roteiro escrito pela IA a partir da transcrição (título, gancho e narração). No Short, a narração do roteiro abre o vídeo sobre o jogo; o longo é o Top 5 da semana, em contagem regressiva, com abertura narrada e o narrador apresentando cada trecho (som do jogo abaixado para 18%, fala do narrador e nome do criador escritos na tela). Não existe mais o formato antigo: sem roteiro válido o vídeo não é feito, e com a IA fora do ar a produção espera ela voltar, sem baixar nada. A Diretoria recusa vídeo sem narração própria.
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


## Equipe da agência: cada pessoa do escritório é uma etapa da produção

No escritório só ficam as 8 pessoas da equipe; os figurantes de volume saíram. Quando uma etapa começa, quem cuida dela fala no escritório e aparece em "Produção agora". O botão "Equipe e funções" do painel explica tudo ao dono.

1. **Bruno (Olheiro de Virais):** busca os vídeos de GTA 6 em português mais vistos da semana, com pelo menos 100 mil visualizações e um por criador.
2. **Caio (T.I. e Downloads):** baixa só 6 minutos de cada vídeo viral e cuida do disco e do Suporte T.I.
3. **Camila (Curadoria e Auditoria):** confere com a IA de imagem se é mesmo GTA 6 e audita cada vídeo pronto (imagem, som e sincronia) antes da Diretoria. Vídeo com defeito é apagado.
4. **Thiago (Roteirista e Narrador):** transcreve a fala do criador e escreve com a IA o título, o gancho e a narração. Sem narração própria nenhum vídeo é feito.
5. **Lucas (Editor de Shorts):** monta um Short de 45 a 60 segundos por vídeo viral.
6. **Mariana (Editora do Top 5):** monta o vídeo longo "Top 5 da semana", de 8min30, em contagem regressiva e com o nome de cada criador na tela.
7. **Dr. Ricardo (Diretoria):** é a aprovação do dono. Nada vai ao YouTube sem ela, e o que for rejeitado é apagado.
8. **Beatriz (Publicação e Horários):** agenda o que foi aprovado: 1 longo às 17:00 e 2 Shorts, às 12:00 e às 19:00.

O Gordão é o mascote da Green Room e não tem etapa na produção.
