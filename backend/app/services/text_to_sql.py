"""Phase 1 text-to-SQL service — the non-agentic one-shot.

The flow is deliberately the simplest thing that can work end-to-end:

    question
      -> one LLM call writes ONE SQL SELECT
      -> we run it read-only
      -> a second LLM call summarizes the rows in plain language
      -> ChatResponse(answer, sql, rows)

It is intentionally **fragile**: there is no tool-calling loop and no
self-correction. The model writes the SQL blind (it never gets to look around
first) and never sees the database's response. If its query errors — a wrong
column name, a bad JOIN — the ``run_query`` call raises and the whole request
fails; the model has no chance to read the error and fix itself. That
self-correction is exactly what Phase 1.5 adds by turning this single shot into
a hand-written agent loop. We build the fragile version first so there is a
working end-to-end answer to improve on.
"""

import json
from typing import Any

from app.llm.client import OpenAIClient
from app.models.chat import ChatResponse
from app.repositories.schema import get_schema_text
from app.repositories.sql_repository import SqlRepository

_SQL_INSTRUCTIONS = f"""You translate plain-language questions into a single PostgreSQL SELECT query.

{get_schema_text()}

Rules:
- Output exactly ONE SQL SELECT statement and nothing else: no prose, no markdown code fences.
- Use only the tables and columns described above.
- The database is read-only; never write INSERT, UPDATE, DELETE, or any DDL.
- Always end with a LIMIT of at most 100 rows.
"""

_SUMMARY_INSTRUCTIONS = """You answer questions about a manufacturing database in plain language.

You are given the user's question, the SQL query that was run, and the rows it returned as JSON.
Answer the question directly and concisely using only the data in those rows. If the rows are empty,
say that no matching data was found. Reply in the same language the question was asked in. Do not
mention SQL, JSON, or how the answer was produced.
"""


class TextToSqlService:
    """Turns a plain-language question into an answer backed by a real query.

    Dependencies are injected (the LLM client and the repository) rather than
    constructed here, so the service stays testable and the repository can be a
    fake in eval — the service depends on the :class:`SqlRepository` interface,
    not on asyncpg.
    """

    def __init__(self, llm: OpenAIClient, repository: SqlRepository) -> None:
        self._llm = llm
        self._repository = repository

    async def answer_question(self, question: str) -> ChatResponse:
        sql = await self._generate_sql(question)
        rows = await self._repository.run_query(sql)
        answer = await self._summarize(question, sql, rows)
        return ChatResponse(answer=answer, sql=sql, rows=rows)

    async def _generate_sql(self, question: str) -> str:
        raw = await self._llm.complete(instructions=_SQL_INSTRUCTIONS, user_input=question)
        return _strip_code_fences(raw)

    async def _summarize(self, question: str, sql: str, rows: list[dict[str, Any]]) -> str:
        rows_json = json.dumps(rows, default=str, ensure_ascii=False)
        user_input = f"Question: {question}\n\nSQL run: {sql}\n\nRows (JSON): {rows_json}"
        return await self._llm.complete(instructions=_SUMMARY_INSTRUCTIONS, user_input=user_input)


def _strip_code_fences(text: str) -> str:
    """Remove a surrounding markdown code fence if the model added one anyway.

    We ask for bare SQL, but models often wrap it in ```sql ... ```. This drops
    the opening fence (with or without a language tag) and the closing fence.
    """
    cleaned = text.strip()
    if not cleaned.startswith("```"):
        return cleaned
    lines = cleaned.splitlines()[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()
