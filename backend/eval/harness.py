"""Execution-accuracy harness — run every question through the real agent and grade it.

This runner ties the ground-truth set (``questions.json``) to the comparison logic
(``comparison.py``): for each *answerable* question it builds the same service the API
uses, calls :meth:`TextToSqlService.answer_question`, and checks the rows the agent's
query returned against the expected result. Off-topic abstention and the summary
metrics are added in the next step (Task 1.30).

It drives the agent **in-process** — no HTTP — so it exercises the exact agent loop a
real request would, minus the gateway. Every run makes real OpenAI calls (schema +
query + answer per question), so it costs a little credit and needs the same ``.env``
the service reads (OpenAI key + the read-only database URL).

Run it from ``backend/`` with:  ``poetry run python -m eval.harness``
"""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.llm.client import OpenAIClient
from app.repositories.sql_repository import AsyncpgRepository
from app.services.text_to_sql import TextToSqlService
from eval.comparison import results_match

_QUESTIONS_PATH = Path(__file__).parent / "questions.json"


@dataclass
class Outcome:
    """One question's grade, plus the agent's query for diagnosing a failure."""

    id: str
    difficulty: str
    passed: bool
    sql: str
    error: str | None = None


def _load_questions() -> list[dict]:
    return json.loads(_QUESTIONS_PATH.read_text(encoding="utf-8"))


async def _build_service() -> tuple[TextToSqlService, AsyncpgRepository]:
    """Compose the same dependency graph as the API's lifespan, for the harness."""
    settings = get_settings()
    repository = await AsyncpgRepository.create(
        settings.database_url_readonly,
        statement_timeout_ms=settings.db_statement_timeout_ms,
    )
    llm = OpenAIClient(api_key=settings.openai_api_key, model=settings.openai_model)
    return TextToSqlService(llm=llm, repository=repository), repository


async def _grade(service: TextToSqlService, question: dict) -> Outcome:
    """Run one answerable question through the agent and grade its result rows.

    A crash (agent error, bad question) is recorded as a failure rather than aborting
    the whole run — one broken question shouldn't cost us the other thirteen results.
    """
    try:
        response = await service.answer_question(question["question"])
    except Exception as exc:  # noqa: BLE001 - in a harness, any failure is just a FAIL
        return Outcome(question["id"], question["difficulty"], False, sql="", error=str(exc))

    passed = results_match(
        question["expected_result"], response.rows, question["order_sensitive"]
    )
    return Outcome(question["id"], question["difficulty"], passed, sql=response.sql)


async def run_eval() -> None:
    answerable = [q for q in _load_questions() if not q["unanswerable"]]
    service, repository = await _build_service()
    try:
        outcomes = [await _grade(service, q) for q in answerable]
    finally:
        await repository.close()

    passed = sum(o.passed for o in outcomes)
    print(f"\nExecution accuracy: {passed}/{len(outcomes)} answerable questions\n")
    for o in outcomes:
        print(f"  {'PASS' if o.passed else 'FAIL'}  {o.id:3} [{o.difficulty}]")
        if not o.passed:
            detail = o.error or (o.sql or "no query was run")
            print(f"        -> {detail}")


if __name__ == "__main__":
    asyncio.run(run_eval())
