# Roadmap do Bastiao Autodidata

Atualizado em 2026-10-08. Estado verificado no servidor (`bastiao-autodidata:e754e0b`, 122 testes passando).

## Onde estamos

**Fase 2 (autonomia supervisionada) — ~70% concluida. Autodidatismo (Fases 3 e 4) ainda nao iniciado.**

Estimativa geral ate o "Bastiao autodidata": **~45%**. A infraestrutura de seguranca e o runner issue → PR estao prontos; o que falta e a inteligencia (planejamento melhor, router de modelos), a memoria e o ciclo de aprendizado.

| Fase | Tema | Status | Evidencia |
| ---- | ---- | ------ | --------- |
| 0 | Implantacao, WebUI, acesso remoto | Concluida | Servico em Docker, WebUI na porta 3000 |
| 0.5 | Sandbox e seguranca (#30, #29) | ~90% | Limites de memoria/CPU/PIDs/tmp, aprovacao por issue e por acao, redaction. Falta quota de `workspace/` |
| 1 | Qualidade (#33 Reviewer, #34 Quality Gate) | ~70% | Gate e revisao deterministica ativos; falta loop de correcao limitado |
| 2 | Autonomia issue → branch → teste → PR (#25, #36) | ~70% | PR #54 gerada de ponta a ponta; falhas de escopo/branch corrigidas (PR #55). Falta provar em varias issues e router/fallback de providers |
| 3 | Memoria persistente (#35) | 0% | Nao iniciada |
| 4 | Pipeline autodidata: pesquisar, estudar, avaliar (#38) | ~5% | Apenas `study_plan.py` |
| 5 | Observabilidade 24/7 (#37) | ~50% | status.json, metricas, healthchecks; falta recuperacao apos reinicio validada |

SWE-agent (#22), OpenHands (#23) e modelo hibrido (#24) seguem adiados.

## Definicao de "Bastiao autodidata" (criterio de pronto)

1. Pega issues sozinho, implementa em branch propria, testa e abre PR; merge continua humano.
2. Taxa de sucesso medida em pelo menos 10 issues reais consecutivas (PR com testes verdes, sem retrabalho manual em >=60%).
3. Registra licoes de cada tentativa (erro, causa, correcao) em memoria persistente e as consulta antes de planejar.
4. Estuda fontes permitidas, gera plano de estudo e avalia o proprio desempenho de forma reproduzivel.
5. Opera continuamente com limites, observabilidade e recuperacao apos reinicio.

## Proximos marcos

### M1 — Autonomia confiavel (1–2 semanas)
- Mergear PR #55 (validacao Python no escopo, extrator de caminhos, branch de retry) e corrigir newline na PR #54.
- Planner para issues sem caminhos explicitos (hoje escopo vazio nao produz patch).
- CI nas PRs geradas (checks de testes).
- Rodar 5 issues pequenas autorizadas uma a uma e registrar taxa de sucesso.
- Loop de correcao limitado do Reviewer/Quality Gate (#33, #34).

### M2 — Modelos e resiliencia (1–2 semanas)
- Router de providers com fallback finito e observavel (#36).
- Validar recuperacao apos reinicio (#37).
- Decidir quota de `workspace/` e fechar #30.

### M3 — Memoria (2–3 semanas)
- Memoria persistente de licoes por issue/repo (#35); comecar com SQLite/JSONL, Chroma so se necessario.
- Planner e Reviewer consultam a memoria antes de agir.

### M4 — Pipeline autodidata (3–4 semanas)
- Fontes permitidas, coleta, resumo, plano de estudo e avaliacao reproduzivel (#38).
- Auto-geracao de issues de melhoria a partir das licoes, sempre com aprovacao humana.

### Depois
- #22, #23, #24 so se M1–M3 mostrarem necessidade.

**Estimativa total: ~7–11 semanas de trabalho ate o criterio de pronto**, dependendo da taxa de sucesso medida em M1.

## Regras que permanecem

- Merge sempre manual; nenhuma operacao 24/7 sem supervisao.
- Aprovacao por issue (`approvals.json`, hoje vazia) ate M1 provar a taxa de sucesso; depois pode-se ampliar o escopo autorizado.
- Fallback de providers sempre finito.
- `complete` nao e prova de sucesso: exigir testes, evidencias e revisao.
- Nao substituir o container sem manter rollback (`bastiao-autodidata-rollback-20261008`).

## Procedimento de retomada

1. Verificar `main`, issues e PRs abertas.
2. Inspecionar container e `state/` sem modifica-los.
3. Trabalhar em clone/branch isolados; rodar a suite na imagem Docker.
4. Atualizar este roadmap e `docs/SESSION-CHECKPOINT.md` a cada marco validado.
