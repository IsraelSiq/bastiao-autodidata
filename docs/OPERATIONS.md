# Operacao

## Estado operacional em 2026-10-07

As PRs #49 e #50 foram mergeadas na `main`; a #50 limitou a captura de saida dos subprocessos. A branch `fix/issue-30-compose-limits` implementa limites operacionais e passou na suite Docker Linux descartavel (84 testes) e na validacao de configuracao Compose. As issues #30 e #37 permanecem abertas. A implantacao existente nao foi reiniciada nem atualizada, e o checkout operacional com alteracoes locais foi preservado sem limpeza ou reset.

O gate de acoes e o modo autonomo por issue estao em desenvolvimento na branch
`feat/issue-29-human-approval` e ainda nao estao disponiveis no container ativo.
Nao reconstrua nem reinicie o servico ativo para esta validacao; implantar exige
revisao e aprovacao operacional separadas.

Antes de qualquer operacao, confirme o estado real com `docker compose --profile agent ps` e inspecione aprovacoes/checkpoints existentes. Nao reutilize uma aprovacao antiga: selecione a issue com o operador e substitua o arquivo de aprovacao somente depois de confirmacao explicita.

## Monitoramento basico

```bash
docker compose --profile agent ps
docker compose --profile agent logs --tail=100 bastiao
docker inspect bastiao-autodidata --format '{{.RestartCount}}'
```

Verifique no GitHub se a branch corresponde a issue, se os checks passaram e se nao existe PR duplicada.

Para autorizar uma issue especifica, substitua `NUMERO_APROVADO` somente depois de aprovacao explicita:

```bash
ISSUE_NUMBER=NUMERO_APROVADO
printf '[%s]\n' "$ISSUE_NUMBER" > state/approvals.json
```

Com `BASTIAO_REQUIRE_APPROVAL=true`, confirme no log um ciclo `pending_approval` antes da aprovacao e o inicio do SWE-agent somente depois do numero estar no arquivo. Nao reinicie o container durante uma validacao que deva ser somente leitura.

## Aprovacoes de acoes sensiveis

A aprovacao inicial por issue autoriza o ciclo delimitado: leitura/escrita nos
caminhos do Planner, testes e validacao, commits locais em `bastiao/issue-N` e
publicacao apos os gates. `BASTIAO_REQUIRE_ACTION_APPROVAL=true` habilita
aprovacoes adicionais para acoes sensiveis e publicacao. No modo padrao, ainda
exigem aprovacao especifica instalacao de dependencias, comandos JavaScript/Node
arbitrarios e inspecao Docker. Scripts de teste/qualidade allowlisted podem
rodar sem confirmacao por etapa. Remova uma issue de `state/approvals.json`
para revogar sua autorizacao persistente e interromper retries.

Revise a acao, o destino, o numero da issue e a validade antes de decidir:

```bash
docker compose --profile agent exec bastiao python -m src.action_approval list
docker compose --profile agent exec bastiao python -m src.action_approval approve REQUEST_ID --approver "Seu nome"
docker compose --profile agent exec bastiao python -m src.action_approval deny REQUEST_ID
```

A aprovacao expira em uma hora por padrao e so pode ser consumida uma vez. A
solicitacao pendente expira em 24 horas; os TTLs sao configuraveis por
`BASTIAO_ACTION_APPROVAL_TTL_SECONDS` e
`BASTIAO_APPROVAL_REQUEST_TTL_SECONDS`. A decisao nao executa o comando: deixe
que um ciclo posterior retome a tarefa. Consulte
`state/action-approval-audit.jsonl` para auditoria; nao edite manualmente o
arquivo de solicitacoes para converter uma negacao em aprovacao.

Podman, operacoes Docker mutaveis, comandos de sistema, push/merge/troca de
branch, caminhos fora do workspace, arquivos de credenciais e execucao Python
arbitraria sao bloqueados. `git add`/`git commit -m` so podem operar na branch
dedicada e nos caminhos do Planner. Inspecoes Docker somente leitura exigem
aprovacao. Durante o piloto, revise os diffs e evidencias de teste antes de
permitir processamento continuo.

## Observabilidade e diagnostico

O runner gera um UUID `cycle_id`, inclui-o no resumo e grava o mesmo identificador em `cycles.jsonl`. O resumo mantem os campos especificos do resultado, como `status`, `issue` e `files`.

Healthchecks somente leitura:

```bash
python -m src.health
docker compose --profile agent run --rm --no-deps bastiao python -m src.health
```

A saida e um JSON com GitHub, Ollama, workspace e ChromaDB (nome, resultado, detalhe e duracao). O codigo de saida e 0 quando os checks obrigatorios passam. ChromaDB e opcional. O token nao aparece na saida; cada sonda usa `BASTIAO_HEALTH_TIMEOUT_SECONDS` (padrao 5) e `CHROMA_URL` (padrao `http://127.0.0.1:8000`). Executar o comando nao inicia o ciclo do agente.

Leituras idempotentes do GitHub (listar issues, verificar PR existente) sao repetidas ate `BASTIAO_GITHUB_RETRY_ATTEMPTS` vezes (padrao 3) com backoff exponencial via `BASTIAO_GITHUB_RETRY_BASE_SECONDS` (padrao 1s, maximo 30s), somente para falhas de rede, timeout, 429 e 5xx; erros 4xx como 401/403/404 nao sao repetidos. Escritas nunca sao repetidas. Cada ciclo grava `state/metrics/status.json` (escrita atomica) com o ultimo resultado e `github_unavailable_since` durante indisponibilidade.

```bash
cat state/metrics/status.json
```

Logs, resumos de ciclo, `cycles.jsonl` e `status.json` usam redaction. `cycles.jsonl` e rotacionado ao atingir `BASTIAO_METRICS_MAX_BYTES` (padrao 5 MiB), mantendo `BASTIAO_METRICS_BACKUPS` arquivos (padrao 5; 0 descarta o antigo).

## Ciclo bem-sucedido

O log deve indicar a issue e o resultado `pull_request_opened`. A issue recebe comentario com o link da PR. O merge continua responsabilidade de revisor humano.

## Ciclo sem patch

Em `failed`, verifique endpoint de chat, modelo instalado, clone valido, requisitos claros e `BASTIAO_MAX_ITERATIONS`. Uma issue sem patch nao deve ser marcada como resolvida automaticamente.

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

O agente executa pytest, compileall, lint/typecheck quando definidos e `git diff --check`. Cada check possui timeout, retorno, duracao e saida limitada; falhas ou timeout terminam o ciclo como `quality_gate_failed` e bloqueiam commit/PR. `BASTIAO_QUALITY_GATE_TIMEOUT_SECONDS` controla o timeout. A captura de stdout e stderr agora e limitada por stream; quando truncada, o resultado registra essa condicao.

## Escopo estrito

`strict_scope` rejeita planos sem caminhos permitidos (`rejected_no_scope`), bloqueia escritas fora do escopo e aborta imediatamente apos violacao. Nao ha recuperacao automatica ou publicacao depois disso.

## Limites do sandbox

`BASTIAO_COMMAND_TIMEOUT_SECONDS` encerra comandos demorados e processos filhos (grupo de processos no POSIX, `taskkill /T` no Windows); `BASTIAO_MAX_COMMANDS` limita comandos; `BASTIAO_MAX_OUTPUT_CHARS` limita caracteres devolvidos; `BASTIAO_MAX_WRITE_BYTES` limita arquivos escritos. A captura de cada stream de comando usa um teto em bytes antes de acumular em memoria e drena o restante ate o processo terminar, evitando bloqueio de pipe. A busca de codigo usa o mesmo executor limitado e ambiente sem credenciais. O Quality Gate limita cada stream a 1.000.000 bytes. A branch de correcao foi testada em Linux/Docker com 512 MiB/1 CPU; uma reproducao de 32 MiB em stdout reteve 1.000.000 bytes e registrou truncamento. Suite completa Docker: 80 testes passaram; Pydantic foi instalado somente no container temporario para coleta dos testes.

Comandos do modelo e o Quality Gate rodam com ambiente sem credenciais (`GITHUB_TOKEN`, `OMNIROUTE_API_KEY` e variaveis com `TOKEN/SECRET/PASSWORD/API_KEY` sao removidas). Cada tarefa usa um diretorio temporario proprio (`TMPDIR/TEMP/TMP`), removido ao fim da tarefa mesmo em falha. Em POSIX, `BASTIAO_MEMORY_LIMIT_MB` (`RLIMIT_AS`, padrao 2048 MiB) e `BASTIAO_CPU_LIMIT_SECONDS` (`RLIMIT_CPU`, padrao 45 s) limitam cada subprocesso do sandbox e do Quality Gate; `0` desativa e os limites nao sao aplicados no Windows. Ao atingir o limite de memoria ou `SIGXCPU`, a ferramenta informa qual limite foi atingido.

O Compose propoe, para o container Bastiao, `mem_limit=4g`, `cpus=2.0`, `pids_limit=256` e `/tmp` tmpfs de 512 MiB (`noexec,nosuid`). Sao limites do container inteiro, nao por issue. O tmpfs controla temporarios sob `/tmp`; `BASTIAO_MAX_WRITE_BYTES` controla cada arquivo criado pela ferramenta `write`. O volume bind-mounted `workspace/` continua sem quota total e comandos podem escrever nele diretamente; monitoramento/quotas do filesystem do host ainda precisam de uma politica operacional.

Em instalacoes existentes, revise `.env`: valores antigos `BASTIAO_MEMORY_LIMIT_MB=0` ou `BASTIAO_CPU_LIMIT_SECONDS=0` mantem os rlimits desativados mesmo com estes defaults no Compose. `docker compose config --quiet` deve passar antes de aplicar a configuracao. A validacao Linux ocorreu em `/tmp/bastiao-issue30-validation-20261007-1715`, com imagem e container descartaveis. Foram medidos 4 GiB de memoria, 2 CPUs, 256 PIDs e tmpfs de 512 MiB. A branch nao foi implantada: validar a configuracao em clone/container descartavel nao autoriza alterar, reconstruir ou reiniciar o servico ativo. Uma aplicacao futura exige aprovacao operacional e janela de manutencao, alem de atualizar o `.env` existente.

## Historico validado

O teste controlado da issue #43 terminou com a PR #46 contendo somente `src/health_marker.py` com `HEALTH_MARKER = "ok"`. As PRs #45, #46, #47, #48, #49 e #50 foram mergeadas manualmente. A PR #49 trouxe observabilidade e a #50 limitou a captura de saida. A validacao atual usou apenas clone/imagem/container descartaveis e nao alterou o servico ativo. Consulte `ROADMAP.md` e `docs/SESSION-CHECKPOINT.md` para pendencias e evidencias.

## Chat do Open WebUI lendo o GitHub (somente leitura)

`openwebui/github_reader_tool.py` e uma Tool do Open WebUI que permite ao chat ler links, issues, PRs e arquivos (por exemplo, `ROADMAP.md`). Nao escreve no GitHub: criar branches/PRs continua dependendo de aprovacao humana.

Instalacao: Open WebUI > Workspace > Tools > `+` > colar o conteudo do arquivo > Salvar. Em Valves, ajuste `allowed_repos` e, para repositorios privados, informe um token fine-grained somente leitura (Contents, Issues, Pull requests: Read). No chat, ative a Tool e use um modelo com suporte a tool calling.
