# Roadmap do Bastiao Autodidata

Este documento registra a ordem de evolucao recomendada, o estado validado do protocolo e o ponto exato de retomada.

## Estado validado na main

A main contem as PRs historicas ate a PR #48, incluindo aprovacao humana, Planner deterministico, workspace isolado, Executor restrito, Reviewer, estado persistente, retomada por checkpoint, Quality Gate, escopo estrito, limites de comandos/timeout/saida/tamanho de arquivo e publicacao sem merge automatico.

A PR #48 foi mergeada em 2026-09-15 pelo commit 6312fc4. Ela entregou os commits e336d1a, 568b7ea e 662bdb6.

## O que foi validado

O teste controlado da issue #43 foi concluido em workspace limpo. A PR #46 conteve exatamente:

```python
HEALTH_MARKER = "ok"
```

As PRs #45 e #46 foram revisadas e mergeadas manualmente. Na fase da PR #48, 38 testes passaram, alem de compileall e git diff --check.

## Ponto de parada atual

A sessao foi encerrada logo apos o merge da PR #48. Nenhuma implementacao da issue #37 foi iniciada. O container Bastiao deve permanecer parado ate nova issue ser escolhida e aprovada explicitamente.

CPU e memoria so possuem limite opcional em POSIX (nao no Windows) e ainda nao foram validados em Docker/runtime real; nao devem ser considerados concluidos.

## Proxima sequencia

### 1. Issue #34 — Quality Gate real — concluida

O gate em src/quality_gate.py executa checks aplicaveis, registra retorno, duracao, timeout e saida limitada, e bloqueia publicacao com quality_gate_failed.

### 2. Reforco de escopo e abortamento — concluido

strict_scope rejeita planos sem caminhos permitidos, bloqueia escritas fora do escopo e aborta imediatamente apos violacao.

### 3. Issue #30 — Limites do sandbox — parcialmente concluida

Entregue: timeout por comando (com encerramento de processos filhos), limite de comandos, limite de saida e limite de bytes por arquivo, diretorio temporario por tarefa com limpeza garantida, ambiente sem credenciais para comandos do modelo e Quality Gate, e limites opcionais de memoria/CPU em POSIX (`src/process.py`).

Pendente: validacao especifica do Docker/runtime (incluindo `mem_limit`/`cpus` no Compose e os rlimits em Linux).

### 4. Issue #37 — Observabilidade operacional — em andamento

Primeiro incremento concluido: cada ciclo recebe um UUID `cycle_id` retornado
pelo runner e persistido junto ao resultado em `cycles.jsonl`.

Segundo incremento concluido: `python -m src.health` verifica GitHub, Ollama,
workspace e ChromaDB (opcional) de forma somente leitura.

Terceiro incremento concluido: retry/backoff limitado para leituras do GitHub
(sem retry de escritas) e estado persistido em `status.json` com
`github_unavailable_since`.

Quarto incremento concluido: redaction de segredos (`src/redaction.py`) em logs,
saida do ciclo, `cycles.jsonl` e `status.json`; retencao por tamanho de
`cycles.jsonl` com backups limitados; testes de reinicio e de falha de
dependencias (recuperacao do estado, 401 sem retry).

Pendentes na #37: validacao em Docker/runtime real e revisao humana da PR antes
de qualquer operacao continua. Nao ampliar para 24/7 antes disso.

Nao ampliar para 24/7 antes desses itens.

### 5. Issue #36 — Providers e fallback

Criar interface comum, selecao por capacidade, timeout, erros e fallback limitado, sem loops ou custos ilimitados.

### 6. Issue #35 — Memoria persistente

Integrar Chroma com categorias e isolamento por projeto, com fallback explicito.

### 7. Issue #38 — Pipeline autodidata

Somente depois: pesquisa com fontes, evidencias, agenda, exercicios, avaliacao reproduzivel e revisao espacada.

## Bloqueios de seguranca

- nao executar em modo 24/7 sem supervisao;
- nao fazer merge automatico;
- nao instalar dependencias automaticamente;
- nao usar fallback ilimitado;
- nao integrar OpenHands;
- nao tratar complete como prova de sucesso;
- manter revisao humana antes do merge.

## Procedimento de retomada

1. verificar issues #30, #34, #35, #36, #37 e #38;
2. confirmar PR #48 na main;
3. confirmar container parado;
4. criar workspace limpo baseado na main;
5. aprovar apenas a issue em teste;
6. implementar um incremento da #37;
7. testar e revisar a PR manualmente;
8. atualizar este documento.

Estado persistente: BASTIAO_STATE_DIR, normalmente /var/lib/bastiao no container e ./state no host.
