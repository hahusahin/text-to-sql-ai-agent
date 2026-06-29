from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment variables / a local .env file.

    Each field maps to an env var of the same name (case-insensitive), e.g.
    the ``database_url`` field is filled from ``DATABASE_URL``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    database_url_readonly: str
    db_statement_timeout_ms: int = 5000

    openai_api_key: str
    openai_model: str = "gpt-5.4-mini"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read env/.env once, reuse everywhere)."""
    return Settings()
