# eval/ — Execution-accuracy evaluation

How we measure whether the agent is actually *good*, and how to catch it getting worse.

## Why evaluate at all

The agent is a probabilistic system: the same question can produce different SQL on different runs,
and a change to the prompt, the model, or the schema can silently make answers worse. "It looked right
when I tried it" is not a safety net. We want a **repeatable** check we can run after any change and get
a number back — did we improve, hold, or regress?

That check is this harness: a fixed set of questions, each paired with the *correct answer*, run through
the real agent against the real database. What counts as "correct" is the whole design problem below.

## The core idea: measure the result, not the text

The naive way to grade generated SQL is to compare it to a hand-written "reference" query as **text** —
did the model produce the same string we did? This is wrong, and it's wrong in both directions:

- **Same result, different text → falsely marked wrong.** These two queries are identical in meaning:

  ```sql
  SELECT line_id, COUNT(*) FROM downtime_events GROUP BY line_id ORDER BY 2 DESC LIMIT 1;
  SELECT line_id, COUNT(*) AS n FROM downtime_events GROUP BY line_id ORDER BY n DESC LIMIT 1;
  ```

  Different aliases, `ORDER BY 2` vs `ORDER BY n` — a text comparison fails them. There are effectively
  infinite correct SQL strings for most questions (table aliases, join order, `WHERE` vs `HAVING`,
  subquery vs CTE). Grading the text means grading style, not correctness.

- **Different result, same-looking text → falsely marked right.** A query can be syntactically fine,
  run without error, and return the *wrong number* — an off-by-one on a date filter, `>` where it
  needed `>=`, forgetting to exclude planned downtime. It "looks like SQL that answers the question"
  but the value is wrong. Text similarity can't see this at all.

So we grade the thing that actually matters to the user: **the rows the query returns.** We run the
model's SQL, run our reference SQL, and compare the two **result sets**. This is called
**execution accuracy** — accuracy measured by *executing* the query and checking its output, not by
inspecting its source. It's the standard metric for text-to-SQL (used by benchmarks like Spider and
BIRD) precisely because SQL has this one-question-many-correct-queries property.

The reference SQL in our ground-truth set is therefore not "the one true query." It's just *a* correct
query whose job is to **produce the expected result** to compare against. Any model query that yields
the same result set passes, however it's written.

## What "the same result" means (and the sharp edges)

Comparing two result sets is less obvious than it sounds. Decisions we're committing to:

- **Row order usually doesn't matter.** `{A, B, C}` and `{C, A, B}` are the same answer *unless the
  question asked for an ordering* ("top 3 by...", "earliest..."). So the comparison is
  **order-insensitive by default**, and we special-case the ranking questions where order is the point.
- **Column names don't matter, values do.** The model might call a column `n`, `count`, or
  `total_downtime`. We compare the *values*, not the labels.
- **Types and rounding bite.** `COUNT(*)` comes back as an int, an average as a float; `100` vs
  `100.0`, or `33.33` vs `33.333333`. The harness normalizes these before comparing so a cosmetic
  difference isn't a false failure.

These are exactly the cases we'll handle in the harness (Task 1.29) rather than hand-wave.

## Beyond a single pass/fail: the extra checks

Execution accuracy is the headline number, but a couple of questions need more than "does the result
match":

- **Did the SQL even execute?** A separate, weaker signal: of all questions, how many produced SQL that
  *ran* without a database error — regardless of whether the value was right. A drop here points at a
  different failure (broken SQL) than a drop in accuracy (wrong logic).
- **Were the right tables used?** A query can hit the right number by luck off the wrong table. A light
  check that the expected tables appear in the executed SQL guards against a coincidentally-correct
  result.
- **Abstention on off-topic questions.** Our set deliberately includes questions the database *can't*
  answer ("What's the weather?", "How many employees quit last year?" — there's no such table). The
  correct behavior there is to **decline**, not to invent a query. Whether the agent declined is a
  *semantic* judgement — it may probe with a query first and may reply in any language — so a small
  separate LLM call (an **LLM-as-judge**) reads the answer text and decides. "Pass" means the agent
  abstained; a "fail" is the agent fabricating a data answer for something the schema can't support.
- **Hybrid questions graded by rubric.** Phase 2 added questions that need semantic search over the
  free-text downtime notes ("which lines had oil-leak problems?"). Their answers are *approximate* —
  the retrieved set is bounded and shifts with how the model phrases the search — so there is no single
  exact result to match. These are graded by the same **LLM-as-judge**, but scoring *correctness*: it
  reads the answer against a rubric of what a right answer must contain and replies YES/NO. A question
  opts in with `"grading": "judge"` and carries an `expected_answer` rubric instead of an
  `expected_result`.

## How it's laid out

- `README.md` — this file (the *why*).
- `questions.json` — the ground-truth set: `(question → reference SQL / expected result)` pairs,
  including the off-topic ones. Data, not code, so questions are easy to add.
- `comparison.py` — the result-set comparison (normalization + match). Pure logic, no I/O.
- `harness.py` — the runner: drives the agent in-process, grades, and prints metrics.
- `runs/latest.json` — the last run's raw agent output (git-ignored; regenerated each run).

The harness runs the **actual agent loop** against the **actual database** — not a mock. That's the
point: we're measuring the system a user would hit, end to end.

## Running it

From `backend/`:

```
poetry run poe eval           # run the agent on every question, grade, and save the run
poetry run poe eval-regrade   # re-grade the last saved run — no OpenAI, no database, free
```

Running the agent is the expensive part (real OpenAI calls); grading is pure. So `eval` saves each
question's answer/SQL/rows to `runs/latest.json`, and `eval-regrade` replays the grading over that file.
When you change the comparison or the metrics — not the agent — re-grade instead of paying to re-run.

**The eval always targets the local database** (`EVAL_DATABASE_URL`, defaulting to the local read-only
role), never the deployed one: the ground-truth values were captured from local data, and the deployed
DB was seeded separately, so its numbers differ. Start it with `docker compose up -d` and make sure
migrations + seed have run.

## Baseline

Model `gpt-5.4-mini`, 20 questions (14 answerable + 3 hybrid + 3 off-topic), local DB:

| Metric | Result |
| --- | --- |
| Execution accuracy | 13/14 (easy 2/2 · medium 3/3 · hard 3/3 · trap 2/3 · veryhard 3/3) |
| SQL executed | 14/14 |
| Correct tables used | 14/14 |
| Hybrid (judge) | 2/3 |
| Abstention (off-topic) | 2/3 |

The agent is strong on the answerable set — the very-hard questions (window function,
correlated-subquery threshold, month bucketing) all pass. The remaining reds are honest signals, not
infrastructure bugs:

- **Trap 2/3** — `T1` ("which machine has the most breakdowns?") is a **three-way tie** at 8 breakdowns
  under the current data, so the reference SQL and the agent each pick a different (equally correct)
  machine. An ambiguity in the question, exposed by the data, not a wrong answer.
- **Hybrid 2/3** — `HY2` asks which line has the most leak-related downtime; the agent named the wrong
  line (the approximate top-k retrieval undercounts), and the judge correctly failed it. The eval doing
  its job.
- **Abstention 2/3** — non-deterministic: the agent occasionally forces an off-topic question onto the
  schema — e.g. answering "which supplier delivered the most?" by naming a *product* — instead of
  declining. A real property of the agent, left visible rather than hidden.

**Ground-truth note.** The seed is anchored to `date.today()`, so re-seeding (as Phase 2 did, to add
the notes) shifts every aggregate and the frozen `expected_result` values go stale. When that happens,
re-capture them by running each `reference_sql` against the current DB — the reference queries are the
oracle; only the numbers move. A sturdier fix (a date-deterministic seed, or executing the reference
SQL live) is noted for later.
