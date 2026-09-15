# Operacao

## Monitoramento basico

```bash
docker compose --profile agent ps
docker compose --profile agent logs --tail=100 bastiao
docker inspect bastiao-autodidata --format '{{.RestartCount}}'
```

Verifique no GitHub:

- se a branch `bastiao/issue-N` foi criada;
- se a pull request corresponde a issue correta;
- se os checks da pull request passaram;
- se nao existe uma pull request duplicada para a mesma issue.

Para autorizar uma issue especifica:

```bash
printf '[43]\n' > state/approvals.json
docker compose --profile agent restart bastiao
```

Confirme no log um ciclo `pending_approval` antes da aprovacao e o inicio do
SWE-agent somente depois que o numero estiver no arquivo.

## Ciclo bem-sucedido

O log deve indicar a issue processada e o resultado
`pull_request_opened`. A issue recebe um comentario com o link da pull request.
O merge continua sendo responsabilidade de um revisor humano.

## Ciclo sem patch

Em `failed`, consulte os logs do modelo e verifique se:

- o endpoint de chat esta respondendo;
- o modelo esta instalado;
- o workspace contem um clone valido;
- a issue tem requisitos suficientemente claros;
- o agente nao atingiu `BASTIAO_MAX_ITERATIONS`.

Uma issue sem patch nao deve ser marcada como resolvida automaticamente.

Consulte o checkpoint correspondente e as metricas:

```bash
cat state/tasks/issue-43.json
tail -n 20 state/metrics/cycles.jsonl
```

## Patch rejeitado

Em `rejected_unsafe_diff`, nao reabra a pull request manualmente sem revisar o
diff. O bloqueio existe para impedir que o modelo substitua um arquivo inteiro
por uma implementacao curta ou destrua codigo existente.

Use no workspace:

```bash
git diff --stat origin/main
git diff --check origin/main
git diff origin/main
```

## Controle de seguranca

Antes de fazer merge:

1. confirme que a pull request veio da branch esperada;
2. revise todos os arquivos alterados;
3. confirme que os testes realmente cobrem a issue;
4. procure mudancas em configuracao, dependencias e scripts;
5. verifique os checks do GitHub;
6. somente entao faca o merge manualmente.

## Parada de emergencia

```bash
docker compose --profile agent stop bastiao
```

Remova o token do ambiente apenas depois de parar o processo. Para impedir novos
commits, revogue o token no GitHub e substitua-o por um token de menor escopo.

## Quality Gate

Antes de revisar ou publicar uma PR, o agente executa os checks descobertos no
workspace:

- `pytest tests -q`, quando existe `tests/`;
- `python -m compileall -q .`, quando existem arquivos Python;
- `npm run lint` e `npm run typecheck`, somente quando definidos em
  `package.json`;
- `git diff --check origin/main`.

Cada check possui timeout, codigo de retorno, duracao e saida limitada. Se um
check falhar ou exceder o timeout, o ciclo termina como
`quality_gate_failed`, grava a evidencia nas metricas e nao cria commit nem PR.
O timeout pode ser ajustado por `BASTIAO_QUALITY_GATE_TIMEOUT_SECONDS`.

## Escopo estrito

No modo operacional, o runner usa `strict_scope`. Um plano sem caminhos
permitidos e rejeitado antes de chamar o modelo (`rejected_no_scope`). Se o
modelo tentar escrever fora do escopo, a escrita e bloqueada e o SWE-agent
aborta imediatamente a tarefa. Nenhuma recuperacao automatica ou publicacao
ocorre depois dessa violacao.

## Registro da ultima fase validada

O teste controlado da issue #43 foi executado em um workspace limpo baseado no
`main`. A primeira tentativa revelou que o Planner nao reconhecia caminhos em
texto simples e permitia `allowed_paths` vazio. Essa falha foi corrigida e
testada com 28 testes locais.

Na segunda execucao, o Planner identificou
`allowed_paths=["src/health_marker.py"]`. O modelo tentou acessar arquivos
inexistentes, mas essas tentativas nao entraram na PR. O ciclo terminou como
`pull_request_opened`, com a PR #46 contendo somente:

```python
HEALTH_MARKER = "ok"
```

As PRs #45 e #46 foram revisadas e mergeadas manualmente. O container deve
permanecer parado ate a proxima issue ser selecionada explicitamente. A
proxima implementacao recomendada e a issue #34, seguida do reforco de escopo,
#30 e #37, conforme [`ROADMAP.md`](../ROADMAP.md).
