# Arquitetura

## Componentes

### `main.py`

Valida as variaveis obrigatorias, cria `AutonomousRunner` e executa ciclos
periodicos. O processo permanece ativo mesmo quando um ciclo nao encontra issues.

### `src/autonomous.py`

Orquestra o fluxo de uma issue:

1. lista issues abertas;
2. atualiza `origin/main`;
3. recria a branch `bastiao/issue-N` a partir da base;
4. executa `SWEAgent` no workspace;
5. coleta arquivos modificados;
6. executa testes;
7. valida o diff;
8. publica o commit e a pull request via `GitHubClient`.

### `src/swe_agent.py`

Mantem o loop de iteracoes com o modelo. O modelo deve retornar somente acoes
`read`, `write`, `run`, `search`, `list` ou `DONE`. Respostas sem acoes sao
solicitadas novamente ate o limite configurado.

### `src/tools.py` e `src/sandbox.py`

Formam a superficie de ferramentas. O caminho recebido e resolvido contra a
raiz do repositorio, e comandos sao executados com `shell=False`, timeout e
allowlist.

### `src/model.py`

Envia mensagens para `/chat/completions`. A URL pode ser informada com ou sem
o sufixo `/v1`; o cliente evita duplicar esse segmento.

### `src/github_client.py`

Encapsula leitura de issues, criacao idempotente de branch, blobs, tree, commit,
pull request e comentarios. O agente publica pela API em vez de executar
`git push` com o token.

## Isolamento

O container monta somente o workspace alvo em `/workspace/target`. O codigo do
agente fica na imagem em `/app`. Assim, uma resposta do modelo nao pode escrever
diretamente sobre o checkout do proprio agente.

A branch local e recriada a partir de `origin/main` a cada issue. Isso evita
carregar alteracoes de uma issue anterior para a seguinte, mas tambem significa
que alteracoes locais nao publicadas sao descartadas no inicio do proximo
ciclo; o workspace deve ser dedicado ao agente.

## Estados de um ciclo

| Estado | Significado |
| --- | --- |
| `no_open_issues` | Nao havia issue aberta para processar |
| `failed` | O modelo nao concluiu ou nao houve patch testavel |
| `rejected_unsafe_diff` | O patch foi bloqueado pela validacao de diff |
| `pull_request_opened` | Commit e pull request foram publicados |

## Dependencias externas

- GitHub Issues e Git Data API;
- endpoint de chat OpenAI-compatible, normalmente Ollama;
- Python e Git no container;
- pytest quando o repositorio alvo possui diretorio `tests`.

O servico ChromaDB esta disponivel no Compose para evolucao futura, mas nao
participa do fluxo atual.
