"""
Конфиг из переменных окружения (.env).
Config: env vars + .env file. SECRET_KEY обязателен.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Приложение / App
    app_name: str = "Nexus Task Manager"
    debug: bool = False
    environment: Literal["dev", "staging", "prod"] = "dev"

    # Security
    secret_key: str = Field(..., min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    bcrypt_rounds: int = 12

    # CORS
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"])

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./nexus.db")
    echo_sql: bool = False

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str | None) -> str:
        if v is None or v == "":
            return "sqlite+aiosqlite:///./nexus.db"
        return v

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"

    # Rate limiting
    rate_limit_per_minute: int = 60
    auth_rate_limit_per_minute: int = 5

    # Logging
    log_level: str = "INFO"
    log_json: bool = Field(default=False, description="Use JSON structured logging")

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.database_url


@lru_cache
def get_settings() -> Settings:
    """Один раз читаем env, дальше из кэша. Single read, then cached."""
    return Settings()
