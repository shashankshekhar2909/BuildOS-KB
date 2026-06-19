import json
import re
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.project import Project
from app.config import settings
import structlog

logger = structlog.get_logger()

TECH_DISPLAY = {
    "nextjs": "Next.js", "react": "React", "vue": "Vue.js", "svelte": "Svelte",
    "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
    "gin": "Gin", "echo": "Echo", "fiber": "Fiber",
    "actix": "Actix", "axum": "Axum", "rocket": "Rocket",
    "postgresql": "PostgreSQL", "mysql": "MySQL", "sqlite": "SQLite",
    "redis": "Redis", "mongodb": "MongoDB",
    "docker": "Docker", "typescript": "TypeScript", "javascript": "JavaScript",
    "python": "Python", "go": "Go", "rust": "Rust", "java": "Java",
}

PROJECT_MARKERS = [
    "package.json", "pyproject.toml", "setup.py", "go.mod",
    "Cargo.toml", "pom.xml", "build.gradle", "Makefile",
    ".git", "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
]


@dataclass
class ProjectCandidate:
    name: str
    slug: str
    path: str
    language: str | None
    framework: str | None
    git_url: str | None
    metadata: dict


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "project"


class DiscoveryService:
    PRIORITY_MARKERS = [
        "package.json", "pyproject.toml", "go.mod",
        "Cargo.toml", ".git", "Dockerfile",
    ]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def scan_all(self) -> list[ProjectCandidate]:
        candidates: list[ProjectCandidate] = []
        for directory in settings.scan_dirs_list:
            p = Path(directory)
            if not p.exists():
                logger.warning("scan_directory_missing", path=directory)
                continue
            found = await self.scan_directory(str(p))
            candidates.extend(found)
        return candidates

    async def scan_directory(self, path: str) -> list[ProjectCandidate]:
        base = Path(path)
        candidates: list[ProjectCandidate] = []

        # Check if base itself is a project
        candidate = await self.detect_project(str(base))
        if candidate:
            candidates.append(candidate)
            return candidates  # don't recurse into project root

        # Check top-level subdirs
        try:
            for entry in sorted(base.iterdir()):
                if not entry.is_dir():
                    continue
                if entry.name.startswith("."):
                    continue
                if entry.name in settings.IGNORE_DIRS:
                    continue
                candidate = await self.detect_project(str(entry))
                if candidate:
                    candidates.append(candidate)
        except PermissionError:
            pass

        return candidates

    async def detect_project(self, path: str) -> ProjectCandidate | None:
        p = Path(path)
        if not p.exists() or not p.is_dir():
            return None

        has_marker = any((p / m).exists() for m in self.PRIORITY_MARKERS)
        if not has_marker:
            return None

        language, framework = self._detect_framework(p)
        git_url = self._get_git_url(p)
        metadata = self._extract_metadata(p)

        name = p.name
        slug = slugify(name)

        return ProjectCandidate(
            name=name,
            slug=slug,
            path=str(p.resolve()),
            language=language,
            framework=framework,
            git_url=git_url,
            metadata=metadata,
        )

    def _detect_framework(self, path: Path) -> tuple[str | None, str | None]:
        pkg = path / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text())
                deps = {
                    **data.get("dependencies", {}),
                    **data.get("devDependencies", {}),
                }
                if "next" in deps:
                    return "typescript" if (path / "tsconfig.json").exists() else "javascript", "nextjs"
                if "react" in deps:
                    return "typescript" if (path / "tsconfig.json").exists() else "javascript", "react"
                if "vue" in deps:
                    return "typescript" if (path / "tsconfig.json").exists() else "javascript", "vue"
                if "svelte" in deps:
                    return "typescript" if (path / "tsconfig.json").exists() else "javascript", "svelte"
                if "express" in deps:
                    return "typescript" if (path / "tsconfig.json").exists() else "javascript", "express"
                return "typescript" if (path / "tsconfig.json").exists() else "javascript", None
            except Exception:
                pass

        for pyfile in ["pyproject.toml", "setup.py", "requirements.txt"]:
            if (path / pyfile).exists():
                content = (path / pyfile).read_text() if (path / pyfile).exists() else ""
                if "fastapi" in content.lower():
                    return "python", "fastapi"
                if "django" in content.lower():
                    return "python", "django"
                if "flask" in content.lower():
                    return "python", "flask"
                return "python", None

        if (path / "go.mod").exists():
            content = (path / "go.mod").read_text()
            if "gin-gonic/gin" in content:
                return "go", "gin"
            if "labstack/echo" in content:
                return "go", "echo"
            if "gofiber/fiber" in content:
                return "go", "fiber"
            return "go", None

        if (path / "Cargo.toml").exists():
            content = (path / "Cargo.toml").read_text()
            if "actix-web" in content:
                return "rust", "actix"
            if "axum" in content:
                return "rust", "axum"
            return "rust", None

        if (path / "pom.xml").exists() or (path / "build.gradle").exists():
            return "java", None

        return None, None

    def _get_git_url(self, path: Path) -> str | None:
        # Parse .git/config directly — avoids git CLI "dubious ownership" errors
        # on volume mounts where container uid != host file owner
        git_config = path / ".git" / "config"
        if git_config.exists():
            try:
                in_origin = False
                for line in git_config.read_text(errors="replace").splitlines():
                    line = line.strip()
                    if line == '[remote "origin"]':
                        in_origin = True
                    elif line.startswith("[") and in_origin:
                        break
                    elif in_origin and line.startswith("url ="):
                        return line.split("=", 1)[1].strip()
            except Exception:
                pass
        return None

    def _extract_metadata(self, path: Path) -> dict:
        meta: dict = {}

        if (path / "Dockerfile").exists() or (path / "docker-compose.yml").exists() or (path / "docker-compose.yaml").exists():
            meta["docker"] = True

        ports: list[int] = []
        for compose_file in ["docker-compose.yml", "docker-compose.yaml"]:
            cf = path / compose_file
            if cf.exists():
                try:
                    import yaml
                    data = yaml.safe_load(cf.read_text())
                    for svc in (data or {}).get("services", {}).values():
                        for port_def in (svc or {}).get("ports", []):
                            p = str(port_def).split(":")[0]
                            if p.isdigit():
                                ports.append(int(p))
                except Exception:
                    pass

        if ports:
            meta["ports"] = ports

        return meta

    async def upsert_project(self, candidate: ProjectCandidate) -> tuple[Project, bool]:
        stmt = select(Project).where(Project.path == candidate.path)
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.name = candidate.name
            existing.language = candidate.language
            existing.framework = candidate.framework
            existing.git_url = candidate.git_url
            existing.metadata_ = candidate.metadata
            existing.updated_at = datetime.utcnow()
            await self.db.flush()
            return existing, False

        # Ensure slug is unique
        slug = candidate.slug
        base_slug = slug
        counter = 1
        while True:
            check = await self.db.execute(select(Project).where(Project.slug == slug))
            if check.scalar_one_or_none() is None:
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        project = Project(
            name=candidate.name,
            slug=slug,
            path=candidate.path,
            language=candidate.language,
            framework=candidate.framework,
            git_url=candidate.git_url,
            metadata_=candidate.metadata,
            status="active",
        )
        self.db.add(project)
        await self.db.flush()
        logger.info("project_discovered", slug=slug, path=candidate.path)
        return project, True

    async def has_changes_since(self, project: Project) -> bool:
        if not project.last_indexed_at:
            return True

        last = project.last_indexed_at.timestamp()
        p = Path(project.path)
        for filename in ["README.md", "CLAUDE.md", "CODEX.md", "package.json",
                         "pyproject.toml", "docker-compose.yml", "Dockerfile"]:
            fp = p / filename
            if fp.exists() and fp.stat().st_mtime > last:
                return True
        return False
