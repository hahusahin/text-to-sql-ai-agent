from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment variables / a local .env file.

    Each field maps to an env var of the same name (case-insensitive), e.g.
    the ``database_url`` field is filled from ``DATABASE_URL``.

    ``database_url`` (the privileged owner role) is optional on purpose: only
    migrations and the seed script use it, and they run locally. The deployed
    runtime is given the SELECT-only ``database_url_readonly`` and never holds
    the owner credentials — least privilege as a real boundary, not a convention.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str | None = None
    database_url_readonly: str
    db_statement_timeout_ms: int = 5000

    # The execution-accuracy eval must run against the SAME dataset its ground truth
    # was captured from — the local database — not the deployed one, whose seeded
    # values differ. So the eval harness reads its own URL (defaulting to the local
    # read-only role) instead of ``database_url_readonly``, which in a real .env points
    # at production. Only the harness reads this; the app runtime ignores it.
    eval_database_url: str = (
        "postgresql://readonly_user:readonly_local_dev@localhost:5432/manufacturing"
    )

    api_key: str

    openai_api_key: str
    openai_model: str = "gpt-5.4-mini"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read env/.env once, reuse everywhere)."""
    return Settings()
