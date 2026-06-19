# BuildOS Knowledge Hub

> Self-hosted AI memory for all your local projects. Auto-discovers codebases, generates knowledge files, and exposes everything via hybrid search and MCP tools — so Claude always knows your codebase.

Built by [BuildWithShashank](https://buildwithshashank.com)

---

## What it does

BuildOS KB scans your local project directories, extracts knowledge from every file, and generates structured **Operational Knowledge Files (OKF)** using an LLM. The result is a searchable, queryable knowledge base that Claude Code can query directly via MCP tools.

```
Your Projects → Auto Discovery → AI Extraction → OKF + Embeddings → Search & MCP
```

---

## Features

- **Auto-discovery** — scans configured directories every 15 minutes, hash-deduped so unchanged projects are skipped
- **AI-generated OKF** — LLM synthesizes architecture, APIs, decisions, and stack per project
- **Hybrid search** — keyword (PostgreSQL tsvector) + semantic (pgvector cosine) combined
- **MCP server** — exposes `list_projects`, `get_project`, `search`, `get_okf`, `reindex` tools to Claude Code
- **Multi-LLM** — LiteLLM gateway supports Gemini, Claude, OpenAI, Groq, or any local model
- **Auth gate** — browse and search freely; Google OAuth (Firebase) required only for LLM reindex operations
- **Self-hosted** — Docker Compose, no cloud required, LAN-ready

---

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI 0.115+ · Python 3.13 · SQLAlchemy 2 async · ARQ workers |
| Database | PostgreSQL 16 + pgvector (768-dim embeddings) |
| AI | LiteLLM → Gemini / Claude / OpenAI / Groq |
| Frontend | Next.js 15 · TypeScript · Tailwind CSS v4 · React Query |
| Auth | Firebase Google OAuth · JWT sessions |
| Queue | ARQ + Redis — async job dedup |
| Protocol | MCP Streamable HTTP, port 8090 |

---

## Quick start

### 1. Clone and configure

```bash
git clone https://github.com/shashankshekhar2909/BuildOS-KB.git
cd BuildOS-KB
cp .env.example .env
```

Edit `.env`:

```env
# Add at least one LLM provider key
GEMINI_API_KEY=your_key_here
# OR
OPENAI_API_KEY=your_key_here
# OR
ANTHROPIC_API_KEY=your_key_here

# Directories to scan (comma-separated)
SCAN_DIRECTORIES=/home/you/projects,/home/you/work

# Models (defaults work with Gemini)
OKF_MODEL=gemini/gemini-2.5-flash
EMBEDDING_MODEL=gemini/text-embedding-004
SUMMARY_MODEL=gemini/gemini-2.5-flash-lite

# Required for JWT signing
SECRET_KEY=your_random_secret_here
```

### 2. Configure Firebase (for Google sign-in)

1. Create a project at [console.firebase.google.com](https://console.firebase.google.com)
2. Enable Authentication → Google sign-in
3. Add your domain to Authorized Domains
4. Copy Web SDK config into `frontend/firebase-config.json`:

```bash
cp frontend/firebase-config.example.json frontend/firebase-config.json
# Fill in your Firebase project values
```

### 3. Start services

```bash
docker compose up -d
```

| Service | URL |
|---------|-----|
| UI | http://localhost:3100 |
| API | http://localhost:8010 |
| MCP server | http://localhost:8090 |

### 4. Add MCP to Claude Code

```bash
claude mcp add buildos-kb --transport http http://localhost:8090/mcp
```

Then in any Claude session:

```
"What projects do I have?"
"How does the auth flow work in my HMS project?"
"Find all places we use pgvector"
```

---

## MCP tools

| Tool | Description |
|------|-------------|
| `list_projects` | List all indexed projects with metadata |
| `get_project` | Get full details for a project by slug |
| `search` | Hybrid keyword + semantic search across all projects |
| `get_okf` | Get the AI-generated Operational Knowledge File |
| `reindex` | Trigger re-indexing for a specific project |

---

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────┐
│  Next.js UI │────▶│  FastAPI (port 8000 / Docker :8010)  │
└─────────────┘     │                                      │
                    │  /api/projects   → project CRUD       │
┌─────────────┐     │  /api/search     → hybrid search      │
│  Claude MCP │────▶│  /api/admin      → index triggers      │
│   (port     │     │  /api/auth       → Firebase JWT        │
│    8090)    │     └──────────┬───────────────────────────-┘
└─────────────┘                │
                    ┌──────────▼──────────┐
                    │  PostgreSQL + pgvec │  ← embeddings, chunks, graph
                    └──────────┬──────────┘
                    ┌──────────▼──────────┐
                    │   ARQ Worker        │  ← discovery, extraction, OKF, embeddings
                    │   (Redis queue)     │
                    └─────────────────────┘
```

**Data flow:**
1. ARQ worker scans `SCAN_DIRECTORIES` → discovers projects by markers (`package.json`, `pyproject.toml`, `.git`, etc.)
2. Extracts documents: README, CLAUDE.md, Dockerfiles, manifests, all markdown
3. LLM generates OKF — purpose, architecture, APIs, decisions, tech stack
4. Text chunked → embeddings generated → stored in pgvector
5. Search merges keyword (tsvector BM25 rank) + semantic (cosine similarity) scores
6. MCP server wraps the same API for Claude Code consumption

---

## Auth model

- **GET routes** — fully public. Browse projects, search, read OKF without logging in.
- **POST routes** (reindex/discovery) — require Google OAuth JWT. These trigger LLM calls that cost tokens.
- **Frontend** — sync buttons disabled when not signed in. Sign in via Google button in NavBar.
- **Backend** — JWT validated on every protected request, independent of frontend state.

---

## Development

```bash
# Backend (hot reload)
cd backend && uv run uvicorn app.main:app --reload --port 8000

# Worker
cd backend && uv run arq app.workers.scheduler.WorkerSettings

# MCP server
cd backend && uv run python -m app.mcp_server

# Frontend
cd frontend && pnpm dev

# DB migrations
cd backend && uv run alembic upgrade head
cd backend && uv run alembic revision --autogenerate -m "description"

# Tests
cd backend && uv run pytest
cd frontend && pnpm test
cd frontend && pnpm type-check
```

### Environment variables reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | one of these | — | Gemini API key |
| `OPENAI_API_KEY` | one of these | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | one of these | — | Anthropic API key |
| `SECRET_KEY` | yes | — | JWT signing secret |
| `SCAN_DIRECTORIES` | yes | — | Comma-separated paths to scan |
| `OKF_MODEL` | no | `claude-sonnet-4-6` | LLM for OKF generation |
| `EMBEDDING_MODEL` | no | `text-embedding-3-small` | Embedding model |
| `SUMMARY_MODEL` | no | `groq/llama-3.1-8b-instant` | Summary model |
| `SCAN_INTERVAL_MINUTES` | no | `15` | How often to auto-scan |
| `DATABASE_URL` | no | localhost default | PostgreSQL connection string |
| `REDIS_URL` | no | localhost default | Redis connection string |
| `API_KEY` | no | — | Static API key for CLI/MCP auth (alternative to Firebase) |

---

## Deployment (public domain)

The UI uses Next.js server-side rewrites to proxy `/api/*` requests internally — no nginx config changes needed.

```yaml
# docker-compose.yml — ui service
environment:
  API_INTERNAL_URL: http://api:8000  # Docker internal network
```

For HTTPS deployments (e.g. behind Caddy/nginx), the frontend auto-detects protocol — no `NEXT_PUBLIC_API_URL` needed.

Add your public domain to Firebase Console → Authentication → Authorized Domains for Google sign-in to work.

---

## License

MIT — [BuildWithShashank](https://buildwithshashank.com)
