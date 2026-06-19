# CLAUDE.md — BuildOS Knowledge Hub

## What This Project Is

Self-hosted AI memory system. Discovers all local projects, extracts knowledge, generates OKF files, exposes everything via search + MCP tools.

Full specs: `00_VISION.md` through `13_ROADMAP.md`.

## Current Phase

Check `13_ROADMAP.md` and `BUILD_LOG.md` for current status.

## Stack

```
Backend:  FastAPI 0.115+ / Python 3.13 / SQLAlchemy 2 / Pydantic v2
Jobs:     ARQ / Redis
DB:       PostgreSQL 16 + pgvector
AI:       LiteLLM → Claude / OpenAI / Groq
Frontend: Next.js 15 / TypeScript / Carbon Design System / React Query / React Flow
MCP:      Custom server, port 8100
```

## Key Commands

```bash
# Backend dev
cd backend && uv run uvicorn app.main:app --reload --port 8000

# Workers
cd backend && uv run arq app.workers.scheduler.WorkerSettings

# MCP server
cd backend && uv run python -m app.mcp_server

# Frontend dev
cd frontend && pnpm dev

# Run all (Docker)
docker compose up -d

# DB migrations
cd backend && uv run alembic upgrade head
cd backend && uv run alembic revision --autogenerate -m "description"

# Tests
cd backend && uv run pytest
cd frontend && pnpm test

# Type check
cd frontend && pnpm type-check
```

## Project Structure

```
buildos-kb/
├── backend/
│   └── app/
│       ├── api/        # routes only
│       ├── services/   # all business logic
│       ├── models/     # SQLAlchemy models
│       ├── schemas/    # Pydantic schemas
│       └── workers/    # ARQ tasks
├── frontend/
│   ├── app/            # Next.js pages
│   ├── components/     # UI components
│   ├── hooks/          # React Query hooks
│   └── lib/            # api.ts, types.ts
└── *.md                # spec files
```

## Architecture Rules

- Routes call services. Services call repos. No DB queries in routes.
- Use `arq_enqueue()` wrapper (not raw ARQ) for job dedup.
- All file reads check `is_safe_path()` — no traversal outside configured dirs.
- Hash check before re-processing any document.
- `.env` and `*.key` files never indexed — silently skipped.

## SQLAlchemy 2 Style

```python
# Correct
from sqlalchemy.orm import Mapped, mapped_column
class Project(Base):
    id: Mapped[UUID] = mapped_column(primary_key=True)

# Queries
stmt = select(Project).where(Project.slug == slug)
result = await db.execute(stmt)
project = result.scalar_one_or_none()
```

## Pydantic v2 Style

```python
from pydantic import BaseModel, field_validator, model_validator

class ProjectCreate(BaseModel):
    name: str
    path: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return v.strip()
```

## Async Patterns

- All service methods: `async def`
- DB sessions: `async with AsyncSession() as db:` or via `Depends(get_session)`
- Redis: `await redis.get(key)`
- LiteLLM: `await litellm.acompletion(...)`
- Never use `asyncio.run()` inside async context

## What NOT to Do

- Don't put logic in route handlers — move to services
- Don't mock PostgreSQL in tests — use real DB
- Don't use `int` IDs — all IDs are UUID
- Don't call `subprocess` or `os.system` in workers
- Don't commit with real API keys
- Don't modify `buildos.okf.md` manually — re-trigger generation

## MCP Integration Test

```bash
# After starting MCP server:
claude mcp add buildos-kb -- uv run --directory $(pwd)/backend python -m app.mcp_server

# Test in Claude session:
# "What projects do I have in my homelab?"
# Claude should call list_projects tool automatically
```
