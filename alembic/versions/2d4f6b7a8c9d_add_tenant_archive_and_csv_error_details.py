"""add tenant archive and csv error details

Revision ID: 2d4f6b7a8c9d
Revises: 9f3c1a8c7b2d
Create Date: 2026-03-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2d4f6b7a8c9d"
down_revision: Union[str, Sequence[str], None] = "9f3c1a8c7b2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("is_archived", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "tenants",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "csv_imports",
        sa.Column("errors", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("csv_imports", "errors")
    op.drop_column("tenants", "archived_at")
    op.drop_column("tenants", "is_archived")
