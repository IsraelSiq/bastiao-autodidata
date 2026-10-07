# Checkpoint da sessao ? 2026-10-07

## Estado confirmado

- `main`: commit `94e107b`.
- PR #49: mergeada em 2026-10-07; adicionou incrementos funcionais da issue #37.
- Issues #30 e #37: abertas no GitHub; nenhuma PR estava aberta no inicio desta retomada.
- O container Bastiao estava ativo quando consultado; nenhuma operacao reiniciou, reconstruiu ou atualizou esse servico.
- O checkout operacional tinha trabalho local nao commitado e permaneceu intocado.
- Todas as validacoes ocorreram em clone, imagem e containers descartaveis.
- O ultimo ciclo observado era `no_open_issues`; issue #43 foi ignorada por ja ter PR. A aprovacao persistente ainda mencionava #43 e nao foi reutilizada nem alterada.

## Validacao concluida

- `docker compose config --quiet`: passou.
- Baseline anterior: suite completa em container descartavel: 77 testes passaram; `compileall` passou.
- Branch `fix/bounded-subprocess-output`: suite completa em Docker Linux: 80 testes passaram; `compileall` passou. Pydantic foi instalado somente dentro do container efemero para coletar os testes.
- Testes focados em subprocessos, ferramentas e Quality Gate sob `--memory=512m --cpus=1`: 25 passaram.
- Teste de stress gerou 32 MiB em stdout; a branch reteve exatamente 1.000.000 bytes, sinalizou truncamento e terminou com sucesso sob os limites do container.
- Os testes de rlimit de CPU e memoria passaram em Linux. Suite local Windows: 78 passaram, 2 ignorados (rlimits POSIX-only).
- Healthcheck somente leitura confirmou Ollama, ChromaDB e workspace acessiveis; a sonda GitHub nao recebeu credenciais e nao confirmou conectividade autenticada.
- Nenhum ciclo de agente, alteracao de aprovacao ou escrita no workspace de producao foi iniciado.

## Correcao e status do branch

A prova original reproduziu uma lacuna em `src/process.py`: `communicate()` acumulou 32 MiB de stdout antes de a ferramenta truncar o texto devolvido. A busca de codigo tambem usava captura sem limite e nao removia credenciais do ambiente do processo.

A branch `fix/bounded-subprocess-output` (commit `27fdb39`) adiciona drenagem concorrente de stdout/stderr com teto em bytes por stream, continua drenando saida excedente para nao bloquear pipes, sinaliza truncamento, limita a saida da busca e usa ambiente sanitizado. O Quality Gate registra quando a captura foi truncada. A validacao Linux/Docker confirmou a correcao; a implantacao ativa nao recebeu esse codigo.

## Pendencias para retomar

1. Revisar/mergear a PR de saida limitada depois de conferir todos os diffs e evidencias.
2. Para concluir #30, decidir com o operador os limites adequados do Compose. A configuracao atual nao define `mem_limit`, `cpus` ou `pids_limit`, nem quota de disco para temporarios/workspace.
3. Revisar #37 e concluir sua revisao humana; nao habilitar 24/7.
4. Somente depois iniciar #36 (providers/fallback).

## Guardas operacionais

- Nao limpar, resetar ou sobrescrever o checkout operacional com mudancas locais.
- Nao iniciar o container/agente ativo, nao escrever em `state/approvals.json` e nao reutilizar a aprovacao antiga.
- Nao alterar o container ativo; qualquer teste deve usar clone, imagem e container descartaveis.
- Nao habilitar 24/7, merge automatico, dependencia instalada automaticamente ou fallback ilimitado.
