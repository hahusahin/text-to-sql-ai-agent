"""downtime embedding column

Phase 2 hybrid search: give ``downtime_events`` a place to store the embedding
of its ``notes`` free text so semantic search ("find oil-leak stops") can rank
rows by meaning instead of a brittle keyword LIKE.

1. Add ``embedding vector(1536)`` — 1536 matches the output dimension of
   ``text-embedding-3-small`` (the model pinned in Settings). Nullable because
   only ~85% of events carry a note, and even those are filled by a separate
   pipeline (Task 2.3b), not this migration.
2. Add an **HNSW** index for approximate nearest-neighbour search with the
   **cosine** operator class. HNSW (not IVFFlat) on purpose: it builds fine on an
   empty column and needs no training pass over existing rows, so it's correct to
   create here, before any vectors exist. Cosine (``vector_cosine_ops`` / the
   ``<=>`` operator) is the conventional text-similarity metric and matches how
   Task 2.3b will query.

Revision ID: c4004287e324
Revises: b3e6f1a9c72d
Create Date: 2026-07-01 17:14:46.639631
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'c4004287e324'
down_revision = 'b3e6f1a9c72d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE downtime_events ADD COLUMN embedding vector(1536);")
    op.execute(
        "CREATE INDEX ix_downtime_events_embedding "
        "ON downtime_events USING hnsw (embedding vector_cosine_ops);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ix_downtime_events_embedding;")
    op.execute("ALTER TABLE downtime_events DROP COLUMN embedding;")
