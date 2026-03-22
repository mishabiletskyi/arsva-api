"""add business fields to call logs

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-03-22 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("call_logs", sa.Column("call_status", sa.String(length=100), nullable=True))
    op.add_column("call_logs", sa.Column("call_summary", sa.Text(), nullable=True))
    op.add_column("call_logs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("call_logs", sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("call_logs", sa.Column("ended_reason", sa.String(length=255), nullable=True))
    op.add_column("call_logs", sa.Column("provider_cost", sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column(
        "call_logs",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(op.f("ix_call_logs_call_status"), "call_logs", ["call_status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_call_logs_call_status"), table_name="call_logs")
    op.drop_column("call_logs", "updated_at")
    op.drop_column("call_logs", "provider_cost")
    op.drop_column("call_logs", "ended_reason")
    op.drop_column("call_logs", "ended_at")
    op.drop_column("call_logs", "started_at")
    op.drop_column("call_logs", "call_summary")
    op.drop_column("call_logs", "call_status")
