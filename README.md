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

**Phase 0 complete** — repo scaffold & local foundations:

- docker-compose Postgres service
- FastAPI backend (Poetry) with `GET /health` and env-based settings
- Next.js 16 frontend (shadcn/ui) with a thin `/api/chat` gateway proxying to the backend

Next: **Phase 1** — plain text-to-SQL (schema, migrations, seed, one-shot query flow).
