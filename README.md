# Manufacturing Text-to-SQL Agent

**Live demo → [text-to-sql-ai-agent-pi.vercel.app](https://text-to-sql-ai-agent-pi.vercel.app)**

An **agentic text-to-SQL assistant** over a manufacturing database with **hybrid retrieval** — it
combines SQL over the structured tables with **semantic search** over free-text operator notes. Ask a
plain-language question (Turkish or English) and an LLM inspects the schema, writes SQL, runs it
**read-only**, searches the notes by meaning when a question needs it, fixes its own query on error, and
answers in plain language.

## What it does

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
its text (there are endless correct ways to write the same query). A reproducible harness runs 20
tiered questions (easy → very-hard, plus **hybrid** questions that need semantic search and off-topic
ones the agent must **decline**) through the real agent against the local database, and also checks
whether the SQL ran, hit the right tables, and — via an **LLM-as-judge** — whether it abstained on the
unanswerable ones and whether its hybrid answers are correct (those have no single exact result to
match, so a rubric judge scores them).

Baseline (`gpt-5.4-mini`): **execution accuracy 13/14** (window-function and correlated-subquery
questions pass; the one miss is a genuine three-way tie in the data), **hybrid 2/3** (LLM-judged), and
**abstention 2/3** — the agent occasionally forces an off-topic question onto the schema instead of
declining. Details in **[backend/eval/README.md](backend/eval/README.md)**.

## Run locally

Postgres runs in Docker; the apps run on the host for fast hot-reload.

```bash
# 1. Database (from repo root)
docker compose up -d

# 2. Backend — FastAPI on http://localhost:8000 (from backend/)
poetry install
poetry run alembic upgrade head   # create tables + pgvector + read-only role
poetry run poe seed               # generate ~12 months of data
poetry run poe embed              # embed the downtime notes for semantic search
poetry run uvicorn app.main:app --reload

# 3. Frontend — Next.js on http://localhost:3000 (from frontend/)
npm install
npm run dev
```

Copy `backend/.env.example` → `backend/.env` and `frontend/.env.local.example` → `frontend/.env.local`
and fill in the values (database URLs, OpenAI key, shared API key).
