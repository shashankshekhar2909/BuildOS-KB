# 11 — Deployment

## Local Development

### Prerequisites
- Docker + Docker Compose
- Python 3.13 + uv
- Node.js 22 + pnpm
- PostgreSQL client (optional, for direct DB access)

### Start everything

```bash
# Clone and enter
cd ~/project/buildos-kb

# Copy env
cp .env.example .env
# Edit .env: add API keys

# Start infrastructure only (DB + Redis)
docker compose up postgres redis -d

# Backend
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# Worker (separate terminal)
cd backend
uv run arq app.workers.scheduler.WorkerSettings

# MCP server (separate terminal)
cd backend
uv run python -m app.mcp_server

# Frontend (separate terminal)
cd frontend
pnpm install
pnpm dev
```

Access:
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- MCP: http://localhost:8100

---

## Docker Compose (Full Stack)

```yaml
# docker-compose.yml
version: "3.9"

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: buildos
      POSTGRES_PASSWORD: buildos
      POSTGRES_DB: buildos
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U buildos"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
    environment:
      DATABASE_URL: postgresql+asyncpg://buildos:buildos@postgres:5432/buildos
      REDIS_URL: redis://redis:6379
      SCAN_DIRECTORIES: /mnt/projects,/mnt/workspace
    volumes:
      - ~/project:/mnt/projects:ro
      - ~/workspace:/mnt/workspace:ro
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    env_file: .env

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: python -m arq app.workers.scheduler.WorkerSettings
    environment:
      DATABASE_URL: postgresql+asyncpg://buildos:buildos@postgres:5432/buildos
      REDIS_URL: redis://redis:6379
      SCAN_DIRECTORIES: /mnt/projects,/mnt/workspace
    volumes:
      - ~/project:/mnt/projects:ro
      - ~/workspace:/mnt/workspace:ro
    depends_on:
      - api
    env_file: .env
    deploy:
      replicas: 2

  mcp:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: python -m app.mcp_server
    environment:
      DATABASE_URL: postgresql+asyncpg://buildos:buildos@postgres:5432/buildos
      REDIS_URL: redis://redis:6379
    ports:
      - "8100:8100"
    depends_on:
      - api
    env_file: .env

  ui:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - api

volumes:
  postgres_data:
  redis_data:
```

---

## Environment Variables

```bash
# .env.example

# Database
DATABASE_URL=postgresql+asyncpg://buildos:buildos@localhost:5432/buildos

# Redis
REDIS_URL=redis://localhost:6379

# LLM Providers (add keys for providers you use)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=

# LiteLLM (if using local proxy, set base URL)
LITELLM_BASE_URL=http://localhost:4000

# Models
OKF_MODEL=claude-sonnet-4-6
EMBEDDING_MODEL=text-embedding-3-small
SUMMARY_MODEL=groq/llama-3.1-8b-instant

# Discovery
SCAN_DIRECTORIES=~/project,~/projects,~/workspace

# App
DEBUG=false
SECRET_KEY=change-me-in-production
```

---

## Backend Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (layer cache)
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source
COPY . .

# Run migrations on startup via entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

```bash
#!/bin/bash
# entrypoint.sh
set -e

if [ "$1" = "uvicorn" ]; then
    uv run alembic upgrade head
fi

exec uv run "$@"
```

---

## Frontend Dockerfile

```dockerfile
# frontend/Dockerfile
FROM node:22-alpine AS base

WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

FROM node:22-alpine AS runner
WORKDIR /app
COPY --from=base /app/.next/standalone ./
COPY --from=base /app/.next/static ./.next/static
COPY --from=base /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
```

---

## Homelab Deployment (Proxmox / Bare Metal)

Run via Docker Compose on a dedicated LXC container or VM:

```bash
# On homelab host
git clone git@github.com:user/buildos-kb.git /opt/buildos-kb
cd /opt/buildos-kb

# Mount project directories from NFS or bind mount
# Edit docker-compose.yml: update volume mounts to homelab paths

docker compose up -d

# Auto-start on reboot
systemctl enable docker
# docker compose up -d already restarts=unless-stopped
```

Add `restart: unless-stopped` to all services in docker-compose.yml for persistence.

---

## Accessing MCP from Claude Code

After deployment:

```bash
# Option 1: stdio (local process, recommended for dev)
claude mcp add buildos-kb -- uv run --directory /home/shashank/project/buildos-kb/backend python -m app.mcp_server

# Option 2: HTTP/SSE (for Docker deployment)
claude mcp add --transport sse buildos-kb http://localhost:8100/mcp
```

Verify:
```
/mcp
# Should show: buildos-kb  ✓ connected
# Tools: list_projects, get_project, search, related, get_okf, reindex
```

---

## Backup

```bash
# Backup PostgreSQL
docker exec buildos-kb-postgres-1 \
  pg_dump -U buildos buildos | gzip > backups/buildos-$(date +%Y%m%d).sql.gz

# Restore
gunzip -c backups/buildos-20260618.sql.gz | \
  docker exec -i buildos-kb-postgres-1 psql -U buildos buildos
```

Cron for daily backup:
```
0 2 * * * /opt/buildos-kb/scripts/backup.sh
```
