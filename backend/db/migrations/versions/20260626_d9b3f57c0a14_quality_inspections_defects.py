"""quality_inspections_defects

Create the quality chain that hangs off production:
work_orders -> quality_inspections -> defects. A QC check is tied to a work
order; a defect is tied to a check. Reaching a defect back to its work order
takes two FK hops.

Revision ID: d9b3f57c0a14
Revises: c4f80a1e6b29
Create Date: 2026-06-26 12:35:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'd9b3f57c0a14'
down_revision = 'c4f80a1e6b29'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE quality_inspections (
            id                 integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            work_order_id      integer NOT NULL REFERENCES work_orders (id),
            inspected_quantity integer NOT NULL CHECK (inspected_quantity > 0),
            passed_quantity    integer NOT NULL CHECK (passed_quantity >= 0),
            inspected_at       timestamptz NOT NULL,
            CHECK (passed_quantity <= inspected_quantity)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE defects (
            id            integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            inspection_id integer NOT NULL REFERENCES quality_inspections (id),
            defect_type   text NOT NULL,
            severity      text NOT NULL
                CHECK (severity IN ('minor', 'major', 'critical')),
            quantity      integer NOT NULL CHECK (quantity > 0)
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE defects;")
    op.execute("DROP TABLE quality_inspections;")
