> **Checkpoint operacional (2026-10-07):** PR #50 mergeada na `main` (commit `95f1f87`). Limites Compose e rlimits da issue #30 passaram na validacao Docker descartavel; a quota agregada de `workspace/` continua pendente. Nenhuma alteracao foi aplicada ao servico ativo. Veja [`ROADMAP.md`](ROADMAP.md) e [`docs/SESSION-CHECKPOINT.md`](docs/SESSION-CHECKPOINT.md).

# Bastiao Autodidata

Agente experimental que transforma issues do GitHub em propostas de implementacao
testadas e publicadas como pull requests. O agente nao faz merge automatico e nao
deve receber acesso de escrita direta a `main`.

## Estado atual

O fluxo implantado usa:

- Ollama local compativel com a API OpenAI;
- um workspace separado do codigo do agente;
- uma branch `bastiao/issue-N` por issue;
- aprovacao humana antes da execucao e, separadamente, antes de acoes sensiveis/publicacao;
- Planner com caminhos permitidos e passos verificaveis;
- testes, validacao de diff e Reviewer antes da publicacao;
- estado e metricas persistentes fora do workspace;
- GitHub Data API para publicar arquivos, commit e pull request;
- observabilidade: `cycle_id` por ciclo, metricas com redaction e rotacao,
  `status.json`, retry com backoff nas leituras e healthcheck
  (`python -m src.health`);
- sandbox com ambiente sanitizado, execucao limitada (`src/process.py`) e
  limpeza do diretorio temporario por tarefa;
- Tool do Open WebUI somente leitura (`openwebui/github_reader_tool.py`) para o
  chat ler links, issues, PRs e arquivos do GitHub.

O protocolo continua experimental. A qualidade da alteracao depende do modelo e
toda pull request deve passar por revisao humana antes do merge.

## Fluxo

```text
issue aberta e explicitamente aprovada
    |
    v
workspace local isolado e branch bastiao/issue-N
    |
    v
SWE-agent (ler, pesquisar, escrever e executar testes)
    |
    +--> acao sensivel: pausa ate aprovacao especifica, temporaria e de uso unico
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
aprovacao humana da publicacao (manifesto de arquivos/fingerprints)
    |
    v
branch GitHub -> commit -> pull request -> comentario na issue
```

O ciclo retorna `no_open_issues`, `pending_approval`, `failed`,
`rejected_out_of_scope`, `rejected_unsafe_diff`, `rejected_by_reviewer`,
`pending_action_approval`, `action_denied`, `quality_gate_failed` ou
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

## Aprovacao de acoes sensiveis

A aprovacao da issue permite iniciar o trabalho, mas nao aprova automaticamente
operacoes sensiveis nem a publicacao no GitHub. Escritas em arquivos de
configuracao/dependencias e execucao de comandos JavaScript ou instalacao de
pacotes pausam o ciclo e criam uma solicitacao persistente. Cada aprovacao fica
vinculada a issue, a acao e ao fingerprint do conteudo/comando exato; e de uso
unico e expira. Se o conteudo mudar, a aprovacao anterior nao vale. Publicar
cria branch remota, commit e PR apenas depois de uma aprovacao separada do
manifesto dos arquivos validados.

Comandos privilegiados, destrutivos, de sistema, acesso fora do workspace,
Podman, operacoes Docker mutaveis, alteracoes de Git e execucao Python
arbitraria sao bloqueados, nao podem ser liberados por aprovacao. Inspecoes
Docker somente leitura exigem aprovacao. Testes e compilacao Python limitados
continuam automaticos. A auditoria JSONL registra contexto sanitizado, nunca o
conteudo dos arquivos; valores em argumentos com nomes de credenciais e codigo
inline de Node sao ocultados. Os arquivos de solicitacao e auditoria usam
permissao `0600` em POSIX.

No Docker Compose, revise as solicitacoes persistidas no volume `./state`:

```bash
docker compose --profile agent exec bastiao python -m src.action_approval list
docker compose --profile agent exec bastiao python -m src.action_approval approve REQUEST_ID --approver "Seu nome"
docker compose --profile agent exec bastiao python -m src.action_approval deny REQUEST_ID
```

Antes de aprovar `publish_changes`, revise o diff local e os resultados do
Quality Gate/Reviewer. No host, use `git -C ./workspace diff origin/main`. O
pedido mostra arquivos e fingerprints, nao copia o conteudo do patch para a
auditoria.

O estado padrao e `/var/lib/bastiao/action-approvals.json`; a auditoria fica
em `/var/lib/bastiao/action-approval-audit.jsonl`. Solicitacoes expiram apos
24 horas e aprovacoes apos 1 hora por padrao. Apos aprovar, um ciclo posterior
retoma a tarefa; a aprovacao nao executa a acao por si mesma. Nao desative
`BASTIAO_REQUIRE_ACTION_APPROVAL` em instalacoes operacionais.

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
| `BASTIAO_COMMAND_TIMEOUT_SECONDS` | nao | `60` | Timeout de cada comando do sandbox |
| `BASTIAO_MAX_COMMANDS` | nao | `100` | Maximo de comandos por tarefa |
| `BASTIAO_MAX_OUTPUT_CHARS` | nao | `10000` | Limite de caracteres devolvidos por comando; stdout/stderr sao limitados antes da captura em memoria |
| `BASTIAO_MAX_WRITE_BYTES` | nao | `1000000` | Limite de bytes por arquivo escrito pela ferramenta `write` |
| `BASTIAO_MEMORY_LIMIT_MB` | nao | `2048` | Limite POSIX de espaco de enderecamento por comando; `0` desativa |
| `BASTIAO_CPU_LIMIT_SECONDS` | nao | `45` | Limite POSIX de CPU por comando; `0` desativa |
| `BASTIAO_CONTAINER_MEMORY_LIMIT` | nao | `4g` | Limite cgroup de memoria do container Bastiao |
| `BASTIAO_CONTAINER_CPUS` | nao | `2.0` | Limite agregado de CPUs do container Bastiao |
| `BASTIAO_CONTAINER_PIDS_LIMIT` | nao | `256` | Maximo de processos/threads no container Bastiao |
| `BASTIAO_REQUIRE_APPROVAL` | nao | `true` | Exige aprovacao no arquivo persistente antes da execucao |
| `BASTIAO_APPROVAL_FILE` | nao | `/var/lib/bastiao/approvals.json` | Arquivo JSON com issues aprovadas |
| `BASTIAO_REQUIRE_ACTION_APPROVAL` | nao | `true` | Exige aprovacao especifica, expirada e de uso unico para acoes sensiveis e publicacao |
| `BASTIAO_ACTION_APPROVAL_FILE` | nao | `/var/lib/bastiao/action-approvals.json` | Solicitacoes e decisoes de aprovacao de acoes |
| `BASTIAO_ACTION_AUDIT_FILE` | nao | `/var/lib/bastiao/action-approval-audit.jsonl` | Auditoria append-only das solicitacoes e decisoes |
| `BASTIAO_APPROVAL_REQUEST_TTL_SECONDS` | nao | `86400` | Validade da solicitacao pendente |
| `BASTIAO_ACTION_APPROVAL_TTL_SECONDS` | nao | `3600` | Validade da aprovacao antes do consumo |
| `BASTIAO_STATE_DIR` | nao | `/var/lib/bastiao` | Diretorio de checkpoints e metricas |
| `OMNIROUTE_URL` | nao | `http://127.0.0.1:11434/v1` | Base URL da API de chat |
| `OMNIROUTE_API_KEY` | nao | vazio | Chave opcional para o endpoint |

Dentro do Compose, `BASTIAO_WORKSPACE` e `OMNIROUTE_URL` sao definidos pelo
servico para `/workspace/target` e `http://ollama:11434/v1`. O container Bastiao
recebe limites agregados de 4 GiB, 2 CPUs e 256 processos/threads; `/tmp` usa tmpfs
limitado a 512 MiB com `noexec,nosuid`. Os comandos POSIX recebem ainda limites de
2 GiB de espaco de enderecamento e 45 segundos de CPU em cada subprocesso do sandbox e do Quality Gate. O `pids_limit` vale para o
container inteiro, nao e um cgroup separado por issue.

O limite de 512 MiB cobre arquivos temporarios em `/tmp`, nao o volume montado em
`workspace/`. A ferramenta `write` limita cada arquivo, mas comandos executados no
sandbox podem escrever diretamente no workspace; o Compose ainda nao imp?e quota
agregada nesse volume. Para atualizar uma instalacao existente, altere os valores
`BASTIAO_MEMORY_LIMIT_MB` e `BASTIAO_CPU_LIMIT_SECONDS` no `.env` (instalacoes
antigas podem manter `0`) e valide a configuracao antes de recriar o servico.

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
- Comandos sao tokenizados sem `shell=True`; comandos destrutivos, privilegiados,
  de sistema, Git mutavel, Docker mutavel/Podman, execucao Python arbitraria e leitura
  de arquivos com nomes de credenciais sao bloqueados antes da execucao.
-   Instalacoes de pacotes, comandos JavaScript, inspecoes Docker e alteracoes em
  configuracao exigem aprovacao de acao especifica; a publicacao no GitHub exige
  aprovacao separada, vinculada ao fingerprint de cada arquivo validado.
- Arquivos `.env` e caminhos dentro de `.git` nao sao publicados.
- O agente nao faz merge e nao deve usar credenciais de administrador.
- Diffs que removem muito mais linhas do que adicionam sao rejeitados.
- O Quality Gate executa testes, compileall, lint/type-check definidos em
  `package.json` e `git diff --check`, registrando comando, saida, retorno,
  duracao e timeout.
- Qualquer falha ou timeout do Quality Gate impede a publicacao e gera o estado
  `quality_gate_failed`.
- O sandbox limita timeout, quantidade de comandos, tamanho da saida capturada e
  tamanho de cada arquivo escrito; ao atingir um limite, a acao falha sem
  publicar uma PR.
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
3. **#30 - limites de CPU, memoria, processos e saida do sandbox** - implementacao e testes Docker descartaveis validados; falta resolver quota de `workspace/` e revisar/mergear.
4. **#37 — observabilidade, checkpoints e diagnostico operacional** - concluida.
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
- [x] Observabilidade (#37): cycle_id, redaction, rotacao, status.json, retry e healthcheck.
- [x] Limites portaveis e saida limitada do sandbox (#30); Compose e rlimits validados em container Linux descartavel. Quota agregada de `workspace/` permanece pendente.
- [x] Tool somente leitura do Open WebUI para ler o GitHub.
- [ ] Memoria persistente (#35), providers/fallback (#36) e pipeline autodidata (#38).
- [x] Quality Gate com timeout, evidencias e bloqueio de publicacao.
- [x] Escopo estrito: planos vazios rejeitados e violacoes abortam o agente.

## Licenca

Consulte o arquivo de licenca do repositorio antes de redistribuir o projeto.
