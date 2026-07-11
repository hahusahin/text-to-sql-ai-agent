"""FastAPI app + the composition root.

The ``lifespan`` handler is the one place allowed to know both the config and the
concrete classes: it reads ``Settings`` once at startup, builds the dependency
graph (DB pool -> repository, OpenAI client, service), and stashes the service on
``app.state`` for routes to pick up. On shutdown it closes the pool. Everything
below this file just receives what it needs — no module reaches for global config.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.security import require_api_key
from app.core.sql_guard import UnsafeSqlError
from app.llm.client import OpenAIClient
from app.repositories.sql_repository import (
    AsyncpgRepository,
    QueryExecutionError,
    SqlRepository,
)
from app.routes import chat
from app.services.text_to_sql import TextToSqlService

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()
    repository = await AsyncpgRepository.create(
        settings.database_url_readonly,
        statement_timeout_ms=settings.db_statement_timeout_ms,
    )
    llm = OpenAIClient(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        embedding_model=settings.openai_embedding_model,
    )
    app.state.repository = repository
    app.state.text_to_sql = TextToSqlService(llm=llm, repository=repository)
    log.info("service_started", extra={"model": settings.openai_model})
    try:
        yield
    finally:
        await repository.close()


app = FastAPI(title="Manufacturing Text-to-SQL AI Service", lifespan=lifespan)

app.include_router(chat.router, dependencies=[Depends(require_api_key)])


@app.exception_handler(UnsafeSqlError)
async def unsafe_sql_handler(request: Request, exc: UnsafeSqlError) -> JSONResponse:
    """Turn a rejected query into a clean 400 instead of a 500 stack trace."""
    return JSONResponse(
        status_code=400,
        content={"detail": f"The generated query was rejected: {exc.reason}"},
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe: confirms the service is up."""
    return {"status": "ok"}


@app.get("/health/db")
async def health_db(request: Request) -> JSONResponse:
    """Readiness probe: confirms the service can actually reach the database.

    Doubles as the Supabase keep-alive target. The free tier pauses a project
    after ~7 days without database activity, and ``/health`` never touches the DB
    — so the scheduled ping has to land here for Postgres to see any traffic.
    """
    repository: SqlRepository = request.app.state.repository
    try:
        await repository.ping()
    except QueryExecutionError as exc:
        log.warning("health_db_unreachable", extra={"error": str(exc)})
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unreachable"},
        )
    return JSONResponse(content={"status": "ok", "database": "ok"})
