"""add despiece_vigas table

Revision ID: 0002
Revises: 0001
Create Date: 2026-01-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.create_table(
        "despiece_vigas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("design_id", sa.Integer(), sa.ForeignKey("designs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("top_bars_qty", sa.Integer(), nullable=False),
        sa.Column("bottom_bars_qty", sa.Integer(), nullable=False),
        sa.Column("max_rebar_length_m", sa.String(length=10), nullable=False),
        sa.Column("lap_splice_length_min_m", sa.Float(), nullable=False),
        sa.Column("lap_splice_location", sa.String(length=255), nullable=False),
        sa.Column("section_changes", sa.JSON(), nullable=True),
        sa.Column("has_multiple_supports", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("has_cantilevers", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("hook_type", sa.String(length=20), nullable=False),
        sa.Column("support_axis_distances", sa.JSON(), nullable=True),
        sa.Column("clear_span_between_supports_m", sa.Float(), nullable=True),
        sa.Column("axis_numbering", sa.String(length=100), nullable=True),
        sa.Column("element_identifier", sa.String(length=100), nullable=False),
        sa.Column("element_level", sa.String(length=50), nullable=True),
        sa.Column("element_quantity", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("stirrups_config", sa.JSON(), nullable=True),
        sa.Column("energy_dissipation_class", sa.String(length=3), nullable=False),
        sa.Column("concrete_strength", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("design_id", name="uq_despiece_vigas_design_id"),
        sa.CheckConstraint(
            "energy_dissipation_class IN ('DES','DMO','DMI')",
            name="ck_despiece_vigas_energy_class",
        ),
    )

    op.create_index("ix_despiece_vigas_design_id", "despiece_vigas", ["design_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_despiece_vigas_design_id", table_name="despiece_vigas")
    op.drop_table("despiece_vigas")
