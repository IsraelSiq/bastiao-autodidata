# Arquitetura

## Componentes

### `main.py`

Valida as variaveis obrigatorias, cria `AutonomousRunner` e executa ciclos
periodicos. O processo permanece ativo mesmo quando um ciclo nao encontra issues.

### `src/autonomous.py`

Orquestra o fluxo de uma issue:

1. lista issues abertas;
2. aplica a selecao e a aprovacao humana;
3. atualiza `origin/main` e recria ou retoma a branch `bastiao/issue-N`;
4. cria ou restaura o plano e o checkpoint;
5. executa `SWEAgent` no workspace;
6. coleta arquivos modificados;
7. executa testes;
8. valida escopo, diff e requisitos explicitos com o `Reviewer`;
9. publica o commit e a pull request via `GitHubClient`.

### `src/swe_agent.py`

Mantem o loop de iteracoes com o modelo. O modelo deve retornar somente acoes
`read`, `write`, `run`, `search`, `list` ou `complete`. A acao `complete` so
encerra quando nao houve erro nas acoes da iteracao. Respostas sem acoes ou
conclusoes apos falhas sao solicitadas novamente ate o limite configurado.

### `src/tools.py` e `src/sandbox.py`

Formam a superficie de ferramentas. O caminho recebido e resolvido contra a
raiz do repositorio, e comandos sao executados com `shell=False`, timeout e
allowlist. Escritas ficam limitadas aos caminhos extraidos pelo Planner e
`complete` e tratado como marcador de controle, nao como comando do shell.

### `src/model.py`

Envia mensagens para `/chat/completions`. A URL pode ser informada com ou sem
o sufixo `/v1`; o cliente evita duplicar esse segmento. A temperatura e
configuravel por `BASTIAO_TEMPERATURE` e usa `0.2` por padrao.

### `src/reviewer.py`

Executa o gate independente do modelo antes da publicacao. Rejeita ausencia de
arquivos, escopo invalido, diff inseguro, Python invalido e valores de
constantes que nao correspondem a requisitos explicitos da issue.

### `src/metrics.py` e `src/task_state.py`

Registram cada ciclo em JSONL e mantem checkpoints por issue. No Compose, ambos
ficam em `/var/lib/bastiao`, separado do workspace montado em
`/workspace/target`.

### `src/github_client.py`

Encapsula leitura de issues, criacao idempotente de branch, blobs, tree, commit,
pull request e comentarios. O agente publica pela API em vez de executar
`git push` com o token.

## Isolamento

O container monta somente o workspace alvo em `/workspace/target` e o estado em
`/var/lib/bastiao`. O codigo do agente fica na imagem em `/app`. Assim, uma
resposta do modelo nao pode escrever diretamente sobre o checkout do proprio
agente e checkpoints nao contaminam o repositorio alvo.

A branch local e recriada a partir de `origin/main` a cada issue. Isso evita
carregar alteracoes de uma issue anterior para a seguinte, mas tambem significa
que alteracoes locais nao publicadas sao descartadas no inicio do proximo
ciclo; o workspace deve ser dedicado ao agente.

## Estados de um ciclo

| Estado | Significado |
| --- | --- |
| `no_open_issues` | Nao havia issue aberta para processar |
| `pending_approval` | Issue selecionada, mas nao aprovada |
| `failed` | O modelo nao concluiu ou nao houve patch testavel |
| `rejected_out_of_scope` | O patch alterou arquivo fora do escopo |
| `rejected_unsafe_diff` | O patch foi bloqueado pela validacao de diff |
| `rejected_by_reviewer` | O Reviewer rejeitou o patch |
| `pull_request_opened` | Commit e pull request foram publicados |

## Dependencias externas

- GitHub Issues e Git Data API;
- endpoint de chat OpenAI-compatible, normalmente Ollama;
- Python e Git no container;
- pytest quando o repositorio alvo possui diretorio `tests`.

O servico ChromaDB esta disponivel no Compose para evolucao futura, mas nao
participa do fluxo atual.
