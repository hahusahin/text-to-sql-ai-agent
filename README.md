# Manufacturing Text-to-SQL AI Assistant

An **agentic text-to-SQL assistant** over a manufacturing database. Ask a plain-language question
(Turkish or English) — an LLM inspects the schema, writes SQL, runs it read-only against the database,
fixes its own query on error, and answers in plain language.

> 🚧 Work in progress. See [`PLAN.md`](./PLAN.md) for the build plan and [`CLAUDE.md`](./CLAUDE.md) for
> the full spec.

## Stack

- **Frontend:** Next.js 16 (App Router, TypeScript, Tailwind, shadcn/ui) + a thin gateway API route.
- **Backend:** Python / FastAPI AI service (layered, async), OpenAI native tool calling.
- **Database:** PostgreSQL (Docker locally, Supabase in production).
- **Tooling:** Poetry, asyncpg, Alembic (raw-SQL migrations).

## Guardrails

The model writes the SQL, so a query could be wrong or unsafe. Several independent layers
(defense in depth) keep the database protected:

- **Read-only access** — the app connects to the database as a user that can *only read*. Even if the
  model tried to change or delete data, the database itself would reject it. This is the main safeguard.
- **Query validation** — every generated query is checked before it runs: it must be a single read-only
  `SELECT`, risky commands are blocked, and a row limit is always applied.
- **Query timeout** — the database stops any query that runs too long, so one heavy query can't slow
  down the whole service.

## Run locally

Postgres runs in Docker; the apps run on the host for fast hot-reload.

```bash
# 1. Database (from repo root)
docker compose up -d

# 2. Backend — FastAPI on http://localhost:8000 (from backend/)
poetry install
poetry run uvicorn app.main:app --reload

# 3. Frontend — Next.js on http://localhost:3000 (from frontend/)
npm install
npm run dev
```

The frontend's `/api/chat` route is a thin gateway that proxies to the backend; configure its
target by copying `frontend/.env.local.example` to `frontend/.env.local` (defaults to
`http://localhost:8000`).

## Status

**Phase 1 complete** — plain text-to-SQL working end-to-end (browser → gateway → FastAPI →
OpenAI + Postgres). Schema, migrations, and seed are in place; a question is answered by a one-shot
LLM query (no agent loop yet).

Next: **Phase 1.5** — security hardening (read-only role, SQL allowlist, API key) and the
agentic tool-calling loop with self-correction.
