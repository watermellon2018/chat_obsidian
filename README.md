# Obsidian MCP Chat

An AI assistant that uses your **Obsidian vault as the primary source of truth**. Instead of relying on the model's general knowledge, it actively searches and reads your notes before answering — so every response is grounded in what you've actually written.

---

## Features

- **MCP Chat** — Agentic mode: the model calls tools to search and read your vault, follows links, finds backlinks, and browses tags before generating an answer.
- **RAG Chat** — Semantic search mode: your notes are indexed with FAISS; relevant chunks are injected into the prompt for fast, context-rich answers.
- **Flashcard Generation** — Auto-generates Q&A flashcards from vault content. Specify a topic or generate randomly.
- **Two model backends** — [OpenRouter](https://openrouter.ai) (cloud, any model) or [Ollama](https://ollama.com) (local, private).
- **Multilingual UI** — English and Russian.
- **No build step** — Frontend is plain HTML + Alpine.js + Tailwind via CDN.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Browser  (Alpine.js SPA)                        │
│  WebSocket /ws  ·  WebSocket /ask  ·  GET /flashcard/batch │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│  FastAPI backend                                 │
│  ┌──────────────┐  ┌────────────────────────┐   │
│  │ Orchestrator │  │  RAG Chain             │   │
│  │ (MCP loop)   │  │  FAISS + LangChain     │   │
│  └──────┬───────┘  └────────────────────────┘   │
│         │ stdio                                  │
│  ┌──────▼──────────────────────────────────┐    │
│  │  MCP Server (subprocess)                │    │
│  │  search_notes · read_note · list_notes  │    │
│  │  search_by_tag · get_backlinks          │    │
│  └──────────────────────┬──────────────────┘    │
└─────────────────────────┼───────────────────────┘
                          │ read-only
                 ┌────────▼────────┐
                 │  Obsidian Vault │
                 │  (Markdown)     │
                 └─────────────────┘
```

---

## Local Setup

### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | |
| pip | any | |
| Obsidian vault | — | A folder of `.md` files |
| OpenRouter API key **or** Ollama | — | See below |

---

### Step 1 — Clone and install dependencies

```bash
git clone https://github.com/your-username/chat_obsidian.git
cd chat_obsidian
pip install -r requirements.txt
```

---

### Step 2 — Configure environment

Copy the example and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set:

```env
# Choose your model backend: openrouter | ollama
MODEL_BACKEND=openrouter

# --- OpenRouter (recommended for cloud) ---
# Get a free key at https://openrouter.ai/keys
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=deepseek/deepseek-chat-v3-0324  # any model from openrouter.ai/models

# --- Ollama (local, no internet required) ---
# OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M
# OLLAMA_BASE_URL=http://localhost:11434

# Path to your Obsidian vault (folder with .md files)
VAULT_PATH=/path/to/your/obsidian/vault

# Where to save the FAISS vector index
SAVE_INDEX_PATH=/path/to/faiss_index

# Embedding model — downloaded automatically on first run (~120 MB)
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

> **Using Ollama?** Start the Ollama server first:
> ```bash
> ollama serve
> ollama pull qwen2.5:7b-instruct-q4_K_M
> ```

---

### Step 3 — Build the vector index (RAG mode)

This step indexes your vault with FAISS for semantic search. Only needed once (re-run when you add many new notes).

```bash
python backend/db_script/vectorization.py
```

The first run downloads the embedding model (~120 MB). Progress is printed to the console.

---

### Step 4 — Run

```bash
python run.py
```

Open **http://localhost:7860** in your browser.

#### Other run options

```bash
python run.py --port 8080              # custom port
python run.py --model openrouter       # explicit backend (default)
python run.py --model ollama           # local Ollama
python run.py --ui cli                 # terminal chat (no browser)
python run.py --model ollama --ollama-model llama3.2:3b  # custom model
```

---

## Chat Modes

### MCP Chat (default)
The model has access to 5 tools that operate directly on your vault:

| Tool | Description |
|------|-------------|
| `search_notes` | BM25 full-text search across all notes |
| `read_note` | Read full markdown content of a note |
| `list_notes` | List all notes (path, title, tags) |
| `search_by_tag` | Find notes by tag |
| `get_backlinks` | Find notes that link to a given note |

The model decides which tools to call and in what order. It can make up to 10 tool calls per response.

### RAG Chat
Your vault is split into chunks, embedded with `text-embedding-3-small` via OpenRouter, and stored in a local FAISS index. On each query, the top relevant chunks are retrieved and injected into the model's context.

> **Note:** RAG Chat requires running `vectorization.py` first.

---

## Docker (production)

```bash
cp .env.example .env
# fill in .env ...

docker compose up -d --build
```

The stack runs:
- **backend** — FastAPI on port 8000 (internal)
- **frontend** — Nginx serving the SPA, proxying API to backend

Set `FRONTEND_PORT` in `.env` to expose on a custom port (default: `8005`).

### Rebuild the FAISS index inside Docker

```bash
docker exec -it chat_obsidian-backend-1 python db_script/vectorization.py
docker compose restart backend
```

---

## Project Structure

```
chat_obsidian/
├── backend/
│   ├── api/routes/         # FastAPI endpoints (chat, flashcards, health)
│   ├── model/              # Model backends (OpenRouter, Ollama)
│   ├── services/           # Orchestrator (agentic loop) + RAG chain
│   ├── retrieval/          # FAISS search service
│   ├── db_script/          # Vault chunking + vectorization
│   ├── config.py           # All settings (dotenv-based)
│   └── prompts.py          # System prompts
├── mcp_server/             # MCP server (runs as subprocess over stdio)
├── client/                 # MCP client (manages subprocess lifecycle)
├── frontend/src/
│   ├── index.html          # SPA shell
│   └── js/                 # Alpine.js components (chat, flashcards, i18n…)
├── run.py                  # Local dev entry point
├── docker-compose.yml
└── .env.example
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MODEL_BACKEND` | yes | `openrouter` | `openrouter` or `ollama` |
| `OPENROUTER_API_KEY` | if using OpenRouter | — | API key from openrouter.ai |
| `OPENROUTER_MODEL` | no | `deepseek/deepseek-chat-v3-0324` | Any chat model on OpenRouter |
| `OLLAMA_MODEL` | if using Ollama | `qwen2.5:7b-instruct-q4_K_M` | Local model name |
| `OLLAMA_BASE_URL` | no | `http://localhost:11434` | Ollama server URL |
| `VAULT_PATH` | yes | `./vault` | Path to Obsidian vault folder |
| `SAVE_INDEX_PATH` | for RAG | — | Directory for FAISS index files |
| `EMBEDDING_MODEL` | no | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | HuggingFace embedding model |

---

## Tech Stack

**Backend:** Python 3.11, FastAPI, MCP SDK, LangChain, FAISS, rank-bm25, OpenAI SDK, ollama SDK

**Frontend:** Alpine.js 3, Tailwind CSS, DaisyUI, marked.js, KaTeX — no build step required

**Infrastructure:** Docker, Docker Compose, Nginx, GitHub Actions
