# Operacao

## Estado operacional atual

A PR #48 foi mergeada na main em 2026-09-15 pelo commit 6312fc4. Ela entregou Quality Gate, escopo estrito e limites portaveis do sandbox. A sessao foi encerrada imediatamente depois do merge. A issue #37 ainda nao foi iniciada.

O container Bastiao deve permanecer parado ate uma nova issue ser selecionada e aprovada explicitamente.

## Monitoramento basico

```bash
docker compose --profile agent ps
docker compose --profile agent logs --tail=100 bastiao
docker inspect bastiao-autodidata --format '{{.RestartCount}}'
```

Verifique no GitHub se a branch corresponde a issue, se os checks passaram e se nao existe PR duplicada.

Para autorizar uma issue especifica:

```bash
printf '[43]\n' > state/approvals.json
docker compose --profile agent restart bastiao
```

Substitua 43 pelo numero explicitamente selecionado. Confirme no log um ciclo pending_approval antes da aprovacao e o inicio do SWE-agent somente depois do numero estar no arquivo.

## Proxima retomada segura

A proxima etapa e a issue #37, dividida em incrementos pequenos: identificador/resumo por ciclo; healthchecks de GitHub, Ollama, workspace e ChromaDB; retry/backoff limitado e estado github_unavailable; retencao/redaction; testes de reinicio e falha de dependencias.

Depois de cada incremento: executar testes, revisar a PR e atualizar ROADMAP.md. Nao executar a etapa seguinte automaticamente.

## Ciclo bem-sucedido

O log deve indicar a issue e o resultado pull_request_opened. A issue recebe comentario com o link da PR. O merge continua responsabilidade de revisor humano.

## Ciclo sem patch

Em failed, verifique endpoint de chat, modelo instalado, clone valido, requisitos claros e BASTIAO_MAX_ITERATIONS. Uma issue sem patch nao deve ser marcada como resolvida automaticamente.

```bash
cat state/tasks/issue-43.json
tail -n 20 state/metrics/cycles.jsonl
```

## Controle de seguranca antes do merge

1. confirme a branch esperada;
2. revise todos os arquivos;
3. confirme que os testes cobrem a issue;
4. procure mudancas em configuracao, dependencias e scripts;
5. verifique os checks;
6. faca o merge manualmente somente depois disso.

## Parada de emergencia

```bash
docker compose --profile agent stop bastiao
```

## Quality Gate

O agente executa pytest, compileall, lint/typecheck quando definidos e git diff --check. Cada check possui timeout, retorno, duracao e saida limitada. Falhas ou timeout terminam o ciclo como quality_gate_failed e bloqueiam commit/PR. Ajuste com BASTIAO_QUALITY_GATE_TIMEOUT_SECONDS.

## Escopo estrito

strict_scope rejeita planos sem caminhos permitidos (rejected_no_scope), bloqueia escritas fora do escopo e aborta imediatamente apos violacao. Nao ha recuperacao automatica ou publicacao depois disso.

## Limites do sandbox

BASTIAO_COMMAND_TIMEOUT_SECONDS encerra comandos demorados; BASTIAO_MAX_COMMANDS limita comandos; BASTIAO_MAX_OUTPUT_CHARS limita saida; BASTIAO_MAX_WRITE_BYTES limita arquivos. CPU, memoria, processos filhos e temporarios ainda nao possuem limite portavel e permanecem pendentes para Docker/runtime.

## Historico validado

O teste controlado da issue #43 terminou com a PR #46 contendo somente src/health_marker.py com HEALTH_MARKER = "ok". As PRs #45, #46, #47 e #48 foram revisadas e mergeadas manualmente. A PR #48 e o ultimo marco desta sessao. A proxima retomada e a issue #37, conforme ROADMAP.md.
