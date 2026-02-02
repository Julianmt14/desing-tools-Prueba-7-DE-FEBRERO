"""adjust #3 stirrup 135 hooks to 0.08 m

Revision ID: 0013
Revises: 0012
Create Date: 2026-02-15
"""

from __future__ import annotations

from decimal import Decimal

from alembic import op
import sqlalchemy as sa


revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


hook_lengths_table = sa.table(
    "hook_lengths",
    sa.column("bar_mark", sa.String(length=10)),
    sa.column("stirrup_135_m", sa.Numeric(5, 3)),
)

NEW_LENGTH = Decimal("0.080")
OLD_LENGTH = Decimal("0.095")


def upgrade() -> None:
    op.execute(
        hook_lengths_table.update()
        .where(hook_lengths_table.c.bar_mark == "#3")
        .values(stirrup_135_m=NEW_LENGTH)
    )


def downgrade() -> None:
    op.execute(
        hook_lengths_table.update()
        .where(hook_lengths_table.c.bar_mark == "#3")
        .values(stirrup_135_m=OLD_LENGTH)
    )
