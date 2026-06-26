"""catalog_tables

Create the reference / catalog tables: products, production_lines, machines, shifts.
These are the "stage and cast" — small, mostly static tables that other rows point at.

Revision ID: f3a91c7b2e84
Revises: 9d6812661c65
Create Date: 2026-06-26 11:15:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'f3a91c7b2e84'
down_revision = '9d6812661c65'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE products (
            id       integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name     text NOT NULL UNIQUE,
            category text NOT NULL
        );
        """
    )

    op.execute(
        """
        CREATE TABLE production_lines (
            id       integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name     text NOT NULL UNIQUE,
            location text NOT NULL
        );
        """
    )

    op.execute(
        """
        CREATE TABLE machines (
            id      integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            line_id integer NOT NULL REFERENCES production_lines (id),
            name    text NOT NULL,
            type    text NOT NULL,
            UNIQUE (line_id, name)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE shifts (
            id         integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name       text NOT NULL UNIQUE,
            start_time time NOT NULL,
            end_time   time NOT NULL
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE shifts;")
    op.execute("DROP TABLE machines;")
    op.execute("DROP TABLE production_lines;")
    op.execute("DROP TABLE products;")
