from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ENV_FILE = REPOSITORY_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "VinFast Digital Showroom"
    app_env: Literal["development", "production", "test"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, ge=1, le=65535)
    api_prefix: str = "/api/v1"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    database_url: str = "sqlite+aiosqlite:///./vinfast.db"
    secret_key: str = "change-this-development-secret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"

    @property
    def effective_database_url(self) -> str:
        import os

        if os.environ.get("VERCEL") and "sqlite" in self.database_url:
            return "sqlite+aiosqlite:////tmp/vinfast.db"
        return self.database_url

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
