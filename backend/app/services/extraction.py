import hashlib
import json
from pathlib import Path
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.project import Project
from app.models.document import Document
import structlog

logger = structlog.get_logger()

PRIORITY_FILES = [
    "README.md", "README.rst", "README.txt",
    "CLAUDE.md", "CODEX.md", "AGENTS.md",
    "PLAN.md", "ARCHITECTURE.md", "TODO.md",
    "package.json", "pyproject.toml", "requirements.txt",
    "go.mod", "Cargo.toml",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", "buildos.okf.md",
]

IGNORE_FILENAMES = {
    ".env", ".env.local", ".env.production", ".env.staging",
    "secrets.json", "credentials.json", "service_account.json",
    ".netrc", "id_rsa", "id_ed25519",
}

FILE_TYPE_MAP = {
    "README.md": "readme", "README.rst": "readme", "README.txt": "readme",
    "CLAUDE.md": "claude_md", "CODEX.md": "codex_md", "AGENTS.md": "agents_md",
    "PLAN.md": "plan", "ARCHITECTURE.md": "architecture", "TODO.md": "todo",
    "package.json": "package_json", "pyproject.toml": "pyproject",
    "requirements.txt": "requirements", "go.mod": "go_mod", "Cargo.toml": "cargo_toml",
    "Dockerfile": "dockerfile",
    "docker-compose.yml": "docker_compose", "docker-compose.yaml": "docker_compose",
    ".env.example": "env_example", "buildos.okf.md": "okf",
}

MAX_CONTENT_BYTES = 500_000  # 500 KB limit per file

IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", "venv", ".venv",
    "dist", "build", ".next", "target", "vendor", ".cache",
    "coverage", ".pytest_cache",
}

MAX_EXTRA_DOCS = 80   # max markdown files scanned beyond priority list
MAX_DEPTH = 4         # max folder depth for recursive markdown scan


class ExtractionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def extract_project(self, project: Project) -> tuple[int, int]:
        processed = 0
        changed = 0
        seen_paths: set[str] = set()

        # 1. Priority files in root
        for filename in PRIORITY_FILES:
            filepath = Path(project.path) / filename
            if not filepath.exists() or filename in IGNORE_FILENAMES:
                continue
            try:
                doc, was_changed = await self.extract_file(project, filepath)
                if doc:
                    seen_paths.add(str(filepath))
                    processed += 1
                    if was_changed:
                        changed += 1
            except Exception as e:
                logger.warning("extract_file_error", path=str(filepath), error=str(e))

        # 2. Recursively find all markdown files in subdirs
        extra_md = self._find_markdown_files(Path(project.path), seen_paths)
        for filepath in extra_md:
            try:
                doc, was_changed = await self.extract_file(project, filepath)
                if doc:
                    processed += 1
                    if was_changed:
                        changed += 1
            except Exception as e:
                logger.warning("extract_file_error", path=str(filepath), error=str(e))

        return processed, changed

    def _find_markdown_files(self, root: Path, already_seen: set[str]) -> list[Path]:
        """Return up to MAX_EXTRA_DOCS .md/.rst files, recursively, skipping ignored dirs."""
        found: list[Path] = []

        def _recurse(path: Path, depth: int) -> None:
            if depth > MAX_DEPTH or len(found) >= MAX_EXTRA_DOCS:
                return
            try:
                for entry in sorted(path.iterdir()):
                    if entry.is_dir():
                        if entry.name in IGNORED_DIRS or entry.name.startswith("."):
                            continue
                        _recurse(entry, depth + 1)
                    elif entry.is_file() and entry.suffix.lower() in (".md", ".rst"):
                        if str(entry) not in already_seen and entry.name not in IGNORE_FILENAMES:
                            found.append(entry)
                            if len(found) >= MAX_EXTRA_DOCS:
                                return
            except (PermissionError, OSError):
                pass

        _recurse(root, 0)
        return found

    async def extract_file(self, project: Project, filepath: Path) -> tuple[Document | None, bool]:
        filename = filepath.name
        if filename in IGNORE_FILENAMES:
            return None, False

        try:
            raw = filepath.read_bytes()
            if len(raw) > MAX_CONTENT_BYTES:
                raw = raw[:MAX_CONTENT_BYTES]
            content = raw.decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning("read_file_error", path=str(filepath), error=str(e))
            return None, False

        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Check if unchanged
        stmt = select(Document).where(
            Document.project_id == project.id,
            Document.path == str(filepath),
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing and existing.content_hash == content_hash:
            return existing, False

        suffix = filepath.suffix.lower()
        doc_type = FILE_TYPE_MAP.get(filename, "markdown" if suffix in (".md", ".rst") else "other")
        parsed_data = self._parse_content(filename, content)

        if existing:
            existing.content = content
            existing.content_hash = content_hash
            existing.word_count = len(content.split())
            existing.char_count = len(content)
            existing.parsed_data = parsed_data
            existing.updated_at = datetime.utcnow()
            await self.db.flush()
            return existing, True

        doc = Document(
            project_id=project.id,
            type=doc_type,
            title=filename,
            path=str(filepath),
            content=content,
            content_hash=content_hash,
            word_count=len(content.split()),
            char_count=len(content),
            parsed_data=parsed_data,
        )
        self.db.add(doc)
        await self.db.flush()
        logger.info("document_extracted", project=project.slug, file=filename)
        return doc, True

    def _parse_content(self, filename: str, content: str) -> dict | None:
        try:
            if filename == "package.json":
                data = json.loads(content)
                return {
                    "name": data.get("name"),
                    "version": data.get("version"),
                    "description": data.get("description"),
                    "scripts": data.get("scripts", {}),
                    "dependencies": list(data.get("dependencies", {}).keys()),
                    "devDependencies": list(data.get("devDependencies", {}).keys()),
                }
            if filename == "pyproject.toml":
                try:
                    import tomllib
                    data = tomllib.loads(content)
                    project = data.get("project", {})
                    return {
                        "name": project.get("name"),
                        "version": project.get("version"),
                        "description": project.get("description"),
                        "dependencies": project.get("dependencies", []),
                    }
                except Exception:
                    return None
            if filename in ("docker-compose.yml", "docker-compose.yaml"):
                try:
                    import yaml
                    data = yaml.safe_load(content)
                    services = {}
                    for svc_name, svc in (data or {}).get("services", {}).items():
                        services[svc_name] = {
                            "image": (svc or {}).get("image"),
                            "ports": (svc or {}).get("ports", []),
                        }
                    return {"services": services}
                except Exception:
                    return None
        except Exception:
            pass
        return None
