"""add cover_cm column to despiece_vigas

Revision ID: 0007
Revises: 0006
Create Date: 2026-01-31
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("despiece_vigas", sa.Column("cover_cm", sa.Integer(), nullable=True))
    op.execute("UPDATE despiece_vigas SET cover_cm = 4 WHERE cover_cm IS NULL")
    op.alter_column("despiece_vigas", "cover_cm", nullable=False)


def downgrade() -> None:
    op.drop_column("despiece_vigas", "cover_cm")
