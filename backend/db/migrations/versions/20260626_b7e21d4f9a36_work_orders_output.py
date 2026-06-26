"""work_orders_output

Create the production backbone: work_orders (the plan) and production_output
(the reality recorded against a work order). First event tables, first
multi-FK row, first one-to-many fact relationship.

Revision ID: b7e21d4f9a36
Revises: f3a91c7b2e84
Create Date: 2026-06-26 11:45:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'b7e21d4f9a36'
down_revision = 'f3a91c7b2e84'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE work_orders (
            id               integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            product_id       integer NOT NULL REFERENCES products (id),
            line_id          integer NOT NULL REFERENCES production_lines (id),
            shift_id         integer NOT NULL REFERENCES shifts (id),
            planned_quantity integer NOT NULL CHECK (planned_quantity > 0),
            start_date       date NOT NULL,
            status           text NOT NULL
                CHECK (status IN ('planned', 'in_progress', 'completed'))
        );
        """
    )

    op.execute(
        """
        CREATE TABLE production_output (
            id                integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            work_order_id     integer NOT NULL REFERENCES work_orders (id),
            produced_quantity integer NOT NULL CHECK (produced_quantity >= 0),
            scrap_quantity    integer NOT NULL DEFAULT 0 CHECK (scrap_quantity >= 0),
            recorded_at       timestamptz NOT NULL,
            CHECK (scrap_quantity <= produced_quantity)
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE production_output;")
    op.execute("DROP TABLE work_orders;")
