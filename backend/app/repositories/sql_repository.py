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


class SqlRepository(Protocol):
    """The read-only SQL access contract the rest of the app depends on.

    Anything that can run a query and hand back rows satisfies this — the real
    asyncpg-backed repository in production, or a fake one in tests/eval. Callers
    depend on this interface, not on asyncpg directly.
    """

    async def run_query(self, sql: str) -> list[dict[str, Any]]:
        """Execute a read-only query and return its rows as dictionaries."""
        ...

    async def get_schema_text(self) -> str:
        """Introspect the live database and return its schema as LLM-readable text."""
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
        async with self._pool.acquire() as connection:
            records = await connection.fetch(sql)
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
