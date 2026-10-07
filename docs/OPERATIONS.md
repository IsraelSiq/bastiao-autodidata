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

O primeiro incremento da issue #37 foi implementado: cada execucao de `run_once`
gera um UUID `cycle_id`, inclui-o no resumo retornado pelo runner e grava o mesmo
identificador junto com o resultado em `cycles.jsonl`. O resumo continua
incluindo os campos especificos do resultado, como `status`, `issue` e `files`.

O segundo incremento adicionou healthchecks somente leitura (`src/health.py`):

```bash
python -m src.health
docker compose --profile agent run --rm --no-deps bastiao python -m src.health
```

A saida e um JSON com GitHub, Ollama, workspace e ChromaDB (nome, resultado,
detalhe e duracao). O codigo de saida e 0 quando todos os checks obrigatorios
passam. ChromaDB e opcional, pois o fluxo atual nao o utiliza. O token nunca e
incluido na saida; cada sonda usa `BASTIAO_HEALTH_TIMEOUT_SECONDS` (padrao 5) e
`CHROMA_URL` (padrao `http://127.0.0.1:8000`). Executar o comando nao inicia o
ciclo do agente.

O terceiro incremento adicionou retry/backoff limitado e estado persistido.
Leituras idempotentes do GitHub (listar issues, verificar PR existente) sao
repetidas ate `BASTIAO_GITHUB_RETRY_ATTEMPTS` vezes (padrao 3) com backoff
exponencial a partir de `BASTIAO_GITHUB_RETRY_BASE_SECONDS` (padrao 1s, maximo
30s), somente para falhas de rede, timeout, 429 e 5xx; erros 4xx como 401/403/404
nao sao repetidos. Escritas (comentarios, commits, PR) nunca sao repetidas, para
evitar duplicatas. Cada ciclo grava `state/metrics/status.json` (escrita atomica)
com o ultimo resultado e, enquanto o GitHub estiver indisponivel,
`github_unavailable_since`, que e removido quando um ciclo volta a funcionar.

```bash
cat state/metrics/status.json
```

O quarto incremento adicionou redaction e retencao. `src/redaction.py` mascara
tokens GitHub (`ghp_`, `github_pat_`...), chaves `sk-`, cabecalhos
`Authorization`, pares `token/password/secret/api_key=` e os valores atuais de
`GITHUB_TOKEN` e `OMNIROUTE_API_KEY`. Isso e aplicado aos logs do processo
(`main.py`), a linha `Cycle complete` e aos registros de `cycles.jsonl` e
`status.json`. O mascaramento e por padroes: nao substitui evitar colocar
segredos em issues, prompts e logs. `cycles.jsonl` e rotacionado quando atinge
`BASTIAO_METRICS_MAX_BYTES` (padrao 5 MiB), mantendo `BASTIAO_METRICS_BACKUPS`
arquivos (`cycles.jsonl.1` e o mais recente; padrao 5; 0 descarta o antigo).

Pendentes: validacao em Docker/runtime real e revisao humana antes de operacao
continua.

Depois de cada incremento: executar testes, revisar a PR e atualizar
`ROADMAP.md`. Nao executar a etapa seguinte automaticamente.

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

BASTIAO_COMMAND_TIMEOUT_SECONDS encerra comandos demorados **e todos os processos filhos** (grupo de processos no POSIX, `taskkill /T` no Windows); BASTIAO_MAX_COMMANDS limita comandos; BASTIAO_MAX_OUTPUT_CHARS limita saida; BASTIAO_MAX_WRITE_BYTES limita arquivos. Comandos do modelo e o Quality Gate rodam com ambiente sem credenciais (`GITHUB_TOKEN`, `OMNIROUTE_API_KEY` e variaveis com TOKEN/SECRET/PASSWORD/API_KEY sao removidas). Cada tarefa usa um diretorio temporario proprio (`TMPDIR/TEMP/TMP`), removido ao fim da tarefa mesmo em falha. Em POSIX, `BASTIAO_MEMORY_LIMIT_MB` (RLIMIT_AS) e `BASTIAO_CPU_LIMIT_SECONDS` (RLIMIT_CPU) limitam cada comando; o padrao 0 desativa. Esses limites nao sao aplicados no Windows e ainda nao foram validados em Docker/runtime real; o limite de memoria do container (`mem_limit` no Compose) continua recomendado.

## Historico validado

O teste controlado da issue #43 terminou com a PR #46 contendo somente src/health_marker.py com HEALTH_MARKER = "ok". As PRs #45, #46, #47 e #48 foram revisadas e mergeadas manualmente. A PR #48 e o ultimo marco desta sessao. A proxima retomada e a issue #37, conforme ROADMAP.md.

## Chat do Open WebUI lendo o GitHub (somente leitura)

`openwebui/github_reader_tool.py` e uma Tool do Open WebUI que deixa o chat ler links, issues, PRs e arquivos (ex.: `ROADMAP.md`) dos repositorios permitidos. Nao escreve nada no GitHub: criar branches/PRs continua sendo papel do agente, com aprovacao humana.

Instalacao: Open WebUI > Workspace > Tools > `+` > colar o conteudo do arquivo > Salvar. Em Valves, ajuste `allowed_repos` e, se quiser repos privados, informe um token fine-grained somente leitura (Contents, Issues, Pull requests: Read). Depois, no chat, ative a Tool e use um modelo com suporte a tool calling (ex.: `qwen3:8b`).

Exemplos: "leia https://github.com/IsraelSiq/bastiao-autodidata/issues/37", "liste as issues abertas e proponha a proxima", "leia o ROADMAP.md".
