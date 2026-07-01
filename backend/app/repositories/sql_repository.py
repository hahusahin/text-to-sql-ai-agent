from typing import Any, Protocol

import asyncpg

from app.repositories.schema import format_schema_text

# Live schema introspection. Postgres keeps a "database about the database": the
# SQL-standard information_schema (portable, column-level metadata) and the richer
# pg_catalog (constraint definitions). We read columns from the former and let
# pg_get_constraintdef render each constraint — PK, FK, and the CHECK clauses that
# encode the allowed values — so we never have to parse constraint text ourselves.
# alembic_version is Alembic's bookkeeping table, not part of the domain; skip it.
_COLUMNS_SQL = """
    SELECT table_name, column_name, data_type, is_nullable, ordinal_position
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name <> 'alembic_version'
    ORDER BY table_name, ordinal_position
"""

_CONSTRAINTS_SQL = """
    SELECT
        rel.relname AS table_name,
        pg_get_constraintdef(con.oid) AS definition
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
    WHERE nsp.nspname = 'public'
      AND rel.relname <> 'alembic_version'
    ORDER BY
        rel.relname,
        CASE con.contype
            WHEN 'p' THEN 0 WHEN 'f' THEN 1 WHEN 'u' THEN 2 WHEN 'c' THEN 3 ELSE 4
        END,
        con.conname
"""


# Semantic search over the free-text operator notes. ORDER BY the cosine-distance
# operator (<=>) against the query vector, nearest first; the HNSW index on
# `embedding` serves this ordering. We JOIN production_lines so each hit carries
# the line it happened on — the note alone ("oil seepage...") can't answer "which
# LINE had oil leaks". We also return `id` so the agent can aggregate exactly over
# the matched events (run_query with WHERE id IN (...)) instead of re-searching the
# table with brittle keyword LIKEs. Rows without a note (embedding IS NULL) are
# excluded. The query vector arrives as pgvector's text form and is cast with
# $1::vector, so we need no asyncpg codec for the type.
_SEARCH_NOTES_SQL = """
    SELECT
        de.id,
        de.occurred_at,
        de.reason_code,
        de.duration_minutes,
        pl.name AS line_name,
        de.notes
    FROM downtime_events de
    JOIN production_lines pl ON pl.id = de.line_id
    WHERE de.embedding IS NOT NULL
    ORDER BY de.embedding <=> $1::vector
    LIMIT $2
"""


def _to_pgvector_literal(embedding: list[float]) -> str:
    """Render a vector as pgvector's text form, e.g. ``[0.1,0.2,0.3]``."""
    return "[" + ",".join(str(x) for x in embedding) + "]"


class QueryExecutionError(Exception):
    """Raised when the database rejects or fails to run a query.

    The repository translates the asyncpg driver's own error into this domain
    error, so the service and the agent loop can react to a failed query — feeding
    the message back to the model so it can self-correct — without importing
    asyncpg or knowing which driver is underneath. The original Postgres message
    (e.g. ``column "duration" does not exist``) is preserved as the string value,
    because that detail is exactly what lets the model fix its SQL.
    """


class SqlRepository(Protocol):
    """The read-only SQL access contract the rest of the app depends on.

    Anything that can run a query and hand back rows satisfies this — the real
    asyncpg-backed repository in production, or a fake one in tests/eval. Callers
    depend on this interface, not on asyncpg directly.
    """

    async def run_query(self, sql: str) -> list[dict[str, Any]]:
        """Execute a read-only query and return its rows as dictionaries.

        Raises :class:`QueryExecutionError` if the database rejects or fails the
        query (bad column, syntax error, statement timeout).
        """
        ...

    async def get_schema_text(self) -> str:
        """Introspect the live database and return its schema as LLM-readable text."""
        ...

    async def search_notes(
        self, embedding: list[float], limit: int
    ) -> list[dict[str, Any]]:
        """Return the downtime events whose note is most similar to ``embedding``.

        ``embedding`` is the query vector; rows come back nearest-first by cosine
        distance, each carrying its downtime context (line, time, reason) so the
        answer can be grounded, not just the note text.
        """
        ...


class AsyncpgRepository(SqlRepository):
    """An :class:`SqlRepository` backed by an asyncpg connection pool.

    The pool is created once at startup (via :meth:`create`) and closed at
    shutdown (via :meth:`close`); each query borrows a connection from it and
    returns it automatically.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._schema_text: str | None = None

    @classmethod
    async def create(cls, dsn: str, statement_timeout_ms: int) -> "AsyncpgRepository":
        """Open the connection pool and return a ready-to-use repository.

        This is an async factory because opening the pool is itself an awaitable
        I/O operation, and ``__init__`` cannot be ``async``.

        ``statement_timeout_ms`` is applied as a Postgres ``statement_timeout`` via
        ``server_settings``, which sends it as a connection startup parameter. The
        cancellation is server-side: even if the app stopped waiting, Postgres
        itself kills a query that runs longer than this, so a runaway query can't
        pin a pooled connection.
        """
        pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=1,
            max_size=10,
            server_settings={"statement_timeout": str(statement_timeout_ms)},
        )
        return cls(pool)

    async def close(self) -> None:
        """Close the pool and all its connections (call on app shutdown)."""
        await self._pool.close()

    async def run_query(self, sql: str) -> list[dict[str, Any]]:
        try:
            async with self._pool.acquire() as connection:
                records = await connection.fetch(sql)
        except asyncpg.PostgresError as exc:
            raise QueryExecutionError(str(exc)) from exc
        return [dict(record) for record in records]

    async def search_notes(
        self, embedding: list[float], limit: int
    ) -> list[dict[str, Any]]:
        try:
            async with self._pool.acquire() as connection:
                records = await connection.fetch(
                    _SEARCH_NOTES_SQL, _to_pgvector_literal(embedding), limit
                )
        except asyncpg.PostgresError as exc:
            raise QueryExecutionError(str(exc)) from exc
        return [dict(record) for record in records]

    async def get_schema_text(self) -> str:
        """Return the schema text, introspecting the database only once per process.

        The schema changes only when a migration runs, and a migration means a
        redeploy/restart — which builds a fresh repository — so memoizing the text
        for the process lifetime is safe and skips two catalog queries on every
        request after the first. (This is separate from OpenAI's prompt caching,
        which discounts the repeated schema *tokens*; this avoids the DB round-trip.)
        """
        if self._schema_text is None:
            self._schema_text = await self._introspect_schema_text()
        return self._schema_text

    async def _introspect_schema_text(self) -> str:
        async with self._pool.acquire() as connection:
            columns = await connection.fetch(_COLUMNS_SQL)
            constraints = await connection.fetch(_CONSTRAINTS_SQL)
        return format_schema_text(
            [dict(record) for record in columns],
            [dict(record) for record in constraints],
        )
