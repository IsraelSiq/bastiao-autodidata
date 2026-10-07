# Roadmap do Bastiao Autodidata

Este documento registra a ordem de evolucao recomendada, o estado verificado do protocolo e o ponto seguro de retomada.

## Estado da main em 2026-10-07

A `main` esta no commit `94e107b`. A PR #49 foi mergeada em 2026-10-07 e adicionou os incrementos de observabilidade da issue #37: identificador por ciclo, healthcheck, retry/backoff somente em leituras idempotentes, estado operacional, redaction/retencao e testes de recuperacao.

As issues #30 e #37 permanecem abertas no GitHub. Nao ha PR aberta no momento deste checkpoint. A validacao nesta retomada foi feita em clone/imagem descartaveis; a implantacao e o checkout local existentes no servidor foram preservados.

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

### 3. Issue #30 ? Limites do sandbox ? parcialmente concluida

Implementado: timeout por comando com encerramento de processos filhos, limite de comandos, limite de caracteres retornados, limite por arquivo escrito, diretorio temporario por tarefa, remocao de credenciais do ambiente, e limites opcionais POSIX de memoria/CPU.

A validacao encontrou uma lacuna: `communicate()` acumulava a saida completa do subprocesso antes de truncar a resposta. Em container descartavel com limite de 512 MiB, uma prova controlada capturou 32 MiB de stdout apesar do limite de caracteres da ferramenta. A busca de codigo tambem usava `subprocess.run(capture_output=True)` sem o ambiente sanitizado.

A branch de correcao substituiu essa captura por drenagem concorrente com limite em bytes por stream, continuou drenando para evitar pipe bloqueado, sinaliza truncamento e encaminhou a busca de codigo pelo executor sanitizado. A imagem da branch foi validada em container descartavel Linux, incluindo saida de 32 MiB, rlimit de CPU/memoria e a suite completa. Nenhuma alteracao foi aplicada ao servico ativo.

Ainda pendente para fechar #30: definir e validar limites operacionais de memoria/CPU/processos/disco no Compose; o Compose atual nao define `mem_limit`, `cpus` ou `pids_limit`, e nao limita disco de temporarios/workspace. Nao escolher valores de producao sem confirmar a capacidade e o perfil do servidor.

### 4. Issue #37 ? Observabilidade operacional ? implementada, validacao/revisao pendentes

A PR #49 entregou `cycle_id`, healthcheck read-only, retry/backoff limitado para leituras do GitHub, `status.json`, redaction, rotacao e testes de recuperacao/falha de dependencia. A suite e os healthchecks foram exercitados em clone/container descartavel.

A issue permanece aberta para revisao humana/merge e confirmacao operacional final. Nao iniciar operacao continua ou modo 24/7 antes disso.

## Proxima sequencia

1. Concluir testes Docker/runtime da branch de saida limitada e revisar a PR.
2. Resolver, com o operador, limites de recursos adequados para o Compose e o servidor antes de declarar #30 concluida.
3. Revisar/fechar #30 e #37 somente quando os respectivos criterios e evidencias estiverem satisfeitos.
4. Depois, avancar para #36 ? providers e fallback limitado, sem loops ou custos ilimitados.
5. Em seguida, #35 ? memoria persistente, com isolamento por projeto e fallback explicito.
6. Por ultimo, #38 ? pipeline autodidata, com fontes, evidencias e avaliacao reproduzivel.

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
