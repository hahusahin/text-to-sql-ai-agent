from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """What the client sends to ``POST /chat``: a single plain-language question."""

    question: str = Field(
        min_length=1,
        description="The user's plain-language question about the manufacturing database.",
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
