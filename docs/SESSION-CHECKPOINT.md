# Checkpoint da sessao ? 2026-10-07

## Estado confirmado

- `main`: commit `94e107b`.
- PR #49: mergeada em 2026-10-07; adicionou incrementos funcionais da issue #37.
- Issues #30 e #37: abertas no GitHub; nenhuma PR estava aberta no inicio da retomada.
- A implantacao no servidor estava ativa quando verificada e nao foi reiniciada, reconstruida nem atualizada.
- O checkout operacional tinha trabalho local nao commitado e permaneceu intocado.
- Todas as validacoes ocorreram em clone e containers descartaveis.

## Validacao concluida antes da correcao atual

- `docker compose config --quiet`: passou.
- `python -m compileall -q .`: passou.
- Suite completa em container descartavel: 77 testes passaram.
- Suite focada em Docker com `--memory=512m --cpus=1`: 32 testes passaram.
- Healthcheck somente leitura: Ollama, ChromaDB e workspace responderam; a sonda GitHub nao recebeu credenciais e nao validou conectividade autenticada.
- Nao houve ciclo de agente, alteracao da aprovacao persistente ou operacao de escrita no workspace de producao.

## Achado e trabalho em andamento

A prova de estresse no container descartavel reproduziu uma lacuna em `src/process.py`: `communicate()` acumulou 32 MiB de stdout antes de a ferramenta truncar o texto devolvido. A busca de codigo tambem usava captura sem limite e nao removia credenciais do ambiente do processo.

A branch `fix/bounded-subprocess-output` adiciona drenagem de stdout/stderr com teto em bytes, continua drenando saida excedente para nao bloquear os pipes, sinaliza truncamento e usa o executor limitado/sanitizado na busca. Foram incluidos testes para ambas as streams, rlimit de CPU, busca e evidencia do Quality Gate.

Validacao local nesta branch: `python -m pytest -q` ? 78 passaram, 2 ignorados; `python -m compileall -q .` e `git diff --check` passaram. Ainda falta construir/testar a imagem Docker com essa correcao e revisar/abrir PR. A branch ainda nao foi aplicada ao servidor.

## Pendencias para retomar

1. Revisar os diffs e validar a branch no container descartavel, incluindo volume de saida maior que o buffer e limite de CPU/memoria.
2. Atualizar a PR/roadmap apenas com evidencias do Docker corrigido.
3. Para concluir #30, decidir com o operador os limites adequados de container; o Compose atual nao define `mem_limit`, `cpus` ou `pids_limit`, nem quota de disco para temporarios/workspace.
4. Revisar #37, que ja tem implementacao via PR #49, mas ainda requer validacao/revisao humana conforme roadmap.
5. Somente depois dessas etapas iniciar #36 (providers/fallback).

## Guardas operacionais

- Nao limpar, resetar ou sobrescrever o checkout operacional com mudancas locais.
- Nao iniciar o container/agente ativo, nao escrever em `state/approvals.json` e nao reutilizar aprovacao antiga.
- Nao alterar o container ativo; qualquer build/teste deve usar clone, imagem e container descartaveis.
- Nao habilitar 24/7, merge automatico, dependencia instalada automaticamente ou fallback ilimitado.
