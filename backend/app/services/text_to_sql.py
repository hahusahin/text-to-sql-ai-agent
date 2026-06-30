"""The agentic text-to-SQL service — a hand-written tool-calling loop.

Turns a plain-language question into a data-backed answer by giving the model two
tools (``get_schema`` and ``run_query``) and running a loop:

    1. send the conversation + the tool catalogue to the model;
    2. if the model answers with plain text, we're done — return it;
    3. if instead it *requests* a tool call, we execute that tool, append both its
       request and our result (or the error text) to the conversation, and go back
       to step 1;
    4. a step cap stops a stuck model from looping forever.

The one idea that makes this "agentic" rather than "retrying": when ``run_query``
fails, we hand the **error message** back to the model as the tool result instead
of raising. The model reads ``column "duration" does not exist``, rewrites its
query, and calls ``run_query`` again — self-correction, with no special-case code
on our side. We never parse its SQL or guess what it meant; we just keep feeding it
truth (schema, rows, errors) until it produces an answer.

The loop lives here in the service, not in the OpenAI wrapper, on purpose: the
tool-calling mechanism stays explicit and framework-free.
"""

import json
from typing import Any

from app.core.sql_guard import UnsafeSqlError, ensure_safe_select
from app.llm.client import OpenAIClient
from app.llm.tools import TOOLS
from app.models.chat import ChatResponse
from app.repositories.sql_repository import QueryExecutionError, SqlRepository

# Each pass of the loop is one model turn (one Responses call). A normal run is
# short: get_schema, run_query, answer — with a turn or two of slack for the model
# to read an error and retry. The cap is the safety net against a model that keeps
# calling tools without ever settling on an answer; it bounds both latency and cost.
_MAX_STEPS = 6

_AGENT_INSTRUCTIONS = """You are a data analyst answering questions about a manufacturing factory's PostgreSQL database. Answer using ONLY data you read from that database, by using the tools you are given.

Work in steps:
1. Call get_schema first to learn the exact tables, columns, and the allowed values of constrained columns. Never guess table or column names.
2. Write a single read-only SELECT and run it with run_query.
3. If run_query returns an error instead of rows, read the error text and call run_query again with a corrected query.
4. Once you have the data you need, reply in plain language.

Rules:
- Keep every query to a single SELECT with a LIMIT of at most 100 rows.
- Reply in the same language the question was asked in.
- If the question cannot be answered from this database, say so plainly instead of inventing an answer.
- Do not mention SQL, tools, or JSON in your final answer — just answer the question.
"""


class TextToSqlService:
    """Runs the agent loop that turns a question into a data-backed answer.

    Dependencies are injected (the LLM client and the repository) rather than
    constructed here, so the service stays testable and the repository can be a
    fake in eval — the service depends on the :class:`SqlRepository` interface,
    not on asyncpg.
    """

    def __init__(self, llm: OpenAIClient, repository: SqlRepository) -> None:
        self._llm = llm
        self._repository = repository

    async def answer_question(self, question: str) -> ChatResponse:
        conversation: list[Any] = [{"role": "user", "content": question}]

        for _ in range(_MAX_STEPS):
            response = await self._llm.respond(
                instructions=_AGENT_INSTRUCTIONS,
                input_items=conversation,
                tools=TOOLS,
            )

            tool_calls = [item for item in response.output if item.type == "function_call"]
            if not tool_calls:
                # No tool requested -> the model is done and this is its final answer.
                # sql/rows are threaded out of the loop in Task 1.24; for now the
                # answer text is what we surface.
                return ChatResponse(answer=response.output_text, sql="", rows=[])

            conversation += response.output
            for call in tool_calls:
                result = await self._run_tool(call.name, call.arguments)
                conversation.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": result,
                    }
                )

        return ChatResponse(
            answer=(
                "I couldn't work out an answer within the allowed number of steps. "
                "Please try rephrasing the question."
            ),
            sql="",
            rows=[],
        )

    async def _run_tool(self, name: str, arguments: str) -> str:
        """Execute a tool the model asked for and return its result as text.

        The return value is always a plain string because it goes straight back to
        the model as the tool's output — rows as JSON on success, or an error
        sentence on failure. Failures are returned, never raised, so the model can
        read them and try again.
        """
        if name == "get_schema":
            return await self._repository.get_schema_text()
        if name == "run_query":
            return await self._run_query_tool(arguments)
        return f"Unknown tool: {name!r}."

    async def _run_query_tool(self, arguments: str) -> str:
        try:
            sql = json.loads(arguments)["sql"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return 'Invalid arguments: expected JSON of the form {"sql": "SELECT ..."}.'

        try:
            safe_sql = ensure_safe_select(sql)
        except UnsafeSqlError as exc:
            return f"Query rejected by the safety check: {exc.reason}"

        try:
            rows = await self._repository.run_query(safe_sql)
        except QueryExecutionError as exc:
            return f"Database error: {exc}"

        return json.dumps(rows, default=str, ensure_ascii=False)
