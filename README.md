# Bastiao Autodidata

Agente experimental que transforma issues do GitHub em propostas de implementacao
testadas e publicadas como pull requests. O agente nao faz merge automatico e nao
deve receber acesso de escrita direta a `main`.

## Estado atual

O fluxo implantado usa:

- Ollama local compativel com a API OpenAI;
- um workspace separado do codigo do agente;
- uma branch `bastiao/issue-N` por issue;
- testes antes da publicacao;
- validacao de diff para rejeitar substituicoes destrutivas;
- GitHub Data API para publicar arquivos, commit e pull request.

O protocolo continua experimental. A qualidade da alteracao depende do modelo e
toda pull request deve passar por revisao humana antes do merge.

## Fluxo

```text
issue aberta
    |
    v
branch bastiao/issue-N baseada em origin/main
    |
    v
SWE-agent (ler, pesquisar, escrever e executar testes)
    |
    v
pytest ou compileall
    |
    v
validacao de diff
    |
    +--> rejeitado: comentario na issue, sem PR
    |
    v
commit via GitHub API -> pull request -> comentario na issue
```

O ciclo retorna `no_open_issues`, `failed`, `rejected_unsafe_diff` ou
`pull_request_opened`. Uma issue e processada por ciclo conforme
`BASTIAO_MAX_ISSUES`.

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

## Configuracao

As variaveis documentadas em `.env.example` sao:

| Variavel | Obrigatoria | Padrao | Funcao |
| --- | --- | --- | --- |
| `GITHUB_TOKEN` | sim | - | Token usado pela API do GitHub |
| `GITHUB_OWNER` | sim | - | Proprietario do repositorio alvo |
| `GITHUB_REPO` | sim | - | Nome do repositorio alvo |
| `BASTIAO_WORKSPACE` | sim | - | Workspace isolado do repositorio alvo |
| `BASTIAO_MODEL` | nao | `llama3.2:3b` | Modelo enviado ao endpoint |
| `BASTIAO_MAX_ISSUES` | nao | `1` | Maximo de issues por ciclo |
| `BASTIAO_MAX_ITERATIONS` | nao | `20` | Iteracoes do SWE-agent por issue |
| `BASTIAO_INTERVAL_SECONDS` | nao | `3600` | Intervalo entre ciclos; minimo efetivo de 300 segundos |
| `OMNIROUTE_URL` | nao | `http://127.0.0.1:11434/v1` | Base URL da API de chat |
| `OMNIROUTE_API_KEY` | nao | vazio | Chave opcional para o endpoint |

Dentro do Compose, `BASTIAO_WORKSPACE` e `OMNIROUTE_URL` sao definidos pelo
servico para `/workspace/target` e `http://ollama:11434/v1`.

## Seguranca e limites

- Caminhos absolutos e caminhos que escapam do workspace sao rejeitados.
- Comandos sao tokenizados sem `shell=True` e aceitam somente
  `pytest`, `python`, `python3`, `git`, `npm` e `node`.
- Arquivos `.env` e caminhos dentro de `.git` nao sao publicados.
- O agente nao faz merge e nao deve usar credenciais de administrador.
- Diffs que removem muito mais linhas do que adicionam sao rejeitados.
- Falhas de teste impedem a publicacao.
- O token deve permanecer somente no ambiente do processo ou no `.env` local,
  que esta fora do contexto de build pelo `.dockerignore`.

Detalhes operacionais e procedimentos de incidente estao em
[`docs/`](docs/).

## Roadmap

- [x] Fase 1: loop SWE-agent com ferramentas restritas
- [x] Fase 2: fluxo autonomo issue → branch → teste → PR
- [x] Fase 3: isolamento Docker e validacao de diff
- [ ] Validacao semantica especifica por issue
- [ ] Memoria persistente com ChromaDB
- [ ] Revisao humana obrigatoria como gate configuravel
- [ ] Observabilidade e metricas por ciclo

## Licenca

Consulte o arquivo de licenca do repositorio antes de redistribuir o projeto.
