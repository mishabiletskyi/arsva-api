"""add dashboard tasks and outbound jobs

Revision ID: 7e1c4d9b2a11
Revises: 2d4f6b7a8c9d
Create Date: 2026-03-03 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7e1c4d9b2a11"
down_revision: Union[str, Sequence[str], None] = "2d4f6b7a8c9d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dashboard_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("created_by_admin_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'in_progress', 'done')",
            name="ck_dashboard_tasks_status",
        ),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dashboard_tasks_id"), "dashboard_tasks", ["id"], unique=False)
    op.create_index(
        op.f("ix_dashboard_tasks_organization_id"),
        "dashboard_tasks",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_dashboard_tasks_property_id"),
        "dashboard_tasks",
        ["property_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_dashboard_tasks_created_by_admin_id"),
        "dashboard_tasks",
        ["created_by_admin_id"],
        unique=False,
    )

    op.create_table(
        "outbound_call_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("property_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="previewed", nullable=False),
        sa.Column("trigger_mode", sa.String(length=50), server_default="manual", nullable=False),
        sa.Column("dry_run", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("requested_by_admin_id", sa.Integer(), nullable=True),
        sa.Column("total_candidates", sa.Integer(), server_default="0", nullable=False),
        sa.Column("eligible_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("blocked_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'previewed', 'processing', 'completed', 'failed')",
            name="ck_outbound_call_jobs_status",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_outbound_call_jobs_id"), "outbound_call_jobs", ["id"], unique=False)
    op.create_index(
        op.f("ix_outbound_call_jobs_organization_id"),
        "outbound_call_jobs",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_outbound_call_jobs_property_id"),
        "outbound_call_jobs",
        ["property_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_outbound_call_jobs_requested_by_admin_id"),
        "outbound_call_jobs",
        ["requested_by_admin_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_outbound_call_jobs_requested_by_admin_id"), table_name="outbound_call_jobs")
    op.drop_index(op.f("ix_outbound_call_jobs_property_id"), table_name="outbound_call_jobs")
    op.drop_index(op.f("ix_outbound_call_jobs_organization_id"), table_name="outbound_call_jobs")
    op.drop_index(op.f("ix_outbound_call_jobs_id"), table_name="outbound_call_jobs")
    op.drop_table("outbound_call_jobs")

    op.drop_index(op.f("ix_dashboard_tasks_created_by_admin_id"), table_name="dashboard_tasks")
    op.drop_index(op.f("ix_dashboard_tasks_property_id"), table_name="dashboard_tasks")
    op.drop_index(op.f("ix_dashboard_tasks_organization_id"), table_name="dashboard_tasks")
    op.drop_index(op.f("ix_dashboard_tasks_id"), table_name="dashboard_tasks")
    op.drop_table("dashboard_tasks")
