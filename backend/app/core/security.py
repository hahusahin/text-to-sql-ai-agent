"""Request authentication — the single shared API key in front of the service.

This is the only auth layer (per-user login / JWT is out of scope). The FastAPI
service will be deployed at a public URL; without a gate, anyone who learns the
URL could call ``/chat`` and burn our OpenAI credits or load the database. The
Next.js gateway holds the key server-side and sends it as ``X-API-Key`` on every
proxied request; the browser never sees it.

The comparison uses :func:`secrets.compare_digest` rather than ``==`` so it runs
in constant time. A plain ``==`` returns as soon as two characters differ, which
leaks — via response timing — how much of a guessed key was correct, letting an
attacker recover it character by character. ``compare_digest`` removes that signal.
"""

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


async def require_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    """Reject the request unless it carries the correct ``X-API-Key`` header.

    Used as a route dependency: FastAPI runs it before the handler, and a raised
    :class:`HTTPException` short-circuits to a 401 without the handler ever running.
    """
    expected = get_settings().api_key
    if x_api_key is None or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
