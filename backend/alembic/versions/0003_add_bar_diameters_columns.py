"""add bar diameter fields to despiece_vigas

Revision ID: 0003
Revises: 0002
Create Date: 2026-01-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("despiece_vigas", sa.Column("top_bar_diameters", sa.JSON(), nullable=True))
    op.add_column("despiece_vigas", sa.Column("bottom_bar_diameters", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("despiece_vigas", "bottom_bar_diameters")
    op.drop_column("despiece_vigas", "top_bar_diameters")
