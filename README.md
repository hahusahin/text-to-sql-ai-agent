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

## Status

Phase 0 — repo scaffold & local foundations.
