# AGENTS.md — Agent Contracts

This file defines how AI agents (Claude, Codex, AGY) should interact with this codebase.

---

## Context

BuildOS Knowledge Hub is a self-hosted AI memory system. Stack:
- **Backend:** FastAPI + Python 3.13 + SQLAlchemy 2 + Pydantic v2 + ARQ + Redis
- **Frontend:** Next.js 15 + TypeScript + Carbon Design System + React Query + React Flow
- **Database:** PostgreSQL 16 + pgvector
- **AI:** LiteLLM gateway → OpenAI / Claude / Gemini / Groq
- **MCP:** Custom MCP server on port 8100

Full specs in `00_VISION.md` through `13_ROADMAP.md`.

---

## Working Agreements

### File Ownership

| Directory | Responsibility |
|-----------|---------------|
| `backend/app/api/` | Route handlers only. No business logic. |
| `backend/app/services/` | All business logic. One service per domain. |
| `backend/app/models/` | SQLAlchemy models only. No methods beyond `__repr__`. |
| `backend/app/schemas/` | Pydantic schemas. Request/response only. |
| `backend/app/workers/` | ARQ task functions. Call services, don't contain logic. |
| `frontend/app/` | Next.js pages. Thin — fetch data, render components. |
| `frontend/components/` | Reusable UI components. No direct API calls (use hooks). |
| `frontend/hooks/` | React Query hooks. All data fetching lives here. |
| `frontend/lib/api.ts` | Single source of truth for all API calls. |

### Code Conventions

**Python:**
- Async everywhere (`async def`, `await`)
- Type hints on all function signatures
- Pydantic models for all API schemas
- SQLAlchemy 2 style: `select()`, not legacy `.query()`
- `UUID` type for all IDs, not `int`
- Raise typed exceptions from services, not HTTP exceptions
- Log with `structlog`, not `print` or raw `logging`

**TypeScript:**
- Strict mode enabled
- No `any` — use `unknown` and type guards if needed
- Interfaces over types for object shapes
- Named exports only (no default exports except pages)
- React Query for all server state — no local state for server data
- Zustand for UI-only state

**General:**
- No magic strings — use constants or enums
- No commented-out code
- No TODO comments — use GitHub Issues

### Testing

- Backend: `pytest` + `pytest-asyncio`
- All service methods have unit tests
- Integration tests use real PostgreSQL (via `pytest-docker` or pre-existing test DB)
- No mocking the database
- Frontend: `vitest` + `@testing-library/react`
- Test files colocated: `service.py` → `test_service.py`

---

## For Claude (Claude Code)

### How to use this repo

1. Read `00_VISION.md` for context on what this builds
2. Read `13_ROADMAP.md` to understand current phase and what's done
3. Read `BUILD_LOG.md` for session-by-session progress
4. Check `PLAN.md` for current active tasks

### Key patterns to follow

- **Service layer pattern:** Routes call services. Services call repos/DB. No DB queries in routes.
- **Dependency injection:** Use FastAPI `Depends()` for db session and redis. Never create global connections.
- **Hash-based dedup:** Always check content hash before re-processing documents.
- **Job dedup:** Use `arq_enqueue()` wrapper (not raw ARQ) to prevent duplicate jobs.

### What to avoid

- Don't add columns to the schema without a migration
- Don't put business logic in route handlers
- Don't call `os.system()` or `subprocess` in workers
- Don't write `.env` files with real secrets in any commit
- Don't import between `api/` modules — go through services

### Current stack versions (as of project start)
- Python 3.13 (use `match` statements, `tomllib`, etc.)
- FastAPI 0.115+
- SQLAlchemy 2.0+ (use `mapped_column`, `Mapped[]` types)
- Pydantic v2 (use `model_validator`, `field_validator` — not v1 patterns)
- Next.js 15 (App Router — no Pages Router)
- React 19

---

## For Codex

### Startup checklist
1. Read `CODEX.md` first — project-specific Codex instructions
2. Run `cat BUILD_LOG.md | tail -50` to see recent progress
3. Run `cat PLAN.md` to see active tasks

### Preferred patterns

- Generate complete, working code — no placeholders or `// TODO: implement`
- Follow existing patterns in the file you're editing
- Run the test suite after changes: `cd backend && uv run pytest`
- Check TypeScript: `cd frontend && pnpm type-check`

### What Codex handles best in this repo

- Implementing new service methods following existing patterns
- Adding new API routes following the existing structure
- Writing Alembic migrations from schema changes
- Adding React Query hooks and frontend components
- Writing pytest tests for services

---

## For AGY

### Priority context to load at session start

```
search("BuildOS architecture")
get_project("buildos-kb")
```

### AGY's role in this project

- Architecture review when adding new modules
- Cross-project pattern analysis ("how does AuraStay handle X?")
- Debugging complex async/DB issues
- Planning phase transitions (what needs to be done before moving to next phase)

### Data access pattern

Use MCP tools:
- `list_projects` — see all local projects
- `search(query)` — find relevant code/docs
- `get_project(slug)` — get full context for a project
- `related(slug)` — find related projects

---

## Shared Constraints (All Agents)

1. **Never commit** `.env` files with real API keys
2. **Never delete** migration files — always create new ones
3. **Never modify** `buildos.okf.md` manually — it's AI-generated, re-generate via reindex
4. **Never bypass** the hash check in extraction — it's there to save API costs
5. **Always run** `alembic upgrade head` after creating migrations
6. **Always write** tests for new service methods before marking task done
