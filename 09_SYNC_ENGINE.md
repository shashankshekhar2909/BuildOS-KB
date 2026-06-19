# 09 — Sync Engine

## Overview

The sync engine keeps knowledge current. It has three modes:

1. **Startup scan** — full discovery on service start
2. **Scheduled scan** — every 15 minutes, detect new/changed projects
3. **File watcher** (Phase 2) — real-time detection of file changes

All work is async, queued via ARQ, idempotent.

---

## Pipeline

```
Trigger (startup / cron / API)
    │
    ▼
┌───────────────────────┐
│  Discovery Job         │  scan_directories()
│  Find project roots    │  upsert projects table
│  Emit discovered event │
└───────┬───────────────┘
        │ per project (parallel)
        ▼
┌───────────────────────┐
│  Extraction Job        │  read priority files
│  Hash check (skip if   │  parse manifests
│  unchanged)            │  store documents
│  Emit extracted event  │
└───────┬───────────────┘
        │ parallel branches
        ├──────────────────────────────────┐
        ▼                                  ▼
┌───────────────────────┐    ┌────────────────────────┐
│  OKF Generation Job    │    │  Embedding Job          │
│  Build prompt          │    │  Chunk new documents    │
│  Call LLM              │    │  Embed batches          │
│  Write buildos.okf.md  │    │  Store chunks + vectors │
│  Store in DB           │    │  Update tsvector        │
└───────────────────────┘    └────────────────────────┘
        │                                  │
        └──────────────┬───────────────────┘
                       ▼
        ┌───────────────────────┐
        │  Graph Build Job       │  detect tech relationships
        │  shared stack patterns │  store in relationships table
        └───────────────────────┘
                       │
                       ▼
        ┌───────────────────────┐
        │  Health Check Job      │  rule-based scoring
        │  Update health_score   │  generate summary
        └───────────────────────┘
```

---

## Discovery Job

```python
async def discover_projects(ctx: dict) -> dict:
    """
    Scan all configured directories.
    Upsert found projects. Queue extraction for new/changed projects.
    """
    db = ctx["db"]
    redis = ctx["redis"]
    service = DiscoveryService(db)

    run = await IndexRunService(db).create(run_type="incremental")

    projects_found = 0
    projects_queued = 0

    for directory in settings.SCAN_DIRECTORIES:
        expanded = Path(directory).expanduser()
        if not expanded.exists():
            continue

        candidates = await service.scan_directory(str(expanded))

        for candidate in candidates:
            project, is_new = await service.upsert_project(candidate)
            projects_found += 1

            # Queue extraction if new or files changed since last index
            if is_new or await service.has_changes_since(project):
                await arq_enqueue(redis, "extract_project", project_id=str(project.id))
                projects_queued += 1

    await IndexRunService(db).complete(run.id, projects_found=projects_found)

    return {"projects_found": projects_found, "projects_queued": projects_queued}
```

---

## Extraction Job

```python
async def extract_project(ctx: dict, project_id: str) -> dict:
    """
    Read and store priority documents for one project.
    Skip files whose content hash hasn't changed.
    Queue OKF and embedding jobs after.
    """
    db = ctx["db"]
    redis = ctx["redis"]

    project = await ProjectRepo(db).get(UUID(project_id))
    service = ExtractionService(db)

    docs_processed = 0
    docs_changed = 0

    for filename in ExtractionService.PRIORITY_FILES:
        filepath = Path(project.path) / filename
        if not filepath.exists():
            continue

        try:
            doc, changed = await service.extract_file(project, str(filepath))
            docs_processed += 1
            if changed:
                docs_changed += 1
                # Queue embedding for changed document
                await arq_enqueue(redis, "embed_document", document_id=str(doc.id))
        except Exception as e:
            await ProjectIndexStateRepo(db).add_error(
                UUID(project_id), f"extract {filename}: {e}"
            )

    # Always queue OKF if any documents changed
    if docs_changed > 0:
        await arq_enqueue(redis, "generate_okf", project_id=project_id)

    # Update last_indexed_at
    await ProjectRepo(db).touch(UUID(project_id))

    return {"docs_processed": docs_processed, "docs_changed": docs_changed}
```

---

## OKF Generation Job

```python
async def generate_okf(ctx: dict, project_id: str) -> dict:
    """
    Generate or regenerate the OKF for a project.
    Skip if user has manually overridden OKF.
    """
    db = ctx["db"]
    project = await ProjectRepo(db).get(UUID(project_id))

    if project.okf_overridden:
        return {"status": "skipped", "reason": "user overridden"}

    service = OKFService(db)

    # Gather context: all documents for this project
    documents = await DocumentRepo(db).list_for_project(UUID(project_id))
    context = service.build_prompt_context(project, documents)

    # Check if context changed since last OKF
    context_hash = hashlib.sha256(context.encode()).hexdigest()
    if await OKFRepo(db).hash_matches(UUID(project_id), context_hash):
        return {"status": "skipped", "reason": "no changes"}

    # Generate via LLM
    okf_content = await service.generate(context)

    # Write to disk
    okf_path = await service.write_to_disk(project, okf_content)

    # Store in DB
    await service.store_version(UUID(project_id), okf_content, context_hash)

    # Queue graph build (OKF contains Related Projects section)
    await arq_enqueue(ctx["redis"], "build_graph", project_id=project_id)

    return {"status": "generated", "okf_path": okf_path}
```

---

## Embedding Job

```python
async def embed_document(ctx: dict, document_id: str) -> dict:
    """
    Chunk a document and generate embeddings for all chunks.
    Delete old chunks first (re-index is idempotent).
    """
    db = ctx["db"]
    doc = await DocumentRepo(db).get(UUID(document_id))

    if not doc.content:
        return {"status": "skipped", "reason": "no content"}

    service = EmbeddingService(db)

    # Delete existing chunks (handles re-index)
    await ChunkRepo(db).delete_for_document(UUID(document_id))

    # Chunk
    chunks = service.chunk_text(doc.content)
    if not chunks:
        return {"status": "skipped", "reason": "no chunks after split"}

    # Embed in batches of 100
    batch_size = 100
    total_chunks = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        embeddings = await service.embed_batch(batch)

        for j, (text, embedding) in enumerate(zip(batch, embeddings)):
            await ChunkRepo(db).create(
                document_id=UUID(document_id),
                project_id=doc.project_id,
                chunk_index=i + j,
                chunk_text=text,
                embedding=embedding,
            )
        total_chunks += len(batch)

    # Update tsvectors in bulk
    await ChunkRepo(db).update_tsvectors_for_document(UUID(document_id))

    return {"status": "embedded", "chunks": total_chunks}
```

---

## Graph Build Job

```python
async def build_graph(ctx: dict, project_id: str) -> dict:
    """
    Detect technology relationships for a project.
    Store in relationships table.
    Run after OKF generation.
    """
    db = ctx["db"]
    project = await ProjectRepo(db).get(UUID(project_id))
    service = GraphService(db)

    # Detect tech usage from project_technologies
    techs = await ProjectTechRepo(db).list_for_project(UUID(project_id))

    # Find other projects sharing same technologies
    relationships_created = 0
    for tech in techs:
        sharing_projects = await ProjectTechRepo(db).projects_using_tech(tech.technology_id)
        for other in sharing_projects:
            if other.project_id == UUID(project_id):
                continue
            rel, created = await RelationshipRepo(db).upsert(
                source_id=UUID(project_id),
                source_type="project",
                target_id=other.project_id,
                target_type="project",
                relationship="SHARES_PATTERN",
                confidence=tech.confidence * other.confidence,
                metadata={"via_technology": tech.technology_id},
            )
            if created:
                relationships_created += 1

    return {"relationships_created": relationships_created}
```

---

## Change Detection

```python
async def has_changes_since(self, project: Project) -> bool:
    """
    Check if any priority files changed since last index.
    Uses file mtime as fast check before reading content.
    """
    if not project.last_indexed_at:
        return True

    last_indexed = project.last_indexed_at.timestamp()

    for filename in self.PRIORITY_FILES:
        filepath = Path(project.path) / filename
        if filepath.exists():
            if filepath.stat().st_mtime > last_indexed:
                return True

    return False
```

---

## Job Deduplication

ARQ doesn't deduplicate by default. Add Redis-based dedup:

```python
async def arq_enqueue(redis, function_name: str, **kwargs) -> bool:
    """
    Enqueue job only if not already queued for same arguments.
    Returns True if enqueued, False if skipped.
    """
    dedup_key = f"job_dedup:{function_name}:{json.dumps(kwargs, sort_keys=True)}"

    # Set with 10-minute TTL (job should complete within 10 min)
    set_result = await redis.set(dedup_key, "1", ex=600, nx=True)

    if set_result:
        await redis.enqueue_job(function_name, **kwargs)
        return True

    return False  # already queued
```

---

## Scheduler

```python
class WorkerSettings:
    functions = [
        discover_projects,
        extract_project,
        generate_okf,
        embed_document,
        build_graph,
        run_health_check,
    ]
    cron_jobs = [
        cron(discover_projects, minute={0, 15, 30, 45}),   # every 15 min
        cron(run_health_check, hour={0, 6, 12, 18}),       # 4x daily
    ]
    max_jobs = 10           # max concurrent jobs
    job_timeout = 300       # 5 minutes max per job
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    on_startup = on_startup
    on_shutdown = on_shutdown
```

---

## Phase 2: File Watcher

Replace 15-minute polling with `watchdog` (Python) for instant detection:

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ProjectFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(tuple(WATCH_EXTENSIONS)):
            project = find_project_for_path(event.src_path)
            if project:
                asyncio.run_coroutine_threadsafe(
                    arq_enqueue(redis, "extract_project", project_id=str(project.id)),
                    loop
                )
```

Extensions to watch: `.md`, `.json`, `.toml`, `.txt`, `.yml`, `.yaml`
