# Seguranca

## Modelo de ameacas

O modelo pode produzir comandos e conteudo incorretos. O agente trata a resposta
como entrada nao confiavel e aplica controles antes de tocar no workspace ou no
GitHub. Isso reduz risco, mas nao substitui revisao humana.

## Controles implementados

- `Path` absoluto e traversal sao rejeitados.
- A execucao usa lista de argumentos com `shell=False`.
- Acoes de terminal possuem allowlist e timeout.
- A coleta de arquivos exclui `.env` e conteudo de `.git`.
- Diffs com muitas remocoes e poucas adicoes sao rejeitados.
- Falha de testes impede a publicacao.
- A aprovacao humana e exigida por padrao antes de iniciar a issue.
- O Reviewer valida escopo, diff, sintaxe Python e requisitos simples de
  constantes antes da criacao da pull request.
- Checkpoints e metricas ficam fora do workspace do repositorio.
- Branches sao criadas a partir de `origin/main`.
- O agente abre pull requests, mas nao faz merge.
- O token fica fora da imagem por meio de `env_file` e `.dockerignore`.

## Credenciais

Use um fine-grained token dedicado ao repositorio. Conceda somente as
permissoes necessarias para ler issues e publicar branches, commits e pull
requests. Nao reutilize token de administrador ou credencial pessoal ampla.

Nunca:

- commite `.env`;
- cole tokens em issues, logs ou prompts;
- inclua segredos no contexto enviado ao modelo;
- publique o conteudo de `GITHUB_TOKEN`;
- use o mesmo token em servidores nao confiaveis.

Se um token for exposto, revogue-o imediatamente no GitHub e gere outro.

## Limites conhecidos

O agente ainda pode criar uma mudanca semanticamente errada que passe por
`compileall` ou por testes insuficientes. O Reviewer cobre requisitos simples
e explicitos, mas nao substitui uma revisao humana profunda nem uma segunda
avaliacao por modelo independente.

O comando `search` usa uma ferramenta externa de busca disponivel no ambiente;
o comando `run` continua limitado pelo nome do executavel, mas nao deve ser
considerado um sandbox de nivel de kernel.
