"""add multi tenant foundation

Revision ID: 9f3c1a8c7b2d
Revises: 3cac48827801
Create Date: 2026-03-01 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f3c1a8c7b2d"
down_revision: Union[str, Sequence[str], None] = "3cac48827801"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organizations_id"), "organizations", ["id"], unique=False)
    op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True)

    op.create_table(
        "properties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("timezone", sa.String(length=100), nullable=False),
        sa.Column("address_line", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "name", name="uq_properties_org_name"),
    )
    op.create_index(op.f("ix_properties_id"), "properties", ["id"], unique=False)
    op.create_index(op.f("ix_properties_organization_id"), "properties", ["organization_id"], unique=False)

    op.create_table(
        "admin_user_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_user_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=50), server_default="viewer", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["admin_user_id"], ["admin_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "admin_user_id",
            "organization_id",
            name="uq_admin_user_memberships_user_org",
        ),
    )
    op.create_index(op.f("ix_admin_user_memberships_id"), "admin_user_memberships", ["id"], unique=False)
    op.create_index(
        op.f("ix_admin_user_memberships_admin_user_id"),
        "admin_user_memberships",
        ["admin_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_user_memberships_organization_id"),
        "admin_user_memberships",
        ["organization_id"],
        unique=False,
    )

    op.create_table(
        "property_user_access",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_user_id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["admin_user_id"], ["admin_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "admin_user_id",
            "property_id",
            name="uq_property_user_access_user_property",
        ),
    )
    op.create_index(op.f("ix_property_user_access_id"), "property_user_access", ["id"], unique=False)
    op.create_index(
        op.f("ix_property_user_access_admin_user_id"),
        "property_user_access",
        ["admin_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_property_user_access_property_id"),
        "property_user_access",
        ["property_id"],
        unique=False,
    )

    op.add_column("tenants", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.add_column("tenants", sa.Column("property_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_tenants_organization_id"), "tenants", ["organization_id"], unique=False)
    op.create_index(op.f("ix_tenants_property_id"), "tenants", ["property_id"], unique=False)

    op.add_column("call_logs", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.add_column("call_logs", sa.Column("property_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_call_logs_organization_id"), "call_logs", ["organization_id"], unique=False)
    op.create_index(op.f("ix_call_logs_property_id"), "call_logs", ["property_id"], unique=False)

    op.add_column("csv_imports", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.add_column("csv_imports", sa.Column("property_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_csv_imports_organization_id"), "csv_imports", ["organization_id"], unique=False)
    op.create_index(op.f("ix_csv_imports_property_id"), "csv_imports", ["property_id"], unique=False)

    connection = op.get_bind()

    default_org_id = connection.execute(
        sa.text(
            """
            INSERT INTO organizations (name, slug, is_active, created_at, updated_at)
            VALUES (:name, :slug, true, now(), now())
            RETURNING id
            """
        ),
        {
            "name": "Default Organization",
            "slug": "default-organization",
        },
    ).scalar_one()

    default_property_id = connection.execute(
        sa.text(
            """
            INSERT INTO properties (
                organization_id,
                name,
                timezone,
                address_line,
                city,
                state,
                is_active,
                created_at,
                updated_at
            )
            VALUES (
                :organization_id,
                :name,
                :timezone,
                NULL,
                NULL,
                NULL,
                true,
                now(),
                now()
            )
            RETURNING id
            """
        ),
        {
            "organization_id": default_org_id,
            "name": "Default Property",
            "timezone": "America/New_York",
        },
    ).scalar_one()

    connection.execute(
        sa.text(
            """
            UPDATE tenants
            SET organization_id = :organization_id,
                property_id = :property_id
            WHERE organization_id IS NULL
               OR property_id IS NULL
            """
        ),
        {
            "organization_id": default_org_id,
            "property_id": default_property_id,
        },
    )

    connection.execute(
        sa.text(
            """
            UPDATE call_logs AS cl
            SET organization_id = t.organization_id,
                property_id = t.property_id
            FROM tenants AS t
            WHERE cl.tenant_id = t.id
              AND (cl.organization_id IS NULL OR cl.property_id IS NULL)
            """
        )
    )

    connection.execute(
        sa.text(
            """
            UPDATE csv_imports
            SET organization_id = :organization_id,
                property_id = :property_id
            WHERE organization_id IS NULL
               OR property_id IS NULL
            """
        ),
        {
            "organization_id": default_org_id,
            "property_id": default_property_id,
        },
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO admin_user_memberships (
                admin_user_id,
                organization_id,
                role,
                is_active,
                created_at
            )
            SELECT
                id,
                :organization_id,
                'org_admin',
                true,
                now()
            FROM admin_users
            ON CONFLICT (admin_user_id, organization_id) DO NOTHING
            """
        ),
        {
            "organization_id": default_org_id,
        },
    )

    op.alter_column("tenants", "organization_id", nullable=False)
    op.alter_column("tenants", "property_id", nullable=False)
    op.alter_column("call_logs", "organization_id", nullable=False)
    op.alter_column("call_logs", "property_id", nullable=False)
    op.alter_column("csv_imports", "organization_id", nullable=False)
    op.alter_column("csv_imports", "property_id", nullable=False)

    op.create_foreign_key(
        "fk_tenants_organization_id_organizations",
        "tenants",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_tenants_property_id_properties",
        "tenants",
        "properties",
        ["property_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_foreign_key(
        "fk_call_logs_organization_id_organizations",
        "call_logs",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_call_logs_property_id_properties",
        "call_logs",
        "properties",
        ["property_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_foreign_key(
        "fk_csv_imports_organization_id_organizations",
        "csv_imports",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_csv_imports_property_id_properties",
        "csv_imports",
        "properties",
        ["property_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_csv_imports_property_id_properties", "csv_imports", type_="foreignkey")
    op.drop_constraint("fk_csv_imports_organization_id_organizations", "csv_imports", type_="foreignkey")
    op.drop_constraint("fk_call_logs_property_id_properties", "call_logs", type_="foreignkey")
    op.drop_constraint("fk_call_logs_organization_id_organizations", "call_logs", type_="foreignkey")
    op.drop_constraint("fk_tenants_property_id_properties", "tenants", type_="foreignkey")
    op.drop_constraint("fk_tenants_organization_id_organizations", "tenants", type_="foreignkey")

    op.drop_index(op.f("ix_csv_imports_property_id"), table_name="csv_imports")
    op.drop_index(op.f("ix_csv_imports_organization_id"), table_name="csv_imports")
    op.drop_column("csv_imports", "property_id")
    op.drop_column("csv_imports", "organization_id")

    op.drop_index(op.f("ix_call_logs_property_id"), table_name="call_logs")
    op.drop_index(op.f("ix_call_logs_organization_id"), table_name="call_logs")
    op.drop_column("call_logs", "property_id")
    op.drop_column("call_logs", "organization_id")

    op.drop_index(op.f("ix_tenants_property_id"), table_name="tenants")
    op.drop_index(op.f("ix_tenants_organization_id"), table_name="tenants")
    op.drop_column("tenants", "property_id")
    op.drop_column("tenants", "organization_id")

    op.drop_index(op.f("ix_property_user_access_property_id"), table_name="property_user_access")
    op.drop_index(op.f("ix_property_user_access_admin_user_id"), table_name="property_user_access")
    op.drop_index(op.f("ix_property_user_access_id"), table_name="property_user_access")
    op.drop_table("property_user_access")

    op.drop_index(
        op.f("ix_admin_user_memberships_organization_id"),
        table_name="admin_user_memberships",
    )
    op.drop_index(
        op.f("ix_admin_user_memberships_admin_user_id"),
        table_name="admin_user_memberships",
    )
    op.drop_index(op.f("ix_admin_user_memberships_id"), table_name="admin_user_memberships")
    op.drop_table("admin_user_memberships")

    op.drop_index(op.f("ix_properties_organization_id"), table_name="properties")
    op.drop_index(op.f("ix_properties_id"), table_name="properties")
    op.drop_table("properties")

    op.drop_index(op.f("ix_organizations_slug"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_id"), table_name="organizations")
    op.drop_table("organizations")
