"""Execution-accuracy harness — run every question through the real agent and grade it.

This runner ties the ground-truth set (``questions.json``) to the comparison logic
(``comparison.py``). It drives the agent **in-process** (no HTTP), so it exercises the
exact agent loop a real request would, minus the gateway. Every run makes real OpenAI
calls, so it costs a little credit and needs the same ``.env`` the service reads (the
OpenAI key + the read-only database URL).

Running the agent (expensive, hits OpenAI) is kept separate from grading (pure, free):
:func:`_run` produces a :class:`Result`, and the grading helpers below are plain
functions over that Result. Execution accuracy is the headline; three cheaper signals
sit alongside it, each catching a different failure than a wrong value:

* **executed** — a data-backed query actually ran (the answer isn't ungrounded);
* **tables used** — the agent's SQL touched the tables the question needs (guards a
  value that came out right off the wrong table). A deliberately loose word-match, not
  a parse — it can be fooled, so it's a hint, not a verdict;
* **abstention** — on an unanswerable question, the agent declined instead of
  inventing an answer. Whether it *declined* is a semantic judgement (the agent may
  explore with a query first, and may reply in any language), so a small separate
  LLM call grades the answer text — "LLM-as-judge", the standard tool for scoring an
  open-ended reply. The judge is eval-only, kept out of the production agent client.

Run it from ``backend/`` with:  ``poetry run python -m eval.harness``
"""

import asyncio
import json
import re
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.llm.client import OpenAIClient
from app.repositories.sql_repository import AsyncpgRepository
from app.services.text_to_sql import TextToSqlService
from eval.comparison import results_match

_QUESTIONS_PATH = Path(__file__).parent / "questions.json"
_LATEST_RUN_PATH = Path(__file__).parent / "runs" / "latest.json"
_TIER_ORDER = ["easy", "medium", "hard", "veryhard"]

_JUDGE_INSTRUCTIONS = (
    "You are grading an AI assistant that answers questions from a manufacturing "
    "database. The assistant is supposed to DECLINE questions the database cannot "
    "answer (no such table or data) instead of inventing an answer. Given the user "
    "question and the assistant's answer, reply with exactly one word: YES if the "
    "assistant declined or said it cannot answer from the available data, or NO if it "
    "gave a substantive data-backed answer."
)


@dataclass
class Result:
    """A ground-truth question paired with what the agent produced for it."""

    question: dict
    answer: str = ""
    sql: str = ""
    rows: list[dict] = field(default_factory=list)
    error: str | None = None
    abstained: bool | None = None  # set only for unanswerable questions (via the judge)


def _load_questions() -> list[dict]:
    return json.loads(_QUESTIONS_PATH.read_text(encoding="utf-8"))


def _json_default(value: object) -> object:
    """Make a row value JSON-serializable while keeping numbers comparable.

    asyncpg hands back ``Decimal`` for numeric columns and ``datetime`` for
    timestamps. We keep Decimals as floats (so a re-grade still compares them
    numerically) and stringify everything else json can't handle.
    """
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _save_run(results: list["Result"]) -> None:
    """Persist the agent's output per question so grading can be replayed for free.

    Running the agent hits OpenAI (slow, costs credit); grading is pure. Saving the
    responses lets us re-grade after changing the comparison or metrics — as we did
    repeatedly building this harness — without paying to re-run the agent.
    """
    payload = [
        {
            "id": r.question["id"],
            "answer": r.answer,
            "sql": r.sql,
            "rows": r.rows,
            "error": r.error,
            "abstained": r.abstained,
        }
        for r in results
    ]
    _LATEST_RUN_PATH.parent.mkdir(exist_ok=True)
    _LATEST_RUN_PATH.write_text(
        json.dumps(payload, indent=2, default=_json_default, ensure_ascii=False),
        encoding="utf-8",
    )


def _load_run(questions: list[dict]) -> list["Result"]:
    """Rebuild results from the last saved run, pairing each with its question."""
    saved = {row["id"]: row for row in json.loads(_LATEST_RUN_PATH.read_text(encoding="utf-8"))}
    return [
        Result(
            q,
            answer=saved[q["id"]]["answer"],
            sql=saved[q["id"]]["sql"],
            rows=saved[q["id"]]["rows"],
            error=saved[q["id"]]["error"],
            abstained=saved[q["id"]]["abstained"],
        )
        for q in questions
    ]


async def _build_service() -> tuple[TextToSqlService, AsyncpgRepository]:
    """Compose the same dependency graph as the API's lifespan, for the harness."""
    settings = get_settings()
    repository = await AsyncpgRepository.create(
        settings.eval_database_url,
        statement_timeout_ms=settings.db_statement_timeout_ms,
    )
    llm = OpenAIClient(api_key=settings.openai_api_key, model=settings.openai_model)
    return TextToSqlService(llm=llm, repository=repository), repository


async def _run(service: TextToSqlService, question: dict) -> Result:
    """Run one question through the agent. A crash is captured, not raised, so one
    broken question can't cost us the rest of the run."""
    try:
        response = await service.answer_question(question["question"])
    except Exception as exc:  # noqa: BLE001 - in a harness, any failure is just a FAIL
        return Result(question, error=str(exc))
    return Result(question, answer=response.answer, sql=response.sql, rows=response.rows)


# --- Grading: pure functions over a Result (no I/O, free to recompute) ---

def _executed(r: Result) -> bool:
    """A successful, data-backed query ran behind the answer."""
    return bool(r.sql) and r.error is None


def _tables_used(r: Result) -> bool:
    """Every table the reference query needed appears (as a whole word) in the SQL."""
    sql = r.sql.lower()
    return all(re.search(rf"\b{table}\b", sql) for table in r.question["expected_tables"])


def _accurate(r: Result) -> bool:
    """Execution accuracy: the returned rows match the expected result."""
    return _executed(r) and results_match(
        r.question["expected_result"], r.rows, r.question["order_sensitive"]
    )


def _abstained(r: Result) -> bool:
    """For an unanswerable question: the judge decided the agent declined."""
    return bool(r.abstained)


async def _judge_abstained(judge: AsyncOpenAI, model: str, question: str, answer: str) -> bool:
    """Ask a separate LLM whether ``answer`` declined the (unanswerable) question."""
    response = await judge.responses.create(
        model=model,
        instructions=_JUDGE_INSTRUCTIONS,
        input=f"Question: {question}\n\nAssistant answer: {answer}",
    )
    return response.output_text.strip().upper().startswith("YES")


def _rate(results: list[Result], predicate) -> str:
    passed = sum(1 for r in results if predicate(r))
    return f"{passed}/{len(results)}" if results else "0/0"


def _report(results: list[Result]) -> None:
    answerable = [r for r in results if not r.question["unanswerable"]]
    offtopic = [r for r in results if r.question["unanswerable"]]

    print("\nPer-question:\n")
    for r in results:
        q = r.question
        if q["unanswerable"]:
            ok = _abstained(r)
            print(f"  {'PASS' if ok else 'FAIL'}  {q['id']:3} [{q['difficulty']}] abstention")
            if not ok:
                print(f"        -> did not decline: {r.error or r.answer}")
        else:
            ok = _accurate(r)
            flags = f"exec={'Y' if _executed(r) else 'N'} tables={'Y' if _tables_used(r) else 'N'}"
            print(f"  {'PASS' if ok else 'FAIL'}  {q['id']:3} [{q['difficulty']}] {flags}")
            if not ok:
                print(f"        -> {r.error or r.sql or 'no query was run'}")

    print("\nSummary:")
    print(f"  Execution accuracy   : {_rate(answerable, _accurate)}")
    print(f"  SQL executed         : {_rate(answerable, _executed)}")
    print(f"  Correct tables used  : {_rate(answerable, _tables_used)}")
    print(f"  Abstention (offtopic): {_rate(offtopic, _abstained)}")

    print("\n  Execution accuracy by difficulty:")
    for tier in _TIER_ORDER:
        tier_results = [r for r in answerable if r.question["difficulty"] == tier]
        if tier_results:
            print(f"    {tier:9}: {_rate(tier_results, _accurate)}")


async def run_eval() -> None:
    settings = get_settings()
    questions = _load_questions()
    service, repository = await _build_service()
    try:
        results = [await _run(service, q) for q in questions]
    finally:
        await repository.close()

    judge = AsyncOpenAI(api_key=settings.openai_api_key)
    for r in results:
        if r.question["unanswerable"]:
            r.abstained = (
                False if r.error else await _judge_abstained(
                    judge, settings.openai_model, r.question["question"], r.answer
                )
            )

    _save_run(results)
    _report(results)


def regrade() -> None:
    """Re-report the last saved run without touching OpenAI or the database."""
    _report(_load_run(_load_questions()))


if __name__ == "__main__":
    if "--regrade" in sys.argv:
        regrade()
    else:
        asyncio.run(run_eval())
