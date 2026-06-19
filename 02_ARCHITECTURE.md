# 02 — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│                                                                 │
│   Next.js 15 UI          Claude Code          Codex / AGY      │
│   (port 3000)            (MCP client)         (MCP client)     │
└────────┬────────────────────────┬───────────────────┬──────────┘
         │ HTTP/REST              │ MCP (stdio/HTTP)  │
         ▼                        ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API LAYER                                │
│                                                                 │
│   FastAPI (port 8000)             MCP Server (port 8100)       │
│   ├── /api/projects               ├── list_projects            │
│   ├── /api/documents              ├── get_project              │
│   ├── /api/search                 ├── search                   │
│   ├── /api/graph                  ├── related                  │
│   └── /api/admin                  ├── reindex                  │
│                                   └── get_okf                  │
└────────┬──────────────────────────────────────────────────────-─┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SERVICE LAYER                              │
│                                                                 │
│  DiscoveryService    ExtractionService    SearchService         │
│  OKFService          GraphService         EmbeddingService      │
│  IndexService        HealthService                              │
└────────┬────────────────────────┬───────────────────┬──────────┘
         │                        │                   │
         ▼                        ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      WORKER LAYER (ARQ)                         │
│                                                                 │
│  discover_projects    extract_project    generate_okf           │
│  embed_documents      build_graph        run_health_check       │
└────────┬────────────────────────┬───────────────────────────────┘
         │                        │
         ▼                        ▼
┌───────────────────────┐  ┌─────────────────────────────────────┐
│       Redis           │  │           PostgreSQL 16              │
│  ├── Job queue (ARQ)  │  │  ├── projects                       │
│  ├── Event bus        │  │  ├── documents                      │
│  └── Search cache     │  │  ├── document_chunks + pgvector     │
└───────────────────────┘  │  ├── technologies                   │
                           │  ├── relationships                   │
                           │  ├── index_runs                     │
                           │  └── search_history                 │
                           └─────────────────────────────────────┘
                                          │
                                          ▼
                           ┌─────────────────────────┐
                           │   LiteLLM Gateway        │
                           │   ├── OpenAI             │
                           │   ├── Claude (Anthropic) │
                           │   ├── Gemini             │
                           │   └── Groq               │
                           └─────────────────────────┘
```

---

## Component Descriptions

### FastAPI Backend
- Single process, async throughout
- Uvicorn with multiple workers in production
- Lifespan events: DB pool init, Redis connect, ARQ scheduler start
- All business logic in service classes, not route handlers
- Routes are thin: validate → call service → return response

### MCP Server
- Separate FastAPI app or standalone process
- Exposes tools over HTTP/SSE (compatible with Claude Code remote MCP)
- Alternatively: stdio transport for direct `claude mcp add` integration
- Shares service layer with main API via direct import (same process) or HTTP calls

### ARQ Workers
- Redis-backed async job queue
- Jobs: discovery, extraction, OKF generation, embedding, graph building
- Cron: discovery every 15 minutes, health check every hour
- Job deduplication: skip if same project already queued

### PostgreSQL + pgvector
- Single database, multiple schemas: `core`, `search`, `graph`
- `pgvector` extension for embedding storage and cosine similarity search
- Full-text search via `tsvector` columns with GIN indexes
- No ORM magic for complex queries — raw SQL via `asyncpg` or SQLAlchemy core

### Redis
- ARQ job queue backend
- Event pub/sub: `project.discovered`, `document.extracted`, `okf.generated`
- Search result cache (TTL: 5 minutes)
- Rate limiting for AI calls

### LiteLLM Gateway
- Unified interface to all LLM providers
- Model routing: use Claude for OKF generation, Groq for fast summaries
- Cost tracking per project
- Retry + fallback logic

### Next.js 15 Frontend
- App Router (`/app` directory)
- React Query for all data fetching and cache
- Carbon Design System (IBM) for UI components
- React Flow for graph visualization
- No SSR for dashboard pages (client-side with React Query)
- SSR only for public-facing pages (if any)

---

## Data Flow

### Project Discovery Flow
```
Startup / Cron trigger
  → DiscoveryService.scan_directories()
  → Find project roots (detect markers)
  → Upsert into projects table
  → Emit project.discovered to Redis
  → ARQ picks up extraction job
  → ExtractionService.extract(project_id)
  → Read documents, parse manifests
  → Store in documents table
  → Emit document.extracted
  → ARQ picks up OKF + embedding jobs (parallel)
```

### Search Flow
```
User query → /api/search
  → SearchService.search(query, filters)
  → Parallel:
      KeywordSearch.search(query)       → PostgreSQL FTS
      SemanticSearch.search(query)      → pgvector similarity
      GraphSearch.search(query)         → relationship traversal
  → MergeRanker.merge(results_list)
  → Cache in Redis (5 min TTL)
  → Return unified results
```

### MCP Tool Call Flow
```
Claude: tool_call("search", {query: "FastAPI Redis"})
  → MCP Server receives
  → Calls SearchService directly (or via HTTP to FastAPI)
  → Returns structured JSON
  → Claude processes and responds
```

---

## Technology Choices

| Technology | Reason |
|------------|--------|
| FastAPI | Async-native, OpenAPI auto-docs, fast dev velocity |
| Python 3.13 | Latest performance improvements, matches homelab stack |
| SQLAlchemy 2 | Async support, type safety with Pydantic integration |
| Pydantic v2 | Performance, strict validation, JSON schema generation |
| ARQ | Lightweight async job queue, Redis-backed, fits Python async |
| PostgreSQL 16 | Proven, pgvector support, full-text search built-in |
| pgvector | No separate vector DB needed, transactional consistency |
| Next.js 15 | App Router maturity, React 19, server components |
| Carbon Design System | Professional, accessible, consistent — good for dev tools |
| React Query | Best-in-class for async data, caching, invalidation |
| React Flow | Standard for graph visualization in React |
| LiteLLM | Single interface to all providers, model switching without code change |
| Redis | ARQ requires it; cache and pub/sub are free bonuses |

---

## Deployment Model

```
Docker Compose (single host)
  ├── buildos-api       (FastAPI, port 8000)
  ├── buildos-mcp       (MCP Server, port 8100)
  ├── buildos-worker    (ARQ workers, n=2)
  ├── buildos-ui        (Next.js, port 3000)
  ├── postgres          (port 5432, volume mounted)
  └── redis             (port 6379, volume mounted)
```

All services on same Docker network. No external exposure by default. Mount `~/project` and `~/projects` as read-only volumes into the API and worker containers.

---

## Constraints

- **Read-only filesystem access**: Discovery and extraction never modify project files (except writing `buildos.okf.md`)
- **Local-first**: No external API calls except to LLM providers
- **Stateless API**: All state in PostgreSQL or Redis
- **Idempotent workers**: Any job can be retried safely
