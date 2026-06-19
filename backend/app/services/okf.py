import hashlib
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.project import Project
from app.models.document import Document
from app.config import settings
import structlog

logger = structlog.get_logger()

OKF_SYSTEM = (
    "You are a senior software architect analyzing a codebase. "
    "Generate a structured OKF (Operational Knowledge File) in Markdown. "
    "Be factual — only include information present in the documents. "
    "Be concise. Do not add speculative content."
)

OKF_USER_TEMPLATE = """Project Name: {name}
Path: {path}
Language: {language}
Framework: {framework}
Git URL: {git_url}

=== DOCUMENTS ===
{documents}
=== END DOCUMENTS ===

Generate the OKF in this exact format (fill in each section):

# {name}

## Purpose
[1-2 sentences: what this project does and why it exists]

## Architecture
[Bullet list: key components, how they connect]

## Stack
[Comma-separated: language, framework, key libraries, databases]

## Key APIs
[List of important endpoints. Format: METHOD /path — description]

## Ports
[Service → port]

## Environment Variables
[Required vars. Format: VAR_NAME — description]

## Commands
```
dev: [start development]
build: [build command]
test: [run tests]
```

## Deployment
[How and where this runs]

## Key Decisions
[Architecture decisions and reasons]

## Related Projects
[Other projects this connects to]
"""


class OKFService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate(self, project: Project) -> str | None:
        if project.okf_overridden:
            return None

        stmt = select(Document).where(Document.project_id == project.id)
        result = await self.db.execute(stmt)
        documents = result.scalars().all()

        context = self._build_context(project, list(documents))
        context_hash = hashlib.sha256(context.encode()).hexdigest()

        # Check if context unchanged since last OKF
        okf_doc_stmt = select(Document).where(
            Document.project_id == project.id,
            Document.type == "okf",
        )
        okf_result = await self.db.execute(okf_doc_stmt)
        existing_okf = okf_result.scalar_one_or_none()
        if existing_okf and existing_okf.content_hash == context_hash:
            return existing_okf.content

        content = await self._call_llm(project, context)
        if not content:
            return None

        await self._store(project, content, context_hash)
        await self._write_to_disk(project, content)
        return content

    def _build_context(self, project: Project, documents: list[Document]) -> str:
        parts: list[str] = []
        priority_types = ["readme", "claude_md", "codex_md", "architecture", "plan", "package_json", "pyproject"]

        docs_by_type = {d.type: d for d in documents}

        for dtype in priority_types:
            if dtype in docs_by_type:
                doc = docs_by_type[dtype]
                if doc.content:
                    parts.append(f"--- {doc.title} ---\n{doc.content[:3000]}")

        # Add remaining docs
        for doc in documents:
            if doc.type not in priority_types and doc.content:
                parts.append(f"--- {doc.title} ---\n{doc.content[:1000]}")

        return "\n\n".join(parts[:10])  # cap at 10 docs

    async def _call_llm(self, project: Project, context: str) -> str | None:
        if not settings.ANTHROPIC_API_KEY and not settings.OPENAI_API_KEY and not settings.GEMINI_API_KEY:
            logger.info("okf_llm_unavailable_generating_placeholder", project=project.slug)
            return self._generate_placeholder(project)

        try:
            import litellm
            prompt = OKF_USER_TEMPLATE.format(
                name=project.name,
                path=project.path,
                language=project.language or "unknown",
                framework=project.framework or "unknown",
                git_url=project.git_url or "none",
                documents=context,
            )
            response = await litellm.acompletion(
                model=settings.OKF_MODEL,
                messages=[
                    {"role": "system", "content": OKF_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=2048,
                num_retries=2,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning("okf_generation_failed", project=project.slug, error=str(e))
            return self._generate_placeholder(project)

    def _generate_placeholder(self, project: Project) -> str:
        return f"""# {project.name}

## Purpose
[Auto-generated placeholder — configure LLM API keys to generate full OKF]

## Architecture
- Language: {project.language or 'unknown'}
- Framework: {project.framework or 'unknown'}

## Stack
{project.language or 'unknown'}, {project.framework or 'unknown'}

## Key APIs
[Not documented]

## Ports
[Not documented]

## Environment Variables
[Not documented]

## Commands
```
dev: [not documented]
build: [not documented]
test: [not documented]
```

## Deployment
Path: {project.path}

## Key Decisions
[Not documented]

## Related Projects
[Not documented]
"""

    async def _store(self, project: Project, content: str, context_hash: str) -> None:
        from app.models.document import Document
        stmt = select(Document).where(
            Document.project_id == project.id,
            Document.type == "okf",
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        okf_path = str(Path(project.path) / "buildos.okf.md")

        if existing:
            existing.content = content
            existing.content_hash = context_hash
            existing.word_count = len(content.split())
        else:
            doc = Document(
                project_id=project.id,
                type="okf",
                title="buildos.okf.md",
                path=okf_path,
                content=content,
                content_hash=context_hash,
                word_count=len(content.split()),
                char_count=len(content),
            )
            self.db.add(doc)
        await self.db.flush()

    async def _write_to_disk(self, project: Project, content: str) -> None:
        try:
            okf_path = Path(project.path) / "buildos.okf.md"
            okf_path.write_text(content, encoding="utf-8")
            project.okf_path = str(okf_path)
            await self.db.flush()
            logger.info("okf_written", project=project.slug, path=str(okf_path))
        except Exception as e:
            logger.warning("okf_write_failed", project=project.slug, error=str(e))
