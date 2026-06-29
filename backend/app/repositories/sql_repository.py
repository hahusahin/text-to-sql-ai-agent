from typing import Any, Protocol

import asyncpg


class SqlRepository(Protocol):
    """The read-only SQL access contract the rest of the app depends on.

    Anything that can run a query and hand back rows satisfies this — the real
    asyncpg-backed repository in production, or a fake one in tests/eval. Callers
    depend on this interface, not on asyncpg directly.
    """

    async def run_query(self, sql: str) -> list[dict[str, Any]]:
        """Execute a read-only query and return its rows as dictionaries."""
        ...


class AsyncpgRepository(SqlRepository):
    """An :class:`SqlRepository` backed by an asyncpg connection pool.

    The pool is created once at startup (via :meth:`create`) and closed at
    shutdown (via :meth:`close`); each query borrows a connection from it and
    returns it automatically.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

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
