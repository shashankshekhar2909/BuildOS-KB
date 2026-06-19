# 10 — Graph Engine

## Overview

Knowledge graph stored in PostgreSQL — no separate graph database needed at this scale.

Entities: Project, Technology, Document, API, Container, Deployment
Relationships: USES, DEPLOYS, DEPENDS_ON, RELATED_TO, DOCUMENTS, EXPOSES, SHARES_PATTERN

---

## Entity Types

| Type | Description | Key Attributes |
|------|-------------|----------------|
| `project` | A software project | slug, name, language, framework |
| `technology` | A framework, language, tool, DB | name, category |
| `document` | A file extracted from a project | type, title, project_id |
| `api` | An API endpoint exposed by a project | method, path, project_id |
| `container` | A Docker container | service_name, image, project_id |
| `deployment` | A deployment target | environment, host, project_id |

Phase 1 implements: `project`, `technology`
Phase 2 adds: `api`, `container`, `deployment`

---

## Relationship Types

| Relationship | Source → Target | Auto-detected | Example |
|-------------|-----------------|---------------|---------|
| `USES` | project → technology | Yes | BuildOS USES postgresql |
| `DEPLOYS` | project → container | Yes (from docker-compose) | BuildOS DEPLOYS postgres |
| `DEPENDS_ON` | project → project | Semi-auto | AuraStay DEPENDS_ON BuildOS |
| `RELATED_TO` | project → project | Manual or AI | BuildOS RELATED_TO NodeCmdr |
| `SHARES_PATTERN` | project → project | Yes (shared tech stack) | BuildOS SHARES_PATTERN AuraStay |
| `DOCUMENTS` | document → project | Yes | README.md DOCUMENTS BuildOS |
| `EXPOSES` | project → api | Phase 2 | FastAPI EXPOSES /api/projects |

---

## Auto-Detection Logic

### USES relationships (project → technology)
Triggered by extraction job. Source: parsed `package.json`, `pyproject.toml`, etc.

```python
async def detect_uses_relationships(project: Project, documents: list[Document]) -> list[Relationship]:
    relationships = []

    for doc in documents:
        if doc.type == "package_json" and doc.parsed_data:
            deps = {
                **doc.parsed_data.get("dependencies", {}),
                **doc.parsed_data.get("devDependencies", {}),
            }
            for dep_name in deps:
                tech = await TechRepo.get_or_create(normalize_tech_name(dep_name))
                relationships.append(Relationship(
                    source_id=project.id,
                    source_type="project",
                    target_id=tech.id,
                    target_type="technology",
                    relationship="USES",
                    confidence=1.0,
                    detected_from="package_json",
                ))

        elif doc.type == "pyproject" and doc.parsed_data:
            for dep_name in doc.parsed_data.get("dependencies", []):
                tech = await TechRepo.get_or_create(normalize_tech_name(dep_name))
                relationships.append(Relationship(...))

    return relationships
```

### SHARES_PATTERN relationships (project → project)
Triggered by graph build job. Two projects share a pattern if they use 3+ of the same technologies.

```python
async def detect_shares_pattern(project_id: UUID) -> list[Relationship]:
    # Get technologies for this project
    my_techs = await ProjectTechRepo.get_tech_ids(project_id)

    # Find other projects sharing at least 3 technologies
    rows = await db.execute("""
        SELECT pt.project_id, COUNT(*) as shared_count
        FROM core.project_technologies pt
        WHERE pt.technology_id = ANY($1)
          AND pt.project_id != $2
        GROUP BY pt.project_id
        HAVING COUNT(*) >= 3
        ORDER BY shared_count DESC
    """, list(my_techs), project_id)

    relationships = []
    for row in rows:
        confidence = min(row.shared_count / 5.0, 1.0)  # 5+ techs = full confidence
        relationships.append(Relationship(
            source_id=project_id,
            source_type="project",
            target_id=row.project_id,
            target_type="project",
            relationship="SHARES_PATTERN",
            confidence=confidence,
            metadata={"shared_tech_count": row.shared_count},
        ))

    return relationships
```

---

## Graph Queries

### Get subgraph for a project (React Flow data)

```python
async def get_project_subgraph(slug: str, depth: int = 2) -> GraphData:
    project = await ProjectRepo.get_by_slug(slug)

    # Get related projects via recursive CTE
    related_rows = await db.execute("""
        WITH RECURSIVE graph_walk AS (
            SELECT
                $1::uuid AS source_id,
                r.target_id,
                r.target_type,
                r.relationship,
                r.weight,
                1 AS depth,
                ARRAY[$1::uuid] AS visited
            FROM graph.relationships r
            WHERE r.source_id = $1

            UNION ALL

            SELECT
                gw.target_id AS source_id,
                r.target_id,
                r.target_type,
                r.relationship,
                r.weight * 0.7,
                gw.depth + 1,
                gw.visited || gw.target_id
            FROM graph.relationships r
            JOIN graph_walk gw ON gw.target_id = r.source_id
            WHERE gw.depth < $2
            AND NOT r.target_id = ANY(gw.visited)
        )
        SELECT DISTINCT source_id, target_id, target_type, relationship, weight, depth
        FROM graph_walk
    """, project.id, depth)

    # Build nodes
    nodes = [GraphNode(id=project.id, type="project", label=project.name, data=project)]
    edges = []
    seen_ids = {project.id}

    for row in related_rows:
        if row.target_type == "project" and row.target_id not in seen_ids:
            related_project = await ProjectRepo.get(row.target_id)
            nodes.append(GraphNode(
                id=row.target_id,
                type="project",
                label=related_project.name,
                data=related_project,
            ))
            seen_ids.add(row.target_id)

        edges.append(GraphEdge(
            id=f"{row.source_id}-{row.target_id}-{row.relationship}",
            source=str(row.source_id),
            target=str(row.target_id),
            label=row.relationship,
            weight=row.weight,
        ))

    return GraphData(nodes=nodes, edges=edges)
```

### Get all technology relationships for visualization

```python
async def get_tech_graph() -> GraphData:
    """
    Returns all projects + their top technologies for global graph view.
    Limit technologies to top 20 by usage to avoid noise.
    """
    top_techs = await db.execute("""
        SELECT t.id, t.name, t.display_name, COUNT(pt.project_id) as usage_count
        FROM core.technologies t
        JOIN core.project_technologies pt ON pt.technology_id = t.id
        GROUP BY t.id, t.name, t.display_name
        ORDER BY usage_count DESC
        LIMIT 20
    """)

    tech_ids = {row.id for row in top_techs}

    uses_rels = await db.execute("""
        SELECT pt.project_id, pt.technology_id, pt.confidence
        FROM core.project_technologies pt
        WHERE pt.technology_id = ANY($1)
    """, list(tech_ids))

    # Build nodes + edges
    ...
```

---

## Manual Relationships API

Allow users to create relationships the auto-detector missed:

```
POST /api/graph/relationships
{
  "source_slug": "buildos",
  "target_slug": "aurastay-hms",
  "relationship": "DEPENDS_ON",
  "metadata": {"reason": "shared user auth service"}
}
```

Manual relationships have `auto_detected = false` and `confidence = 1.0`.

---

## Graph Statistics

```python
async def get_graph_stats() -> dict:
    return {
        "total_nodes": await db.scalar("SELECT COUNT(*) FROM core.projects"),
        "total_edges": await db.scalar("SELECT COUNT(*) FROM graph.relationships"),
        "relationship_types": await db.fetch("""
            SELECT relationship, COUNT(*) as count
            FROM graph.relationships
            GROUP BY relationship
            ORDER BY count DESC
        """),
        "most_connected": await db.fetch("""
            SELECT p.name, COUNT(r.id) as connections
            FROM core.projects p
            LEFT JOIN graph.relationships r ON r.source_id = p.id
            GROUP BY p.id, p.name
            ORDER BY connections DESC
            LIMIT 10
        """),
    }
```

---

## Technology Normalization

Map package names to canonical technology names:

```python
TECH_ALIASES = {
    # Python
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "sqlalchemy": "sqlalchemy",
    "pydantic": "pydantic",
    "arq": "arq",
    "redis": "redis",
    "asyncpg": "postgresql",
    "psycopg2": "postgresql",
    "psycopg": "postgresql",

    # JavaScript/TypeScript
    "next": "nextjs",
    "react": "react",
    "react-dom": "react",
    "@tanstack/react-query": "react-query",
    "@xyflow/react": "react-flow",
    "@carbon/react": "carbon",
    "prisma": "prisma",
    "drizzle-orm": "drizzle",
    "pg": "postgresql",

    # Infrastructure
    "docker-compose": "docker",
}

def normalize_tech_name(raw: str) -> str:
    clean = raw.lower().strip().lstrip("@").split("/")[-1]
    return TECH_ALIASES.get(clean, clean)
```
