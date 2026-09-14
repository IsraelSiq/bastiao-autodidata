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
