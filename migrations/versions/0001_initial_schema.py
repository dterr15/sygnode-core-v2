"""Initial schema.

Revision ID: 0001
Create Date: 2026-03-04
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The schema is created via SQLAlchemy models + Base.metadata.create_all
    # For production, use the full SQL from 07_db_schema.sql
    #
    # The PostgreSQL RULEs for append-only timeline are applied here:
    op.execute("""
        CREATE RULE no_update_timeline AS ON UPDATE TO case_timeline_events DO INSTEAD NOTHING;
    """)
    op.execute("""
        CREATE RULE no_delete_timeline AS ON DELETE TO case_timeline_events DO INSTEAD NOTHING;
    """)


def downgrade() -> None:
    op.execute("DROP RULE IF EXISTS no_update_timeline ON case_timeline_events;")
    op.execute("DROP RULE IF EXISTS no_delete_timeline ON case_timeline_events;")
