"""sync despiece schema with frontend payload

Revision ID: 0005
Revises: 0004
Create Date: 2026-01-31
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("despiece_vigas", sa.Column("project_name", sa.String(length=255), nullable=True))
    op.add_column("despiece_vigas", sa.Column("beam_label", sa.String(length=255), nullable=True))
    op.add_column("despiece_vigas", sa.Column("reinforcement", sa.String(length=100), nullable=True))
    op.add_column("despiece_vigas", sa.Column("span_count", sa.Integer(), nullable=True))
    op.add_column("despiece_vigas", sa.Column("support_widths_cm", sa.JSON(), nullable=True))
    op.add_column("despiece_vigas", sa.Column("span_geometries", sa.JSON(), nullable=True))
    op.add_column("despiece_vigas", sa.Column("segments", sa.JSON(), nullable=True))

    op.execute(
        """
        UPDATE despiece_vigas dv
        SET
            project_name = COALESCE(NULLIF(d.settings->>'project_name', ''), 'Proyecto sin nombre'),
            beam_label = COALESCE(NULLIF(d.settings->>'beam_label', ''), dv.element_identifier),
            reinforcement = COALESCE(NULLIF(d.settings->>'reinforcement', ''), '420 MPa (Grado 60)'),
            span_count = COALESCE(NULLIF(d.settings->>'span_count', '')::integer, 1),
            support_widths_cm = COALESCE((d.settings::jsonb -> 'support_widths_cm')::json, '[]'::json),
            span_geometries = COALESCE((d.settings::jsonb -> 'span_geometries')::json, '[]'::json),
            segments = COALESCE((d.settings::jsonb -> 'segments')::json, '[]'::json)
        FROM designs d
        WHERE dv.design_id = d.id
        """
    )

    op.execute(
        """
        UPDATE despiece_vigas
        SET project_name = COALESCE(project_name, 'Proyecto sin nombre'),
            beam_label = COALESCE(beam_label, element_identifier),
            reinforcement = COALESCE(reinforcement, '420 MPa (Grado 60)'),
            span_count = COALESCE(span_count, 1),
            span_geometries = COALESCE(span_geometries, '[]'::json),
            segments = COALESCE(segments, '[]'::json)
        """
    )

    op.alter_column("despiece_vigas", "project_name", existing_type=sa.String(length=255), nullable=False)
    op.alter_column("despiece_vigas", "beam_label", existing_type=sa.String(length=255), nullable=False)
    op.alter_column("despiece_vigas", "reinforcement", existing_type=sa.String(length=100), nullable=False)
    op.alter_column("despiece_vigas", "span_count", existing_type=sa.Integer(), nullable=False)
    op.alter_column("despiece_vigas", "span_geometries", existing_type=sa.JSON(), nullable=False)
    op.alter_column("despiece_vigas", "segments", existing_type=sa.JSON(), nullable=False)

    op.drop_column("despiece_vigas", "has_multiple_supports")
    op.drop_column("despiece_vigas", "support_axis_distances")
    op.drop_column("despiece_vigas", "clear_span_between_supports_m")


def downgrade() -> None:
    op.add_column(
        "despiece_vigas",
        sa.Column(
            "has_multiple_supports",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column("despiece_vigas", sa.Column("support_axis_distances", sa.JSON(), nullable=True))
    op.add_column(
        "despiece_vigas",
        sa.Column("clear_span_between_supports_m", sa.Float(), nullable=True),
    )

    op.drop_column("despiece_vigas", "segments")
    op.drop_column("despiece_vigas", "span_geometries")
    op.drop_column("despiece_vigas", "support_widths_cm")
    op.drop_column("despiece_vigas", "span_count")
    op.drop_column("despiece_vigas", "reinforcement")
    op.drop_column("despiece_vigas", "beam_label")
    op.drop_column("despiece_vigas", "project_name")