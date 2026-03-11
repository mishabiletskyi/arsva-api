"""add call policies and job policy snapshot

Revision ID: b6d7e8f90123
Revises: 8c9a2b1d4e55
Create Date: 2026-03-10 20:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b6d7e8f90123"
down_revision: Union[str, Sequence[str], None] = "8c9a2b1d4e55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "call_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("min_hours_between_calls", sa.Integer(), server_default="72", nullable=False),
        sa.Column("max_calls_7d", sa.Integer(), server_default="2", nullable=False),
        sa.Column("max_calls_30d", sa.Integer(), server_default="4", nullable=False),
        sa.Column("call_window_start", sa.String(length=5), server_default="08:00", nullable=False),
        sa.Column("call_window_end", sa.String(length=5), server_default="21:00", nullable=False),
        sa.Column("days_late_min", sa.Integer(), server_default="3", nullable=False),
        sa.Column("days_late_max", sa.Integer(), server_default="10", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "min_hours_between_calls >= 1 AND min_hours_between_calls <= 720",
            name="ck_call_policies_min_hours_between_calls",
        ),
        sa.CheckConstraint(
            "max_calls_7d >= 0 AND max_calls_7d <= 14",
            name="ck_call_policies_max_calls_7d",
        ),
        sa.CheckConstraint(
            "max_calls_30d >= 0 AND max_calls_30d <= 60",
            name="ck_call_policies_max_calls_30d",
        ),
        sa.CheckConstraint(
            "days_late_min >= 0",
            name="ck_call_policies_days_late_min",
        ),
        sa.CheckConstraint(
            "days_late_max >= days_late_min",
            name="ck_call_policies_days_late_max",
        ),
        sa.CheckConstraint(
            "length(call_window_start) = 5 "
            "AND substr(call_window_start, 3, 1) = ':' "
            "AND CAST(substr(call_window_start, 1, 2) AS INTEGER) BETWEEN 0 AND 23 "
            "AND CAST(substr(call_window_start, 4, 2) AS INTEGER) BETWEEN 0 AND 59",
            name="ck_call_policies_call_window_start_format",
        ),
        sa.CheckConstraint(
            "length(call_window_end) = 5 "
            "AND substr(call_window_end, 3, 1) = ':' "
            "AND CAST(substr(call_window_end, 1, 2) AS INTEGER) BETWEEN 0 AND 23 "
            "AND CAST(substr(call_window_end, 4, 2) AS INTEGER) BETWEEN 0 AND 59",
            name="ck_call_policies_call_window_end_format",
        ),
        sa.CheckConstraint(
            "call_window_start <> call_window_end",
            name="ck_call_policies_call_window_not_equal",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "property_id",
            name="uq_call_policies_org_property",
        ),
    )
    op.create_index(op.f("ix_call_policies_id"), "call_policies", ["id"], unique=False)
    op.create_index(op.f("ix_call_policies_organization_id"), "call_policies", ["organization_id"], unique=False)
    op.create_index(op.f("ix_call_policies_property_id"), "call_policies", ["property_id"], unique=False)

    op.add_column("outbound_call_jobs", sa.Column("policy_snapshot", sa.JSON(), nullable=True))

    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            INSERT INTO call_policies (
                organization_id,
                property_id,
                min_hours_between_calls,
                max_calls_7d,
                max_calls_30d,
                call_window_start,
                call_window_end,
                days_late_min,
                days_late_max,
                is_active,
                created_at,
                updated_at
            )
            SELECT
                p.organization_id,
                p.id,
                72,
                2,
                4,
                '08:00',
                '21:00',
                3,
                10,
                true,
                now(),
                now()
            FROM properties p
            ON CONFLICT (organization_id, property_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_column("outbound_call_jobs", "policy_snapshot")

    op.drop_index(op.f("ix_call_policies_property_id"), table_name="call_policies")
    op.drop_index(op.f("ix_call_policies_organization_id"), table_name="call_policies")
    op.drop_index(op.f("ix_call_policies_id"), table_name="call_policies")
    op.drop_table("call_policies")
