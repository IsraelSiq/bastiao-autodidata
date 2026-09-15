# Troubleshooting

## Container nao inicia

```bash
docker compose --profile agent logs --tail=200 bastiao
docker compose --profile agent config
```

Confirme que `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO` e
`BASTIAO_WORKSPACE` estao definidos. No Compose, o ultimo e sobrescrito para
`/workspace/target`.
Confirme tambem que `state/approvals.json` existe e contem JSON valido quando
`BASTIAO_REQUIRE_APPROVAL=true`.

## Erro 401 do GitHub

O token esta ausente, expirado ou sem permissao no repositorio. Valide a
autenticacao fora dos logs e substitua o valor no `.env`. Nunca registre o
token para depurar.

## Erro de modelo ou timeout

```bash
docker compose up -d ollama
docker exec bastiao-ollama ollama list
curl http://127.0.0.1:11434/api/tags
```

Confira `BASTIAO_MODEL` e `OMNIROUTE_URL`. Dentro do container, `localhost`
nao aponta para o servico Ollama; use `http://ollama:11434/v1`.

## Workspace invalido

O workspace deve ser um clone Git com `origin` configurado e acesso a `main`.

```bash
git -C workspace status
git -C workspace remote -v
git -C workspace fetch origin main
```

Nao use o diretorio que contem o codigo do agente como workspace alvo.

## Nenhuma pull request foi aberta

Leia o resultado do ciclo:

- `no_open_issues`: nao havia issue aberta;
- `pending_approval`: a issue foi selecionada, mas nao foi aprovada;
- `failed`: o agente nao produziu patch testavel;
- `rejected_out_of_scope`: foram alterados arquivos fora do escopo;
- `rejected_by_reviewer`: o Reviewer rejeitou o conteudo ou a sintaxe;
- `rejected_unsafe_diff`: o patch violou o bloqueio de diff.

Revise o comentario publicado na issue e o log do container antes de repetir o
ciclo. Nao aumente `BASTIAO_MAX_ITERATIONS` como primeira resposta a um patch
destrutivo.

Para entender uma retomada, examine o checkpoint e as metricas:

```bash
cat state/tasks/issue-N.json
tail -n 20 state/metrics/cycles.jsonl
```

## Testes locais

```bash
python -m pytest tests -q
python -m compileall -q .
```

Se o repositorio alvo nao possui `tests`, o executor usa `compileall`. Isso
detecta erros de sintaxe, mas nao substitui testes de comportamento.
