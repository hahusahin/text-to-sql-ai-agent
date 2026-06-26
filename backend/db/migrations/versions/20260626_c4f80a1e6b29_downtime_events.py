"""downtime_events

Create downtime_events: recorded stops on the shop floor. Tied to a line and a
shift (always), and optionally to a specific machine. First nullable FK, first
boolean column, reason_code as a small fixed set.

Revision ID: c4f80a1e6b29
Revises: b7e21d4f9a36
Create Date: 2026-06-26 12:10:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'c4f80a1e6b29'
down_revision = 'b7e21d4f9a36'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE downtime_events (
            id               integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            line_id          integer NOT NULL REFERENCES production_lines (id),
            machine_id       integer REFERENCES machines (id),
            shift_id         integer NOT NULL REFERENCES shifts (id),
            reason_code      text NOT NULL
                CHECK (reason_code IN (
                    'setup_changeover',
                    'breakdown',
                    'material_shortage',
                    'planned_maintenance'
                )),
            is_planned       boolean NOT NULL,
            duration_minutes integer NOT NULL CHECK (duration_minutes > 0),
            occurred_at      timestamptz NOT NULL
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE downtime_events;")
