from sqlalchemy.orm import Session, selectinload

from app.core.security import get_password_hash
from app.models.admin_user import AdminUser
from app.models.admin_user_membership import AdminUserMembership
from app.models.organization import Organization
from app.models.property import Property
from app.models.property_user_access import PropertyUserAccess
from app.schemas.admin_user import (
    AdminUserCreate,
    AdminUserMembershipAssignment,
    AdminUserUpdate,
    PropertyAccessAssignment,
)
from app.services.access_service import (
    ROLE_ORG_ADMIN,
    ROLE_PROPERTY_MANAGER,
    ROLE_VIEWER,
    is_platform_owner,
)

MANAGED_MEMBERSHIP_ROLES = {
    ROLE_ORG_ADMIN,
    ROLE_PROPERTY_MANAGER,
    ROLE_VIEWER,
}


def _base_admin_user_query(db: Session):
    return db.query(AdminUser).options(
        selectinload(AdminUser.memberships),
        selectinload(AdminUser.property_accesses),
    )


def _require_platform_owner(db: Session, current_user: AdminUser) -> None:
    if not is_platform_owner(db, current_user):
        raise PermissionError("Only platform owners can manage admin users")


def get_admin_users(
    db: Session,
    current_user: AdminUser,
    skip: int = 0,
    limit: int = 50,
) -> list[AdminUser]:
    _require_platform_owner(db, current_user)

    return (
        _base_admin_user_query(db)
        .order_by(AdminUser.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_admin_user_by_id(
    db: Session,
    admin_user_id: int,
    current_user: AdminUser,
) -> AdminUser | None:
    _require_platform_owner(db, current_user)

    return (
        _base_admin_user_query(db)
        .filter(AdminUser.id == admin_user_id)
        .first()
    )


def create_admin_user_record(
    db: Session,
    payload: AdminUserCreate,
    current_user: AdminUser,
) -> AdminUser:
    _require_platform_owner(db, current_user)

    normalized_email = payload.email.strip().lower()
    existing_user = (
        db.query(AdminUser)
        .filter(AdminUser.email == normalized_email)
        .first()
    )
    if existing_user is not None:
        raise ValueError("Admin user with this email already exists")

    admin_user = AdminUser(
        email=normalized_email,
        full_name=payload.full_name.strip() if payload.full_name else None,
        hashed_password=get_password_hash(payload.password),
        is_active=payload.is_active,
        is_superuser=payload.is_superuser,
    )

    db.add(admin_user)
    db.commit()

    return get_admin_user_by_id(db, admin_user.id, current_user)


def update_admin_user_record(
    db: Session,
    admin_user: AdminUser,
    payload: AdminUserUpdate,
    current_user: AdminUser,
) -> AdminUser:
    _require_platform_owner(db, current_user)

    update_data = payload.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] is not None:
        normalized_email = update_data["email"].strip().lower()
        existing_user = (
            db.query(AdminUser)
            .filter(
                AdminUser.email == normalized_email,
                AdminUser.id != admin_user.id,
            )
            .first()
        )
        if existing_user is not None:
            raise ValueError("Admin user with this email already exists")

        update_data["email"] = normalized_email

    if "full_name" in update_data and update_data["full_name"] is not None:
        update_data["full_name"] = update_data["full_name"].strip()

    password = update_data.pop("password", None)
    if password:
        admin_user.hashed_password = get_password_hash(password)

    for field, value in update_data.items():
        setattr(admin_user, field, value)

    db.add(admin_user)
    db.commit()

    return get_admin_user_by_id(db, admin_user.id, current_user)


def replace_admin_user_memberships(
    db: Session,
    admin_user: AdminUser,
    memberships: list[AdminUserMembershipAssignment],
    current_user: AdminUser,
) -> list[AdminUserMembership]:
    _require_platform_owner(db, current_user)

    organization_ids = {item.organization_id for item in memberships}
    if organization_ids:
        existing_org_ids = {
            org_id
            for (org_id,) in db.query(Organization.id)
            .filter(Organization.id.in_(organization_ids))
            .all()
        }
        missing_org_ids = sorted(organization_ids - existing_org_ids)
        if missing_org_ids:
            raise ValueError(f"Organizations not found: {missing_org_ids}")

    seen_org_ids: set[int] = set()
    new_rows: list[AdminUserMembership] = []

    for item in memberships:
        if item.organization_id in seen_org_ids:
            raise ValueError("Duplicate organization_id in memberships payload")

        if item.role not in MANAGED_MEMBERSHIP_ROLES:
            raise ValueError(f"Unsupported role: {item.role}")

        seen_org_ids.add(item.organization_id)
        new_rows.append(
            AdminUserMembership(
                admin_user_id=admin_user.id,
                organization_id=item.organization_id,
                role=item.role,
                is_active=item.is_active,
            )
        )

    (
        db.query(AdminUserMembership)
        .filter(AdminUserMembership.admin_user_id == admin_user.id)
        .delete(synchronize_session=False)
    )

    for row in new_rows:
        db.add(row)

    db.commit()

    return (
        db.query(AdminUserMembership)
        .filter(AdminUserMembership.admin_user_id == admin_user.id)
        .order_by(AdminUserMembership.created_at.asc())
        .all()
    )


def replace_admin_user_property_accesses(
    db: Session,
    admin_user: AdminUser,
    property_accesses: list[PropertyAccessAssignment],
    current_user: AdminUser,
) -> list[PropertyUserAccess]:
    _require_platform_owner(db, current_user)

    property_ids = {item.property_id for item in property_accesses}
    membership_by_org = {
        row.organization_id: row
        for row in db.query(AdminUserMembership)
        .filter(
            AdminUserMembership.admin_user_id == admin_user.id,
            AdminUserMembership.is_active.is_(True),
        )
        .all()
    }

    properties = (
        db.query(Property)
        .filter(Property.id.in_(property_ids))
        .all()
        if property_ids
        else []
    )
    properties_by_id = {item.id: item for item in properties}

    missing_property_ids = sorted(property_ids - set(properties_by_id))
    if missing_property_ids:
        raise ValueError(f"Properties not found: {missing_property_ids}")

    seen_property_ids: set[int] = set()
    new_rows: list[PropertyUserAccess] = []

    for item in property_accesses:
        if item.property_id in seen_property_ids:
            raise ValueError("Duplicate property_id in property_accesses payload")

        property_obj = properties_by_id[item.property_id]
        membership = membership_by_org.get(property_obj.organization_id)
        if membership is None:
            raise ValueError(
                f"User must have an active organization membership before property access can be granted for property {item.property_id}"
            )

        if membership.role == ROLE_ORG_ADMIN:
            raise ValueError(
                f"Organization admins do not need explicit property access rows for property {item.property_id}"
            )

        seen_property_ids.add(item.property_id)
        new_rows.append(
            PropertyUserAccess(
                admin_user_id=admin_user.id,
                property_id=item.property_id,
            )
        )

    (
        db.query(PropertyUserAccess)
        .filter(PropertyUserAccess.admin_user_id == admin_user.id)
        .delete(synchronize_session=False)
    )

    for row in new_rows:
        db.add(row)

    db.commit()

    return (
        db.query(PropertyUserAccess)
        .filter(PropertyUserAccess.admin_user_id == admin_user.id)
        .order_by(PropertyUserAccess.created_at.asc())
        .all()
    )
