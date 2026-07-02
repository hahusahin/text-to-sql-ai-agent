"""Structured (JSON-lines) logging for the AI service.

We emit one JSON object per log line to stdout. JSON because these lines are meant
to be *queried*, not just read: "show the slowest questions", "sum the tokens for
today" — impossible with free-form text, trivial once every line is a record with
named fields. stdout because in a container (Docker / Hugging Face Spaces) that's
what the platform captures and shows; the app should not care where logs are stored.

Built on the standard library's ``logging`` (no third-party log framework), so the
logger -> handler -> formatter chain stays visible. Call :func:`configure_logging`
once at startup; everywhere else just do ``logging.getLogger(__name__)`` (module
names live under the ``app`` package, so they inherit this configuration) and pass
structured fields via ``extra=``::

    log.info("tool_call", extra={"tool": "run_query", "duration_ms": 34})
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

# The id shared by every log line of one agent run. A ContextVar (not a plain global
# or threading.local) because the service handles many questions concurrently on the
# same thread: asyncio gives each task its own copy of the context, so one request's
# id never leaks into another's log lines. Code deep in the loop never passes it
# around — the logging filter below reads it ambiently at write time.
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def new_request_id() -> str:
    """Mint a short id for the current agent run and bind it to this context."""
    request_id = uuid4().hex[:8]
    _request_id.set(request_id)
    return request_id


# The attribute names the standard library puts on every LogRecord. We build the set
# from a throwaway record so it tracks the running Python version instead of being a
# hand-copied list. Anything on a record that is NOT in here was passed by us via
# ``extra=`` and belongs in the JSON payload.
_STANDARD_ATTRS = frozenset(vars(logging.makeLogRecord({}))) | {
    "message",
    "asctime",
    "taskName",
}


class _RequestIdFilter(logging.Filter):
    """Attach the current context's request id to every record, when one is set.

    A filter, not formatter code, so the formatter stays generic (it just serializes
    whatever fields a record carries). Records logged outside any request (e.g. at
    startup) have no id, so we leave the field off rather than writing ``null``.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        request_id = _request_id.get()
        if request_id is not None:
            record.request_id = request_id
        return True


class JsonFormatter(logging.Formatter):
    """Render a LogRecord as a single-line JSON object.

    The log *message* is treated as the event name (``log.info("tool_call")`` ->
    ``"event": "tool_call"``); any keyword fields passed through ``extra=`` are
    merged in alongside it. This keeps call sites terse while still producing a
    structured, machine-readable line.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS:
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    """Point the ``app`` logger tree at a JSON handler on stdout.

    We configure the ``app`` logger rather than the root so uvicorn's own access/
    error logs keep their default format — only our application's lines become JSON.
    ``propagate = False`` stops these lines from also bubbling to the root handler
    and being printed twice.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(_RequestIdFilter())

    app_logger = logging.getLogger("app")
    app_logger.handlers.clear()
    app_logger.addHandler(handler)
    app_logger.setLevel(level)
    app_logger.propagate = False
