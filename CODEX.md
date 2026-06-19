# CODEX.md — BuildOS Knowledge Hub

## Startup Sequence

```bash
# 1. See what phase we're in
cat 13_ROADMAP.md | grep -A 5 "## Phase 1"

# 2. See recent progress
cat BUILD_LOG.md 2>/dev/null | tail -60 || echo "No build log yet"

# 3. See current active tasks
cat PLAN.md 2>/dev/null || echo "No plan file yet"

# 4. Check DB state
cd backend && uv run alembic current
```

## Your Job

Implement tasks from `PLAN.md` (or `13_ROADMAP.md` if no PLAN.md). Follow all patterns in `AGENTS.md` and `CLAUDE.md`.

Write complete, working code. No stubs, no `pass` without reason, no `# TODO: implement`.

---

## Implementation Patterns

### Adding a new API route

```python
# backend/app/api/things.py
from fastapi import APIRouter, Depends
from app.api.deps import get_db
from app.schemas.thing import ThingResponse
from app.services.thing import ThingService

router = APIRouter(prefix="/things", tags=["things"])

@router.get("/{slug}", response_model=ThingResponse)
async def get_thing(slug: str, db=Depends(get_db)):
    service = ThingService(db)
    result = await service.get_by_slug(slug)
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    return result
```

Register in `app/main.py`:
```python
from app.api.things import router as things_router
app.include_router(things_router, prefix="/api")
```

### Adding a new service

```python
# backend/app/services/thing.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.thing import Thing
from uuid import UUID

class ThingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_slug(self, slug: str) -> Thing | None:
        stmt = select(Thing).where(Thing.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
```

### Adding a new ARQ job

```python
# backend/app/workers/tasks.py
async def process_thing(ctx: dict, thing_id: str) -> dict:
    db = ctx["db"]
    thing = await ThingRepo(db).get(UUID(thing_id))
    # ... do work
    return {"status": "done", "thing_id": thing_id}
```

Add to `WorkerSettings.functions`.

### Adding a new migration

```bash
# After changing models:
uv run alembic revision --autogenerate -m "add thing_metadata column"
# Review the generated file in alembic/versions/
# Apply:
uv run alembic upgrade head
```

### Adding a React Query hook

```typescript
// frontend/hooks/useThing.ts
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useThing(slug: string) {
  return useQuery({
    queryKey: ['thing', slug],
    queryFn: () => api.getThing(slug),
    enabled: !!slug,
  })
}
```

### Adding a frontend page

```tsx
// frontend/app/things/[slug]/page.tsx
'use client'
import { useThing } from '@/hooks/useThing'

export default function ThingPage({ params }: { params: { slug: string } }) {
  const { data, isLoading, error } = useThing(params.slug)

  if (isLoading) return <Loading />
  if (error || !data) return <ErrorState />

  return <ThingDetail thing={data} />
}
```

---

## Test Patterns

### Backend service test

```python
# backend/tests/services/test_thing_service.py
import pytest
from app.services.thing import ThingService

@pytest.mark.asyncio
async def test_get_thing_by_slug(db_session):
    service = ThingService(db_session)
    thing = await service.get_by_slug("test-thing")
    assert thing is not None
    assert thing.slug == "test-thing"
```

Use `conftest.py` fixtures for `db_session` (real PostgreSQL, not mock).

### Frontend component test

```typescript
// frontend/components/ThingCard.test.tsx
import { render, screen } from '@testing-library/react'
import { ThingCard } from './ThingCard'

it('renders thing name', () => {
  render(<ThingCard thing={{ name: 'BuildOS', slug: 'buildos' }} />)
  expect(screen.getByText('BuildOS')).toBeInTheDocument()
})
```

---

## Coding Standards

### Python
- `ruff` for linting and formatting (configured in `pyproject.toml`)
- Type hints mandatory on all function signatures
- `UUID` not `str` for ID parameters in service functions
- Exceptions: raise `ProjectNotFoundError` from services, not `HTTPException`
- Max function length: 50 lines — extract helpers if longer

### TypeScript
- `eslint` + `prettier` (configured in project)
- Strict TypeScript: no `any`
- Prefer `interface` over `type` for object shapes
- Component files: PascalCase (`ProjectCard.tsx`)
- Hook files: camelCase (`useProject.ts`)
- Utility files: camelCase (`api.ts`, `utils.ts`)

---

## Files You Will Touch Most

| File | Purpose |
|------|---------|
| `backend/app/services/*.py` | Business logic — usually where new features start |
| `backend/app/api/*.py` | Route handlers — add after service is done |
| `backend/app/workers/tasks.py` | New ARQ jobs |
| `backend/alembic/versions/*.py` | DB migrations |
| `frontend/hooks/*.ts` | Data fetching |
| `frontend/components/*.tsx` | UI components |
| `frontend/app/**/page.tsx` | Page components |

---

## Quick Reference

```bash
# Full backend test suite
cd backend && uv run pytest -v

# Single test file
cd backend && uv run pytest tests/services/test_search.py -v

# Frontend type check
cd frontend && pnpm type-check

# Frontend test
cd frontend && pnpm test

# Lint backend
cd backend && uv run ruff check . && uv run ruff format --check .

# Lint fix
cd backend && uv run ruff check --fix . && uv run ruff format .

# Check DB schema matches models
cd backend && uv run alembic check
```
