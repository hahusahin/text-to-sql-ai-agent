# PLAN.md — Manufacturing Text-to-SQL AI Assistant

Working plan derived from `CLAUDE.md`. Tasks are **commit-sized**: each is small enough to review,
understand, and commit on its own. We do them one at a time, you approve, then I commit + tick the box.

**How to read this file**
- `[ ]` = not started, `[x]` = done & committed (only I tick it, only after your explicit approval).
- Each task line is roughly one commit. A task that turns out too big gets split when we reach it.
- Phase order: **Phase 0 (scaffold) → 1 → 1.5 → First Deploy → 1.7 → 2 → 3.**
- Concepts to teach are tagged inline: `🎓 SQL`, `🎓 async`, `🎓 agent`, `🎓 design`, `🎓 tooling`.

**Settled stack** (no open decisions): Poetry (Python deps/venv) · asyncpg (async driver) · Alembic
with hand-written raw-SQL migrations, no ORM models · shadcn/ui (frontend base) · Supabase (managed
Postgres, ships pgvector) · pgvector + small OpenAI embedding model (Phase 2). Two remaining picks made
*at the task* (need live data): exact OpenAI chat model name (Task 1.13) and embedding model (Task 2.2).

---

## Target folder structure (where we're heading)

This is the destination, not something we build all at once — it grows phase by phase.

```
23-text-to-sql-agent/
├── CLAUDE.md
├── PLAN.md
├── README.md
├── .gitignore
├── docker-compose.yml                 # Postgres (+ backend later)
│
├── frontend/                          # Next.js 16, App Router, TS, Tailwind, shadcn/ui
│   ├── package.json
│   ├── components.json                # shadcn config
│   ├── .env.local.example
│   └── src/
│       ├── app/
│       │   ├── page.tsx               # full-page chat (the product)
│       │   ├── layout.tsx
│       │   └── api/chat/route.ts      # thin gateway → FastAPI (no business logic)
│       ├── components/
│       │   └── ui/                    # shadcn components
│       ├── lib/                       # api client, types
│       └── i18n/                      # TR/EN static string dictionary
│
└── backend/                           # FastAPI AI service (layered, async)
    ├── pyproject.toml                 # Poetry: deps + tooling
    ├── poetry.lock
    ├── Dockerfile
    ├── .env.example
    ├── alembic.ini                    # Alembic config
    ├── app/
    │   ├── main.py                    # FastAPI app + wiring
    │   ├── routes/                    # thin HTTP layer (/health, /chat)
    │   ├── services/                  # business logic (the text-to-SQL flow, later the agent loop)
    │   ├── repositories/              # DB access behind an interface (schema introspection, run_query)
    │   ├── core/                      # config, errors, security (api-key, sql allowlist)
    │   ├── llm/                       # OpenAI client wrapper + tool definitions
    │   └── models/                    # Pydantic request/response models
    ├── db/
    │   ├── migrations/                # Alembic versions (hand-written, raw SQL)
    │   └── seed/                      # synthetic data generator
    └── eval/                          # execution-accuracy harness + ground-truth set
```

---

## Phase 0 — Repo scaffold & local foundations

Goal: a clean repo, git initialized, Postgres running locally, both apps booting with a "hello"
endpoint. No AI yet. Sets the table so Phase 1 can go straight to the vertical slice.

- [x] **0.1** `git init` + root `.gitignore` (Python, Node, `.env`, `__pycache__`, `.next/`, etc.) + empty `README.md` stub.
- [x] **0.2** `docker-compose.yml` with a Postgres service only (named volume, exposed port, healthcheck). 🎓 design: why Postgres-as-"existing-system".
- [x] **0.3** Backend skeleton with **Poetry**: `poetry init`/`pyproject.toml` (`fastapi`, `uvicorn`) + `app/main.py` exposing `GET /health`. 🎓 tooling: Poetry via npm analogies (pyproject≈package.json, lock file, `poetry add`/`install`/`run`). 🎓 async: first `async def` endpoint, why it's async.
- [x] **0.4** Backend `core/config.py` — Pydantic `Settings` reading `.env` (DB URL, will hold API key/OpenAI key later) + `.env.example`.
- [x] **0.5** Frontend skeleton: `create-next-app` (Next 16, TS, Tailwind, App Router) in `frontend/`, then init **shadcn/ui** + add a few base components we'll need (button, input, card, collapsible, table). Default page boots. Verify installed Next version vs package.json.
- [x] **0.6** Frontend `/api/chat/route.ts` thin gateway stub that proxies a hardcoded string to backend `/health` (proves the two services talk). 🎓 design: gateway vs business logic separation.

---

## Phase 1 — Plain text-to-SQL (NO agent loop)

Goal (skeleton-first): an **ugly but working** end-to-end answer. One question → model writes ONE SQL →
we run it read-only → model summarizes. This is where the **schema + migrations + seed** get built, and
where most of the SQL teaching happens.

### 1A — The database (mental model → schema → migrations → seed)

- [x] **1.1** 🎓 SQL (big picture): write `db/README.md` mental-model doc — what the factory makes, line/machine/shift/work_order/output/downtime/inspection/defect and how they connect. (Doc only, no SQL yet — you read it before we write a single table.)
- [x] **1.2** **Alembic** setup: `alembic init`, point `env.py` at our DB, write the **first hand-written migration** (raw `CREATE TABLE` via `op.execute`, no ORM models). 🎓 SQL: what a migration is, why versioned; 🎓 tooling: `upgrade`/`downgrade`, the version chain.
- [x] **1.3** Migration: core "catalog" tables — `products`, `production_lines`, `machines`, `shifts`. 🎓 SQL: PK, column types, `machines.line_id` as first **foreign key**.
- [x] **1.4** Migration: `work_orders` (FKs → products, lines, shifts) + `production_output` (FK → work_orders). 🎓 SQL: one-to-many, FK constraints, the production backbone.
- [x] **1.5** Migration: `downtime_events` (FKs → lines, machines, shifts; `is_planned`, `duration_minutes`, `occurred_at`). 🎓 SQL: boolean + timestamp columns, reason_code as a small fixed set.
- [x] **1.6** Migration: `quality_inspections` (FK → work_orders) + `defects` (FK → inspections). 🎓 SQL: how quality "hangs off" production; the chain work_order → inspection → defect.
- [x] **1.7** Migration: indexes on FK/time columns used by eval questions. 🎓 SQL: what an index is, why FK + `occurred_at`/`start_date` columns.
- [x] **1.8** Seed generator (Python script in `db/seed/`): catalog rows + ~12 months of work orders/output/downtime/inspections/defects. 🎓 design: internal consistency rules (scrap≤produced, passed≤inspected, valid FKs, planned/reason_code coherence).
- [x] **1.9** Run + sanity-check seed: a few manual `SELECT`/`JOIN` queries to eyeball realism. 🎓 SQL: your first hand-written `JOIN` + `GROUP BY` on our real data.

### 1B — The non-agentic vertical slice

- [x] **1.10** Pydantic models: `ChatRequest { question }`, `ChatResponse { answer, sql, rows }` in `app/models/`. 🎓 design: typed contract between layers.
- [x] **1.11** Repository: async DB connection pool with **asyncpg** + `run_query(sql) -> rows`. 🎓 async: what an async driver is & why (I/O-bound, `await`, connection pool); 🎓 design: repository behind an interface.
- [x] **1.12** Hardcoded schema text helper (`get_schema_text()` returns the table/column list as a string) — Phase 1 reads it from a constant/file, not live introspection yet.
- [x] **1.13** OpenAI client wrapper in `app/llm/` (pick current cheap mini/nano model from live docs/pricing together; Responses vs Chat Completions decided here). Get OpenAI key into `.env`. 🎓 SDK: the call, messages, what it returns.
- [x] **1.14** Service: `answer_question()` — build prompt (schema + question) → one LLM call → extract SQL → `run_query` → second LLM call to summarize rows → return `ChatResponse`. 🎓 design: this is the *non-agentic* one-shot; name why it's fragile (no self-correction).
- [x] **1.15** Route: `POST /chat` wiring request → service → response. End-to-end works from `curl`/Swagger.
- [x] **1.16** Frontend: minimal full-page chat UI — input, send, render answer (ugly is fine). Wire through the `/api/chat` gateway. First real end-to-end from the browser. 🎉 skeleton done.

---

## Phase 1.5 — Security hardening + the agent loop

Goal: make it **safe** and **agentic**. First the guardrails (must be in place before we expose a
public URL at deploy), then convert the one-shot into a hand-written tool-calling loop that self-corrects.

### 1.5A — Security / guardrails

- [x] **1.17** Read-only Postgres role (SELECT-only) + migration/script creating it; backend connects as the read-only role. 🎓 SQL: DB roles/privileges, why this is the *real* protection.
- [x] **1.18** SQL allowlist in `core/`: single statement, must be `SELECT`, block multiple statements + dangerous keywords, force a `LIMIT`. 🎓 design: defense-in-depth vs the role.
- [x] **1.19** Statement timeout on the DB connection. 🎓 SQL: runaway-query protection.
- [x] **1.20** Shared `X-API-Key` check on every FastAPI request (dependency) + gateway sends it from env. 🎓 design: the only auth layer; why it's enough here.

### 1.5B — The agent loop (the heart) 🎓 agent

- [x] **1.21** Define the two tools as OpenAI tool schemas: `get_schema()` and `run_query(sql)`. 🎓 agent: what a "tool" is to the model (JSON schema), how the model *requests* a call.
- [x] **1.22** Live schema introspection for `get_schema()` (repository reads `information_schema`), replacing the Phase 1 hardcoded constant. 🎓 SQL: querying the catalog.
- [x] **1.23** The loop in the service: send tools → if model returns tool_calls, execute → feed result **or error text** back → repeat → stop on final text answer. Max-step cap. 🎓 agent: the whole mechanism, termination, why feeding the error back enables self-correction.
- [x] **1.24** Capture the executed SQL + rows through the loop into `ChatResponse` (the last successful `run_query`), so the UI can show proof.
- [x] **1.25** Frontend: SQL **hidden-but-expandable** disclosure + result rendered as a small table (shadcn collapsible + table). 🎓 design: proof-of-real-query UX.
- [x] **1.26** Frontend: informative empty state (what-this-is + what-data + 3–4 clickable example questions that auto-send) + TR/EN **static** UI toggle (string dictionary). 🎓 design: static i18n vs translating the answer (it doesn't).

---

## >> First Deploy (after Phase 1.5, before Phase 1.7)

Goal: a working public link early, as soon as the agent loop works. Eval (1.7) then runs locally and
improvements auto-redeploy via CD. **Vercel + Hugging Face Spaces + Supabase.** (Backend host switched
off Render → **HF Spaces free `cpu-basic`**: $0, no credit card, 2 vCPU/16 GB, sleeps only after 48h
idle. One open risk we verify at D.2: the HF proxy request-timeout must cover the agent loop — if it's
too short, fall back to Render free + a ~10-min keep-alive ping.)

- [x] **D.1** Provision **Supabase** managed Postgres (free tier; inactive projects pause, not deleted) + run Alembic migrations + seed against it + create the read-only role there.
- [x] **D.2** Backend `Dockerfile` for a **Hugging Face Spaces** Docker SDK Space (app listens on **port 7860**; `app_port`/metadata in the Space `README`); deploy it; secrets (DB URL, OpenAI key, API key) in **Space Settings → Secrets** (not the repo — free Spaces are public). 🎓 deploy: HF Space = its own git repo, push/sync to deploy. **Verify the HF proxy request-timeout covers the agent loop (~20–40s); if too low, fall back to Render free + keep-alive ping.** Health check green.
- [x] **D.3** Deploy frontend to Vercel; gateway env points at the HF Space URL (`*.hf.space`) + API key. **Set the Vercel gateway function `maxDuration` to comfortably exceed the backend's worst-case agent-loop response.** End-to-end works on the public URL.
- [x] **D.4** Keep-alive: a scheduled **GitHub Action** (or external cron) that pings `/health` more often than every 48h (e.g. daily) so the free Space never hits the idle-sleep. 🎓 design: why a portfolio link that can sit idle for days needs this.
- [x] **D.5** README: live link, screenshot, run-locally instructions, **and a proper "what is this / what happens in this factory" section** — reuse the factory mental-model from `backend/db/README.md` (Task 1.1) so a reader who never saw the schema understands the domain (products, lines, machines, shifts, work orders, output, downtime, quality) and the example questions it can answer. 🎉 shippable portfolio link exists.

---

## Phase 1.7 — Evaluation (execution-accuracy)

Goal: a reproducible harness that measures the **result**, not the text. Catches regressions; fixes
auto-redeploy via the CD already wired in First Deploy.

- [x] **1.27** 🎓 design (eval from scratch): write `eval/README.md` — what execution-accuracy is and why text-match is wrong for SQL.
- [x] **1.28** Ground-truth set: ~10–15 `(question → reference SQL / expected result)` pairs incl. a few off-topic/unanswerable. Stored as data (JSON/YAML) in `eval/`.
- [x] **1.29a** Harness comparison logic (result normalization + match). 🎓 design: value-based, order- and type-insensitive.
- [x] **1.29b** Harness core: run each question through the agent, execute generated SQL, compare result to expected (order-insensitive). Report per-question pass/fail.
- [x] **1.30** Extra checks: (a) did SQL execute without error, (b) right tables used, (c) abstention on off-topic. Summary metrics printed.
- [x] **1.31** One script entrypoint to rerun the whole eval; baseline numbers recorded in README.

---

## Phase 1.8 — Multi-turn conversation (stateless history)

Goal: turn the single-shot page into a real chatbot — previous Q&As stay on screen, and a follow-up
can reference an earlier answer (e.g. *"list the lines"* → *"now show downtime for the second one"*).
Decided **after** First Deploy on purpose (ship the link first; this changes the `/chat` contract).
Keep the **single-question path still valid** (empty history) so the 1.7 eval harness is unaffected.

- [x] **1.8.1** Backend: `ChatRequest` carries prior turns (a `messages` history); the agent loop seeds
  the LLM conversation with them instead of starting empty. 🎓 agent: conversation memory vs the
  per-question tool loop; why **stateless** (client sends history) beats a server session store here.
- [ ] **1.8.2** Frontend: keep a `messages[]` list and render the whole thread (question + answer +
  per-answer SQL/table disclosure), instead of replacing the last response. Send history with each ask.
- [ ] **1.8.3** Frontend: chat layout polish — scrollable thread with the input pinned at the bottom;
  switch the page shell to `100dvh`/`min-h-dvh` so it behaves on mobile (address-bar height). 🎓 design:
  why `dvh` over `vh` on mobile.

---

## Phase 2 — Hybrid (structured + unstructured)

Goal: add free-text data, embed it, and combine semantic search with SQL when a question needs both.
Vector store = **pgvector in the same Postgres** (Supabase ships it — no separate vector DB).

- [ ] **2.1** Migration: enable `pgvector` extension + add the free-text source (`downtime_events.notes` or a `maintenance_logs` table w/ `description`) + seed realistic free-text. 🎓 SQL: extending the schema, enabling an extension.
- [ ] **2.2** 🎓 design: embeddings + vector search primer; pick a **small OpenAI embedding model** (verify current name/price live).
- [ ] **2.3** Embedding pipeline: generate + store vectors in a pgvector column. 🎓 SQL: vector column + similarity operator (`<->`), an index on it.
- [ ] **2.4** New tool `search_notes(query)` (semantic search) exposed to the agent alongside the SQL tools.
- [ ] **2.5** Service/agent: let the model combine SQL results + semantic hits for questions that need both. 🎓 agent: multi-tool reasoning.
- [ ] **2.6** Add a few hybrid questions to the eval set; rerun harness.

---

## Phase 3 — Production polish (kept light)

Goal: light hardening + visibility. Document more than gold-plate. (NOT a dashboard, NOT SSE streaming.)

- [ ] **3.1** Observability/tracing: structured logging of each agent step (tool calls, SQL, latency, token use). 🎓 design: what to log in an agent.
- [ ] **3.2** GitHub Actions CI: run tests + lint + eval on push (CD already wired: Vercel auto-deploys; HF Spaces deploys from its Space repo). 🎓 design: CI before auto-deploy.
- [ ] **3.3** Backend tests + linter/formatter config wired into CI.
- [ ] **3.4** (Optional) Surface the agent's intermediate steps in the UI ("inspecting schema… running query… fixing query…"). 🎓 agent: why this beats token streaming in an agent flow.
- [ ] **3.5** (Optional) Model routing: cheap model default, escalate hard questions. 🎓 design: cost vs capability.
- [ ] **3.6** Final README/docs polish: architecture diagram, eval numbers, security notes, cost notes.
```
