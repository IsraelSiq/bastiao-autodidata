# 🤖 Bastiao Autodidata

**Agente de IA autodidata que aprende sozinho.**

Um agente autô¡³¬nomo que planeja, executa e avalia seu prÃ³prio aprendizado usando LLMs (GitHub Models + Ollama) e RAG.

---

## 🎯 Objetivo

Criar um agente que:

1. **Planeja** um currÃ¬culo de estudos (ex: Python, ML, etc.)
2. **Executa** tarefas (lÃª docs, escreve cÃ³digo, roda testes)
3. **Avalia** seu prÃ³prio desempenho (testes, auto-crÃ¬tica)
4. **Ajusta** o plano com base nos resultados

---

## 🚀 Arquitetura

```
┌─────────────────┐
│   User (VocÃª)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ CLI / Dashboard │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐      ┌──────────────────┐
│  Orchestrator   │─────▶│  OmniRoute   │─────▶│ GitHub Models    │
│  (Python)       │      │  (Proxy)     │      │ Ollama Local     │
└────────┬────────┘      └──────────────┘      └──────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Planejador → Executor → Avaliador      │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  RAG: Chroma    │
│  + Docs         │
└─────────────────┘
```

---

## 📋 Roadmap

### ✅ Fase 1: Setup & Infra (COMPLETA)

- [x] Criar repo pÃºblico no GitHub
- [x] Estrutura de pastas
- [x] README.md
- [x] requirements.txt
- [x] .gitignore
- [x] Configurar VS Code + SSH pro host
- [x] Ambiente Python (venv)
- [x] Docker Compose (Ollama + Chroma)

### 🟡 Fase 2: Core do Agente (EM ANDAMENTO)

- [x] Orchestrator (Python, chama OmniRoute)
- [ ] Config de providers (GitHub + Ollama) ← **VOCÃª ESTÃ¡ AQUI**
- [x] Sistema de prompts (templates)
- [x] Logging e mÃ©tricas bÃ¡sicas

### ⏳ Fase 3: Planejamento de Estudos

- [ ] Planejador de currÃ¬culo (GPT-4o)
- [ ] Quebra de tÃ³picos em tarefas
- [ ] Agenda de estudos (cronograma)
- [ ] Progress tracking

### ⏳ Fase 4-8: (Ver issues no GitHub)

---

## 🛠 Como Rodar

### 1. Clone o repo

```bash
git clone https://github.com/IsraelSiq/bastiao-autodidata.git
cd bastiao-autodidata
```

### 2. Crie o ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate  # Windows
```

### 3. Instale as dependÃªncias

```bash
pip install -r requirements.txt
```

### 4. Suba os serviÃ§os (Ollama + Chroma)

```bash
docker-compose up -d
```

### 5. Configure o OmniRoute (NO SEU PC LOCAL)

O OmniRoute deve estar rodando no seu **PC local** (nÃ£o no host remoto).

```bash
# No seu PC (Windows/PowerShell)

# Inicia o OmniRoute
omniroute serve --log

# Adiciona GitHub Models (OAuth ou API key)
omniroute providers add github --credential ghp_... --name github

# Adiciona Ollama (aponta pro host remoto)
omniroute providers add ollama --credential "" --base-url http://SEU_HOST:11434 --name ollama-remote

# Testa
omniroute test github
omniroute test ollama
```

### 6. Configura VariÃ¡veis de Ambiente

No **host remoto** (VPS), cria `.env`:

```bash
# No host remoto
cd bastiao-autodidata
nano .env
```

ConteÃºdo do `.env`:

```env
# OmniRoute (URL do seu PC local)
OMNIROUTE_URL=http://SEU_PC_LOCAL:20128
OMNIROUTE_API_KEY=sua_api_key_aqui

# Modelo padrÃ£o
DEFAULT_MODEL=github/gpt-4o-mini
```

### 7. Testa o Orchestrator

```bash
# No host remoto
source venv/bin/activate
python src/orchestrator.py
```

Se funcionar, vai aparecer:

```
Testing connection...
Available models:
  - github/gpt-4o-mini
  - ollama/qwen2.5-coder:7b
  ...

Testing chat...
Response: OlÃ¡! Sou o BastiÃ£o Autodidata.
```

---

## 📂 Estrutura de Pastas

```
bastiao-autodidata/
â¬¤ src/               # CÃ³digo fonte
  â ¬œ orchestrator.py  # Orchestrator principal
  â ¬œ logging_config.py # Config de logging
  â ¬œ prompts/         # Templates de prompts
  â ¬œ __init__.py
â¬¤ tests/             # Testes
â¬¤ docs/              # DocumentaÃ§Ã£o
â¬¤ data/              # Dados (RAG, vector DB)
â¬¤ notebooks/         # Jupyter notebooks
â¬¤ config/            # ConfiguraÃ§Ãµes
â¬¤ scripts/           # Scripts utilitÃ¡rios
â¬¤ docker-compose.yml # Docker Compose
â¬¤ requirements.txt   # DependÃªncias Python
â¬¤ README.md          # Este arquivo
```

---

## �ª Testes

### Testar ConexÃ£o com OmniRoute

```bash
# No host remoto
python -c "
from src.orchestrator import BastiaoOrchestrator
orch = BastiaoOrchestrator()
print('Models:', len(orch.list_models()))
print('Connection OK!')
"
```

### Testar Chat

```bash
python -c "
from src.orchestrator import BastiaoOrchestrator, ChatMessage
orch = BastiaoOrchestrator()
messages = [
    ChatMessage(role='user', content='OlÃ¡! Qual ÃƒÂ© seu nome?')
]
response = orch.chat(messages)
print('Response:', response)
"
```

---

## 🔧 Troubleshooting

### Erro: "Connection refused"

- Verifica se OmniRoute tÃ¡ rodando no PC local: `omniroute serve --log`
- Verifica se firewall tÃ¡ bloqueando porta 20128
- No host remoto, usa URL correta: `http://SEU_PC_LOCAL:20128`

### Erro: "401 Unauthorized"

- API key errada ou faltando
- Adiciona no `.env`: `OMNIROUTE_API_KEY=sua_key`

### Erro: "Model not found"

- Modelo nÃ£o existe no OmniRoute
- Lista modelos: `omniroute models`
- Usa nome correto: `github/gpt-4o-mini`, `ollama/qwen2.5-coder:7b`

---

## ðŸ“š DocumentaÃ§Ã£o

- [Issues no GitHub](https://github.com/IsraelSiq/bastiao-autodidata/issues)
- [Roadmap Completo](https://github.com/IsraelSiq/bastiao-autodidata/issues?q=label%3Aroadmap)

---

## ðŸ”„ LicenÃ§a

MIT

---

**Feito com â™  por IsraelSiq**
