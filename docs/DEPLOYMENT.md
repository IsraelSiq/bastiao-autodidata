# Implantacao

## Pre-requisitos

- Docker Engine com Compose v2;
- token GitHub armazenado fora do Git;
- modelo instalado no Ollama;
- repositorio alvo clonado em uma pasta exclusiva para o agente;
- permissao de rede entre o container Bastiao e o Ollama.

## Configuracao inicial

```bash
cp .env.example .env
```

Edite `.env` e preencha `GITHUB_TOKEN`. Mantenha `GITHUB_OWNER` e
`GITHUB_REPO` apontando para o repositorio que deve receber as pull requests.
Nao coloque tokens, senhas ou URLs privadas em arquivos rastreados.

Mantenha a aprovacao humana habilitada:

```env
BASTIAO_REQUIRE_APPROVAL=true
BASTIAO_APPROVAL_FILE=/var/lib/bastiao/approvals.json
BASTIAO_REQUIRE_ACTION_APPROVAL=false
BASTIAO_ACTION_APPROVAL_FILE=/var/lib/bastiao/action-approvals.json
BASTIAO_ACTION_AUDIT_FILE=/var/lib/bastiao/action-approval-audit.jsonl
BASTIAO_APPROVAL_REQUEST_TTL_SECONDS=86400
BASTIAO_ACTION_APPROVAL_TTL_SECONDS=3600
BASTIAO_STATE_DIR=/var/lib/bastiao
BASTIAO_TEMPERATURE=0.2
```

Antes de executar uma issue, escreva os numeros aprovados em
`state/approvals.json`, por exemplo:

```json
[43]
```

Uma aprovacao explicita da issue autoriza o ciclo completo daquela issue,
incluindo escritas no escopo do Planner, commits locais na branch dedicada e
publicacao apos Quality Gate e Reviewer. Merge continua manual. Instalacao de
dependencias, execucao JavaScript/Node arbitraria e inspecao Docker ainda exigem
aprovacao individual. Configure `BASTIAO_REQUIRE_ACTION_APPROVAL=true` para exigir
aprovacao adicional tambem para outras acoes sensiveis e para a publicacao.
Scripts padrao allowlisted de teste e qualidade (`npm test`, `npm run test`,
`test:unit`, `test:vitest`, `lint`, `typecheck` e `check`) nao pedem aprovacao
adicional.
O arquivo de issues aprovadas e persistente: remova o numero da issue em
`state/approvals.json` para revogar a autorizacao e impedir novas tentativas.

Para revisar e decidir solicitacoes adicionais no container:

```bash
docker compose --profile agent exec bastiao python -m src.action_approval list
docker compose --profile agent exec bastiao python -m src.action_approval approve REQUEST_ID --approver "Seu nome"
docker compose --profile agent exec bastiao python -m src.action_approval deny REQUEST_ID
```

Cada aprovacao e de uso unico, expira e corresponde ao fingerprint exato da
acao/arquivos. Aprovar nao executa imediatamente: a tarefa retoma no proximo ciclo.
Solicitacoes e auditoria persistem em `state/`. Nao habilite modo sem aprovacao
por issue durante a operacao normal.

Baixe o modelo no Ollama:

```bash
docker compose up -d ollama
docker exec bastiao-ollama ollama pull llama3.2:3b
```

## Subida do agente

```bash
docker compose --profile agent build bastiao
docker compose --profile agent up -d bastiao
docker compose --profile agent ps
```

Valide os logs:

```bash
docker compose --profile agent logs --tail=100 bastiao
```

O container deve permanecer `Up`. O servico usa `restart: on-failure:3`, portanto
falhas repetidas nao entram em um loop infinito de reinicio.

Valide tambem os dados persistentes:

```bash
cat state/approvals.json
cat state/action-approvals.json
tail -n 20 state/action-approval-audit.jsonl
find state/tasks -maxdepth 1 -type f -print
tail -n 20 state/metrics/cycles.jsonl
```

## Atualizacao

1. Pare o agente para evitar um ciclo durante a atualizacao.
2. Atualize o codigo e o arquivo de configuracao sem expor o `.env`.
3. Reconstrua a imagem.
4. Inicie o agente e valide os logs.

```bash
docker compose --profile agent stop bastiao
docker compose --profile agent build --no-cache bastiao
docker compose --profile agent up -d bastiao
docker compose --profile agent ps
```

Nao execute `docker compose down -v` em uma atualizacao normal: isso remove os
volumes persistentes do Ollama e do ChromaDB.

## Backup e recuperacao

O codigo do repositorio alvo permanece no GitHub. Os volumes locais contem
modelos do Ollama e dados do ChromaDB. Faca backup desses volumes conforme a
politica operacional do servidor.

Para recuperar o agente, restaure o workspace limpo, valide `.env` e repita a
subida descrita acima. Nunca restaure um workspace com credenciais ou alteracoes
nao revisadas como se fosse uma branch limpa.
