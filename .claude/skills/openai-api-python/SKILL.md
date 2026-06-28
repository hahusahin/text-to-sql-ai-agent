---
name: openai-api-python
description: How to call the OpenAI API from Python in THIS project — which API surface we use, how to pick the model, and the tool-calling loop pattern. Read this before writing or changing any code that calls OpenAI (app/llm/, the agent loop, embeddings).
---

# OpenAI API (Python) — project conventions

Ground rules for every OpenAI call in this repo. Do not rely on model knowledge for
names/prices/SDK shapes — they drift. Verify against the live docs linked below.

## Canonical docs (open these, don't guess)

- API overview / surfaces: https://developers.openai.com/api/docs
- Responses API guide: https://developers.openai.com/api/docs/guides/migrate-to-responses
- Function / tool calling: https://developers.openai.com/api/docs/guides/function-calling
- Models list: https://developers.openai.com/api/docs/models
- Pricing: https://developers.openai.com/api/docs/pricing
- Python SDK: https://github.com/openai/openai-python

## Settled decisions for this project

1. **API surface: the Responses API.** Use `client.responses.create(...)`. This is OpenAI's
   recommended default for new projects; Chat Completions is the legacy surface. **Stay consistent —
   do not mix Chat Completions (`client.chat.completions.create`) into this codebase.**

2. **Async client.** DB and LLM calls are I/O-bound and the service is async throughout, so use
   `AsyncOpenAI` and `await` the call — never the sync `OpenAI` client in request paths.

3. **Model is config, never hardcoded from memory.** The model id lives in `Settings`
   (`OPENAI_MODEL`, env-driven), not as a literal in code. When choosing or changing it, **read the
   live pricing/models pages** and pick a current cheap mini/nano-class tool-calling model. Prices and
   names change — confirm before writing one down.

4. **Key from env only.** `OPENAI_API_KEY` comes from `Settings` / `.env` (git-ignored). Never inline
   a key, never print it, never paste a real key into chat or commits.

## Cost behavior to design around

- **Prompt caching is automatic** on a static prompt *prefix*. Put stable content (system
  instructions, the DB schema) at the **front**; put the variable content (the user's question) at the
  **end**. In the agent loop the schema rides along every step, so prefix-caching is what keeps cost
  low. Cached input is billed at a steep discount.
- Watch **output** tokens (far pricier than input) and the **number of loop steps** — both are the
  real cost drivers, not the schema text.

## Plain call (Phase 1 — no tools)

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=settings.openai_api_key)

response = await client.responses.create(
    model=settings.openai_model,
    instructions=system_text,   # stable, cache-friendly (schema lives here)
    input=user_question,        # variable
)
answer = response.output_text   # SDK convenience: concatenated text output
```

## Tool-calling loop (Phase 1.5) — the pattern we hand-write

The loop is written by hand (no LangChain/framework) so the mechanism is explicit.

1. **Define tools** as a list passed to `tools=`:
   ```python
   tools = [{
       "type": "function",
       "name": "run_query",
       "description": "Execute a read-only SQL SELECT and return rows.",
       "parameters": {
           "type": "object",
           "properties": {"sql": {"type": "string", "description": "A single SELECT statement."}},
           "required": ["sql"],
       },
   }]
   ```

2. **Call**, keeping a running `input` list (the conversation):
   ```python
   response = await client.responses.create(model=..., tools=tools, input=input_list)
   ```

3. **Inspect `response.output`.** If an item has `type == "function_call"`, it carries `call_id`,
   `name`, and JSON-encoded `arguments`. Otherwise the model is done — read `response.output_text`.

4. **Execute the tool**, then append BOTH the model's call and your result back into `input_list`:
   ```python
   input_list += response.output                       # the function_call item(s)
   input_list.append({
       "type": "function_call_output",
       "call_id": item.call_id,
       "output": result_or_error_text,                 # feed errors back too → self-correction
   })
   ```
   Feeding the **DB error text** back (not raising) is what lets the model fix its own SQL.

5. **Loop** back to step 2 until the model returns a final text answer. **Enforce a max-step cap**
   (e.g. 5 tool calls) so a stuck model can't loop forever.

## Checklist before committing OpenAI code

- [ ] Uses `client.responses.create` (not chat.completions).
- [ ] `AsyncOpenAI` + `await`.
- [ ] Model and key come from `Settings`, not literals.
- [ ] Stable content (schema/instructions) is at the front for caching.
- [ ] (Loop code) errors are fed back as `function_call_output`; a max-step cap exists.
