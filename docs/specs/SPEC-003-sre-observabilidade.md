# SPEC-003: Observabilidade, resiliência e correção do editor

## Pedido

O console do painel estava parado, nenhum vídeo era produzido e era preciso descobrir se a causa era limite de requisições, cota da API ou o próprio editor.

## Causas encontradas

| # | Sintoma | Causa | Correção |
|---|---------|-------|----------|
| 1 | Nenhum Short era gerado | O caminho da legenda chegava mal escapado ao FFmpeg (`Unable to open`) | `filtro_legendas` em `src/pipeline/ffmpeg_runner.py` |
| 2 | FFmpeg encerrava com `0xC0000005` | `drawtext` sem arquivo de fonte e Fontconfig não configurado | `filtro_texto` com `fontfile` e `FONTCONFIG_FILE` |
| 3 | Console vazio | O painel nunca consultava `/api/ti_terminal` e o worker não gravava o log | Consulta contínua em `painel.js` e `log_terminal` persistente |
| 4 | Ciclo de mais de 30 minutos | O Whisper transcrevia a live inteira para aproveitar 3 cortes | Janela de 8 minutos por ciclo |
| 5 | Respostas inconsistentes | Dois servidores escutando a porta 8501 | Verificação de instância única no `main.py` |
| 6 | Arquivos em uso eram apagados | Ciclos simultâneos dividiam os mesmos temporários | `TravaCiclo` entre threads e processos |
| 7 | `.env` e tokens acessíveis pela rede | A raiz do projeto era publicada como pasta estática | `static_folder=None` e host padrão `127.0.0.1` |
| 8 | Exclusão de arquivos fora da exportação | `/api/negar` aceitava `../` no nome | Validação em `_resolver_video` |

Limite de requisições e cota da API não foram a causa: os registros mostram falhas apenas na etapa de renderização.

## Critérios de aceitação

1. Um Short completo é renderizado em caminho com espaço e acento, em 1080x1920 e `yuv420p`.
2. O console exibe cada etapa da produção em até 2,5 segundos.
3. O painel diferencia produzindo, ocioso, pausado, com erro, travado, robô desligado e offline.
4. Cada falha informa sua categoria: render, rate limit, bloqueio do YouTube, cota, rede, disco ou desconhecida.
5. Pedidos repetidos de produção e aprovação não duplicam trabalho nem envios ao YouTube.
6. Processo encerrado à força, trava órfã, JSON corrompido e disco cheio não impedem a recuperação.
7. Um vídeo com falha definitiva entra em quarentena após 3 tentativas. Falhas temporárias não contam.
8. Arquivos da raiz do projeto nunca são servidos por HTTP.

## Como testar

```powershell
python -m unittest discover -s tests
```
