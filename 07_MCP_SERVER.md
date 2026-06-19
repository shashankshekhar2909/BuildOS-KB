# 07 — MCP Server

## Overview

BuildOS exposes a Model Context Protocol (MCP) server that gives Claude, Codex, AGY, and any MCP-compatible client full access to the knowledge hub.

Protocol: MCP (JSON-RPC 2.0)
Transport: HTTP/SSE (remote) or stdio (local)
Port: 8100 (HTTP mode)

---

## Integration

### Claude Code (stdio)
```bash
claude mcp add buildos-kb -- uv run --directory /path/to/buildos-kb/mcp python -m app.mcp_server
```

### Claude Code (HTTP/SSE)
```json
// ~/.claude/settings.json
{
  "mcpServers": {
    "buildos-kb": {
      "type": "sse",
      "url": "http://localhost:8100/mcp"
    }
  }
}
```

### Codex
```json
// ~/.codex/config.json
{
  "mcp": {
    "servers": {
      "buildos-kb": {
        "transport": "http",
        "url": "http://localhost:8100/mcp"
      }
    }
  }
}
```

---

## Tools

### `list_projects`

List all indexed projects with basic metadata.

**Input:**
```json
{
  "language": "string | null",      // filter: typescript, python, go
  "framework": "string | null",     // filter: nextjs, fastapi, gin
  "status": "string | null",        // filter: active, archived
  "limit": "integer"                // default: 50, max: 200
}
```

**Output:**
```json
{
  "projects": [
    {
      "name": "BuildOS",
      "slug": "buildos",
      "path": "/home/shashank/project/buildos",
      "language": "typescript",
      "framework": "nextjs",
      "description": "Private AI operating system",
      "status": "active",
      "health_score": 85,
      "technologies": ["nextjs", "typescript", "tailwind", "postgresql"],
      "last_indexed_at": "2026-06-18T10:00:00Z"
    }
  ],
  "total": 42
}
```

---

### `get_project`

Get full details for a single project, including OKF content.

**Input:**
```json
{
  "slug": "string"    // required: project slug (e.g. "buildos")
}
```

**Output:**
```json
{
  "project": {
    "name": "BuildOS",
    "slug": "buildos",
    "path": "/home/shashank/project/buildos",
    "language": "typescript",
    "framework": "nextjs",
    "description": "...",
    "metadata": {
      "ports": [3000, 8000],
      "docker": true,
      "git_url": "git@github.com:user/buildos.git"
    },
    "technologies": ["nextjs", "fastapi", "postgresql", "redis"]
  },
  "okf": "# BuildOS\n\n## Purpose\n...",
  "documents": [
    {
      "type": "readme",
      "title": "README.md",
      "word_count": 342
    }
  ],
  "health": {
    "score": 85,
    "missing_docs": ["ARCHITECTURE.md"],
    "has_tests": true,
    "has_docker": true
  }
}
```

---

### `search`

Hybrid search across all project knowledge.

**Input:**
```json
{
  "query": "string",                // required
  "type": "all | keyword | semantic | graph",  // default: all
  "language": "string | null",
  "framework": "string | null",
  "project_slug": "string | null",  // restrict to one project
  "limit": "integer"                // default: 10, max: 50
}
```

**Output:**
```json
{
  "query": "FastAPI Redis background jobs",
  "results": [
    {
      "project_name": "BuildOS",
      "project_slug": "buildos",
      "document_title": "ARCHITECTURE.md",
      "document_type": "architecture",
      "chunk_text": "ARQ is a Redis-backed async job queue for Python. Workers run as separate processes.",
      "highlight": "ARQ is a **Redis**-backed async job queue for Python.",
      "score": 0.87,
      "score_breakdown": {
        "keyword": 0.72,
        "semantic": 0.91,
        "graph": 0.0
      }
    }
  ],
  "total": 12,
  "latency_ms": 145
}
```

---

### `get_okf`

Get OKF (Operational Knowledge File) for a project. Faster than `get_project` — returns only the OKF markdown.

**Input:**
```json
{
  "slug": "string"
}
```

**Output:**
```json
{
  "slug": "buildos",
  "name": "BuildOS",
  "okf": "# BuildOS\n\n## Purpose\n...",
  "generated_at": "2026-06-18T10:00:00Z",
  "overridden": false
}
```

---

### `related`

Get projects related to a given project via graph relationships.

**Input:**
```json
{
  "slug": "string",       // required
  "depth": "integer",     // default: 2, max: 3
  "relationship": "string | null"  // filter: USES, DEPENDS_ON, DEPLOYS
}
```

**Output:**
```json
{
  "project": "buildos",
  "related": [
    {
      "name": "AuraStay HMS",
      "slug": "aurastay-hms",
      "relationship": "SHARES_PATTERN",
      "depth": 1,
      "reason": "Both use FastAPI + ARQ + PostgreSQL pattern"
    },
    {
      "name": "Node Commander",
      "slug": "node-commander",
      "relationship": "RELATED_TO",
      "depth": 1,
      "reason": "Shares Docker infrastructure"
    }
  ]
}
```

---

### `reindex`

Trigger re-index for a specific project or all projects.

**Input:**
```json
{
  "slug": "string | null",   // null = full re-index of all projects
  "force": "boolean"         // default: false — skip unchanged files if false
}
```

**Output:**
```json
{
  "job_id": "uuid",
  "status": "queued",
  "message": "Re-index queued for buildos"
}
```

---

## MCP Server Implementation

```python
# mcp/server.py
from mcp.server.fastmcp import FastMCP
from app.services.search import SearchService
from app.services.discovery import DiscoveryService
from app.database import get_session

mcp = FastMCP("BuildOS Knowledge Hub")

@mcp.tool()
async def list_projects(
    language: str | None = None,
    framework: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> dict:
    """List all indexed projects. Use to discover what projects exist."""
    async with get_session() as db:
        service = ProjectService(db)
        return await service.list(language=language, framework=framework,
                                   status=status, limit=limit)

@mcp.tool()
async def get_project(slug: str) -> dict:
    """Get full project details including OKF knowledge file."""
    async with get_session() as db:
        service = ProjectService(db)
        return await service.get_full(slug)

@mcp.tool()
async def search(
    query: str,
    type: str = "all",
    language: str | None = None,
    framework: str | None = None,
    project_slug: str | None = None,
    limit: int = 10,
) -> dict:
    """Search across all project knowledge. Supports natural language queries."""
    async with get_session() as db:
        service = SearchService(db)
        filters = SearchFilters(
            language=language, framework=framework,
            project_slug=project_slug, search_type=type
        )
        return await service.search(query, filters, limit)

@mcp.tool()
async def related(
    slug: str,
    depth: int = 2,
    relationship: str | None = None,
) -> dict:
    """Find projects related to the given project via graph relationships."""
    async with get_session() as db:
        service = GraphService(db)
        return await service.get_related(slug, depth, relationship)

@mcp.tool()
async def get_okf(slug: str) -> dict:
    """Get the OKF (Operational Knowledge File) for a project."""
    async with get_session() as db:
        service = OKFService(db)
        return await service.get_for_mcp(slug)

@mcp.tool()
async def reindex(
    slug: str | None = None,
    force: bool = False,
) -> dict:
    """Trigger re-indexing. Omit slug to re-index everything."""
    async with get_session() as db:
        service = IndexService(db)
        return await service.queue_reindex(slug, force)
```

---

## Error Handling

All tools return errors in consistent format:
```json
{
  "error": "ProjectNotFound",
  "message": "No project found with slug 'foobar'",
  "code": 404
}
```

Tool functions never raise exceptions — catch internally and return error dict. This prevents MCP protocol errors that confuse the AI client.

---

## Prompts (Optional Resources)

MCP server also exposes these as resources for context injection:

```python
@mcp.resource("buildos://projects/all")
async def all_projects_summary() -> str:
    """Short summary of all projects for initial context."""
    # Returns condensed list: name, stack, description

@mcp.resource("buildos://project/{slug}")
async def project_okf(slug: str) -> str:
    """Full OKF content for a specific project."""
```

Use in Claude prompts:
```
<resource>buildos://projects/all</resource>
Tell me which projects need architecture documentation.
```
