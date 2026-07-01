"""Embed ``downtime_events.notes`` into the pgvector ``embedding`` column.

Run from ``backend/`` after the seed::

    poetry run poe embed        # == python -m db.seed.embed_notes

Offline one-off pipeline, not part of the live request path. Like ``seed.py`` it
uses the **sync** psycopg2 driver and the **sync** OpenAI client on purpose: a
batch job has no concurrent I/O to overlap (we send whole batches in one call),
so async would add ceremony for no gain — unlike the async request path.

Two design choices worth noting:

* **Idempotent** — only rows that have a note *and* a NULL embedding are fetched,
  so a re-run embeds just what's missing. Safe to repeat.
* **Resumable** — we commit after each batch, so if a later OpenAI call fails, the
  vectors already paid for are persisted and a re-run skips them (see idempotent).

Writing the vector: pgvector accepts its text form ``[0.1,0.2,...]`` and applies
its input function when the value is assigned to a ``vector`` column, so we send
the embedding as that literal string via a normal parameter — no extra adapter
or numpy dependency needed.
"""

from openai import OpenAI
import psycopg2

from app.core.config import get_settings

# OpenAI accepts a list of strings per call; batching keeps the request count
# (and round-trip latency) down. A few hundred short notes need only a handful.
BATCH_SIZE = 128


def _vector_literal(embedding: list[float]) -> str:
    """Render an embedding as pgvector's text form, e.g. ``[0.1,0.2,0.3]``."""
    return "[" + ",".join(str(x) for x in embedding) + "]"


def _fetch_unembedded(cur) -> list[tuple[int, str]]:
    """Return (id, notes) for annotated events that still lack an embedding."""
    cur.execute(
        "SELECT id, notes FROM downtime_events "
        "WHERE notes IS NOT NULL AND embedding IS NULL "
        "ORDER BY id;"
    )
    return cur.fetchall()


def _embed(client: OpenAI, model: str, texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts; response vectors come back in input order."""
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]


def main() -> None:
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    conn = psycopg2.connect(settings.database_url)
    try:
        with conn.cursor() as cur:
            rows = _fetch_unembedded(cur)

        if not rows:
            print("Nothing to embed: every note already has an embedding.")
            return

        total = 0
        for start in range(0, len(rows), BATCH_SIZE):
            batch = rows[start : start + BATCH_SIZE]
            vectors = _embed(
                client, settings.openai_embedding_model, [notes for _, notes in batch]
            )
            with conn.cursor() as cur:
                cur.executemany(
                    "UPDATE downtime_events SET embedding = %s WHERE id = %s;",
                    [
                        (_vector_literal(vector), row_id)
                        for (row_id, _), vector in zip(batch, vectors)
                    ],
                )
            conn.commit()
            total += len(batch)
            print(f"  embedded {total}/{len(rows)}")

        print(f"Done: embedded {total} downtime notes with {settings.openai_embedding_model}.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
