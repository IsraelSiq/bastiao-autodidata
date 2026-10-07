# Operacao

## Estado operacional em 2026-10-07

A PR #49 foi mergeada na `main` (commit `94e107b`). A branch `fix/bounded-subprocess-output` passou em suite completa e testes de stress em container descartavel; a PR de correcao ainda requer revisao/merge. As issues #30 e #37 permanecem abertas. A implantacao existente nao foi reiniciada nem atualizada, e o checkout operacional com alteracoes locais foi preservado sem limpeza ou reset.

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

Comandos do modelo e o Quality Gate rodam com ambiente sem credenciais (`GITHUB_TOKEN`, `OMNIROUTE_API_KEY` e variaveis com `TOKEN/SECRET/PASSWORD/API_KEY` sao removidas). Cada tarefa usa um diretorio temporario proprio (`TMPDIR/TEMP/TMP`), removido ao fim da tarefa mesmo em falha. Em POSIX, `BASTIAO_MEMORY_LIMIT_MB` (`RLIMIT_AS`) e `BASTIAO_CPU_LIMIT_SECONDS` (`RLIMIT_CPU`) limitam cada comando; o padrao 0 desativa e os limites nao sao aplicados no Windows.

A issue #30 ainda nao esta concluida: o `docker-compose.yml` nao define `mem_limit`, `cpus` ou `pids_limit`, e nao ha quota de disco para temporarios/workspace. Validacao de limites em Docker nao autoriza alterar ou reiniciar o container existente. Defina os valores de producao somente depois de confirmar a capacidade do servidor e obter aprovacao do operador.

## Historico validado

O teste controlado da issue #43 terminou com a PR #46 contendo somente `src/health_marker.py` com `HEALTH_MARKER = "ok"`. As PRs #45, #46, #47, #48 e #49 foram mergeadas manualmente. A PR #49 trouxe os incrementos de observabilidade listados acima. A validacao atual usou apenas clone/imagem/container descartaveis e nao alterou o servico ativo. Consulte `ROADMAP.md` e `docs/SESSION-CHECKPOINT.md` para pendencias e evidencias.

## Chat do Open WebUI lendo o GitHub (somente leitura)

`openwebui/github_reader_tool.py` e uma Tool do Open WebUI que permite ao chat ler links, issues, PRs e arquivos (por exemplo, `ROADMAP.md`). Nao escreve no GitHub: criar branches/PRs continua dependendo de aprovacao humana.

Instalacao: Open WebUI > Workspace > Tools > `+` > colar o conteudo do arquivo > Salvar. Em Valves, ajuste `allowed_repos` e, para repositorios privados, informe um token fine-grained somente leitura (Contents, Issues, Pull requests: Read). No chat, ative a Tool e use um modelo com suporte a tool calling.
