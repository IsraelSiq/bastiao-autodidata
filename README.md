# Bastiao Autodidata

Seu assistente pessoal de estudos com IA! Crie planos de estudo personalizados, execute exercicios e acompanhe seu progresso.

## Features

- **Planos Personalizados**: Gera curriculos completos com IA (GPT-4o, Claude, etc)
- **Execucao Segura**: Sandbox para rodar codigo Python e comandos shell
- **Progress Tracking**: Acompanha seu progresso automaticamente
- **Interface CLI**: Menu interativo facil de usar
- **Multi-Modelo**: Suporta GPT-4o, Claude, Llama, e mais via OmniRoute

## Instalacao

### 1. Clone o repositorio

```bash
git clone https://github.com/IsraelSiq/bastiao-autodidata.git
cd bastiao-autodidata
```

### 2. Crie o ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
```

### 3. Instale as dependencias

```bash
pip install -r requirements.txt
```

### 4. Configure o OmniRoute

Crie um arquivo `.env` na raiz:

```bash
OMNIROUTE_BASE_URL=http://localhost:20128
DEFAULT_MODEL=auto/best-fast
```

## Uso

### Criar Plano de Estudo

```bash
python -m src.cli plan "Python" -l iniciante -o "Aprender Python para dados" -H 2
```

### Iniciar Sessao de Estudo

```bash
python -m src.cli study
```

### Ver Progresso

```bash
python -m src.cli progress
```

### Chat Direto

```bash
python -m src.cli chat "Ola! Qual seu nome?"
```

## Estrutura do Projeto

```
bastiao-autodidata/
  src/
    orchestrator.py    # Interface com LLMs
    planner.py         # Planejador de estudos
    study_plan.py      # Gerenciador de planos
    sandbox.py         # Sandbox de execucao
    executor.py        # Executor de tarefas
    task_runner.py     # Runner de tarefas
    cli.py             # Interface CLI
    prompts/           # Templates de prompts
  data/                # Planos e checkpoints
  tests/               # Testes unitarios
  README.md            # Este arquivo
```

## Arquitetura

### Fases do Projeto

| Fase | Descricao | Status |
|------|-----------|--------|
| Fase 1 | Setup & Infra (OmniRoute, venv, .env) | OK |
| Fase 2 | Core do Agente (Orchestrator, Chat) | OK |
| Fase 3 | Planejamento (Planner, StudyPlan) | OK |
| Fase 4 | Executor (Sandbox, TaskRunner) | OK |
| Fase 5 | Interface CLI (Menu interativo) | OK |

## Comandos da CLI

| Comando | Descricao | Exemplo |
|---------|-----------|----------|
| plan | Criar plano de estudo | `bastiao plan "Python"` |
| study | Iniciar sessao de estudo | `bastiao study` |
| progress | Ver progresso | `bastiao progress` |
| chat | Chat direto com IA | `bastiao chat "Ola"` |

## Exemplo de Uso

### 1. Criar Plano

```bash
python -m src.cli plan "Machine Learning" -l intermediario -H 3
```

### 2. Estudar

```bash
python -m src.cli study
```

Menu interativo:
```
Iniciando sessao de estudo

Plano: Machine Learning
Topicos: 12

[ ] 1. Introducao ao Machine Learning
[ ] 2. Algebra Linear para ML
...

Opcoes:
  [1-12] Estudar topico
  [p] Progresso
  [q] Sair

Escolha: 1
```

### 3. Ver Progresso

```bash
python -m src.cli progress
```

Output:
```
Progresso dos Estudos

Plano: Machine Learning
  Progresso: 25%
  Topicos: 3/12
  Horas: 15/60
```

## Desenvolvimento

### Rodar Testes

```bash
python -m pytest tests/
```

## Contribuicao

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add some AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Pull Request

## License

MIT License

---

**Feito com  por IsraelSiq**
