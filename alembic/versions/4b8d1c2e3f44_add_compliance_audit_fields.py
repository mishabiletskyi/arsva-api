"""add compliance audit fields

Revision ID: 4b8d1c2e3f44
Revises: 7e1c4d9b2a11
Create Date: 2026-03-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4b8d1c2e3f44"
down_revision: Union[str, Sequence[str], None] = "7e1c4d9b2a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("consent_source", sa.String(length=255), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("consent_document_version", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("opt_out_timestamp", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "call_logs",
        sa.Column("script_version", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("call_logs", "script_version")
    op.drop_column("tenants", "opt_out_timestamp")
    op.drop_column("tenants", "consent_document_version")
    op.drop_column("tenants", "consent_source")
