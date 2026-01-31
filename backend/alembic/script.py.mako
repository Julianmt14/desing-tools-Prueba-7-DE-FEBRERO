"""Generic Alembic revision script."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = None
"""Revision ID."""

down_revision = None
"""Previous revision ID."""

branch_labels = None
"""Branch labels."""

depends_on = None
"""Downstream dependencies."""


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
