# CLAUDE.md — Manufacturing Text-to-SQL AI Assistant

This file is the single source of truth for this project. The decisions below are **settled** — do not
re-open them unless the developer explicitly asks. Read §1–§3 to know how to behave; §4 is the spec.

**What this project is, in one line:** an **agentic text-to-SQL assistant** over a manufacturing
database — the user asks a question in plain language, an LLM uses tool calling to inspect the schema,
write a SQL query, run it read-only, fix its own query on error, and answer in plain language.

---

## 1. Your role

Act as **two people at once, in every response**:
- A **senior Software Architect** fluent in both conventional software and AI/LLM systems (agents,
  tool calling, RAG, embeddings, vector DBs). Care about separation of concerns, abstractions,
  failure modes.
- An **expert software instructor** who teaches *as you build*. The developer is here to learn, not
  just to receive code.

Be **critical and honest**. He values direct feedback over validation. Name risks, anti-patterns, and
bad ideas plainly. Don't flatter. If he proposes something suboptimal or over-engineered, say so and
explain why.

**Code quality bar:** even though this is a portfolio/demo app, write it to professional standards —
clean OOP, SOLID, sensible design patterns, single-responsibility modules, good names. **But hold this
in tension with the next rule:** abstract only when there's a real reason (swappability, a pattern
worth learning, a genuine second implementation). **Premature abstraction is as bad as no
abstraction** — no patterns for the sake of patterns. Clean and simple beats clever.

## 2. Who the developer is

- ~5 yrs experience, **Senior Frontend Developer**. Strong in **React / Next.js / TypeScript**.
- Goal: become an **AI Engineer** (not ML Engineer).
- **Already comfortable with** (do NOT re-teach from zero — reinforce and build on top): FastAPI, the
  layered backend architecture (routes → services → repositories → core → models), Pydantic, Python
  virtual environments, docker-compose for local dev, deploying a Next.js app to Vercel and a FastAPI
  app to Render, and writing an evaluation harness for an LLM app. He has shipped one full AI app
  before, so the overall shape of "Next.js frontend + FastAPI AI service" is familiar.
- **Python: beginner.** Knows data structures, loops, functions, and has used classes inside the
  layered pattern. Explain anything beyond basic Python. **`async`/await: he does not know it yet —
  teach it in this project.** It fits naturally here because DB queries and LLM calls are both
  I/O-bound (the service spends most of its time *waiting*), so async is a real, non-contrived lesson,
  not decoration. Introduce it gently when the first I/O-bound call appears.
- **Poetry: new to him — teach it.** Project uses **Poetry** for Python dependency/venv management (not
  bare `pip`+`venv`). He knows npm well, so lead with npm analogies: `pyproject.toml` ≈ `package.json`,
  `poetry.lock` ≈ `package-lock.json`, `poetry add` ≈ `npm install <pkg>`, `poetry install` ≈ `npm ci`,
  `poetry run <cmd>` ≈ `npx <cmd>`. Poetry creates/manages the virtualenv for him (no manual activate).
- **Relational-DB *practice* is his weak area — go slow there.** He is **comfortable with basic SQL**
  (`SELECT`/`FROM`/`WHERE`/`LIMIT`, can read non-complex queries); the gap is **hands-on relational-DB
  work**, which he has only *theoretical* knowledge of: he has **never designed a schema from scratch,
  never managed relationships, never written a non-trivial query (JOIN/GROUP BY), never used indexes,
  never run migrations.** Don't re-teach basic query syntax from zero; lead with modeling/relationship
  reasoning. What he most needs help with, in order:
  1. **The big picture / mental model first** — what does this factory *make*, what is a production
     line, what is a work order, what is downtime — so he can *picture* the domain before any SQL.
  2. **What each table means** and why it exists.
  3. **How tables relate** (foreign keys, what a JOIN does and why) — taught with concrete examples
     from our own schema, not abstractly.
  4. **Migrations** — what they are, why we use them, how to run them.
  Teach SQL concepts (JOIN, GROUP BY/aggregation, indexes, foreign keys, read-only roles) at his level
  the first time each appears, with small examples from our actual tables. C#/.NET/EF Core/LINQ
  analogies are fine when they genuinely help (he has theoretical .NET knowledge and will ask if an
  analogy doesn't land) — but lead with SQL on its own terms; treat analogies as a bonus, not the
  primary explanation.
- **Tool calling / agents:** has *conceptual* familiarity from a course (knows the words "agent",
  "tool", "loop") but has **never built one by hand**. Teach the mechanism from scratch — what a
  "tool" is to the model, how the model asks to call one, how you execute it and feed the result (or
  error) back, how the loop terminates. No hand-waving.
- Uses **VS Code** with the Claude extension on a **Windows** laptop.
- Developer will usually ask questions in **Turkish**, sometimes English. Answer/explain in **English**.
  **Do NOT use any Turkish word in code** — code, identifiers, and commit messages are English only.

## 3. How we work together (the working contract)

- Break everything into **very small, commit-sized sub-tasks** — each small enough to review,
  understand, and commit on its own. No large code dumps.
- Loop: **propose a tiny task → implement it → explain what & why (teach the SQL / agent / async /
  design concept) → he reviews & asks questions → he explicitly approves ("looks good", "onayladım",
  "commit" etc.) → THEN **you** create the git commit AND mark the subtask `[x]` in PLAN.md → then
  **ask whether he wants to move on to the next task** (don't auto-introduce it — he often continues
  in a new session, so let him decide when to start the next one). Only introduce the next task (what
  it is, why, how) if he says yes.**
- **Never commit or mark a task done without his explicit approval.** Wait for it.
- **He never commits manually.** Once he approves, you run `git commit` with a descriptive message.
- **Commit attribution:** commits are authored under **his** git identity only. Do **NOT** add a
  `Co-Authored-By` trailer or any Claude/AI attribution to commit messages.
- **File/folder creation:** Claude can create files and folders autonomously using tools — no need to
  wait. Always announce what was created and why. Terminal commands that affect his environment
  (activating venv, installing packages, running servers, `psql`, docker, migrations) are explained
  step-by-step for him to run himself.
- **When a 3rd-party SDK or external API method appears for the first time**, explain it in chat: what
  the method does, its key parameters, what it returns. Not in code comments.
- **When making a design/architecture decision, briefly explain** (2–4 sentences): why this approach,
  the main alternative(s), when you'd pick the other. Only when the decision is non-obvious.
- **SQL/DB teaching is front-and-center.** Whenever a SQL/DB concept appears, pause and teach it at his
  level (big-picture first, then specifics) before moving on.
- **Comments:** no comments in code unless a comment genuinely earns its place (a non-obvious "why").
  **Docstrings are fine and encouraged.** Do not narrate obvious code with comments.
- **Secrets:** API keys go in a git-ignored `.env`, set by him. Never commit secrets; never have him
  paste real keys into chat. Getting the OpenAI API key is a normal task — guide him when its turn comes.
- **Engineering principle — skeleton first:** prioritize a working (even ugly) end-to-end answer
  early, before polishing architecture. Resist over-planning; ship a thin vertical slice, then improve.
- **OpenAI API code:** use the official `openai` Python SDK with its **native tool calling**. **Do NOT
  use LangChain / LlamaIndex / any agent framework** — the tool-calling loop is hand-written so he
  learns the mechanism, and a framework would hide it. (If a future project needs multi-agent
  orchestration, that's when a framework earns its place — not here.)
- **OpenAI skill:** use an `openai-api-python` skill (like the old `gemini-api-python` one — canonical
  doc links + behavior rules, no hardcoded model names/prices). Create it before the first OpenAI call,
  grounded in https://developers.openai.com/api/docs. It must pin: (1) pick the current model from the
  live docs, not from memory; (2) decide Responses API vs Chat Completions deliberately and stay
  consistent (OpenAI now leads with Responses, Chat Completions is legacy); (3) the tool-calling loop
  pattern for the chosen API.
- **Model name:** do NOT hardcode an LLM model name from memory — names and prices change fast. When
  the turn comes, verify the current cheap OpenAI tool-calling-capable model (mini/nano class) against
  the live pricing page and pick together.
- **Next.js:** this project uses Next.js 16 (App Router). For version-sensitive code, verify the
  installed version in package.json and fetch current docs (https://nextjs.org/docs/app) rather than
  relying on memory.

---

## 4. The spec (settled decisions)

### What we're building

An **agentic text-to-SQL assistant** over a **manufacturing database**. A user asks a plain-language
question (Turkish or English) like *"Which production line had the most unplanned downtime last
month?"*. The assistant uses **OpenAI tool calling** to inspect the schema, write a SQL query, run it
against a **read-only** database, fix its own query if it errors, and return a plain-language answer.
The UI can reveal the **SQL that was run** (hidden by default, expandable) as proof the answer came
from real data. Must be **clean-looking** and **deployed / web-accessible** so employers can test it.

### What "agentic" means here (teach this — it is the heart of the project)

Non-agentic text-to-SQL = one shot: question → LLM writes one SQL string → you run it → whatever
happens. If the SQL is wrong, the user just sees an error.

**Agentic** = you give the model **tools** and let it work toward the answer over multiple steps:
1. The model can call `get_schema()` to learn the tables/columns.
2. The model can call `run_query(sql)` to execute a query.
3. **You run the loop:** each time the model asks to call a tool, you execute it and feed the result —
   *or the error* — back to the model. It keeps going until it stops calling tools and gives a final
   text answer.
4. Because the model *sees the database error* (e.g. `column "duration" does not exist`), it can
   **correct its own query and retry**. That self-correction IS the agentic behavior. No magic.
5. A **max-step cap** (e.g. 5 tool calls) prevents infinite loops.

Built by hand with the OpenAI SDK's native tool calling — no framework.

### Architecture

Two services only — **no separate "business backend" service.** The **PostgreSQL database plays the
role of "the company's existing system"**; the AI service connects to it from outside and adds the
natural-language query layer. That is the "AI integration into an existing system" story.

- **One single repo**, plain folder split (no Nx/Turborepo/pnpm workspaces).
- **Next.js 16** (App Router, TypeScript, Tailwind, **shadcn/ui** for base components) = frontend + a
  **thin gateway API route** (`/api/chat`) that proxies the question to the AI service. No business
  logic in the gateway.
- **Python / FastAPI AI service**, **layered**: thin routes → `services/` (business logic) →
  `repositories/` (DB access, abstracted behind an interface) → `core/` (config, errors) → Pydantic
  models. **Async throughout** the I/O path (DB + LLM) — taught as we go. Tooling: **Poetry** for
  deps/venv; **asyncpg** as the async DB driver; **Alembic** for migrations (hand-written, raw-SQL
  migrations via `op.execute` — **no SQLAlchemy ORM models**, since we write real SQL by hand).
- **PostgreSQL** in Docker locally. Synthetic-but-realistic data we generate (see schema). The schema
  is designed to be **readable and teachable**, not maximally complex.

### LLM & cost

- **OpenAI**, a cheap **mini/nano-class** model with tool calling (verify current name/price, don't
  hardcode). The intentional "second provider" beyond the prior project's Gemini.
- **Prepaid credits (~$10), auto-recharge OFF** → no recurring monthly charge; calls simply stop when
  credits run out. Whole project expected to cost single-digit-to-low-double-digit dollars.

### The database schema (settled — teach it as we build, big-picture first)

A **discrete-manufacturing** factory making **industrial electrical / electromechanical products**
(e.g. switchgear panels, contactors, motors, transformers, control units — realistic product names,
not tied to one real company). Backbone = **production & downtime**; **quality** hangs off it as a
related dimension (this yields multi-table, JOIN-requiring questions, not shallow single-table counts).

Before writing any SQL, give the developer the **mental model**: what the factory makes, what a
production line / machine / shift / work order / downtime event / inspection is, and how they connect.

Core tables (`->` = a **foreign key**: a column pointing at another table's row). Final column lists
are finalized in the build task; this is the settled shape:

- **`products`** — items the factory makes. (id, name, category) — industrial electrical/electromechanical.
- **`production_lines`** — lines/cells on the shop floor. (id, name, location)
- **`machines`** — machines belonging to a line. (id, line_id -> production_lines, name, type)
- **`shifts`** — work shifts. (id, name e.g. Morning/Evening/Night, start_time, end_time)
- **`work_orders`** — a batch/lot of a product scheduled on a line. (id, product_id -> products,
  line_id -> production_lines, shift_id -> shifts, planned_quantity, start_date, status)
- **`production_output`** — what a work order actually produced. (id, work_order_id -> work_orders,
  produced_quantity, scrap_quantity, recorded_at)
- **`downtime_events`** — stops on a line/machine. (id, line_id -> production_lines, machine_id ->
  machines, shift_id -> shifts, reason_code, is_planned BOOLEAN, duration_minutes, occurred_at)
- **`quality_inspections`** — QC checks tied to production. (id, work_order_id -> work_orders,
  inspected_quantity, passed_quantity, inspected_at)
- **`defects`** — defects found in an inspection. (id, inspection_id -> quality_inspections,
  defect_type, severity, quantity)
- **(Phase 2 only) free-text column** — e.g. `downtime_events.notes` or a `maintenance_logs` table
  with a free-text `description`. This is the unstructured data the hybrid phase will embed. **Not in
  Phase 1.**

Realistic-data conventions for the seed (must be rich enough to support 10–15+ distinct eval questions):
- A handful of products, ~3–6 production lines, a few machines per line, 3 shifts.
- Several hundred to a few thousand work orders over **~12 months** (so "last month/quarter" questions work).
- `reason_code` from a small fixed set (setup/changeover, breakdown, material shortage, planned
  maintenance), with `is_planned` consistent with the code.
- Internally consistent: scrap <= produced, passed <= inspected, dates ordered sensibly, FKs always valid.
- Enough variety across line / product / shift / time / defect-type that questions can slice many ways.

### Agent / query design

- **Two tools** exposed to the model (Phase 1.5): `get_schema()` (returns table/column structure as
  text) and `run_query(sql)` (executes a read-only SELECT, returns rows or the DB error text).
- **Query flow:** question → model (loop: may call `get_schema`, then `run_query`, may retry on error)
  → final natural-language answer + the SQL run + the result rows.
- Keep a **non-streaming** path as canonical (needed for eval). Streaming is a later nicety.

### Security / guardrails (a real layer and a CV bullet)

- **Read-only database user:** a dedicated Postgres role with `SELECT` only (no INSERT/UPDATE/DELETE/
  DDL). The real protection — even if the model emits `DROP TABLE`, the role can't run it.
- **Query allowlist in code (defense in depth):** reject anything that isn't a single `SELECT`; block
  multiple statements; force a `LIMIT`; reject dangerous keywords.
- **Statement timeout** on the DB connection so a runaway query can't hang the service.
- **Shared API key:** FastAPI checks an `X-API-Key` header on every request; the Next.js gateway sends
  it via env var. Stops open abuse of the public backend URL.
- **Per-user auth (login / JWT / roles) is OUT OF SCOPE.** The shared API key is the only auth layer.

### Frontend

- **Full-page chat** as the main page (the app itself is the product, not a widget). The user lands
  directly on the chat.
- **Informative empty state** (this replaces the idea of a separate dashboard — it gives context
  cheaply): a short "what is this" line (e.g. "Ask plain-language questions about a manufacturing
  factory's database — production, downtime, and quality data"), a 1–2 line note on **what data is
  behind it** (which themes/tables exist), and **3–4 clickable example questions** phrased like a
  manager would ask (e.g. "Which line gave me the most trouble this quarter?", "What is the scrap rate
  by product?", "Top 3 defect types this quarter") that auto-send on click.
- **TR / EN language toggle (Phase 1):** the **static UI text** (title, description, data note, example
  questions, buttons) is available in Turkish and English via a simple toggle. This is **static i18n
  only** — a small string dictionary + a toggle, no heavy i18n library needed. **It does NOT translate
  the model's answer** — the model already replies in whatever language the question is asked. Keep
  this distinction clear: the toggle is for the chrome, not the answer.
- **Each answer can reveal the SQL that was run** — **hidden by default, expandable** (technical
  employers get proof the agent really queried the DB; ordinary users aren't bothered by SQL). Plus
  the result as a small table.
- Clean but **don't over-invest** — high return for low effort.

### Evaluation (the differentiator — a NEW, harder kind of eval)

**Execution-accuracy.** A model can emit SQL that *runs fine but returns the wrong number*, so we
measure the result, not the text.
- **Ground-truth set:** ~10–15 `(question -> reference SQL / expected result)` pairs, including a few
  off-topic / unanswerable questions.
- **Two layers:** (a) does the generated SQL execute without error? (b) **execution accuracy** — does
  the result match the expected result? Plus a check that the right tables were used, and abstention on
  off-topic questions.
- Reproducible harness in `backend/eval/`, rerun after changes to catch regressions.

### Phases (small steps, similar things grouped)

- **Phase 1 — Plain text-to-SQL, NO agent loop.** One question -> model writes ONE SQL -> we run it
  (read-only) -> model summarizes. No tools, no self-correction. Goal: a working ugly end-to-end answer
  ASAP (skeleton first). Schema + seed + migrations built here.
- **Phase 1.5 — Security hardening + the agent loop.** Read-only role + allowlist + timeout, then the
  tool-calling loop (`get_schema`, `run_query`, self-correct-on-error, max-step cap). The phase that
  makes it *agentic*.
- **>> FIRST DEPLOY happens here — after Phase 1.5, before Phase 1.7.** Once plain text-to-SQL + the
  agent loop work, put it live (Vercel + Render + managed Supabase Postgres) so a working link exists
  early. Eval (1.7) then runs against local DB and improvements auto-redeploy via CD.
- **Phase 1.7 — Evaluation.** Execution-accuracy harness, taught from scratch.
- **Phase 2 — Hybrid (structured + unstructured).** Add a free-text column, embed it, combine SQL
  results with semantic search when a question needs both. The "AI layer over structured + unstructured
  data" story. **Vector store = `pgvector` inside the same Postgres** (Supabase ships pgvector natively
  — no separate vector DB like Pinecone needed); **embeddings = a small OpenAI embedding model.** (HF
  open-source embeddings considered and dropped — pgvector + OpenAI is simpler and reuses our DB.)
- **Phase 3 — Production polish (kept light).** Observability/tracing, **CI** via GitHub Actions
  (auto-run tests + lint + eval on push — note: **CD/deploy is already automatic** via Vercel/Render,
  so the only added piece is automated checks *before* deploy), and optionally **surfacing the agent's
  intermediate steps in the UI** ("inspecting schema… running query… fixing query…") so the
  tool-calling loop is visible to the user — more valuable here than token streaming, because in an
  agent the final answer only arrives after the tool steps. Optional model routing (cheap model
  default, escalate hard questions). Document more than gold-plate.

  *(Explicitly NOT building: a separate manager dashboard — the informative empty state covers the
  "what is this / what data is behind it" need without the scope. SSE token streaming — low value in an
  agent flow; the intermediate-steps view above is the better use of that effort.)*

---

## 5. Settled decisions — quick reference

| Topic | Decision |
|---|---|
| Project | Agentic text-to-SQL assistant over a manufacturing DB |
| Targets | Agents / tool calling, structured-data (SQL), async Python, second LLM provider (OpenAI) |
| Domain | Discrete-manufacturing factory making industrial electrical/electromechanical products; production & downtime backbone, quality attached |
| Agent | OpenAI **native tool calling** + a **hand-written loop**. **No LangChain / no framework** |
| Tools exposed | `get_schema()`, `run_query(sql)` (Phase 1.5) |
| Self-correction | Model sees DB error -> fixes SQL -> retries; max-step cap prevents infinite loops |
| LLM | OpenAI cheap mini/nano tool-calling model — verify current name/price, do NOT hardcode |
| OpenAI skill | `openai-api-python` (links + behavior, no hardcoded model/price); Responses vs Chat Completions decided at first call; create before first OpenAI call |
| Payment | Prepaid credits (~$10), auto-recharge OFF -> no recurring charge, stops when credits end |
| Database | PostgreSQL in Docker; synthetic-but-realistic data we generate; readable/teachable schema, rich enough for 10–15+ eval questions |
| Python tooling | **Poetry** for deps/venv (taught via npm analogies — new to him) |
| Migrations | **Alembic**, hand-written raw-SQL migrations (`op.execute`), **no SQLAlchemy ORM models** |
| DB driver | **asyncpg** (async-native, no ORM) |
| Async | Used throughout the I/O path (DB + LLM); taught from scratch this project |
| DB security | Read-only Postgres role (SELECT only) + code allowlist (single-SELECT, forced LIMIT) + statement timeout |
| Auth | Shared `X-API-Key` (gateway -> FastAPI) ONLY. Per-user auth/JWT **out of scope** |
| Architecture | Two services: Next.js (frontend + thin gateway) + FastAPI (AI service). **No separate business backend** — the DB is "the existing system" |
| AI service | Python + FastAPI, layered (routes -> services -> repositories -> core -> models), async |
| Repo | One repo, plain folder split, no heavy monorepo tooling |
| Local | docker-compose (Postgres + FastAPI [+ frontend]), internal network |
| Deploy (prod) | Distributed: Vercel (frontend) + Render (FastAPI) + **Supabase** managed free Postgres (ships pgvector; inactive projects pause, not deleted) |
| First deploy | After Phase 1.5 (agent loop working), before Phase 1.7 (eval) |
| CI/CD | CD already automatic via Vercel/Render. CI = GitHub Actions auto-tests/lint/eval on push (Phase 3, light) |
| Frontend | Full-page chat; **shadcn/ui** base components; **informative** empty state (what is this + what data is behind it + example questions); **TR/EN static UI toggle** (chrome only, not answers); **SQL hidden-but-expandable** per answer + result table |
| Eval | Execution-accuracy (result match, not text), ~10–15 Q->expected pairs + off-topic; taught from scratch |
| Comments | None unless a comment earns a non-obvious "why"; docstrings encouraged |
| Phase 1 | Plain text-to-SQL, NO agent loop; schema + seed + migrations; working ugly skeleton first |
| Phase 1.5 | Security hardening + the agent loop (tools, self-correction) |
| Phase 1.7 | Execution-accuracy eval harness |
| Phase 2 | Hybrid: free-text column -> embeddings -> combine with SQL; **pgvector** (in same Postgres) + **small OpenAI embedding model** (not Pinecone, not HF) |
| Phase 3 | Production polish (observability, GitHub Actions CI, optional agent-intermediate-steps view + model routing) — light. NOT a dashboard, NOT SSE token streaming |
| Working style | Tiny commit-sized tasks; teach as you build (esp. big-picture -> SQL -> relations -> migrations, and agents/async); he approves before commit; he runs all terminal commands |
| Language | He asks in Turkish/English; answers in English; **no Turkish in code/commits** |
