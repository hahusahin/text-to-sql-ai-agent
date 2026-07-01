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
  correct behavior there is to **decline**, not to invent a query. For these, "pass" means the agent
  *abstained* — it did not fabricate an answer.

## How it's laid out

- `README.md` — this file (the *why*).
- `questions.*` — the ground-truth set: `(question → reference SQL / expected result)` pairs, including
  the off-topic ones. Data, not code, so questions are easy to add (Task 1.28).
- the harness — runs each question through the real agent, executes the SQL, compares results, and
  prints per-question pass/fail plus summary metrics (Tasks 1.29–1.31).

The harness runs the **actual agent loop** against the **actual database** — not a mock. That's the
point: we're measuring the system a user would hit, end to end.
