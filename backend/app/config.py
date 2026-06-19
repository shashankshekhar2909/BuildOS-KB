from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "BuildOS Knowledge Hub"
    API_PREFIX: str = "/api"
    DEBUG: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    DATABASE_URL: str = "postgresql+asyncpg://buildos:buildos@localhost:5436/buildos"
    REDIS_URL: str = "redis://localhost:6382"

    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    LITELLM_BASE_URL: str = ""

    OKF_MODEL: str = "claude-sonnet-4-6"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    SUMMARY_MODEL: str = "groq/llama-3.1-8b-instant"

    SCAN_DIRECTORIES: str = "/home/shashank/project,/home/shashank/projects"
    IGNORE_DIRS: List[str] = [
        ".git", "node_modules", "__pycache__", "venv", ".venv",
        "dist", "build", ".next", "target", "vendor", ".cache",
        "coverage", ".pytest_cache", "eggs", ".eggs",
    ]
    SCAN_INTERVAL_MINUTES: int = 15

    SEARCH_CACHE_TTL: int = 300
    MAX_SEARCH_RESULTS: int = 50
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64

    MCP_PORT: int = 8100

    REQUIRE_API_KEY: bool = False
    API_KEY: str = ""
    SECRET_KEY: str = "change-me-in-production"

    # Firebase Auth
    FIREBASE_PROJECT_ID: str = "gen-lang-client-0198159235"
    ADMIN_EMAILS: str = ""  # comma-separated; auto-promoted to admin on first login
    ALLOWED_EMAILS: str = ""  # comma-separated; empty = any Google account allowed
    JWT_EXPIRE_HOURS: int = 24

    @property
    def admin_emails_list(self) -> list[str]:
        return [e.strip().lower() for e in self.ADMIN_EMAILS.split(",") if e.strip()]

    @property
    def allowed_emails_list(self) -> list[str]:
        return [e.strip().lower() for e in self.ALLOWED_EMAILS.split(",") if e.strip()]

    @property
    def scan_dirs_list(self) -> List[str]:
        return [d.strip() for d in self.SCAN_DIRECTORIES.split(",") if d.strip()]


settings = Settings()
