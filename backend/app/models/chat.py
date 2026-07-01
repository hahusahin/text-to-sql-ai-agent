from typing import Any, Literal

from pydantic import BaseModel, Field


class Turn(BaseModel):
    """One earlier message in the conversation, as the client saw it.

    Only the natural-language dialogue is carried back — a user question or an
    assistant answer. The internal tool trace (schema dumps, row JSON) is
    deliberately *not* replayed: it would bloat the context and couple the client
    to the service's internals. If a follow-up needs data, the model re-queries.
    """

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    """What the client sends to ``POST /chat``: the new question plus prior turns.

    ``history`` makes the chat multi-turn while keeping the server **stateless** —
    the client carries the conversation, so no server session store is needed and
    the service scales freely. An empty ``history`` reproduces the original
    single-shot behaviour exactly, which keeps the eval harness unaffected.
    """

    question: str = Field(
        min_length=1,
        description="The user's plain-language question about the manufacturing database.",
    )
    history: list[Turn] = Field(
        default_factory=list,
        description="Prior user/assistant turns, oldest first, for follow-up context.",
    )


class ChatResponse(BaseModel):
    """What ``POST /chat`` returns: the answer plus proof of the query behind it.

    ``sql`` and ``rows`` are surfaced so the UI can reveal exactly which query
    produced the answer — proof the response came from real data, not the model
    making things up.
    """

    answer: str = Field(description="The plain-language answer to the question.")
    sql: str = Field(description="The SQL query that was executed against the database.")
    rows: list[dict[str, Any]] = Field(
        description="The rows the query returned, each as a column-name -> value mapping."
    )
