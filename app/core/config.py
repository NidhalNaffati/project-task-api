from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # If set, this takes precedence over the individual DB_* fields.
    # Useful for tests (SQLite) and local development.
    DATABASE_URL: Optional[str] = None

    # ── Database connection ──────────────────────────────────────────────────
    DB_HOST: str = "db"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "projectdb"

    # ── API ──────────────────────────────────────────────────────────────────
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Project & Task API"

    @property
    def database_url(self) -> str:
        # Allow DATABASE_URL env var / field to override.
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.DB_HOST.startswith("/"):
            # Cloud Run Unix socket connection
            return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@/{self.DB_NAME}?host={self.DB_HOST}"
        # Standard TCP connection
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
