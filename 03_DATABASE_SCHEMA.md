# 03 — Database Schema

## Setup

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS search;
CREATE SCHEMA IF NOT EXISTS graph;
```

---

## Core Schema

### projects
```sql
CREATE TABLE core.projects (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,           -- kebab-case, URL-safe
    path            TEXT NOT NULL UNIQUE,           -- absolute filesystem path
    language        TEXT,                           -- primary: typescript, python, go, rust
    framework       TEXT,                           -- nextjs, fastapi, gin, actix
    git_url         TEXT,                           -- remote origin URL
    git_branch      TEXT,                           -- default branch
    last_commit_at  TIMESTAMPTZ,
    description     TEXT,                           -- extracted or AI-generated
    status          TEXT NOT NULL DEFAULT 'active', -- active, archived, error
    health_score    INTEGER,                        -- 0-100, computed
    metadata        JSONB NOT NULL DEFAULT '{}',   -- flexible: ports, docker, etc.
    okf_path        TEXT,                           -- path to buildos.okf.md
    okf_overridden  BOOLEAN NOT NULL DEFAULT FALSE, -- user wrote their own OKF
    discovered_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_indexed_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_projects_slug ON core.projects(slug);
CREATE INDEX idx_projects_language ON core.projects(language);
CREATE INDEX idx_projects_framework ON core.projects(framework);
CREATE INDEX idx_projects_status ON core.projects(status);
CREATE INDEX idx_projects_last_indexed ON core.projects(last_indexed_at);
```

### documents
```sql
CREATE TABLE core.documents (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id  UUID NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
    type        TEXT NOT NULL,      -- readme, claude_md, codex_md, agents_md, plan,
                                    -- architecture, package_json, pyproject, dockerfile,
                                    -- docker_compose, okf, other
    title       TEXT NOT NULL,
    path        TEXT NOT NULL,      -- absolute path
    content     TEXT,               -- raw content
    content_hash TEXT NOT NULL,     -- SHA256 of content, for change detection
    word_count  INTEGER,
    char_count  INTEGER,
    parsed_data JSONB,              -- structured extraction: deps, scripts, services, etc.
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(project_id, path)
);

CREATE INDEX idx_documents_project ON core.documents(project_id);
CREATE INDEX idx_documents_type ON core.documents(type);
CREATE INDEX idx_documents_hash ON core.documents(content_hash);
```

### technologies
```sql
CREATE TABLE core.technologies (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL UNIQUE,   -- lowercase: fastapi, nextjs, postgresql
    display_name TEXT NOT NULL,         -- FastAPI, Next.js, PostgreSQL
    category    TEXT NOT NULL,          -- language, framework, database, tool, platform
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE core.project_technologies (
    project_id      UUID NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
    technology_id   UUID NOT NULL REFERENCES core.technologies(id) ON DELETE CASCADE,
    confidence      FLOAT NOT NULL DEFAULT 1.0,  -- 0-1, how certain we are
    detected_from   TEXT,                         -- package_json, dockerfile, pyproject
    PRIMARY KEY (project_id, technology_id)
);

CREATE INDEX idx_project_tech_project ON core.project_technologies(project_id);
CREATE INDEX idx_project_tech_tech ON core.project_technologies(technology_id);
```

---

## Search Schema

### document_chunks
```sql
CREATE TABLE search.document_chunks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID NOT NULL REFERENCES core.documents(id) ON DELETE CASCADE,
    project_id      UUID NOT NULL REFERENCES core.projects(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    chunk_text      TEXT NOT NULL,
    token_count     INTEGER,
    embedding       vector(1536),           -- OpenAI text-embedding-3-small dimensions
    tsv             TSVECTOR,               -- full-text search vector
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(document_id, chunk_index)
);

CREATE INDEX idx_chunks_document ON search.document_chunks(document_id);
CREATE INDEX idx_chunks_project ON search.document_chunks(project_id);
CREATE INDEX idx_chunks_embedding ON search.document_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_chunks_tsv ON search.document_chunks USING GIN(tsv);
```

### search_history
```sql
CREATE TABLE search.search_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query           TEXT NOT NULL,
    filters         JSONB NOT NULL DEFAULT '{}',
    result_count    INTEGER,
    latency_ms      INTEGER,
    search_types    TEXT[],     -- ['keyword', 'semantic', 'graph']
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_search_history_created ON search.search_history(created_at);
```

---

## Graph Schema

### relationships
```sql
CREATE TABLE graph.relationships (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id       UUID NOT NULL,      -- project or technology UUID
    source_type     TEXT NOT NULL,      -- project, technology, document
    target_id       UUID NOT NULL,
    target_type     TEXT NOT NULL,
    relationship    TEXT NOT NULL,      -- USES, DEPLOYS, DEPENDS_ON, RELATED_TO,
                                        -- DOCUMENTS, EXPOSES, SHARES_PATTERN
    weight          FLOAT NOT NULL DEFAULT 1.0,
    confidence      FLOAT NOT NULL DEFAULT 1.0,
    auto_detected   BOOLEAN NOT NULL DEFAULT TRUE,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(source_id, target_id, relationship)
);

CREATE INDEX idx_rel_source ON graph.relationships(source_id, relationship);
CREATE INDEX idx_rel_target ON graph.relationships(target_id, relationship);
CREATE INDEX idx_rel_type ON graph.relationships(relationship);
```

---

## Operations Schema

### index_runs
```sql
CREATE TABLE core.index_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_type        TEXT NOT NULL,      -- full, incremental, single_project
    status          TEXT NOT NULL,      -- pending, running, completed, failed
    projects_found  INTEGER DEFAULT 0,
    projects_indexed INTEGER DEFAULT 0,
    documents_processed INTEGER DEFAULT 0,
    chunks_created  INTEGER DEFAULT 0,
    embeddings_created INTEGER DEFAULT 0,
    errors          JSONB NOT NULL DEFAULT '[]',
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_index_runs_status ON core.index_runs(status);
CREATE INDEX idx_index_runs_created ON core.index_runs(created_at);
```

### project_index_state
```sql
CREATE TABLE core.project_index_state (
    project_id          UUID PRIMARY KEY REFERENCES core.projects(id) ON DELETE CASCADE,
    discovery_completed BOOLEAN NOT NULL DEFAULT FALSE,
    extraction_completed BOOLEAN NOT NULL DEFAULT FALSE,
    okf_completed       BOOLEAN NOT NULL DEFAULT FALSE,
    embedding_completed BOOLEAN NOT NULL DEFAULT FALSE,
    graph_completed     BOOLEAN NOT NULL DEFAULT FALSE,
    last_full_index_at  TIMESTAMPTZ,
    errors              JSONB NOT NULL DEFAULT '[]',
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## Common Queries

### Find all projects using a technology
```sql
SELECT p.name, p.path, p.framework, p.last_indexed_at
FROM core.projects p
JOIN core.project_technologies pt ON pt.project_id = p.id
JOIN core.technologies t ON t.id = pt.technology_id
WHERE t.name = 'fastapi'
ORDER BY p.last_indexed_at DESC;
```

### Keyword search across chunks
```sql
SELECT
    dc.chunk_text,
    d.title,
    d.type,
    p.name AS project_name,
    ts_rank(dc.tsv, plainto_tsquery('english', $1)) AS rank
FROM search.document_chunks dc
JOIN core.documents d ON d.id = dc.document_id
JOIN core.projects p ON p.id = dc.project_id
WHERE dc.tsv @@ plainto_tsquery('english', $1)
ORDER BY rank DESC
LIMIT 20;
```

### Semantic search (nearest neighbors)
```sql
SELECT
    dc.chunk_text,
    d.title,
    p.name AS project_name,
    1 - (dc.embedding <=> $1::vector) AS similarity
FROM search.document_chunks dc
JOIN core.documents d ON d.id = dc.document_id
JOIN core.projects p ON p.id = dc.project_id
WHERE dc.embedding IS NOT NULL
ORDER BY dc.embedding <=> $1::vector
LIMIT 20;
```

### Get project relationships (2 hops)
```sql
WITH RECURSIVE graph_walk AS (
    -- Base: direct relationships
    SELECT source_id, target_id, relationship, 1 AS depth, ARRAY[source_id] AS path
    FROM graph.relationships
    WHERE source_id = $1

    UNION ALL

    -- Recursive: follow relationships up to depth 2
    SELECT r.source_id, r.target_id, r.relationship, gw.depth + 1, gw.path || r.source_id
    FROM graph.relationships r
    JOIN graph_walk gw ON gw.target_id = r.source_id
    WHERE gw.depth < 2
    AND NOT r.source_id = ANY(gw.path)  -- prevent cycles
)
SELECT DISTINCT target_id, relationship, depth
FROM graph_walk
ORDER BY depth, relationship;
```

---

## Migrations

Use `alembic` for schema migrations. Migration files in `backend/alembic/versions/`.

```
alembic upgrade head      # apply all migrations
alembic revision --autogenerate -m "add project health score"
alembic downgrade -1      # roll back one migration
```
