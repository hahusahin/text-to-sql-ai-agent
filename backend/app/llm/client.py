"""Thin async wrapper over the OpenAI Responses API.

Phase 1 is non-agentic and needs only a plain text-in / text-out call (write one
SQL statement, then summarize the rows). Tool calling and the hand-written agent
loop arrive in Phase 1.5; keeping this minimal now avoids building for a shape we
do not use yet.

Conventions (see the ``openai-api-python`` skill): Responses API only, the async
client, model + key come from config. Stable content (schema/instructions) goes at
the front so OpenAI's automatic prompt caching can discount the repeated prefix.
"""

from openai import AsyncOpenAI


class OpenAIClient:
    """An OpenAI Responses-API client bound to one model.

    Created once at startup and reused; the underlying ``AsyncOpenAI`` keeps its
    own connection pool, so a single instance serves every request.
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, max_retries=2)
        self._model = model

    async def complete(self, instructions: str, user_input: str) -> str:
        """Send one request and return the model's plain-text answer.

        ``instructions`` is the stable, system-level guidance (the DB schema lives
        here — keeping it first makes the prompt prefix cache-friendly).
        ``user_input`` is the variable part (the user's question).
        """
        response = await self._client.responses.create(
            model=self._model,
            instructions=instructions,
            input=user_input,
        )
        return response.output_text
