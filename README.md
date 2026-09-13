# 🤖 Bastiao Autodidata

**Agente de IA autodidata que aprende sozinho.**

Um agente autô¡³¬nomo que planeja, executa e avalia seu prÃ³prio aprendizado usando LLMs (GitHub Models + Ollama) e RAG.

---

## ðŸŽ“ Objetivo

Criar um agente que:

1. **Planeja** um currÃ¬culo de estudos (ex: Python, ML, etc.)
2. **Executa** tarefas (lÃª docs, escreve cÃ³digo, roda testes)
3. **Avalia** seu prÃ³prio desempenho (testes, auto-crÃ¬tica)
4. **Ajusta** o plano com base nos resultados

---

## ðŸš€ Arquitetura

```
â¬¤ User (VocÃª)
   â†“
[CLI / Dashboard]
   â†“
[Orchestrator] â†” [OmniRoute] â†” [GitHub Models / Ollama]
   â†“
[Planejador] â†’ [Executor] â†’ [Avaliador]
   â†“
[RAG: Chroma + Docs]
```

---

## ðŸ“‹ Roadmap

### Fase 1: Setup & Infra (Semana 1)

- [x] Criar repo pÃºblico no GitHub
- [ ] Estrutura de pastas
- [x] README.md
- [x] requirements.txt
- [x] .gitignore
- [ ] Configurar VS Code + SSH pro host
- [ ] Ambiente Python (venv)
- [ ] Docker Compose (Ollama + Chroma)

### Fase 2: Core do Agente (Semana 2)

- [ ] Orchestrator (Python, chama OmniRoute)
- [ ] Config de providers (GitHub + Ollama)
- [ ] Sistema de prompts (templates)
- [ ] Logging e mÃ©tricas bÃ¡sicas

### Fase 3: Planejamento de Estudos (Semana 3)

- [ ] Planejador de currÃ¬culo (GPT-4o)
- [ ] Quebra de tÃ³picos em tarefas
- [ ] Agenda de estudos (cronograma)
- [ ] Progress tracking

### Fase 4: Executor de Tarefas (Semana 4)

- [ ] Runner de cÃ³digo (sandbox)
- [ ] Test runner (pytest)
- [ ] Code reviewer (LLM)
- [ ] Auto-correÃ§Ã£o

### Fase 5: RAG + MemÃ³ria (Semana 5)

- [ ] Chroma DB local
- [ ] IngestÃ£o de docs (PDF, MD)
- [ ] Retrieval (busca contexto)
- [ ] MemÃ³ria de longo prazo

### Fase 6: AutoavaliaÃ§Ã£o (Semana 6)

- [ ] Testes de conhecimento
- [ ] MÃ©tricas de aprendizado
- [ ] Auto-crÃ¬tica (LLM avalia LLM)
- [ ] Ajuste de plano

### Fase 7: Interface (Semana 7)

- [ ] CLI (`bastiao learn python`)
- [ ] Dashboard (Streamlit)
- [ ] VisualizaÃ§Ã£o de progresso
- [ ] Logs e relatÃ³rios

### Fase 8: Autonomia (Semana 8)

- [ ] Auto-melhoria (ajusta plano)
- [ ] Multi-agente (professor, aluno, avaliador)
- [ ] PersistÃªncia de estado
- [ ] Deploy em produÃ§Ã£o

---

## ðŸ›  Como Rodar

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

### 5. Configure o OmniRoute

No seu PC local (com OmniRoute instalado):

```bash
omniroute providers add github --credential ghp_... --name github
omniroute providers add ollama --credential "" --base-url http://localhost:11434 --name ollama-local
```

---

## ðŸ“‚ Estrutura de Pastas

```
bastiao-autodidata/
â¬¤ src/               # CÃ³digo fonte
â¬¤ tests/             # Testes
â¬¤ docs/              # DocumentaÃ§Ã£o
â¬¤ data/              # Dados (RAG, vector DB)
â¬¤ notebooks/         # Jupyter notebooks
â¬¤ config/            # ConfiguraÃ§Ãµes
â¬¤ scripts/           # Scripts utilitÃ¡rios
```

---

## ðŸ”„ LicenÃ§a

MIT

---

**Feito com â™  por IsraelSiq**
