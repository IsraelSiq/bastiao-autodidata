# Checkpoint da sessao ? 2026-10-07 (retomada #30)

## Atualizacao posterior: autonomia por issue (#29)

- Continuacao implementada localmente na branch `feat/issue-29-human-approval`; a
  PR #53 ainda nao recebeu estes novos commits, e nada foi implantado no servidor.
- Uma aprovacao persistente por issue autoriza trabalho delimitado pelo Planner,
  testes/validacao, commits locais em `bastiao/issue-N` e publicacao apos os
  quality gates e Reviewer. Merge permanece manual; remover o numero de
  `state/approvals.json` revoga a autorizacao.
- `git add` e `git commit -m` foram liberados somente para arquivos explicitamente
  permitidos e na branch esperada; push, merge, troca de branch, operacoes
  destrutivas e arquivos `.git`/credenciais continuam bloqueados.
- Instalacao de dependencias, comandos JavaScript/Node arbitrarios e inspecao
  Docker continuam com aprovacao adicional. Scripts padrao de teste/qualidade
  podem executar sem pausa por etapa.
- Validacao: `python -m pytest -q` — 109 passed, 2 skipped;
  `python -m compileall -q src tests` e `git diff --check` passaram.
- PR #53/issue #29 permanecem pendentes de publicacao/revisao; a implantacao
  ativa e o estado persistente de aprovacoes nao foram alterados.

## Estado confirmado

- `main` usada como base: commit `95f1f87` (PR #50 mergeada em 2026-10-07).
- PR #49 e PR #50: mergeadas.
- Issues #30 e #37: continuam abertas no GitHub; nenhuma PR aberta para a branch de limites.
- Branch atual: `fix/issue-30-compose-limits`, ainda sem commit/publicacao.
- O container Bastiao estava ativo quando consultado; nenhuma operacao reiniciou, reconstruiu ou atualizou esse servico.
- O checkout operacional tinha trabalho local nao commitado e permaneceu intocado.
- Todas as validacoes ocorreram em clone, imagem e containers descartaveis.
- O ultimo ciclo observado era `no_open_issues`; issue #43 foi ignorada por ja ter PR. A aprovacao persistente ainda mencionava #43 e nao foi reutilizada nem alterada.

## Validacao concluida antes da branch atual

- `docker compose config --quiet`: passou.
- Baseline anterior: suite completa em container descartavel: 77 testes passaram; `compileall` passou.
- Branch `fix/bounded-subprocess-output`: suite completa em Docker Linux: 80 testes passaram; `compileall` passou. Pydantic foi instalado somente dentro do container efemero para coletar os testes.
- Testes focados em subprocessos, ferramentas e Quality Gate sob `--memory=512m --cpus=1`: 25 passaram.
- Teste de stress gerou 32 MiB em stdout; a branch reteve exatamente 1.000.000 bytes, sinalizou truncamento e terminou com sucesso sob os limites do container.
- Os testes de rlimit de CPU e memoria passaram em Linux. Suite local Windows: 78 passaram, 2 ignorados (rlimits POSIX-only).
- Healthcheck somente leitura confirmou Ollama, ChromaDB e workspace acessiveis; a sonda GitHub nao recebeu credenciais e nao confirmou conectividade autenticada.
- Nenhum ciclo de agente, alteracao de aprovacao ou escrita no workspace de producao foi iniciado.

## Validacao da branch atual `fix/issue-30-compose-limits`

- `python -m pytest tests/test_process.py tests/test_tools.py tests/test_quality_gate.py tests/test_autonomous.py -q`: 39 passed, 2 skipped (Windows; rlimits POSIX-only).
- `python -m pytest -q` no Windows: 82 passed, 2 skipped.
- `python -m pytest -q` na imagem Linux descartavel sob 4 GiB/2 CPUs/256 PIDs e `/tmp` tmpfs 512 MiB: 84 passed.
- `python -m compileall -q .` passou no Windows e no container Linux; `git diff --check` passou localmente.
- `docker compose --profile agent config --quiet` passou no diretorio descartavel no servidor; o Compose avisou que o campo `version` legado e ignorado.
- Medicao real no container descartavel: `memory.max=4294967296`, `cpu.max=200000 100000`, `pids.max=256`, `/tmp=536870912` bytes. Pydantic foi instalado somente na camada da imagem temporaria para executar os testes; manifests do projeto nao mudaram.
- Nao foi iniciado/recriado qualquer container do stack Bastiao/Ollama/Chroma/Open WebUI ativo; nenhum ciclo ou aprovacao persistente foi tocado.

## PR #50 e estado da branch de limites

A prova original reproduziu uma lacuna em `src/process.py`: `communicate()` acumulou 32 MiB de stdout antes de a ferramenta truncar o texto devolvido. A PR #50 (merge commit `95f1f87`) adicionou drenagem concorrente com teto em bytes, sinalizacao de truncamento, ambiente sanitizado e limite para busca; a validacao Linux/Docker passou. A implantacao ativa nao recebeu esse codigo.

A branch atual `fix/issue-30-compose-limits` modifica `.env.example`, `docker-compose.yml`, `src/autonomous.py`, `src/process.py`, `src/tools.py`, `src/quality_gate.py` e testes. Propoe container Bastiao limitado a 4 GiB, 2 CPUs, 256 PIDs, `/tmp` tmpfs de 512 MiB; por subprocesso POSIX, 2048 MiB de espaco de enderecamento e 45 s de CPU. O codigo diagnostica `MemoryError` e `SIGXCPU`, inclusive no Quality Gate. A validacao Linux confirmou os limites configurados; eles nao foram aplicados ao container ativo.

Gap conhecido: `pids_limit` e por container; `/tmp` tem teto, mas o volume `workspace/` nao tem quota de disco agregada, e comandos podem escrever diretamente nele. Valores antigos `0` em `.env` podem continuar desativando rlimits por comando; a implantacao futura requer revisar esse arquivo.

## Pendencias para retomar

1. Corrigir eventuais falhas dos testes e validar testes focados + suite completa em Linux.
2. Validar `docker compose config` e os limites em um container descartavel no servidor; nao tocar no stack ativo.
3. Fechar a politica pendente de disco do workspace, registrar evidencias, fazer revisao e abrir PR para #30 mantendo a issue aberta enquanto faltar requisito.
4. Revisar #37 e concluir sua revisao humana; nao habilitar 24/7.
5. Somente depois iniciar #36 (providers/fallback).

## Guardas operacionais

- Nao limpar, resetar ou sobrescrever o checkout operacional com mudancas locais.
- Nao iniciar o container/agente ativo, nao escrever em `state/approvals.json` e nao reutilizar a aprovacao antiga.
- Nao alterar o container ativo; qualquer teste deve usar clone, imagem e container descartaveis.
- Nao habilitar 24/7, merge automatico, dependencia instalada automaticamente ou fallback ilimitado.
