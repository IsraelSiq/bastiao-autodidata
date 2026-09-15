# Bastiao Autodidata

Agente experimental que transforma issues do GitHub em propostas de implementacao
testadas e publicadas como pull requests. O agente nao faz merge automatico e nao
deve receber acesso de escrita direta a `main`.

## Estado atual

O fluxo implantado usa:

- Ollama local compativel com a API OpenAI;
- um workspace separado do codigo do agente;
- uma branch `bastiao/issue-N` por issue;
- aprovacao humana antes da execucao;
- Planner com caminhos permitidos e passos verificaveis;
- testes, validacao de diff e Reviewer antes da publicacao;
- estado e metricas persistentes fora do workspace;
- GitHub Data API para publicar arquivos, commit e pull request.

O protocolo continua experimental. A qualidade da alteracao depende do modelo e
toda pull request deve passar por revisao humana antes do merge.

## Fluxo

```text
issue aberta e explicitamente aprovada
    |
    v
branch bastiao/issue-N baseada em origin/main
    |
    v
SWE-agent (ler, pesquisar, escrever e executar testes)
    |
    v
pytest ou compileall + validacao semantica
    |
    v
Reviewer deterministico
    |
    +--> rejeitado: comentario na issue, sem PR
    |
    v
commit via GitHub API -> pull request -> comentario na issue
```

O ciclo retorna `no_open_issues`, `pending_approval`, `failed`,
`rejected_out_of_scope`, `rejected_unsafe_diff`, `rejected_by_reviewer` ou
`pull_request_opened`. Uma issue e processada por ciclo conforme
`BASTIAO_MAX_ISSUES`.

## Planner, Executor e estado

Cada issue selecionada passa primeiro por `Planner.build_issue_plan()`, que
produz critérios de aceitação, caminhos explicitamente mencionados e quatro
passos verificáveis: `inspect`, `implement`, `verify` e `review`. O
`SandboxEnv`/`ToolHandler` funciona como Executor: ações de escrita são
rejeitadas quando o caminho não pertence ao plano, além das restrições gerais
de comandos e caminhos.

O `TaskExecutionState` e salvo em
`/var/lib/bastiao/tasks/issue-N.json` no Docker Compose e contem o plano
serializado, passo atual, tentativas, ultimo resultado, branch e erro. Esse
checkpoint e atualizado antes de iniciar a execucao, apos a verificacao e em
falhas. Ele permite retomar o contexto essencial sem depender do historico
textual do modelo. A conclusao do SWE-agent exige a acao explicita
`complete`, reconhecida pelo Executor; texto livre como `DONE` nao encerra
uma tarefa. Uma conclusao acompanhada de erro de ferramenta tambem e
rejeitada.

O arquivo de aprovacao e `/var/lib/bastiao/approvals.json` e deve conter uma
lista JSON de numeros de issues, por exemplo `[43]`. Com
`BASTIAO_REQUIRE_APPROVAL=true`, issues fora dessa lista permanecem em
`pending_approval`.

## Execucao local

Requisitos: Python 3.12+, Git, acesso a um endpoint de chat compativel com
OpenAI e um token GitHub com permissao minima para ler issues e criar branches,
commits e pull requests no repositorio alvo.

```bash
python -m venv .venv
python -m pip install -r requirements.txt
copy .env.example .env
python main.py
```

No Linux, use `cp .env.example .env`. O arquivo `.env` nunca deve ser commitado.
Para executar apenas os testes:

```bash
python -m pytest tests -q
python -m compileall -q .
```

## Execucao com Docker Compose

O perfil `agent` inicia o agente e o servico Ollama. O workspace montado em
`./workspace` e o repositorio que o agente pode modificar; o codigo do agente
fica dentro da imagem.

```bash
copy .env.example .env
docker compose up -d ollama
docker compose --profile agent build bastiao
docker compose --profile agent up -d bastiao
docker compose --profile agent logs -f bastiao
```

No Linux, substitua `copy` por `cp`. Para parar somente o agente:

```bash
docker compose --profile agent stop bastiao
```

O ChromaDB continua definido no Compose para a futura camada de memoria, mas nao
e utilizado pelo fluxo issue→PR atual.

O estado e as metricas sao montados separadamente:

```text
./state/tasks/issue-N.json   -> /var/lib/bastiao/tasks/issue-N.json
./state/metrics/cycles.jsonl -> /var/lib/bastiao/metrics/cycles.jsonl
```

## Configuracao

As variaveis documentadas em `.env.example` sao:

| Variavel | Obrigatoria | Padrao | Funcao |
| --- | --- | --- | --- |
| `GITHUB_TOKEN` | sim | - | Token usado pela API do GitHub |
| `GITHUB_OWNER` | sim | - | Proprietario do repositorio alvo |
| `GITHUB_REPO` | sim | - | Nome do repositorio alvo |
| `BASTIAO_WORKSPACE` | sim | - | Workspace isolado do repositorio alvo |
| `BASTIAO_MODEL` | nao | `llama3.2:3b` | Modelo enviado ao endpoint |
| `BASTIAO_TEMPERATURE` | nao | `0.2` | Temperatura das respostas do agente |
| `BASTIAO_MAX_ISSUES` | nao | `1` | Maximo de issues por ciclo |
| `BASTIAO_MAX_ITERATIONS` | nao | `20` | Iteracoes do SWE-agent por issue |
| `BASTIAO_INTERVAL_SECONDS` | nao | `3600` | Intervalo entre ciclos; minimo efetivo de 300 segundos |
| `BASTIAO_ISSUE_NUMBERS` | nao | vazio | Lista separada por virgulas para limitar issues |
| `BASTIAO_RETRY_ISSUES` | nao | `false` | Permite retry de issues que ja possuem PR |
| `BASTIAO_GITHUB_TIMEOUT_SECONDS` | nao | `20` | Timeout de cada requisicao a API do GitHub |
| `BASTIAO_QUALITY_GATE_TIMEOUT_SECONDS` | nao | `120` | Timeout de cada comando do Quality Gate |
| `BASTIAO_REQUIRE_APPROVAL` | nao | `true` | Exige aprovacao no arquivo persistente antes da execucao |
| `BASTIAO_APPROVAL_FILE` | nao | `/var/lib/bastiao/approvals.json` | Arquivo JSON com issues aprovadas |
| `BASTIAO_STATE_DIR` | nao | `/var/lib/bastiao` | Diretorio de checkpoints e metricas |
| `OMNIROUTE_URL` | nao | `http://127.0.0.1:11434/v1` | Base URL da API de chat |
| `OMNIROUTE_API_KEY` | nao | vazio | Chave opcional para o endpoint |

Dentro do Compose, `BASTIAO_WORKSPACE` e `OMNIROUTE_URL` sao definidos pelo
servico para `/workspace/target` e `http://ollama:11434/v1`.

Para iniciar pelo roadmap em uma issue especifica, use por exemplo
`BASTIAO_ISSUE_NUMBERS=29` e registre a aprovacao em
`state/approvals.json`:

```json
[29]
```

O agente ignora automaticamente branches que ja possuem uma pull request, a
menos que `BASTIAO_RETRY_ISSUES=true`.

## Seguranca e limites

- Caminhos absolutos e caminhos que escapam do workspace sao rejeitados.
- Comandos sao tokenizados sem `shell=True` e aceitam somente
  `pytest`, `python`, `python3`, `git`, `npm` e `node`.
- Arquivos `.env` e caminhos dentro de `.git` nao sao publicados.
- O agente nao faz merge e nao deve usar credenciais de administrador.
- Diffs que removem muito mais linhas do que adicionam sao rejeitados.
- O Quality Gate executa testes, compileall, lint/type-check definidos em
  `package.json` e `git diff --check`, registrando comando, saida, retorno,
  duracao e timeout.
- Qualquer falha ou timeout do Quality Gate impede a publicacao e gera o estado
  `quality_gate_failed`.
- O Reviewer valida caminhos, seguranca do diff, sintaxe Python e constantes
  explicitamente exigidas pela issue.
- O modelo nao pode publicar commits diretamente; a publicacao usa a API do
  GitHub somente depois dos gates.
- O token deve permanecer somente no ambiente do processo ou no `.env` local,
  que esta fora do contexto de build pelo `.dockerignore`.

Detalhes operacionais e procedimentos de incidente estao em
[`docs/`](docs/).

## Roadmap

O roadmap detalhado, a ordem de dependencias e o historico de validacao estao
em [`ROADMAP.md`](ROADMAP.md). A proxima retomada deve seguir esta ordem:

1. **#34 — quality gate real antes de publicar uma PR** — concluida.
2. **Reforco de escopo e abortamento apos violacao** — concluido.
3. **#30 — limites de CPU, memoria, processos e saida do sandbox**.
4. **#37 — observabilidade, checkpoints e diagnostico operacional**.
5. **#36 — abstracao de providers e fallback limitado**.
6. **#35 — memoria persistente com ChromaDB**.
7. **#38 — pipeline autodidata de pesquisa, estudo e avaliacao**.

OpenHands, execucao 24/7, merge automatico e maior autonomia permanecem
bloqueados ate que essas etapas tenham testes e gates verificaveis.

Resumo do que ja foi concluido:

- [x] Loop SWE-agent com ferramentas restritas.
- [x] Fluxo issue → branch → testes → Reviewer → PR.
- [x] Isolamento Docker e validacao de diff.
- [x] Aprovacao humana persistente antes da execucao.
- [x] Checkpoints e metricas fora do workspace.
- [x] Retomada com erro anterior do Reviewer.
- [x] Planner com caminhos em markdown e texto simples.
- [x] Coleta de arquivos novos nao rastreados.
- [x] Reviewer semantico para constantes e sintaxe Python.
- [x] Teste controlado #43 concluido com a PR #46 contendo somente
  `src/health_marker.py`.
- [ ] Quality gate completo, limites de recursos e memoria persistente.
- [x] Quality Gate com timeout, evidencias e bloqueio de publicacao.
- [x] Escopo estrito: planos vazios rejeitados e violacoes abortam o agente.

## Licenca

Consulte o arquivo de licenca do repositorio antes de redistribuir o projeto.
