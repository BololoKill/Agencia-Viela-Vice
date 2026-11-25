# SPEC-004: Padrão de edição, busca de GTA 6 e estrelas por canal

## Pedido

Os Shorts saíam sem marca visível e sem a narração final, a edição estava abaixo dos grandes canais, as estrelas sumiram do painel do gerente e a busca precisava priorizar lives e vídeos novos de GTA 6.

## Diagnóstico do Short analisado

| Problema | Evidência |
|----------|-----------|
| Narração final inaudível | O `cta.mp3` tem a fala, mas a transcrição dos últimos 8 segundos veio vazia |
| Marca quase invisível | Apenas `@VielaVice` pequeno, encostado nas legendas |
| Tela preta no meio do vídeo | 2,7 s detectados entre 29,0 s e 31,7 s |
| Legenda cobrindo a imagem | Frases inteiras em até 3 linhas |
| Intro baixa | Volume médio de -30 dB, contra -22 dB no restante |
| Gameplay cortado | Vídeo 16:9 recortado direto para 9:16 |
| Momentos sem critério | Sempre os primeiros trechos da janela analisada |

## Requisitos

### Edição

1. Layout 1080x1920 com fundo desfocado escuro e gameplay nítido em 4:3 no centro.
2. Título-gancho no topo, baseado na fala do próprio corte.
3. Legendas de até 3 palavras, com a palavra falada em destaque amarelo sobre box preto.
4. Legendas encerradas antes da chamada final.
5. Logo da Viela Vice e `@VielaVice` visíveis do início ao fim.
6. Pausas longas e telas pretas removidas do corte.
7. Aproximação alternada nos cortes secos para dar ritmo.
8. Narração final audível, com o som do jogo reduzido a 10%.
9. Áudio padronizado em -14 LUFS, com narração e jogo no mesmo nível.
10. Render final em `-crf 18 -preset medium` e transcrição com Whisper `small`.
11. Cortes escolhidos pela intensidade da fala, sem sobreposição.
12. Imagem, som e legendas usam os mesmos cortes, alinhados em quadros inteiros.
13. Abertura com o jogo em movimento e o título na tela desde o primeiro quadro.
14. Vídeo com som e imagem fora de sincronia é recusado antes de entrar na fila.

### Busca

1. Matéria-prima: os vídeos de GTA 6 em português mais vistos da semana; com a semana aproveitada, os do mês. Lives não são mais gravadas.
2. Títulos fora do tema são ignorados: contagem regressiva, GTA 5 e transmissões em outro idioma.
   Se o começo do vídeo mostrar outro jogo, o meio é conferido antes de descartá-lo: live às vezes começa
   com outro jogo enquanto o GTA 6 não abre. A IA de imagem confunde GTA V com GTA 6 (mesma interface):
   um veredito de GTA V não descarta o vídeo, e a palavra final é da Diretoria.
3. De cada vídeo viral são baixados só 6 minutos; um criador entra no máximo uma vez por ciclo.
   A imagem e o som descem separados. Se o YouTube derruba a conexão, o download continua de onde parou,
   e a parte que chega cortada é baixada de novo sozinha. Se o FFmpeg cair no meio, a parte é baixada de novo uma vez.
4. Áudio que não esteja em português é descartado antes do render.
5. Um trecho conferido sem fala do criador em português fica guardado por 30 dias (`trechos_sem_fala.json`) e não é
   baixado de novo: o próximo ciclo vai direto para o outro trecho do vídeo.
6. Os downloads e os arquivos temporários ficam no SSD (`D:/VielaVice/video-bruto`), que é mais rápido e poupa o HD do
   Windows; sem o SSD, ficam na pasta do projeto. Os vídeos prontos continuam em `exportacao`.
7. Bloqueio anti-robô do YouTube pausa a busca e os downloads por 2 horas, sem login e sem tentar driblar o bloqueio.
   A pausa fica guardada (`pausa_youtube.json`) e continua valendo depois de um reinício; o painel mostra até que horas.
8. Vídeo com restrição de idade ou só para membros do canal não é bloqueio: sai da busca na hora, sem pausar o YouTube.

### Produção e estoque

1. Cada ciclo produz até 4 Shorts (um por vídeo viral) e 1 vídeo longo Top 5 da semana, com um trecho de cada vídeo.
   Só entra no ciclo o vídeo com um momento seguido de fala para Short ou para o Top; fala espalhada em pedaços
   curtos não conta. O vídeo que não rende Short passa a vaga para o próximo.
2. A fila guarda no máximo 9 vídeos, 3 dias de publicação do canal: 6 Shorts e 3 longos.
3. Vídeos longos são horizontais, em 1280x720, com 8min30, abertura narrada e chamada final.
4. Toda descrição traz o crédito e o link do vídeo original, e o longo mostra o nome de cada criador na tela.
5. Falas fora do português não entram em legendas, títulos nem cortes.

### Estrelas

1. Padrão dark num canal só: ele recebe 1 vídeo longo e 2 Shorts por ciclo e mostra de 0 a 3 estrelas conforme os envios.
   O longo é publicado às 17:00 e os Shorts às 12:00 e às 19:00; o 2º longo ou o 3º Short do dia no mesmo canal é recusado.
2. O ciclo da cota reinicia às 05:00.
3. Só contam os vídeos realmente enviados ao YouTube.
4. O painel do gerente mostra as estrelas do canal escolhido e bloqueia o envio quando o tipo do vídeo já completou o dia.
5. O servidor também recusa envios acima da cota.
6. O botão de estrelas e o contador "Envios de Hoje" refletem os números reais.
7. A estrela é gasta no momento do envio, mesmo que a publicação esteja agendada para outro dia.
8. Um vídeo agendado não volta a contar quando é publicado em um ciclo posterior.
9. Sem confirmação da cota no YouTube, o envio é cancelado.
10. Cada canal tem a própria grade de horários por tipo de vídeo, sempre com horários futuros.
11. Vídeo sem narração própria (formato antigo) não é produzido nem aprovado.

### Escritório virtual

1. O cenário é desenhado em código (`escritorio.js`), com tema neon de pôr do sol, e cada móvel ocupa espaço real no piso.
2. No escritório só ficam as 8 pessoas da equipe, e cada uma cobre uma etapa real da produção: Bruno (busca dos virais),
   Caio (download e computador), Camila (curadoria e auditoria), Thiago (roteiro e narração), Lucas (Shorts),
   Mariana (Top 5 da semana), Dr. Ricardo (Diretoria, a aprovação do dono) e Beatriz (publicação e horários).
   Os figurantes de volume saíram.
3. Quando uma etapa começa, quem cuida dela fala no escritório e aparece em "Produção agora". Clicar numa pessoa mostra
   a função dela; o botão "Equipe e funções" explica como um vídeo nasce e o que faz cada botão do painel.
4. Os personagens desviam dos móveis e uns dos outros, tomam café, usam o celular e conversam.
5. O Gordão, de terno VIP verde, é o mascote da Green Room e não tem etapa na produção: descansa no sofá, joga sinuca,
   pega bebida no freezer, vai ao bar, toca nas pickups, joga arcade e pebolim e dança.
6. A Green Room tem bar, freezer de bebidas, mesa de sinuca, pickups, arcades e pebolim.
7. Cada personagem tem aparência própria, com proporção humana e iluminação realista.
8. O botão de produção funciona como play/pause e mostra a bolinha verde com "PRODUZINDO" quando a produção está ligada.
9. O topo do painel mostra os vídeos na Diretoria, a publicação de hoje e os números reais do canal no YouTube,
   consultados em segundo plano no máximo uma vez por hora.

## Como testar

```powershell
python -m unittest discover -s tests
```
