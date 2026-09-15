# Roadmap do Bastiao Autodidata

Este documento registra a ordem de evolucao recomendada e o estado validado do
protocolo. A ordem evita ampliar a autonomia antes de existirem controles de
qualidade, recursos e retomada confiaveis.

## Estado validado

O fluxo atual possui:

- aprovacao humana antes da execucao;
- Planner deterministico com caminhos permitidos;
- workspace isolado e branch por issue;
- Executor com allowlist de ferramentas e caminhos;
- testes, diff check e Reviewer antes da PR;
- estado e metricas persistidos fora do workspace;
- retomada com checkpoint e erro anterior;
- publicacao via API do GitHub sem merge automatico.

O teste controlado da issue #43 foi concluido com sucesso. A execucao abriu a
PR #46 com exatamente um arquivo:

```python
HEALTH_MARKER = "ok"
```

As PRs #45 e #46 foram mergeadas manualmente. A #45 consolidou a retomada,
coleta de arquivos nao rastreados e extracao de caminhos em texto simples. A
#46 serviu como evidencia operacional de que o fluxo consegue limitar uma PR
ao escopo aprovado mesmo quando o modelo tenta acessar ou criar arquivos
incorretos.

## Proxima sequencia

### 1. Issue #34 — Quality Gate real — concluida nesta fase

Impedir a criacao de PR quando o resultado for apenas uma declaracao do modelo.
O gate deve:

- descobrir e executar testes relevantes;
- executar lint e type-check quando definidos;
- executar `git diff --check`;
- verificar arquivos alterados e criterios semanticos;
- registrar comando, saida, codigo de retorno e duracao;
- devolver falhas ao agente em uma quantidade limitada de tentativas;
- bloquear publicacao em caso de falha ou resultado inconclusivo;
- testar sucesso, falha e timeout do proprio Bastiao.

Implementacao entregue em `src/quality_gate.py`: o gate descobre pytest,
compileall, scripts `lint`/`typecheck` de `package.json` e `git diff --check`.
Cada comando tem timeout configuravel, captura limitada de saida, codigo de
retorno, duracao e estado de timeout. A publicacao e bloqueada com
`quality_gate_failed` quando qualquer check falha.

Validacao local desta fase: **32 testes passaram**.

### 2. Reforco de escopo e abortamento — concluida nesta fase

Esta etapa deve acompanhar ou preceder a implementacao de #34:

- rejeitar imediatamente qualquer `write` fora de `allowed_paths`;
- rejeitar planos seguros com `allowed_paths=[]`;
- abortar o ciclo apos uma violacao de escopo;
- nao permitir recuperacao apos alteracao proibida;
- registrar a acao bloqueada no relatorio;
- limitar arquivos e linhas modificadas.

Tambem deve ser avaliada a troca do protocolo textual de acoes por JSON
estruturado, especialmente para `write`, para preservar conteudo multilinha e
aspas sem ambiguidade.

Implementacao entregue:

- modo `strict_scope` impede qualquer escrita quando o Planner nao produziu
  caminhos permitidos;
- o runner rejeita planos sem escopo antes de iniciar o modelo;
- uma tentativa de escrita fora do escopo aborta imediatamente o SWE-agent;
- o ciclo registra `rejected_no_scope` ou `failed` sem criar commit ou PR;
- testes cobrem bloqueio de escopo vazio e abortamento imediato.

Validacao local desta fase: **35 testes passaram**.

### 3. Issue #30 — Limites do sandbox

Adicionar timeout por comando, limites de processos, memoria, CPU, arquivos
temporarios e tamanho de saida. O encerramento deve ser limpo, observavel e
testado. Isolamento de kernel completo fica fora desta etapa.

Implementacao parcial entregue nesta fase:

- timeout configuravel por comando;
- limite de comandos por tarefa;
- limite de saida capturada;
- limite de bytes por arquivo escrito;
- falhas de limite retornam erro explicito e impedem conclusao/publicacao.

CPU, memoria, processos filhos e limpeza de temporarios continuam pendentes
para uma segunda etapa da #30, pois exigem primitivas especificas do runtime ou
do container.

### 4. Issue #37 — Observabilidade operacional

Consolidar identificador por ciclo, metricas de latencia e consumo,
healthchecks de GitHub/Ollama/workspace/Chroma, relatorio resumido, retencao e
redaction de segredos, alem de testes de reinicio em cada etapa.

### 5. Issue #36 — Providers e fallback

Criar uma interface comum para providers, selecao por capacidade, timeout,
erros e fallback limitado. Nao permitir loops de fallback nem custos ou
latencias ilimitados. Cobrir o comportamento com provider falso.

### 6. Issue #35 — Memoria persistente

Integrar Chroma com categorias episodica, semantica, procedural e de projeto.
Registrar origem, versao, relevancia, expiracao e isolamento por projeto.
Falhas do Chroma devem possuir fallback explicito; memoria nao pode ser
requisito do fluxo de codigo antes disso.

### 7. Issue #38 — Pipeline autodidata

Somente depois das etapas anteriores: pesquisa com fontes permitidas,
evidencias, topicos, agenda, exercicios, avaliacao reproduzivel, lacunas e
revisao espacada. O agente nao deve afirmar que aprendeu sem evidencia
registrada.

## Bloqueios de seguranca

Enquanto as etapas acima nao forem concluidas e validadas:

- nao executar em modo 24/7 sem supervisao;
- nao fazer merge automatico;
- nao permitir instalacao automatica de dependencias;
- nao usar fallback ilimitado;
- nao integrar OpenHands;
- nao tratar `complete` como prova de sucesso;
- manter revisao humana antes do merge.

## Registro de retomada

Ao continuar o trabalho:

1. verificar o estado das issues #30, #34, #35, #36, #37 e #38;
2. confirmar que o container Bastiao esta parado;
3. criar um workspace limpo baseado no `main`;
4. aprovar explicitamente apenas a issue em teste;
5. executar a menor validacao possivel antes de abrir PR;
6. revisar manualmente a PR e os checks;
7. atualizar este documento com comandos, resultados e decisoes.

O estado persistente operacional fica no diretorio configurado por
`BASTIAO_STATE_DIR`, normalmente `/var/lib/bastiao` no container e `./state`
no host. Nao usar workspaces antigos para medir um novo ciclo.
