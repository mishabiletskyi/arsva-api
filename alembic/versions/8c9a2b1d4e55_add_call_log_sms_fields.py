"""add call log sms fields

Revision ID: 8c9a2b1d4e55
Revises: 4b8d1c2e3f44
Create Date: 2026-03-09 22:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8c9a2b1d4e55"
down_revision: Union[str, Sequence[str], None] = "4b8d1c2e3f44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "call_logs",
        sa.Column("sms_sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("call_logs", sa.Column("sms_status", sa.String(length=100), nullable=True))
    op.add_column("call_logs", sa.Column("sms_message_sid", sa.String(length=255), nullable=True))
    op.add_column("call_logs", sa.Column("sms_error_message", sa.Text(), nullable=True))
    op.add_column("call_logs", sa.Column("sms_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_call_logs_sms_message_sid"), "call_logs", ["sms_message_sid"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_call_logs_sms_message_sid"), table_name="call_logs")
    op.drop_column("call_logs", "sms_sent_at")
    op.drop_column("call_logs", "sms_error_message")
    op.drop_column("call_logs", "sms_message_sid")
    op.drop_column("call_logs", "sms_status")
    op.drop_column("call_logs", "sms_sent")
