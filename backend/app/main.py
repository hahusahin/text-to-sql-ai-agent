"""FastAPI app + the composition root.

The ``lifespan`` handler is the one place allowed to know both the config and the
concrete classes: it reads ``Settings`` once at startup, builds the dependency
graph (DB pool -> repository, OpenAI client, service), and stashes the service on
``app.state`` for routes to pick up. On shutdown it closes the pool. Everything
below this file just receives what it needs — no module reaches for global config.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.core.config import get_settings
from app.llm.client import OpenAIClient
from app.repositories.sql_repository import AsyncpgRepository
from app.routes import chat
from app.services.text_to_sql import TextToSqlService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    repository = await AsyncpgRepository.create(settings.database_url)
    llm = OpenAIClient(api_key=settings.openai_api_key, model=settings.openai_model)
    app.state.text_to_sql = TextToSqlService(llm=llm, repository=repository)
    try:
        yield
    finally:
        await repository.close()


app = FastAPI(title="Manufacturing Text-to-SQL AI Service", lifespan=lifespan)

app.include_router(chat.router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe: confirms the service is up."""
    return {"status": "ok"}
