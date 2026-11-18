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

1. Ordem de prioridade: lives de GTA 6 no ar, vídeos de GTA 6 dos últimos 7 dias, GTA RP como reserva.
2. Títulos fora do tema são ignorados: contagem regressiva, GTA 5 e transmissões em outro idioma.
3. Live no ar é gravada por 21 minutos, sem esperar o fim da transmissão.
4. Áudio que não esteja em português é descartado antes do render.

### Produção e estoque

1. Cada ciclo produz até 4 Shorts e 2 vídeos longos.
2. A fila guarda no máximo 60 vídeos: 40 Shorts e 20 longos.
3. Vídeos longos são horizontais, em 1280x720, com cerca de 10 minutos, abertura narrada e chamada final.
4. Lives de GTA 6 dos canais cadastrados na Twitch têm prioridade sobre a busca no YouTube.
5. Falas fora do português não entram em legendas, títulos nem cortes.

### Estrelas

1. Cada canal mostra de 0 a 6 estrelas conforme os envios do ciclo atual.
2. O ciclo da cota reinicia às 05:00.
3. Só contam os vídeos realmente enviados ao YouTube.
4. O painel do gerente mostra as estrelas do canal escolhido e bloqueia o envio em 6/6.
5. O servidor também recusa envios acima da cota.
6. O botão de estrelas e o contador "Envios de Hoje" refletem os números reais.
7. A estrela é gasta no momento do envio, mesmo que a publicação esteja agendada para outro dia.
8. Um vídeo agendado não volta a contar quando é publicado em um ciclo posterior.
9. Sem confirmação da cota no YouTube, o envio é cancelado.
10. Cada canal tem a própria grade de horários, sempre com horários futuros.

### Escritório virtual

1. O cenário é desenhado em código (`escritorio.js`), com tema neon de pôr do sol, e cada móvel ocupa espaço real no piso.
2. Os personagens desviam dos móveis e uns dos outros, tomam café, usam o celular, conversam e dançam.
3. O Gordão, de terno VIP verde, vive na Green Room: descansa no sofá, joga sinuca, pega bebida no freezer, vai ao bar, toca nas pickups, joga arcade e pebolim e dança.
4. A Green Room tem barman, bar, freezer de bebidas, mesa de sinuca, pickups, arcades e pebolim.
5. Cada personagem tem aparência própria, com proporção humana e iluminação realista.
6. O botão de varredura funciona como play/pause e mostra a bolinha verde quando a produção está ao vivo.

## Como testar

```powershell
python -m unittest discover -s tests
```
