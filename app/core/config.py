from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

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
    def DATABASE_URL(self) -> str:
        if self.DB_HOST.startswith("/"):
            # Cloud Run Unix socket connection
            return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@/{self.DB_NAME}?host={self.DB_HOST}"
        # Standard TCP connection
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
