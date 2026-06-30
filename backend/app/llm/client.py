"""Thin async wrapper over the OpenAI Responses API.

The wrapper stays deliberately dumb: it knows the model id and the API key and how
to make one Responses call with tools. It does **not** own the agent loop — that
lives in the service (see :class:`TextToSqlService`), so the tool-calling mechanism
is explicit and hand-written rather than hidden behind a framework. This method
just makes the call and hands the raw response back for the service to inspect.

Conventions (see the ``openai-api-python`` skill): Responses API only, the async
client, model + key come from config. Stable content (schema/instructions) goes at
the front so OpenAI's automatic prompt caching can discount the repeated prefix —
in the loop the instructions and the growing conversation prefix ride along every
step, so prefix-caching is what keeps the per-step cost down.
"""

from typing import Any

from openai import AsyncOpenAI
from openai.types.responses import Response


class OpenAIClient:
    """An OpenAI Responses-API client bound to one model.

    Created once at startup and reused; the underlying ``AsyncOpenAI`` keeps its
    own connection pool, so a single instance serves every request.
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, max_retries=2)
        self._model = model

    async def respond(
        self,
        instructions: str,
        input_items: list[Any],
        tools: list[dict[str, Any]],
    ) -> Response:
        """Make one Responses API call and return the raw response.

        ``instructions`` is the stable system guidance (cache-friendly prefix).
        ``input_items`` is the running conversation: the user's question plus, on
        later turns, the model's own tool-call items and our tool results.
        ``tools`` is the catalogue the model may call from.

        Returns the raw SDK ``Response`` so the caller can read ``response.output``
        (to spot tool-call requests) or ``response.output_text`` (the final answer).
        """
        return await self._client.responses.create(
            model=self._model,
            instructions=instructions,
            input=input_items,
            tools=tools,
        )
