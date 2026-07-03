# Manufacturing Text-to-SQL Agent

**Live demo → [text-to-sql-ai-agent-pi.vercel.app](https://text-to-sql-ai-agent-pi.vercel.app)**

An **agentic text-to-SQL assistant** over a manufacturing database: ask a plain-language question and it answers from real data — combining SQL over the structured tables with
**semantic search** over free-text operator notes (**hybrid retrieval**).

## What it does

A question flows through a thin gateway to the agent, which loops over three tools — inspect the schema,
run SQL, search the notes — self-correcting on database errors, then answers in plain language and shows
the exact SQL it ran.

![How the agent works: a user question (TR/EN) goes through the Next.js gateway to the FastAPI service, where gpt-5.4-mini runs a tool-calling loop — get_schema(), run_query(sql) and search_notes(query) against PostgreSQL + pgvector — reading each result or database error and self-correcting up to six steps, then returns a plain-language answer with the exact SQL and result rows. Every step is logged as one structured JSON line, and read-only DB access plus single-SELECT validation, a forced LIMIT and a statement timeout keep the database safe.](docs/agent-flow.svg)

## The data — a manufacturing factory

The database models a **discrete-manufacturing** factory making industrial electrical / electromechanical
products (switchgear panels, contactors, motors, transformers, control units). It holds ~12 months of
synthetic-but-consistent data across eight tables:

- **Catalog** (the stage & cast): `products`, `production_lines`, `machines`, `shifts`.
- **Events** (what actually happened, over time): `work_orders` (a batch — what/where/when),
  `production_output` (produced vs scrap), `downtime_events` (planned/unplanned stops, each with a
  free-text operator **note**), `quality_inspections` and the `defects` found in them.

The downtime notes are the **unstructured** side: short operator comments ("oil seepage around the main
cylinder…") that the coarse `reason_code` column can't capture. They're embedded into vectors so the
agent can search them by meaning, not keywords.

Full mental model + ER diagram: **[backend/db/README.md](backend/db/README.md)**.

Sample questions it can answer:

- "Which production line had the most unplanned downtime last month, and which reason codes drove it?"
- "What's the scrap rate by product over the last quarter, and which three are worst?"
- "Which production lines had oil or hydraulic leak problems?" _(answered from the free-text notes, not
  the reason codes)_
- "Which products have the highest defect rate, and what are their most common defect types?"

## Stack

| Layer    | Tech                                                                                           |
| -------- | ---------------------------------------------------------------------------------------------- |
| Frontend | Next.js 16 (App Router, TypeScript, Tailwind, shadcn/ui) + thin gateway API route              |
| Backend  | Python / FastAPI (layered), OpenAI native tool calling — hand-written agent loop, no framework |
| AI       | OpenAI `gpt-5.4-mini` (agent) + `text-embedding-3-small` (semantic search over notes)          |
| Database | PostgreSQL + **pgvector** — Docker locally, Supabase in production                              |
| Tooling  | Poetry, asyncpg, Alembic (raw-SQL migrations, no ORM)                                          |
| Deploy   | Vercel (frontend) · Hugging Face Spaces (backend, Docker) · Supabase (Postgres)                |
| CI/CD    | GitHub Actions — `ruff` lint/format + import build-check gate a deploy of `backend/` to HF Spaces |

## Guardrails

The model writes the SQL, so a query could be wrong or unsafe. Independent layers (defense in depth) keep
the database protected:

- **Read-only access** — the app connects as a database user that can _only read_. Even if the model
  emitted `DROP TABLE`, the database itself would reject it. This is the main safeguard.
- **Query validation** — every generated query must be a single read-only `SELECT`; risky commands are
  blocked and a row limit is always applied.
- **Query timeout** — the database cancels any query that runs too long, so one heavy query can't tie up
  the service.

## Evaluation

A model can emit SQL that _runs fine but returns the wrong number_, so the agent is graded on
**execution accuracy** — run the generated query and compare its **result** to a known-correct one, not
its text (there are endless correct ways to write the same query). A reproducible harness runs 20 tiered
questions (plus hybrid ones that need semantic search and off-topic ones the agent must decline) through
the real agent.

Baseline (`gpt-5.4-mini`): **execution accuracy 13/14**. Full breakdown in
**[backend/eval/README.md](backend/eval/README.md)**.

## Limitations & scaling

Deliberate trade-offs for a portfolio demo, and where they'd change in production:

- **The model is probabilistic** — generated SQL can run yet be subtly wrong (a bad JOIN, a wrong date
  boundary). Execution-accuracy eval is the guard, but it covers a fixed question set, not everything.
- **The whole schema fits in the prompt** — fine at eight tables; at thousands you'd retrieve only the
  relevant tables (embeddings + the foreign-key graph) or point the agent at a curated view layer.
- **Access is all-or-nothing** — a read-only role plus one shared API key; no per-user auth or
  row-level security (out of scope by design).
- **Agentic cost/latency** — each question is several LLM round-trips, so it's costlier and slower than
  a single-shot query; caching or model routing would help at volume.
