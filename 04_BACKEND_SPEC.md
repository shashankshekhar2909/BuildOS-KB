# 04 — Backend Spec

## Project Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app factory, lifespan
│   ├── config.py                # Settings via pydantic-settings
│   ├── database.py              # Async SQLAlchemy engine + session
│   ├── redis.py                 # Redis connection pool
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py              # Shared dependencies (db session, etc.)
│   │   ├── projects.py          # /api/projects routes
│   │   ├── documents.py         # /api/documents routes
│   │   ├── search.py            # /api/search routes
│   │   ├── graph.py             # /api/graph routes
│   │   └── admin.py             # /api/admin routes (index, health)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── project.py           # SQLAlchemy Project model
│   │   ├── document.py          # Document, DocumentChunk models
│   │   ├── technology.py        # Technology, ProjectTechnology models
│   │   ├── relationship.py      # Relationship model
│   │   └── index_run.py         # IndexRun, ProjectIndexState models
│   ├── schemas/
│   │   ├── project.py           # Pydantic request/response schemas
│   │   ├── document.py
│   │   ├── search.py
│   │   └── graph.py
│   ├── services/
│   │   ├── discovery.py         # DiscoveryService
│   │   ├── extraction.py        # ExtractionService
│   │   ├── okf.py               # OKFService
│   │   ├── search.py            # SearchService (hybrid)
│   │   ├── embedding.py         # EmbeddingService
│   │   ├── graph.py             # GraphService
│   │   └── health.py            # HealthService
│   └── workers/
│       ├── __init__.py
│       ├── tasks.py             # ARQ task functions
│       └── scheduler.py        # Cron definitions
├── alembic/
│   ├── env.py
│   └── versions/
├── tests/
├── pyproject.toml
└── Dockerfile
```

---

## Configuration (`app/config.py`)

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # App
    APP_NAME: str = "BuildOS Knowledge Hub"
    API_PREFIX: str = "/api"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://buildos:buildos@localhost:5432/buildos"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # AI
    LITELLM_API_KEY: str = ""
    LITELLM_BASE_URL: str = "http://localhost:4000"  # local litellm proxy
    OKF_MODEL: str = "claude-sonnet-4-6"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    SUMMARY_MODEL: str = "groq/llama-3.1-8b-instant"

    # Discovery
    SCAN_DIRECTORIES: List[str] = ["~/project", "~/projects", "~/workspace"]
    IGNORE_DIRS: List[str] = [
        ".git", "node_modules", "__pycache__", "venv", ".venv",
        "dist", "build", ".next", "target", "vendor"
    ]
    SCAN_INTERVAL_MINUTES: int = 15

    # Search
    SEARCH_CACHE_TTL: int = 300  # seconds
    MAX_SEARCH_RESULTS: int = 50
    CHUNK_SIZE: int = 512          # tokens per chunk
    CHUNK_OVERLAP: int = 64        # token overlap between chunks

    # MCP
    MCP_PORT: int = 8100

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## API Routes

### Projects (`/api/projects`)

```
GET    /api/projects                    List all projects
GET    /api/projects/{slug}             Get project by slug
GET    /api/projects/{slug}/documents   Get project documents
GET    /api/projects/{slug}/okf         Get project OKF content
GET    /api/projects/{slug}/graph       Get project graph relationships
GET    /api/projects/{slug}/health      Get project health report
POST   /api/projects/{slug}/reindex     Trigger re-index for one project
DELETE /api/projects/{slug}             Remove project from index (not from disk)
```

**GET /api/projects response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "BuildOS",
      "slug": "buildos",
      "path": "/home/shashank/project/buildos",
      "language": "typescript",
      "framework": "nextjs",
      "description": "...",
      "status": "active",
      "health_score": 85,
      "technologies": ["nextjs", "typescript", "tailwind"],
      "last_indexed_at": "2026-06-18T10:00:00Z",
      "metadata": {
        "ports": [3000],
        "docker": true,
        "git_url": "git@github.com:user/buildos.git"
      }
    }
  ],
  "total": 42,
  "page": 1,
  "size": 20
}
```

**Query params for list:** `page`, `size`, `language`, `framework`, `status`, `q` (text search on name/description)

### Documents (`/api/documents`)

```
GET    /api/documents                   List documents (with project_id filter)
GET    /api/documents/{id}              Get document by ID
GET    /api/documents/{id}/chunks       Get document chunks
```

### Search (`/api/search`)

```
GET    /api/search?q=...                Hybrid search
GET    /api/search/keyword?q=...        Keyword-only search
GET    /api/search/semantic?q=...       Semantic-only search
GET    /api/search/graph?q=...          Graph search
```

**GET /api/search response:**
```json
{
  "query": "FastAPI Redis background jobs",
  "results": [
    {
      "type": "chunk",
      "chunk_text": "ARQ is a Redis-backed async job queue for Python...",
      "document_title": "ARCHITECTURE.md",
      "document_type": "architecture",
      "project_name": "BuildOS",
      "project_slug": "buildos",
      "score": 0.87,
      "score_breakdown": {
        "keyword": 0.72,
        "semantic": 0.91,
        "graph": 0.0
      },
      "highlight": "...ARQ is a **Redis**-backed async job queue..."
    }
  ],
  "total": 12,
  "latency_ms": 145,
  "search_types_used": ["keyword", "semantic"]
}
```

### Graph (`/api/graph`)

```
GET    /api/graph/nodes                 All graph nodes (projects + technologies)
GET    /api/graph/edges                 All graph edges (relationships)
GET    /api/graph/project/{slug}        Project subgraph (2 hops)
POST   /api/graph/relationships         Create manual relationship
DELETE /api/graph/relationships/{id}    Delete relationship
```

### Admin (`/api/admin`)

```
POST   /api/admin/index/full            Trigger full re-index
POST   /api/admin/index/discovery       Trigger discovery only
GET    /api/admin/index/status          Get current index run status
GET    /api/admin/health                System health check
GET    /api/admin/stats                 Counts: projects, docs, chunks, embeddings
```

---

## Service Layer

### DiscoveryService

```python
class DiscoveryService:
    async def scan_all(self) -> IndexRun:
        """Scan all configured directories, upsert projects."""

    async def scan_directory(self, path: str) -> list[ProjectCandidate]:
        """Find project roots in a directory (non-recursive at top level)."""

    async def detect_project(self, path: str) -> ProjectCandidate | None:
        """Detect if path is a project root. Return metadata if yes."""

    async def _detect_framework(self, path: str) -> tuple[str, str]:
        """Return (language, framework) from project markers."""
```

**Framework detection priority:**
1. `package.json` → check `dependencies` for next, react, vue, svelte
2. `pyproject.toml` / `setup.py` → check deps for fastapi, django, flask
3. `go.mod` → Go project, check for gin, echo, fiber
4. `Cargo.toml` → Rust project, check for actix, axum
5. `Dockerfile` → parse FROM instruction as fallback
6. Language from primary file extension count

### ExtractionService

```python
class ExtractionService:
    PRIORITY_FILES = [
        "README.md", "README.rst", "CLAUDE.md", "CODEX.md",
        "AGENTS.md", "PLAN.md", "ARCHITECTURE.md", "TODO.md",
        "package.json", "pyproject.toml", "requirements.txt",
        "go.mod", "Cargo.toml", "Dockerfile", "docker-compose.yml",
        "docker-compose.yaml", ".env.example"
    ]

    async def extract(self, project_id: UUID) -> list[Document]:
        """Extract all priority files for a project."""

    async def extract_file(self, project: Project, path: str) -> Document | None:
        """Extract a single file. Skip if hash unchanged."""

    async def parse_package_json(self, content: str) -> dict:
        """Extract name, version, scripts, deps, devDeps."""

    async def parse_pyproject(self, content: str) -> dict:
        """Extract project name, version, dependencies."""

    async def parse_docker_compose(self, content: str) -> dict:
        """Extract services with ports, volumes, environment."""
```

### OKFService

```python
class OKFService:
    OKF_TEMPLATE = """
You are analyzing a software project. Generate a structured OKF (Operational Knowledge File).

Project: {name}
Path: {path}
Language: {language}
Framework: {framework}

Available documents:
{documents}

Generate the OKF in this exact format:
# {name}

## Purpose
[1-2 sentences describing what this project does]

## Architecture
[Stack, key components, how they connect]

## Key APIs
[List of important endpoints or interfaces]

## Ports
[Services and their ports]

## Environment Variables
[Required env vars with descriptions]

## Key Decisions
[Architecture decisions and why]

## Commands
[How to run, build, test, deploy]

## Deployment
[How this is deployed]

## Related Projects
[Projects this depends on or relates to]
"""

    async def generate(self, project_id: UUID) -> str:
        """Generate OKF content via LiteLLM."""

    async def write_to_disk(self, project: Project, content: str) -> str:
        """Write buildos.okf.md to project directory. Return path."""

    async def store_version(self, project_id: UUID, content: str) -> Document:
        """Store OKF as document in DB."""
```

### SearchService

```python
class SearchService:
    async def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        limit: int = 20,
    ) -> SearchResponse:
        """Hybrid search: keyword + semantic + graph, merged."""

    async def keyword_search(self, query: str, limit: int) -> list[SearchResult]:
        """PostgreSQL FTS with ts_rank."""

    async def semantic_search(self, query: str, limit: int) -> list[SearchResult]:
        """pgvector cosine similarity on embeddings."""

    async def graph_search(self, query: str, limit: int) -> list[SearchResult]:
        """Find related projects from matched projects."""

    def _merge_results(
        self,
        keyword: list[SearchResult],
        semantic: list[SearchResult],
        graph: list[SearchResult],
    ) -> list[SearchResult]:
        """
        Merge and re-rank. Score = 0.4*kw + 0.4*sem + 0.2*graph.
        Deduplicate by chunk_id.
        """
```

### EmbeddingService

```python
class EmbeddingService:
    async def embed_document(self, document_id: UUID) -> int:
        """Chunk document, generate embeddings, store chunks. Return chunk count."""

    def _chunk_text(self, text: str) -> list[str]:
        """
        Split into overlapping chunks of CHUNK_SIZE tokens.
        Use tiktoken for accurate token counting.
        """

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Call LiteLLM embedding API. Batch size = 100."""

    async def update_tsv(self, chunk_ids: list[UUID]) -> None:
        """Update tsvector column for keyword search."""
```

---

## ARQ Workers (`app/workers/tasks.py`)

```python
async def discover_projects(ctx: dict) -> dict:
    """Scan directories, upsert projects, queue extraction jobs."""

async def extract_project(ctx: dict, project_id: str) -> dict:
    """Extract documents for one project, queue OKF + embedding jobs."""

async def generate_okf(ctx: dict, project_id: str) -> dict:
    """Generate OKF for one project, write to disk + DB."""

async def embed_document(ctx: dict, document_id: str) -> dict:
    """Chunk and embed one document."""

async def build_graph(ctx: dict, project_id: str) -> dict:
    """Detect and store technology relationships for one project."""

async def run_health_check(ctx: dict, project_id: str) -> dict:
    """Compute health score for one project."""
```

**Cron schedule:**
```python
class WorkerSettings:
    functions = [discover_projects, extract_project, generate_okf,
                 embed_document, build_graph, run_health_check]
    cron_jobs = [
        cron(discover_projects, minute={0, 15, 30, 45}),   # every 15 min
        cron(run_health_check, hour={0, 6, 12, 18}),       # 4x daily
    ]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
```

---

## Error Handling

- All service methods raise typed exceptions: `ProjectNotFoundError`, `ExtractionError`, `EmbeddingError`
- Route handlers catch and convert to appropriate HTTP status codes
- Worker jobs catch all exceptions, store in `project_index_state.errors`, and don't crash the worker
- LiteLLM calls: retry 3x with exponential backoff, fallback model on provider error

---

## Health Check

`GET /api/admin/health` returns:
```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "workers": "ok",
    "litellm": "ok"
  },
  "stats": {
    "projects": 42,
    "documents": 318,
    "chunks": 4821,
    "embeddings": 4821,
    "relationships": 156
  }
}
```
