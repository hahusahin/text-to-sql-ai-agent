"""pgvector extension + downtime_events.notes

Phase 2 groundwork for hybrid (structured + unstructured) search:

1. Enable the ``vector`` extension (pgvector) so a later migration can add an
   embedding column and a similarity index. Supabase ships pgvector; locally we
   run the ``pgvector/pgvector:pg16`` image, which bundles it.
2. Add ``downtime_events.notes`` — a free-text operator comment on a stop. This
   is the unstructured data the embedding pipeline (Task 2.3) will vectorize.
   Nullable on purpose: not every stop is annotated in real life, and it lets us
   exercise the pipeline's handling of missing text.

No embedding/vector column yet — that arrives in Task 2.3.

Revision ID: b3e6f1a9c72d
Revises: a2f5c9e30b18
Create Date: 2026-07-01 10:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'b3e6f1a9c72d'
down_revision = 'a2f5c9e30b18'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("ALTER TABLE downtime_events ADD COLUMN notes text;")


def downgrade() -> None:
    op.execute("ALTER TABLE downtime_events DROP COLUMN notes;")
    op.execute("DROP EXTENSION IF EXISTS vector;")
