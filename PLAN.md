# PLAN.md — Active Build Plan

## How to Use This File

- Update before starting a session: mark tasks `[~]` = in progress
- Update after finishing: mark `[x]` = done, add notes
- Add blockers inline: `[x] Task — BLOCKED: reason`
- Add date when completing a phase

---

## Current Phase: Phase 4 — Search + MCP

**Goal:** Semantic search working, MCP server connectable by Claude Code.
**Status:** Phase 1–3 complete. Search works (keyword). Embeddings pending API keys.

---

## Phases 1–3 Complete ✓ (2026-06-18)

### Infrastructure ✓
- [x] `docker-compose.yml` — 6 services: postgres (pgvector), redis, api, worker, mcp, ui
- [x] `.env` / `.env.example` with all vars
- [x] Ports: API=8010, MCP=8090, UI=3100, PG=5436, Redis=6382
- [x] All 6 containers running healthy

### Backend ✓
- [x] `app/main.py` — FastAPI with lifespan
- [x] `app/config.py` — pydantic-settings, scan_dirs_list property
- [x] `app/database.py` — async SQLAlchemy engine
- [x] `app/redis_client.py` — singleton Redis client
- [x] `app/api/deps.py` — `get_arq_pool()` using ARQ create_pool (not plain Redis)

### Database ✓
- [x] Alembic async migrations (public schema version table)
- [x] `core.projects`, `core.documents`, `core.project_index_state`
- [x] `core.technologies`, `core.project_technologies`
- [x] `search.document_chunks` with pgvector embedding column
- [x] `graph.relationships`

### Models + Services ✓
- [x] `app/models/` — project, document, technology, relationship, index_run
- [x] `app/services/discovery.py` — scans dirs, detects language/framework, upserts
- [x] `app/services/extraction.py` — reads 19 priority files, hash change detection
- [x] `app/services/embedding.py` — tiktoken chunking + LiteLLM batch embed
- [x] `app/services/okf.py` — LiteLLM OKF generation, placeholder fallback
- [x] `app/services/search.py` — keyword (tsvector) + semantic (pgvector) + merge

### Workers ✓
- [x] `app/workers/scheduler.py` — WorkerSettings, cron every 15min
- [x] Tasks: discover_projects, extract_project, generate_okf, embed_document

### API Routes ✓
- [x] `GET /api/projects`, `GET /api/projects/{slug}`
- [x] `GET /api/search`
- [x] `POST /api/admin/index/full`, `GET /api/admin/stats`

### MCP Server ✓
- [x] `app/mcp_server.py` — FastMCP with StreamableHTTP, port 8100
- [x] Tools: list_projects, get_project, search, get_okf, reindex
- [x] Registered in Claude Code: `claude mcp add buildos-kb --transport http http://localhost:8090/mcp`

### Frontend ✓
- [x] Next.js 15 + Carbon g100 dark theme (plain CSS, no SCSS)
- [x] Dashboard page with stats + reindex button
- [x] Projects list with filters + pagination
- [x] Project detail with Overview/Documents/OKF tabs
- [x] Search page with debounced query + score breakdown

### Deployment ✓
- [x] All 6 Docker containers running
- [x] 19 projects discovered from `/home/shashank/project`
- [x] 108 documents indexed, 4595 chunks
- [x] Volume mounts fixed: `/home/shashank/project:/home/shashank/project:ro`
- [x] SCAN_DIRECTORIES corrected to real host paths (not /mnt/ aliases)

---

## Phase 4 Tasks — Search Enhancement

### Semantic Search (needs API key)
- [ ] Add `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` to `.env`
- [ ] Trigger reindex → embed_document jobs will run
- [ ] Verify `embeddings > 0` in `/api/admin/stats`
- [ ] Test semantic search via `/api/search?q=...&mode=semantic`

### Graph Engine (Phase 5 in roadmap)
- [ ] Implement `app/services/graph.py` — entity extraction + relationship building
- [ ] Populate `graph.relationships` table
- [ ] Add graph-aware search merge (weight 0.2)

### OKF with Real LLM
- [ ] Once API key added, verify OKF files are generated (not placeholder)
- [ ] Check `buildos.okf.md` created in project directories

---

## Upcoming Phases

- **Phase 5** — Graph Engine (relationship traversal)
- **Phase 6** — Production hardening (auth, rate limits, health checks)

---

## Decisions Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-06-18 | Spec-first: all 17 docs written before code | Enables Claude/Codex continuity across sessions |
| 2026-06-18 | PostgreSQL + pgvector over separate vector DB | Simpler ops, transactional consistency |
| 2026-06-18 | ARQ over Celery | Native async Python, lighter weight for this scale |
| 2026-06-18 | Carbon Design System for UI | Professional look, accessible, IBM dev tool aesthetic |
| 2026-06-18 | pip install in Dockerfile over uv | uv recreated venv on each container start (path mismatch) |
| 2026-06-18 | Alembic version table in public schema | core schema didn't exist yet when Alembic tried to create it |
| 2026-06-18 | get_arq_pool() via create_pool not Redis | Plain Redis doesn't have enqueue_job — ARQ pool required |
| 2026-06-18 | Volume mount at same path as host | Prevents duplicate project rows with /mnt/ vs real paths |

---

## Blockers

- **Embeddings = 0**: No LLM API key in .env. Add ANTHROPIC_API_KEY or OPENAI_API_KEY.
- **OKF = placeholder**: Same as above. LLM not available without key.

---

## Notes

- Scan directories: `/home/shashank/project`, `/home/shashank/projects`
- pgvector uses `pgvector/pgvector:pg16` Docker image
- Worker startup must NOT set ctx["redis"] — ARQ provides its own pool in ctx
- `TIMESTAMP(timezone=True)` not `postgresql.TIMESTAMPTZ` — import not available in SQLAlchemy 2
- UI root redirects 307 → /dashboard (correct Next.js behavior)
