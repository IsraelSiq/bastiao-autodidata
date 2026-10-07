# Checkpoint da sessao — 2026-10-07 (triagem de issues)

## Estado confirmado

- `main` inclui a PR #51, merge commit `724c6a9` (PR #50 permanece em `95f1f87`).
- PRs #49, #50 e #51 estao mergeadas. Nenhuma PR estava aberta durante a auditoria.
- Issues #43, #6, #10, #11 e #21 foram fechadas com comentarios de justificativa: #43 concluida; #6 substituida por #36; #10/#11 incorporadas em #38; #21 substituida pelo roadmap #31.
- Permanecem abertas: #22, #23, #24, #25, #29, #30, #31, #33, #34, #35, #36, #37 e #38.
- A triagem nao alterou o servico ativo nem iniciou ciclo do agente.

## Trabalho de sandbox ja mergeado

- PR #50 limitou captura de stdout/stderr antes da retencao, com drenagem para evitar bloqueio de pipes, indicacao de truncamento e busca de codigo pelo executor sanitizado.
- PR #51 definiu limites Compose de 4 GiB, 2 CPUs, 256 PIDs e tmpfs de `/tmp` de 512 MiB; limites POSIX por subprocesso de 2048 MiB e 45 segundos de CPU; propagacao e diagnostico de limites no Quality Gate.
- Validacao documentada da PR #51: Windows 82 testes passaram, 2 skips POSIX-only; Linux/Docker descartavel 84 testes passaram; `compileall`, `git diff --check` e `docker compose --profile agent config --quiet` passaram. Medicoes descartaveis confirmaram os limites cgroup/tmpfs.
- A validacao foi feita em clone e container descartaveis. Nenhum container do stack ativo foi reiniciado, reconstruido ou atualizado.

## Riscos e pendencias

- `workspace/` nao tem quota agregada; comandos podem escrever diretamente no bind mount. `pids_limit` e agregado ao container, nao por issue. Decidir se a quota de workspace entra no escopo antes de fechar #30.
- A PR #51 nao foi aplicada ao servico ativo. Em `.env` antigo, `BASTIAO_MEMORY_LIMIT_MB=0` e `BASTIAO_CPU_LIMIT_SECONDS=0` podem desativar os rlimits por subprocesso. Qualquer implantacao requer revisao do `.env` e janela operacional aprovada.
- #29, #33, #34 e #37 possuem implementacoes parciais, mas restam criterios descritos em `ROADMAP.md`; nao marcar como concluidas ainda.
- #22 precisa esclarecer se requer o produto SWE-agent upstream ou apenas o fluxo autonomo proprio do Bastiao. #25 continua sem implementacao mergeada; PRs #26/#28 fecharam sem merge.
- #23/#24 seguem adiadas; #35/#36/#38 sao fases futuras.
- A atualizacao do roadmap e deste checkpoint esta nesta branch documental; fechar #31 apos revisar e mergear esta documentacao.

## Proxima retomada

1. Revisar e mergear a atualizacao documental; fechar #31 somente depois disso.
2. Definir quota do workspace e atualizar escopo/issue #30 conforme a decisao.
3. Completar os requisitos pendentes de #29, #33, #34 e #37 com testes antes de ampliar autonomia.
4. Manter o stack ativo intacto ate aprovacao expressa para implantacao.
