# Roadmap do Bastiao Autodidata

Este documento registra a ordem de evolucao recomendada, o estado verificado do protocolo e o ponto seguro de retomada.

## Estado da main em 2026-10-07

A PR #50 foi mergeada em 2026-10-07; a `main` usada como base para a retomada esta no commit `95f1f87`. A PR #50 limitou a captura de stdout/stderr antes de reter os dados e encaminhou a busca de codigo pelo executor sanitizado. A PR #49 havia adicionado incrementos de observabilidade da issue #37.

As issues #30 e #37 continuam abertas no GitHub; nao ha PR aberta para esta branch. A validacao da #50 ocorreu em clone/imagem descartaveis. A implantacao e o checkout local existentes no servidor foram preservados.

## O que ja foi validado

- PR #49 mergeada na `main`; a suite no container descartavel passou com 77 testes e `compileall` passou.
- `docker compose config --quiet` passou.
- A suite focada de limites, health, redaction e retry passou com 32 testes sob limites Docker de 512 MiB e 1 CPU.
- Healthchecks somente leitura confirmaram Ollama, ChromaDB e workspace acessiveis. A sonda GitHub nao recebeu credenciais e, portanto, nao foi validada como conectada.
- A suite completa local da branch de correcao passou com 78 testes e 2 skips; `compileall` e `git diff --check` passaram.
- Nenhum teste ou comando iniciou um ciclo do agente, atualizou aprovacoes, reiniciou o container ativo ou publicou alteracoes no workspace de producao.

## Ponto atual

### 1. Issue #34 ? Quality Gate real ? concluida

O gate em `src/quality_gate.py` executa verificacoes aplicaveis, registra retorno, duracao, timeout e saida limitada, e bloqueia publicacao quando falha.

### 2. Reforco de escopo e abortamento ? concluido

`strict_scope` rejeita planos sem caminhos permitidos, bloqueia escritas fora do escopo e aborta imediatamente apos violacao.

### 3. Issue #30 ? Limites do sandbox ? implementacao validada em container, gap de quota pendente

Ja existente: timeout por comando com encerramento da arvore de processos, limite de comandos e de saida, limite por arquivo pela ferramenta `write`, diretorio temporario por tarefa, remocao de credenciais do ambiente, rlimits POSIX opcionais, e captura limitada antes de acumular stdout/stderr (PR #50).

Nesta branch `fix/issue-30-compose-limits`, o `.env.example` e o Compose propoem 4 GiB de memoria, 2 CPUs, 256 PIDs para o container Bastiao, `/tmp` tmpfs de 512 MiB, e limites por comando POSIX de 2048 MiB de espaco de enderecamento e 45 segundos de CPU. O limite de CPU fica abaixo do timeout de comando padrao (60 s), para que possa ser observado antes do timeout de parede. O diagnostico diferencia `SIGXCPU` e `MemoryError` e o Quality Gate registra o tipo de limite atingido.

`pids_limit` e um teto agregado do container, nao um cgroup por issue. O fluxo atual executa uma issue por vez, mas filhos/threads de um comando compartilham esse teto. `/tmp` fica limitado a 512 MiB; o volume bind-mounted `workspace/` nao tem quota agregada. `BASTIAO_MAX_WRITE_BYTES` cobre a ferramenta `write`, mas nao impede comandos arbitrarios de escrever diretamente no workspace. Essa limitacao precisa permanecer explicita e exige uma decisao de quota/politica do host antes de considerar #30 totalmente fechada.

A validacao encontrou uma lacuna: `communicate()` acumulava a saida completa do subprocesso antes de truncar a resposta. Em container descartavel com limite de 512 MiB, uma prova controlada capturou 32 MiB de stdout apesar do limite de caracteres da ferramenta. A busca de codigo tambem usava `subprocess.run(capture_output=True)` sem o ambiente sanitizado.

A branch de correcao substituiu essa captura por drenagem concorrente com limite em bytes por stream, continuou drenando para evitar pipe bloqueado, sinaliza truncamento e encaminhou a busca de codigo pelo executor sanitizado. A imagem da branch foi validada em container descartavel Linux, incluindo saida de 32 MiB, rlimit de CPU/memoria e a suite completa. Nenhuma alteracao foi aplicada ao servico ativo.

Validacao da branch atual: suite focada Windows `39 passed, 2 skipped`; suite completa Windows `82 passed, 2 skipped`; suite completa em Docker Linux `84 passed`; `compileall` passou em Windows e Docker; `git diff --check` passou; `docker compose --profile agent config --quiet` passou no servidor descartavel (com aviso preexistente de `version` obsoleto). Medicao dentro do container descartavel confirmou `memory.max=4294967296`, `cpu.max=200000 100000` (2 CPUs), `pids.max=256` e `/tmp` com 536870912 bytes. A camada de teste instalou Pydantic somente na imagem descartavel; nenhuma dependencia do projeto foi alterada.

Os limites implementados ainda nao foram aplicados ao servico ativo. Permanece sem quota agregada o volume bind-mounted `workspace/`; `pids_limit` continua sendo um teto de container, nao por issue. A issue #30 deve ficar aberta ate que haja politica de disco para o workspace e revisao/merge das evidencias.

### 4. Issue #37 ? Observabilidade operacional ? implementada, validacao/revisao pendentes

A PR #49 entregou `cycle_id`, healthcheck read-only, retry/backoff limitado para leituras do GitHub, `status.json`, redaction, rotacao e testes de recuperacao/falha de dependencia. A suite e os healthchecks foram exercitados em clone/container descartavel.

A issue permanece aberta para revisao humana/merge e confirmacao operacional final. Nao iniciar operacao continua ou modo 24/7 antes disso.

### Autonomia por issue (em validacao nesta branch)

A aprovacao inicial por issue autoriza leitura, alteracoes somente nos caminhos
do Planner, validacao/testes e commits locais apenas na branch
`bastiao/issue-N`. Quality Gate, validacao de diff e Reviewer continuam
obrigatorios antes da publicacao automatica da PR; merge continua manual.
Instalacao de dependencias, execucao JavaScript/Node arbitraria e inspecao Docker
ainda exigem aprovacao especifica; scripts padrao de teste/qualidade sao liberados.
Esta mudanca esta em `feat/issue-29-human-approval`,
nao foi implantada no servidor e nao conclui a fase de providers/inteligencia
descrita pela issue #31.

## Proxima sequencia

1. Revisar se a politica de quota agregada do bind mount `workspace/` e necessaria antes de fechar #30; documentar explicitamente se ficar fora do escopo de implementacao.
2. Abrir/revisar PR com as evidencias Linux/Docker; nao alterar o container ativo sem aprovacao operacional especifica.
3. Revisar/fechar #30 e #37 somente apos os requisitos e evidencias serem aceitos.
4. Depois, avancar para #36 ? providers e fallback limitado, sem loops ou custos ilimitados.
5. Em seguida, #35 ? memoria persistente, com isolamento por projeto e fallback explicito.
6. Por ultimo, #38 ? pipeline autodidata, com fontes, evidencias e avaliacao reproduzivel.
5. Depois, avancar para #36 ? providers e fallback limitado, sem loops ou custos ilimitados.
6. Em seguida, #35 ? memoria persistente, com isolamento por projeto e fallback explicito.
7. Por ultimo, #38 ? pipeline autodidata, com fontes, evidencias e avaliacao reproduzivel.

## Bloqueios de seguranca

- nao reiniciar, reconstruir ou substituir o container existente durante validacao;
- nao iniciar ciclo do agente nem reaproveitar aprovacao persistida de issue anterior;
- nao operar em modo 24/7 sem supervisao;
- nao fazer merge automatico;
- nao instalar dependencias automaticamente;
- nao usar fallback ilimitado;
- nao integrar OpenHands;
- nao tratar `complete` como prova de sucesso;
- manter revisao humana antes do merge.

## Procedimento de retomada

1. verificar a `main`, issues e PRs abertas;
2. inspecionar o estado do container e do checkout de producao sem modifica-los;
3. trabalhar em clone/branch isolados;
4. executar a suite e a validacao Docker em container descartavel;
5. pedir aprovacao antes de aplicar mudancas na implantacao ativa;
6. atualizar este documento e o checkpoint apos cada marco validado.

Estado persistente do agente: `BASTIAO_STATE_DIR`, normalmente `/var/lib/bastiao` no container e `./state` no host.
