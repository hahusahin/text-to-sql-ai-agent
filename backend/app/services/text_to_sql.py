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
from dataclasses import dataclass
from typing import Any

from app.core.sql_guard import UnsafeSqlError, ensure_safe_select
from app.llm.client import OpenAIClient
from app.llm.tools import TOOLS
from app.models.chat import ChatResponse, Turn
from app.repositories.sql_repository import QueryExecutionError, SqlRepository

# Each pass of the loop is one model turn (one Responses call). A normal run is
# short: get_schema, run_query, answer — with a turn or two of slack for the model
# to read an error and retry. The cap is the safety net against a model that keeps
# calling tools without ever settling on an answer; it bounds both latency and cost.
_MAX_STEPS = 6

# How many nearest notes search_notes hands back. Enough for the model to see a
# theme and its spread across lines, without flooding the context with near-dupes.
_NOTES_SEARCH_LIMIT = 8


@dataclass
class _ToolResult:
    """What running one tool produced.

    ``output`` is the text fed back to the model (rows as JSON, schema text, or an
    error sentence). ``sql`` and ``rows`` are set **only** when a ``run_query`` call
    succeeded, so the loop can capture the query behind the answer as proof — a
    failed query has nothing to show and leaves them ``None``.
    """

    output: str
    sql: str | None = None
    rows: list[dict[str, Any]] | None = None

_AGENT_INSTRUCTIONS = """You are a data analyst answering questions about a manufacturing factory's PostgreSQL database. Answer using ONLY data you read from that database, by using the tools you are given.

Work in steps:
1. Call get_schema first to learn the exact tables, columns, and the allowed values of constrained columns. Never guess table or column names.
2. Write a single read-only SELECT and run it with run_query.
3. If run_query returns an error instead of rows, read the error text and call run_query again with a corrected query.
4. Once you have the data you need, reply in plain language.

Downtime events also carry a free-text operator note describing what happened. The structured reason_code column has only four coarse values (breakdown, setup_changeover, material_shortage, planned_maintenance) and cannot express finer themes like "oil leaks" or "hydraulic problems". When a question is about what operators described in those notes, call search_notes with a short description of the theme. You can combine tools: use search_notes to find the relevant downtime events, then run_query to count or aggregate them.

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

    async def answer_question(
        self, question: str, history: list[Turn] | None = None
    ) -> ChatResponse:
        conversation: list[Any] = [
            {"role": turn.role, "content": turn.content} for turn in (history or [])
        ]
        conversation.append({"role": "user", "content": question})
        last_sql = ""
        last_rows: list[dict[str, Any]] = []

        for _ in range(_MAX_STEPS):
            response = await self._llm.respond(
                instructions=_AGENT_INSTRUCTIONS,
                input_items=conversation,
                tools=TOOLS,
            )

            tool_calls = [item for item in response.output if item.type == "function_call"]
            if not tool_calls:
                # No tool requested -> the model is done; surface its answer plus the
                # last query that actually returned rows (the proof behind it).
                return ChatResponse(answer=response.output_text, sql=last_sql, rows=last_rows)

            conversation += response.output
            for call in tool_calls:
                result = await self._run_tool(call.name, call.arguments)
                if result.sql is not None:
                    last_sql, last_rows = result.sql, result.rows or []
                conversation.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": result.output,
                    }
                )

        return ChatResponse(
            answer=(
                "I couldn't work out an answer within the allowed number of steps. "
                "Please try rephrasing the question."
            ),
            sql=last_sql,
            rows=last_rows,
        )

    async def _run_tool(self, name: str, arguments: str) -> _ToolResult:
        """Execute a tool the model asked for and return its result.

        ``_ToolResult.output`` always carries the text fed back to the model — rows
        as JSON on success, or an error sentence on failure. Failures are returned,
        never raised, so the model can read them and try again. A successful
        ``run_query`` additionally carries the SQL and rows for the loop to capture.
        """
        if name == "get_schema":
            return _ToolResult(output=await self._repository.get_schema_text())
        if name == "run_query":
            return await self._run_query_tool(arguments)
        if name == "search_notes":
            return await self._run_search_notes_tool(arguments)
        return _ToolResult(output=f"Unknown tool: {name!r}.")

    async def _run_query_tool(self, arguments: str) -> _ToolResult:
        try:
            sql = json.loads(arguments)["sql"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return _ToolResult('Invalid arguments: expected JSON of the form {"sql": "SELECT ..."}.')

        try:
            safe_sql = ensure_safe_select(sql)
        except UnsafeSqlError as exc:
            return _ToolResult(f"Query rejected by the safety check: {exc.reason}")

        try:
            rows = await self._repository.run_query(safe_sql)
        except QueryExecutionError as exc:
            return _ToolResult(f"Database error: {exc}")

        output = json.dumps(rows, default=str, ensure_ascii=False)
        return _ToolResult(output=output, sql=safe_sql, rows=rows)

    async def _run_search_notes_tool(self, arguments: str) -> _ToolResult:
        """Embed the model's query and return the nearest downtime notes as JSON.

        Unlike run_query this doesn't set ``sql``/``rows``: the retrieval isn't a
        query the user could inspect, and it isn't the SQL proof the UI shows. The
        notes are only fed back into the conversation for the model to reason over.
        """
        try:
            query = json.loads(arguments)["query"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return _ToolResult('Invalid arguments: expected JSON of the form {"query": "..."}.')

        try:
            embedding = await self._llm.embed_query(query)
            rows = await self._repository.search_notes(embedding, _NOTES_SEARCH_LIMIT)
        except QueryExecutionError as exc:
            return _ToolResult(f"Database error: {exc}")

        return _ToolResult(output=json.dumps(rows, default=str, ensure_ascii=False))
