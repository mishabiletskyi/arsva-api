"""add csv import soft delete fields

Revision ID: c1d2e3f4a5b6
Revises: b6d7e8f90123
Create Date: 2026-03-18 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b6d7e8f90123"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("csv_imports", sa.Column("deleted_by_admin_id", sa.Integer(), nullable=True))
    op.add_column("csv_imports", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_csv_imports_deleted_by_admin_id_admin_users",
        "csv_imports",
        "admin_users",
        ["deleted_by_admin_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_csv_imports_deleted_by_admin_id_admin_users",
        "csv_imports",
        type_="foreignkey",
    )
    op.drop_column("csv_imports", "deleted_at")
    op.drop_column("csv_imports", "deleted_by_admin_id")
