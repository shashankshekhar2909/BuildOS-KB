# 01 — Product Requirements

## User Stories

### Discovery
- As a developer, I want BuildOS to automatically find all projects in `~/project`, `~/projects`, and `~/workspace` so I don't manually register anything
- As a developer, I want projects detected by framework (Next.js, FastAPI, Go, Rust) so context extraction is targeted
- As a developer, I want re-indexing triggered on file changes so knowledge stays fresh without manual intervention

### Context Extraction
- As an AI agent, I want structured project summaries available via MCP so I can answer questions without reading raw files
- As a developer, I want CLAUDE.md, CODEX.md, AGENTS.md, README.md, PLAN.md read and parsed automatically
- As a developer, I want `package.json`, `pyproject.toml`, `requirements.txt`, `go.mod`, `Cargo.toml` parsed for stack detection

### OKF Generation
- As a developer, I want every project to have a machine-readable `buildos.okf.md` that summarizes purpose, architecture, APIs, and decisions
- As an AI agent, I want OKF files to follow a consistent schema so I can parse them programmatically

### Search
- As a developer, I want to search across all projects using natural language ("show me projects that deploy with Docker")
- As a developer, I want keyword search for exact terms (function names, env vars, port numbers)
- As an AI agent, I want graph-aware search that returns related projects when I query one

### MCP
- As a Claude Code user, I want a configured MCP server that exposes all knowledge tools
- As an AI agent, I want `list_projects`, `get_project`, `search`, `related`, `reindex` tools
- As a developer, I want MCP responses fast enough for interactive use (< 500ms for search)

### Frontend
- As a developer, I want a web UI to browse all projects, documents, and relationships
- As a developer, I want a search interface like Notion/Obsidian — one box, instant results
- As a developer, I want a graph view (React Flow) showing project relationships

---

## Functional Requirements

### Module 1 — Project Discovery Engine
- FR-1.1: Scan configured directories on startup and on schedule (every 15 minutes)
- FR-1.2: Detect project type from: `.git`, `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `Dockerfile`, `docker-compose.yml`
- FR-1.3: Extract: name, path, language, framework, git remote URL, last commit date
- FR-1.4: Store scan results in `projects` table, upsert on re-scan
- FR-1.5: Emit `project.discovered` event to Redis for downstream processing
- FR-1.6: Support configurable ignore patterns (`.git`, `node_modules`, `__pycache__`, `venv`, `.venv`, `dist`, `build`)

### Module 2 — Context Extraction Engine
- FR-2.1: Read priority documents: `README.md`, `CLAUDE.md`, `CODEX.md`, `AGENTS.md`, `PLAN.md`, `ARCHITECTURE.md`, `TODO.md`
- FR-2.2: Parse manifest files: `package.json` (name, version, scripts, dependencies), `pyproject.toml` / `requirements.txt` (deps), `go.mod`, `Cargo.toml`
- FR-2.3: Extract Docker config: `Dockerfile` base image, exposed ports; `docker-compose.yml` services, ports, volumes
- FR-2.4: Store documents in `documents` table with content hash for change detection
- FR-2.5: Only re-extract documents whose content hash changed since last scan

### Module 3 — OKF Engine
- FR-3.1: Generate `buildos.okf.md` for every project using AI (LiteLLM gateway)
- FR-3.2: OKF schema: Purpose, Architecture, Key APIs, Ports, Environment Variables, Key Decisions, Related Projects, Commands, Deployment
- FR-3.3: Regenerate OKF when any source document changes
- FR-3.4: Version OKF files (store previous versions in DB, write latest to project directory)
- FR-3.5: Support manual OKF override (if user writes their own, don't overwrite)

### Module 4 — Knowledge Graph Engine
- FR-4.1: Entity types: `Project`, `Technology`, `Document`, `API`, `Container`, `Deployment`
- FR-4.2: Relationship types: `USES`, `DEPLOYS`, `DEPENDS_ON`, `RELATED_TO`, `DOCUMENTS`, `EXPOSES`
- FR-4.3: Auto-detect relationships from shared technology stacks
- FR-4.4: Support manual relationship creation via API
- FR-4.5: Graph stored in `relationships` table in PostgreSQL (not a separate graph DB)

### Module 5 — Search Engine
- FR-5.1: Keyword search using PostgreSQL full-text search (`tsvector`)
- FR-5.2: Semantic search using `pgvector` cosine similarity on document chunks
- FR-5.3: Graph search: given a project, return related projects via relationship traversal
- FR-5.4: Hybrid merge: score = `0.4 * keyword + 0.4 * semantic + 0.2 * graph_proximity`
- FR-5.5: Search results include: project name, document title, matched chunk, relevance score, relationship path

### Module 6 — MCP Server
- FR-6.1: Implement MCP protocol (JSON-RPC 2.0 over stdio or HTTP/SSE)
- FR-6.2: Tools: `list_projects`, `get_project`, `search`, `related`, `reindex`, `get_okf`
- FR-6.3: All tools return structured JSON with consistent schema
- FR-6.4: MCP server runnable as standalone process: `uv run mcp serve`

### Module 7 — Frontend
- FR-7.1: Dashboard: counts for projects, documents, embeddings, relationships
- FR-7.2: Projects list: name, stack, last scan, health indicator
- FR-7.3: Project detail: tabbed view (Overview, Architecture, Knowledge, Files, Graph)
- FR-7.4: Search: universal search box, real-time results, filter by type/tech/language
- FR-7.5: Graph view: React Flow, nodes = projects, edges = relationships, interactive

---

## Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Search latency (keyword) | < 100ms p99 |
| Search latency (semantic) | < 500ms p99 |
| Discovery scan (50 projects) | < 30 seconds |
| OKF generation per project | < 15 seconds |
| MCP tool response | < 500ms p99 |
| Frontend initial load | < 2 seconds |
| Uptime (local service) | Best-effort; graceful restart |
| Data storage | Local PostgreSQL only |

---

## Acceptance Criteria

### Phase 1 — Backend Foundation
- [ ] `GET /api/projects` returns all discovered projects
- [ ] Discovery scan finds all projects in configured directories
- [ ] Projects table populated with correct framework detection
- [ ] Redis connection healthy, ARQ workers running

### Phase 2 — Context Extraction
- [ ] README.md content stored in documents table for each project
- [ ] CLAUDE.md, CODEX.md parsed and stored when present
- [ ] `package.json` / `pyproject.toml` dependencies extracted
- [ ] Document hash change detection prevents duplicate work

### Phase 3 — OKF
- [ ] `buildos.okf.md` generated and written to each project directory
- [ ] OKF contains all required sections
- [ ] OKF regenerates when source changes
- [ ] Previous OKF version stored in DB

### Phase 4 — Search
- [ ] Keyword search returns correct results with highlight
- [ ] Semantic search returns semantically relevant results
- [ ] Hybrid merge produces better results than either alone

### Phase 5 — MCP
- [ ] Claude Code connects to MCP server without errors
- [ ] `list_projects` returns all projects
- [ ] `search` returns relevant results
- [ ] `get_project` returns full OKF + metadata

### Phase 6 — UI
- [ ] Dashboard loads without errors
- [ ] Projects page shows all projects with correct stack
- [ ] Search returns results in < 500ms
- [ ] Graph renders project relationships
