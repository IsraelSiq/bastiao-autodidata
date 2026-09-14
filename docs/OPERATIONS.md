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
