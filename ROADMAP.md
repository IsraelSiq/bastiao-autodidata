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

CPU, memoria, processos filhos e temporarios ainda nao estao limitados de forma portavel e nao devem ser considerados concluidos.

## Proxima sequencia

### 1. Issue #34 — Quality Gate real — concluida

O gate em src/quality_gate.py executa checks aplicaveis, registra retorno, duracao, timeout e saida limitada, e bloqueia publicacao com quality_gate_failed.

### 2. Reforco de escopo e abortamento — concluido

strict_scope rejeita planos sem caminhos permitidos, bloqueia escritas fora do escopo e aborta imediatamente apos violacao.

### 3. Issue #30 — Limites do sandbox — parcialmente concluida

Entregue: timeout por comando, limite de comandos, limite de saida e limite de bytes por arquivo.

Pendente: CPU, memoria, processos filhos, arquivos temporarios/limpeza e validacao especifica do Docker/runtime.

### 4. Issue #37 — Observabilidade operacional — proxima etapa

Implementar em incrementos: identificador/resumo por ciclo; healthchecks de GitHub, Ollama, workspace e ChromaDB; retry/backoff limitado; estado github_unavailable persistido; retencao/redaction de logs; testes de reinicio e falha de dependencias.

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
