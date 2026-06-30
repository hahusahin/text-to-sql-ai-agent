---
title: Manufacturing Text-to-SQL AI Service
emoji: 🏭
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Manufacturing Text-to-SQL AI Service

FastAPI service behind the [Manufacturing Text-to-SQL assistant](../README.md). It
takes a plain-language question, uses OpenAI tool calling to inspect the schema,
write a read-only SQL query, run it (and self-correct on error), and answer in
plain language.

This `README.md` doubles as the **Hugging Face Space** config: the YAML front
matter above tells HF to build this folder as a Docker SDK Space and route
traffic to port **7860** (see the `Dockerfile`).

## Runtime configuration (set as Space Secrets, never committed)

| Secret | Purpose |
|---|---|
| `DATABASE_URL_READONLY` | SELECT-only Supabase connection (session pooler). The only DB credential the runtime holds. |
| `OPENAI_API_KEY` | OpenAI API key. |
| `OPENAI_MODEL` | Chat model name. |
| `API_KEY` | Shared secret the gateway must send as `X-API-Key`. |
| `DB_STATEMENT_TIMEOUT_MS` | Per-statement timeout (optional; defaults to 5000). |

The privileged owner `DATABASE_URL` is **not** set here — migrations and seed run
locally, so the deployed service never holds the owner credentials.
