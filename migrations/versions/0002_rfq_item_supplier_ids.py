"""Add supplier_ids column to rfq_items.

Revision ID: 0002
Down Revision: 0001
Create Date: 2026-03-06
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE rfq_items ADD COLUMN IF NOT EXISTS supplier_ids uuid[] NOT NULL DEFAULT '{}'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE rfq_items DROP COLUMN IF EXISTS supplier_ids")
