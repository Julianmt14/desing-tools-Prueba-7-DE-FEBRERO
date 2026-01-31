"""convert element level to numeric

Revision ID: 0004
Revises: 0003
Create Date: 2026-01-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "despiece_vigas",
        "element_level",
        existing_type=sa.String(length=50),
        type_=sa.Numeric(6, 2),
        postgresql_using=(
            r"NULLIF(regexp_replace(element_level, '[^0-9\+\-\.]+', '', 'g'), '')::numeric(6,2)"
        ),
    )


def downgrade() -> None:
    op.alter_column(
        "despiece_vigas",
        "element_level",
        existing_type=sa.Numeric(6, 2),
        type_=sa.String(length=50),
        postgresql_using="CASE WHEN element_level IS NULL THEN NULL ELSE element_level::text END",
    )
