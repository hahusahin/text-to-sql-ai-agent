"""readonly_role

Create a SELECT-only Postgres role (``readonly_user``) that the app runtime
connects as. This is the *real* guardrail: even if the LLM emits ``DROP TABLE``,
this role physically cannot run it. Migrations and seed keep using the owner
role (``app``); only the request path runs as ``readonly_user``.

Roles are cluster-global, not schema objects, so putting this in a migration is
a slight stretch conceptually. We accept it because it makes the role
reproducible the same way everywhere (``alembic upgrade`` locally and on
Supabase) and keeps one source of truth.

The committed password is a *local-dev* convenience only (mirrors
``app_local_dev`` in docker-compose). In production the password is rotated
out-of-band (``ALTER ROLE ... PASSWORD``) and kept in an env secret.

Revision ID: a2f5c9e30b18
Revises: e1a4c8d70f53
Create Date: 2026-06-28 10:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'a2f5c9e30b18'
down_revision = 'e1a4c8d70f53'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'readonly_user') THEN
                CREATE ROLE readonly_user LOGIN PASSWORD 'readonly_local_dev';
            END IF;
            EXECUTE format('GRANT CONNECT ON DATABASE %I TO readonly_user', current_database());
        END
        $$;
        """
    )

    op.execute("GRANT USAGE ON SCHEMA public TO readonly_user;")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;")
    op.execute(
        """
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            GRANT SELECT ON TABLES TO readonly_user;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            REVOKE SELECT ON TABLES FROM readonly_user;
        """
    )
    op.execute("REVOKE SELECT ON ALL TABLES IN SCHEMA public FROM readonly_user;")
    op.execute("REVOKE USAGE ON SCHEMA public FROM readonly_user;")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'readonly_user') THEN
                EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM readonly_user', current_database());
                DROP ROLE readonly_user;
            END IF;
        END
        $$;
        """
    )
