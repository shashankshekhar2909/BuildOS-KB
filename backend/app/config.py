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

    OKF_MODEL: str = ""
    EMBEDDING_MODEL: str = ""
    SUMMARY_MODEL: str = ""

    @property
    def has_any_llm_key(self) -> bool:
        return bool(
            self.GROQ_API_KEY
            or self.GEMINI_API_KEY
            or self.OPENAI_API_KEY
            or self.ANTHROPIC_API_KEY
        )

    @property
    def resolved_okf_model(self) -> str:
        if self.OKF_MODEL:
            return self.OKF_MODEL
        if self.GROQ_API_KEY:
            return "groq/llama-3.3-70b-versatile"
        if self.GEMINI_API_KEY:
            return "gemini/gemini-2.5-flash"
        if self.OPENAI_API_KEY:
            return "openai/gpt-4o-mini"
        if self.ANTHROPIC_API_KEY:
            return "claude-sonnet-4-6"
        return ""

    @property
    def resolved_summary_model(self) -> str:
        if self.SUMMARY_MODEL:
            return self.SUMMARY_MODEL
        if self.GROQ_API_KEY:
            return "groq/llama-3.1-8b-instant"
        if self.GEMINI_API_KEY:
            return "gemini/gemini-2.5-flash-lite"
        if self.OPENAI_API_KEY:
            return "openai/gpt-4o-mini"
        if self.ANTHROPIC_API_KEY:
            return "claude-haiku-4-5-20251001"
        return ""

    @property
    def resolved_embedding_model(self) -> str:
        if self.EMBEDDING_MODEL:
            return self.EMBEDDING_MODEL
        if self.GEMINI_API_KEY:
            return "gemini/text-embedding-004"
        if self.OPENAI_API_KEY:
            return "text-embedding-3-small"
        return ""

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
