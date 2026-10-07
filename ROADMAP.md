# Roadmap do Bastiao Autodidata

Este documento registra a ordem de evolucao recomendada, o estado verificado do protocolo e o ponto seguro de retomada.

## Estado verificado em 2026-10-07

A `main` inclui a PR #51 (merge commit `724c6a9`), baseada no commit `95f1f87` da PR #50. A PR #51 aplica limites configuraveis no container e por subprocesso, com testes em Windows e Docker/Linux descartavel. Nenhuma dessas alteracoes foi aplicada ao servico ativo.

Nao ha PR aberta no momento. Issues abertas apos a triagem: #22, #23, #24, #25, #29, #30, #31, #33, #34, #35, #36, #37 e #38.

Issues encerradas nesta triagem: #43 como concluida (PR #46 mergeada); #6 como duplicada/supersedida pela #36; #10 e #11 como incorporadas a #38; #21 como meta de planejamento substituida pelo roadmap #31. O encerramento das issues #6, #10 e #11 nao declara suas funcionalidades implementadas.

## O que ja foi validado

- PRs #49, #50 e #51 mergeadas na `main`.
- A PR #50 limita a captura de stdout/stderr antes de reter os bytes e usa o executor sanitizado para busca de codigo.
- A PR #51 limita o container Bastiao a 4 GiB, 2 CPUs e 256 PIDs, e define `/tmp` tmpfs de 512 MiB. Subprocessos POSIX recebem limites configuraveis de 2048 MiB de espaco de enderecamento e 45 segundos de CPU.
- Testes da PR #51: suite Windows 82 passed, 2 skipped; suite Linux/Docker descartavel 84 passed; `compileall`, `git diff --check` e configuracao do Compose passaram. Medicoes no container descartavel confirmaram os limites cgroup e tmpfs.
- PR #49 entregou cycle_id, healthchecks read-only, retry limitado para leituras GitHub, `status.json`, redaction e rotacao de metricas.
- Nenhum ciclo foi iniciado para esta triagem. O container e o workspace ativos nao foram reiniciados, reconstruidos nem modificados.

## Ponto atual e criterio por issue

### Seguranca e execucao

- **#29 — aprovacoes humanas: parcial, manter aberta.** O fluxo exige aprovacao persistente por issue (PR #42), mas a issue pede politica por classe de acao, expiracao e auditoria de quem aprovou/quando/qual acao. Confirmar e testar esses requisitos antes de fechar.
- **#30 — recursos do sandbox: implementacao mergeada, manter aberta ate decisao do workspace.** A PR #51 valida limites de memoria, CPU, PIDs por container e `/tmp`; a PR #50 limita stdout/stderr. O limite de PIDs e agregado ao container, nao isolado por issue. `workspace/` continua sem quota agregada: `BASTIAO_MAX_WRITE_BYTES` cobre a ferramenta `write`, nao escritas feitas por comandos. Decidir se sera implementada quota no filesystem ou se a limitacao sera aceita explicitamente como fora de escopo. Os novos limites nao foram aplicados ao servico ativo; revisar `.env` legado (valores `0` desativam rlimits por subprocesso) e obter aprovacao operacional antes de qualquer implantacao.
- **#31 — roadmap: atualizar/validar esta documentacao e entao fechar.** Esta revisao atualiza a situacao das issues e os criterios de conclusao; a issue fica aberta ate a documentacao ser revisada e mergeada.

### Agente de desenvolvimento

- **#22 — SWE-agent: manter aberta para clarificar escopo.** O Bastiao possui um fluxo proprio issue → planejamento → edicao/testes → publicacao de PR. Nao foi verificada integracao com o projeto SWE-agent upstream. Fechar apenas se o requisito era o agente proprio; caso contrario, redefinir o escopo.
- **#25 — hello.py: manter aberta.** PRs #26 e #28 foram fechadas sem merge; o arquivo requerido nao esta na `main`. Fechar como nao planejada somente se este teste controlado nao for mais necessario.
- **#33 — Reviewer: parcial, manter aberta.** Ha revisao deterministica de escopo/diff e validacao de certos requisitos explicitos; ainda faltam os criterios completos da issue, incluindo loop de correcao limitado e cobertura adequada de falhas do modelo.
- **#34 — Quality Gate: parcial, manter aberta.** O gate executa verificacoes descobertas, registra evidencias e bloqueia PR em falha. A issue ainda exige repassar falhas ao agente para uma rodada de correcao limitada e verificar presenca de testes relacionados quando necessario; isso nao deve ser declarado concluido sem implementacao e testes.

### Fases futuras

- **#23 OpenHands e #24 hibrido:** adiadas ate controles de seguranca, qualidade e abstracao de provider estarem prontos; nao iniciar agora.
- **#35 memoria persistente:** fase futura; Chroma nao e requisito do fluxo atual.
- **#36 providers/router/fallback:** fase futura, com fallback finito e observavel.
- **#37 observabilidade: parcial, manter aberta.** PR #49 entregou os artefatos basicos. Ainda e necessario demonstrar os criterios restantes, em particular recuperacao apos reinicio nas etapas principais, retencao/diagnostico e validacao operacional final. Nao habilitar 24/7.
- **#38 pipeline autodidata:** fase futura; depende de memoria, fontes permitidas e avaliacao reproduzivel.

## Proxima sequencia recomendada

1. Mergear esta atualizacao documental e fechar #31 apos revisao.
2. Decidir o escopo da quota de `workspace/`; criar uma issue dedicada se a quota for necessaria. So entao decidir se #30 pode ser fechada como concluida com essa limitacao aceita e documentada.
3. Completar #29, #33 e #34, com testes para expiracao/auditoria de aprovacao e correcao limitada do Reviewer/Quality Gate.
4. Validar os criterios restantes de #37 sem operacao 24/7.
5. Reavaliar #22 e #25 explicitamente; nao considerar PR fechada sem merge como evidencia de conclusao.
6. Avancar para #36, depois #35 e entao #38; manter #23/#24 bloqueadas ate os pre-requisitos.

## Bloqueios de seguranca

- Nao reiniciar, reconstruir ou substituir o container existente sem aprovacao operacional especifica.
- Nao iniciar ciclos do agente nem reaproveitar aprovacoes persistidas de issues anteriores durante validacao.
- Nao operar em modo 24/7 sem supervisao, nao fazer merge automatico e nao usar fallback ilimitado.
- Nao integrar OpenHands antes de concluir os pre-requisitos de seguranca/qualidade.
- Nao tratar status `complete` como prova suficiente de sucesso; exigir evidencias e revisao humana.

## Procedimento de retomada

1. Verificar `main`, issues abertas e PRs abertas.
2. Inspecionar container e checkout operacional sem modifica-los.
3. Trabalhar em clone/branch isolados.
4. Validar primeiro testes focados e depois a suite em Linux descartavel; executar `compileall`, `git diff --check` e validacao de Compose quando aplicavel.
5. Pedir aprovacao antes de aplicar qualquer mudanca a implantacao ativa.
6. Atualizar este roadmap e `docs/SESSION-CHECKPOINT.md` apos cada marco validado.

Estado persistente do agente: `BASTIAO_STATE_DIR`, normalmente `/var/lib/bastiao` no container e `./state` no host.
