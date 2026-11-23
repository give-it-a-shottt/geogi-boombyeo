"""처음 테이블 4개: places, snapshots, forecasts, place_status

Revision ID: 0001
Revises:
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "places",
        sa.Column("code", sa.String(10), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("eng_name", sa.String(200), nullable=False),
        sa.Column("lat", sa.Float, nullable=False),
        sa.Column("lng", sa.Float, nullable=False),
    )
    op.create_index("ix_places_category", "places", ["category"])

    op.create_table(
        "snapshots",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "place_code",
            sa.String(10),
            sa.ForeignKey("places.code", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("level", sa.Integer, nullable=False),
        sa.Column("ppltn_min", sa.Integer, nullable=True),
        sa.Column("ppltn_max", sa.Integer, nullable=True),
        sa.UniqueConstraint("place_code", "observed_at", name="uq_snapshots_place_observed"),
        sa.CheckConstraint("level BETWEEN 1 AND 4", name="ck_snapshots_level"),
    )

    op.create_table(
        "forecasts",
        sa.Column(
            "place_code",
            sa.String(10),
            sa.ForeignKey("places.code", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("forecast_time", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("level", sa.Integer, nullable=False),
        sa.Column("ppltn_min", sa.Integer, nullable=True),
        sa.Column("ppltn_max", sa.Integer, nullable=True),
        sa.CheckConstraint("level BETWEEN 1 AND 4", name="ck_forecasts_level"),
    )

    op.create_table(
        "place_status",
        sa.Column(
            "place_code",
            sa.String(10),
            sa.ForeignKey("places.code", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("level", sa.Integer, nullable=True),
        sa.Column("ppltn_min", sa.Integer, nullable=True),
        sa.Column("ppltn_max", sa.Integer, nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fail_count", sa.Integer, nullable=False),
        sa.Column("last_error", sa.String(200), nullable=True),
        sa.CheckConstraint("level IS NULL OR level BETWEEN 1 AND 4", name="ck_place_status_level"),
    )


def downgrade() -> None:
    op.drop_table("place_status")
    op.drop_table("forecasts")
    op.drop_table("snapshots")
    op.drop_index("ix_places_category", table_name="places")
    op.drop_table("places")
