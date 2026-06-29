"""SQL allowlist — defense in depth in front of the read-only database role.

The Postgres read-only role (Task 1.17) is the *real* protection: even a perfect
prompt injection that makes the model emit ``DROP TABLE`` cannot run, because the
role simply lacks the privilege. This module is the second, in-code layer: before
any model-written SQL reaches the database we confirm it is a single read-only
query and force a row cap. Two independent layers means a gap in one is still
covered by the other — that is what "defense in depth" means.

A query may start with ``SELECT`` or with a ``WITH`` (a Common Table Expression):
both are read-only constructs and the model legitimately produces CTEs for the
multi-step analytic questions this domain invites. Postgres does allow a
data-modifying CTE (``WITH t AS (DELETE ... RETURNING ...) SELECT ...``), but the
forbidden-keyword scan below still rejects those, so allowing ``WITH`` does not
open a write path.

The checks are deliberately string/regex based, not a full SQL parser. A parser
is a heavy dependency and a new attack surface of its own, and it would be
redundant with the role that already makes writes impossible. We take the
conservative stance: reject anything that is not obviously a safe single SELECT
rather than trying to fully understand every possible query.
"""

import re

DEFAULT_LIMIT = 100

_FORBIDDEN_KEYWORDS = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "truncate",
    "grant",
    "revoke",
    "merge",
    "copy",
    "call",
    "execute",
    "vacuum",
)


class UnsafeSqlError(Exception):
    """Raised when a query fails the allowlist.

    ``reason`` is a short human-readable explanation of which rule was broken.
    In the Phase 1.5 agent loop this text is fed back to the model the same way a
    database error is, so it can correct its own query.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def ensure_safe_select(sql: str) -> str:
    """Validate read-only SQL and return it with a ``LIMIT`` guaranteed.

    On success returns the query unchanged, except a ``LIMIT`` is appended when it
    had none. Raises :class:`UnsafeSqlError` (with a reason) when any rule fails.
    """
    cleaned = sql.strip().rstrip(";").strip()

    if not cleaned:
        raise UnsafeSqlError("Query is empty.")

    if ";" in cleaned:
        raise UnsafeSqlError("Only a single statement is allowed; remove the ';'.")

    if not re.match(r"^(select|with)\b", cleaned, re.IGNORECASE):
        raise UnsafeSqlError("Only SELECT (or WITH … SELECT) queries are allowed.")

    for keyword in _FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", cleaned, re.IGNORECASE):
            raise UnsafeSqlError(f"Disallowed keyword: {keyword.upper()}.")

    if not re.search(r"\blimit\b", cleaned, re.IGNORECASE):
        cleaned = f"{cleaned} LIMIT {DEFAULT_LIMIT}"

    return cleaned
