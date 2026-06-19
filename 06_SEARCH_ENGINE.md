# 06 — Search Engine

## Overview

Three search modes, always run in parallel, merged by weighted scoring.

```
Query
  ├─→ KeywordSearch     PostgreSQL FTS (tsvector + ts_rank)
  ├─→ SemanticSearch    pgvector cosine similarity
  └─→ GraphSearch       Relationship traversal from matched projects

        ↓
    MergeRanker
    score = 0.4·keyword + 0.4·semantic + 0.2·graph

        ↓
    Deduplication (by chunk_id)

        ↓
    SearchResponse
```

---

## Keyword Search

**Technology:** PostgreSQL full-text search

**How it works:**
1. `tsvector` column on `document_chunks.tsv`, updated on insert/update
2. Query converted to `tsquery` via `plainto_tsquery('english', $1)` (handles stemming, stopwords)
3. Ranked with `ts_rank_cd` (cover density, penalizes scattered matches)
4. Highlighted with `ts_headline`

**SQL:**
```sql
SELECT
    dc.id AS chunk_id,
    dc.chunk_text,
    dc.document_id,
    d.title AS document_title,
    d.type AS document_type,
    p.id AS project_id,
    p.name AS project_name,
    p.slug AS project_slug,
    ts_rank_cd(dc.tsv, query) AS rank,
    ts_headline(
        'english',
        dc.chunk_text,
        query,
        'MaxWords=35, MinWords=15, StartSel=**, StopSel=**'
    ) AS highlight
FROM search.document_chunks dc
JOIN core.documents d ON d.id = dc.document_id
JOIN core.projects p ON p.id = dc.project_id,
     plainto_tsquery('english', $1) query
WHERE dc.tsv @@ query
  AND ($2::text IS NULL OR p.language = $2)    -- language filter
  AND ($3::text IS NULL OR p.framework = $3)   -- framework filter
ORDER BY rank DESC
LIMIT $4;
```

**Index:** GIN index on `tsv` column (already in schema).

**Normalization:** Map raw `ts_rank` to 0-1 by dividing by max rank in result set.

---

## Semantic Search

**Technology:** pgvector + OpenAI `text-embedding-3-small` (1536 dims)

**How it works:**
1. Embed query using same model as document chunks
2. Find nearest neighbors via cosine distance (`<=>` operator)
3. Filter by minimum similarity threshold (default: 0.3)
4. IVFFlat index for approximate nearest neighbor (fast at scale)

**SQL:**
```sql
SELECT
    dc.id AS chunk_id,
    dc.chunk_text,
    dc.document_id,
    d.title AS document_title,
    d.type AS document_type,
    p.id AS project_id,
    p.name AS project_name,
    p.slug AS project_slug,
    1 - (dc.embedding <=> $1::vector) AS similarity
FROM search.document_chunks dc
JOIN core.documents d ON d.id = dc.document_id
JOIN core.projects p ON p.id = dc.project_id
WHERE dc.embedding IS NOT NULL
  AND 1 - (dc.embedding <=> $1::vector) > $2   -- similarity threshold
  AND ($3::text IS NULL OR p.language = $3)
ORDER BY dc.embedding <=> $1::vector
LIMIT $4;
```

**Embedding pipeline:**
```python
async def embed_query(query: str) -> list[float]:
    response = await litellm.aembedding(
        model=settings.EMBEDDING_MODEL,
        input=[query]
    )
    return response.data[0].embedding
```

**Index configuration:**
```sql
CREATE INDEX idx_chunks_embedding ON search.document_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);   -- sqrt(row_count), recalibrate when rows > 10000
```

---

## Graph Search

**Technology:** PostgreSQL recursive CTE

**How it works:**
1. Run keyword search to find matching projects
2. For each matched project, traverse relationships up to 2 hops
3. Return related projects with their best documents as additional results
4. Score = matched project score × hop decay (0.7^hop)

**SQL:**
```sql
WITH matched_projects AS (
    -- Projects matched by keyword
    SELECT DISTINCT p.id, MAX(ts_rank_cd(dc.tsv, $1)) AS base_score
    FROM search.document_chunks dc
    JOIN core.projects p ON p.id = dc.project_id
    WHERE dc.tsv @@ $1
    GROUP BY p.id
),
related AS (
    -- 1-hop relationships
    SELECT
        r.target_id AS project_id,
        r.relationship,
        mp.base_score * 0.7 AS score,
        1 AS depth
    FROM graph.relationships r
    JOIN matched_projects mp ON mp.id = r.source_id
    WHERE r.target_type = 'project'

    UNION ALL

    -- 2-hop relationships
    SELECT
        r2.target_id,
        r2.relationship,
        rel.score * 0.7,
        2
    FROM graph.relationships r2
    JOIN related rel ON rel.project_id = r2.source_id
    WHERE r2.target_type = 'project'
    AND rel.depth < 2
)
SELECT DISTINCT ON (project_id)
    project_id,
    relationship,
    score,
    depth
FROM related
ORDER BY project_id, score DESC;
```

---

## Merge & Ranking

```python
class MergeRanker:
    WEIGHTS = {"keyword": 0.4, "semantic": 0.4, "graph": 0.2}

    def merge(
        self,
        keyword: list[SearchResult],
        semantic: list[SearchResult],
        graph: list[SearchResult],
    ) -> list[SearchResult]:
        scores: dict[str, dict] = {}

        for result in keyword:
            scores[result.chunk_id] = {
                "result": result,
                "keyword": result.score,
                "semantic": 0.0,
                "graph": 0.0,
            }

        for result in semantic:
            if result.chunk_id in scores:
                scores[result.chunk_id]["semantic"] = result.score
            else:
                scores[result.chunk_id] = {
                    "result": result,
                    "keyword": 0.0,
                    "semantic": result.score,
                    "graph": 0.0,
                }

        for result in graph:
            if result.chunk_id in scores:
                scores[result.chunk_id]["graph"] = result.score
            else:
                scores[result.chunk_id] = {
                    "result": result,
                    "keyword": 0.0,
                    "semantic": 0.0,
                    "graph": result.score,
                }

        final = []
        for chunk_id, data in scores.items():
            combined_score = (
                self.WEIGHTS["keyword"] * data["keyword"]
                + self.WEIGHTS["semantic"] * data["semantic"]
                + self.WEIGHTS["graph"] * data["graph"]
            )
            result = data["result"]
            result.score = combined_score
            result.score_breakdown = {
                "keyword": data["keyword"],
                "semantic": data["semantic"],
                "graph": data["graph"],
            }
            final.append(result)

        return sorted(final, key=lambda r: r.score, reverse=True)
```

---

## Caching

Redis cache with 5-minute TTL:

```python
cache_key = f"search:{hashlib.md5(f'{query}:{filters}'.encode()).hexdigest()}"

cached = await redis.get(cache_key)
if cached:
    return SearchResponse.model_validate_json(cached)

results = await _execute_search(query, filters)

await redis.setex(cache_key, settings.SEARCH_CACHE_TTL, results.model_dump_json())
return results
```

Cache invalidated on project re-index: `await redis.delete(f"search:*")` (pattern delete via SCAN).

---

## Chunking Strategy

Documents chunked before embedding. Goal: each chunk is semantically self-contained.

```python
def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """
    Token-aware chunking using tiktoken.
    Prefer splitting at paragraph boundaries (double newline).
    Fall back to sentence boundaries (period + space).
    Hard split at chunk_size if no boundary found.
    """
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)

    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)

        # Try to end at a natural boundary
        last_para = chunk_text.rfind("\n\n")
        if last_para > chunk_size // 2:
            chunk_text = chunk_text[:last_para]

        chunks.append(chunk_text.strip())
        start += len(encoding.encode(chunk_text)) - overlap

    return [c for c in chunks if len(c.strip()) > 50]  # skip tiny chunks
```

---

## Search Filters

```python
class SearchFilters(BaseModel):
    language: str | None = None          # typescript, python, go
    framework: str | None = None         # nextjs, fastapi, gin
    document_type: str | None = None     # readme, claude_md, architecture
    project_slug: str | None = None      # restrict to one project
    min_score: float = 0.3
    search_type: Literal["all", "keyword", "semantic", "graph"] = "all"
```

---

## Performance Targets

| Operation | Target | Method |
|-----------|--------|--------|
| Keyword search (10k chunks) | < 50ms | GIN index |
| Semantic search (10k chunks) | < 200ms | IVFFlat index |
| Graph traversal (2 hops) | < 50ms | B-tree indexes on source/target |
| Merge + rank | < 10ms | In-process Python |
| Total with cache hit | < 5ms | Redis |
| Total without cache | < 500ms | All above |

---

## Future: Typesense Integration (Phase 2)

For full-text search at scale (> 100k chunks), migrate keyword search to Typesense:
- Faster BM25 at scale
- Typo tolerance
- Faceting
- Keep pgvector for semantic search
- Merge results after both return
