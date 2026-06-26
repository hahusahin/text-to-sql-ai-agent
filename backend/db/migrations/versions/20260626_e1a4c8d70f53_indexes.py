"""indexes

Add indexes on the foreign-key columns (which Postgres does NOT index
automatically) and on the timestamp/date columns that eval questions filter by
("last month/quarter"). Speeds up JOINs and time-range filters.

Revision ID: e1a4c8d70f53
Revises: d9b3f57c0a14
Create Date: 2026-06-26 13:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'e1a4c8d70f53'
down_revision = 'd9b3f57c0a14'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Foreign-key columns (JOIN / filter targets).
    op.execute("CREATE INDEX ix_machines_line_id ON machines (line_id);")
    op.execute("CREATE INDEX ix_work_orders_product_id ON work_orders (product_id);")
    op.execute("CREATE INDEX ix_work_orders_line_id ON work_orders (line_id);")
    op.execute("CREATE INDEX ix_work_orders_shift_id ON work_orders (shift_id);")
    op.execute("CREATE INDEX ix_production_output_work_order_id ON production_output (work_order_id);")
    op.execute("CREATE INDEX ix_downtime_events_line_id ON downtime_events (line_id);")
    op.execute("CREATE INDEX ix_downtime_events_machine_id ON downtime_events (machine_id);")
    op.execute("CREATE INDEX ix_downtime_events_shift_id ON downtime_events (shift_id);")
    op.execute("CREATE INDEX ix_quality_inspections_work_order_id ON quality_inspections (work_order_id);")
    op.execute("CREATE INDEX ix_defects_inspection_id ON defects (inspection_id);")

    # Time columns (date-range filters).
    op.execute("CREATE INDEX ix_work_orders_start_date ON work_orders (start_date);")
    op.execute("CREATE INDEX ix_production_output_recorded_at ON production_output (recorded_at);")
    op.execute("CREATE INDEX ix_downtime_events_occurred_at ON downtime_events (occurred_at);")
    op.execute("CREATE INDEX ix_quality_inspections_inspected_at ON quality_inspections (inspected_at);")


def downgrade() -> None:
    op.execute("DROP INDEX ix_quality_inspections_inspected_at;")
    op.execute("DROP INDEX ix_downtime_events_occurred_at;")
    op.execute("DROP INDEX ix_production_output_recorded_at;")
    op.execute("DROP INDEX ix_work_orders_start_date;")
    op.execute("DROP INDEX ix_defects_inspection_id;")
    op.execute("DROP INDEX ix_quality_inspections_work_order_id;")
    op.execute("DROP INDEX ix_downtime_events_shift_id;")
    op.execute("DROP INDEX ix_downtime_events_machine_id;")
    op.execute("DROP INDEX ix_downtime_events_line_id;")
    op.execute("DROP INDEX ix_production_output_work_order_id;")
    op.execute("DROP INDEX ix_work_orders_shift_id;")
    op.execute("DROP INDEX ix_work_orders_line_id;")
    op.execute("DROP INDEX ix_work_orders_product_id;")
    op.execute("DROP INDEX ix_machines_line_id;")
