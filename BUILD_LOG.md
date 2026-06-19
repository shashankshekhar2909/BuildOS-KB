# BUILD_LOG.md — Session-by-Session Progress

## Purpose

Continuity file. Every session ends with an update here.
New session starts by reading the last entry.

Format per entry:
```
## YYYY-MM-DD — Session N
Phase: X | Status: [what state things are in]
Done: what was completed
Next: first 3 tasks for next session
Blockers: anything stuck
Notes: decisions, surprises, context
```

---

## 2026-06-18 — Session 1

**Phase:** Pre-build | **Status:** Specs complete, no code yet

**Done:**
- Wrote all 17 specification files
- `00_VISION.md` through `13_ROADMAP.md` — senior-engineer-level specs
- `AGENTS.md` — contracts for Claude, Codex, AGY
- `CLAUDE.md` — project context for Claude Code sessions
- `CODEX.md` — startup sequence and patterns for Codex
- `PLAN.md` — active checklist with Phase 1 tasks fully broken down
- `BUILD_LOG.md` — this file

**Next session (Phase 1 start):**
1. Create `docker-compose.yml` with postgres (pgvector image) + redis
2. `uv init` in `backend/`, install FastAPI, SQLAlchemy 2, Pydantic v2, ARQ, asyncpg
3. Create `app/main.py`, `app/config.py`, `app/database.py`

**Blockers:** None

**Notes:**
- Use `pgvector/pgvector:pg16` Docker image — not stock postgres
- LiteLLM not needed until Phase 3 (OKF generation) — skip for now
- pgvector needs `CREATE EXTENSION vector;` in migration, not just SQL file
- Discovery scans: `~/project`, `~/projects`, `~/workspace`
- All IDs: UUID, not integer
- Python: async SQLAlchemy 2 style (`Mapped[]`, `mapped_column`)

---

## 2026-06-18 — Session 2

**Phase:** 1–3 (Backend + Frontend + Deployment) | **Status:** COMPLETE

**Done:**
- Full backend implementation: FastAPI, all models, all services, ARQ workers, MCP server
- Full frontend: Next.js 15, Carbon g100 dark theme (plain CSS, no SCSS), all 4 pages
- Alembic async migrations with schema support (public schema for version table)
- Docker: all 6 containers running healthy on free ports (API=8010, MCP=8090, UI=3100, PG=5436, Redis=6382)
- 19 projects discovered from `/home/shashank/project`, 108 docs, 4595 chunks indexed
- MCP server registered with Claude Code: `buildos-kb` at `http://localhost:8090/mcp` ✓

**Bugs Fixed:**
- `TIMESTAMPTZ` → `TIMESTAMP(timezone=True)` (SQLAlchemy 2 import issue)
- Alembic `version_table_schema="core"` removed (core schema didn't exist yet)
- `enqueue_job` on plain Redis → use `get_arq_pool()` via `arq.connections.create_pool()`
- Worker `startup()` was overwriting ARQ pool with plain Redis → made it a no-op
- `NoForeignKeysError` on ProjectIndexState → added `ForeignKey` annotation
- pyproject.toml `[tool.hatch.build.targets.wheel] packages = ["app"]` missing
- pnpm lockfile not generated → ran `pnpm install` locally first
- uv venv recreation on each container start → switched to pip in Dockerfile
- globals.css used SCSS `@use` syntax → replaced with hardcoded CSS custom properties
- Volume mounts `/mnt/projects` → `/home/shashank/project:...` (same path as host)
- SCAN_DIRECTORIES env var had `/mnt/` paths → updated to real host paths

**State at end of session:**
- All containers healthy, no errors in logs
- Worker scanning correct paths, no duplicates
- UI returning 200 on /dashboard, 307 redirect from /
- MCP connected: `claude mcp list` shows `buildos-kb: ✔ Connected`
- Embeddings = 0 (expected — no API key configured)

**Next session:**
1. Add `ANTHROPIC_API_KEY` to `.env`, restart api+worker, verify embeddings populate
2. Test semantic search: `GET /api/search?q=authentication&mode=semantic`
3. Begin graph engine: `app/services/graph.py` entity extraction

**Blockers:**
- No LLM API key → OKF = placeholder, embeddings = 0, semantic search disabled

**Notes:**
- MCP StreamableHTTP on port 8100 (container), 8090 (host) — registered via `--transport http`
- Worker cron fires every 15min for discovery
- `buildos-kb` project itself excluded from scan (path filter in discovery service? verify)

---

_Append new entries here as sessions complete._
