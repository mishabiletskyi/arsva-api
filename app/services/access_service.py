from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.admin_user import AdminUser
from app.models.admin_user_membership import AdminUserMembership
from app.models.property_user_access import PropertyUserAccess

ROLE_PLATFORM_OWNER = "platform_owner"
ROLE_ORG_ADMIN = "org_admin"
ROLE_PROPERTY_MANAGER = "property_manager"
ROLE_VIEWER = "viewer"

ALL_ROLES = {
    ROLE_PLATFORM_OWNER,
    ROLE_ORG_ADMIN,
    ROLE_PROPERTY_MANAGER,
    ROLE_VIEWER,
}

PROPERTY_SCOPED_ROLES = {
    ROLE_PROPERTY_MANAGER,
    ROLE_VIEWER,
}


def get_active_memberships(db: Session, admin_user_id: int) -> Sequence[AdminUserMembership]:
    return (
        db.query(AdminUserMembership)
        .filter(
            AdminUserMembership.admin_user_id == admin_user_id,
            AdminUserMembership.is_active.is_(True),
        )
        .all()
    )


def get_active_property_accesses(
    db: Session,
    admin_user_id: int,
) -> Sequence[PropertyUserAccess]:
    return (
        db.query(PropertyUserAccess)
        .filter(PropertyUserAccess.admin_user_id == admin_user_id)
        .all()
    )


def is_platform_owner(db: Session, user: AdminUser) -> bool:
    if user.is_superuser:
        return True

    memberships = get_active_memberships(db, user.id)
    return any(item.role == ROLE_PLATFORM_OWNER for item in memberships)


def get_membership_for_organization(
    db: Session,
    user: AdminUser,
    organization_id: int,
) -> AdminUserMembership | None:
    return (
        db.query(AdminUserMembership)
        .filter(
            AdminUserMembership.admin_user_id == user.id,
            AdminUserMembership.organization_id == organization_id,
            AdminUserMembership.is_active.is_(True),
        )
        .first()
    )


def get_accessible_organization_ids(db: Session, user: AdminUser) -> list[int]:
    if is_platform_owner(db, user):
        return []

    memberships = get_active_memberships(db, user.id)
    return sorted({item.organization_id for item in memberships})


def get_accessible_property_ids(
    db: Session,
    user: AdminUser,
    organization_id: int | None = None,
) -> list[int]:
    if is_platform_owner(db, user):
        return []

    memberships = get_active_memberships(db, user.id)

    if organization_id is not None:
        memberships = [
            item for item in memberships if item.organization_id == organization_id
        ]

    if any(item.role == ROLE_ORG_ADMIN for item in memberships):
        return []

    access_rows = get_active_property_accesses(db, user.id)
    property_ids = {item.property_id for item in access_rows}

    return sorted(property_ids)


def can_access_organization(
    db: Session,
    user: AdminUser,
    organization_id: int,
) -> bool:
    if is_platform_owner(db, user):
        return True

    membership = get_membership_for_organization(db, user, organization_id)
    return membership is not None


def can_manage_organization(
    db: Session,
    user: AdminUser,
    organization_id: int,
) -> bool:
    if is_platform_owner(db, user):
        return True

    membership = get_membership_for_organization(db, user, organization_id)
    if membership is None:
        return False

    return membership.role == ROLE_ORG_ADMIN


def can_access_property(
    db: Session,
    user: AdminUser,
    organization_id: int,
    property_id: int,
) -> bool:
    if is_platform_owner(db, user):
        return True

    membership = get_membership_for_organization(db, user, organization_id)
    if membership is None:
        return False

    if membership.role == ROLE_ORG_ADMIN:
        return True

    if membership.role not in PROPERTY_SCOPED_ROLES:
        return False

    return (
        db.query(PropertyUserAccess)
        .filter(
            PropertyUserAccess.admin_user_id == user.id,
            PropertyUserAccess.property_id == property_id,
        )
        .first()
        is not None
    )


def can_manage_property(
    db: Session,
    user: AdminUser,
    organization_id: int,
    property_id: int,
) -> bool:
    if is_platform_owner(db, user):
        return True

    membership = get_membership_for_organization(db, user, organization_id)
    if membership is None:
        return False

    if membership.role == ROLE_ORG_ADMIN:
        return True

    if membership.role != ROLE_PROPERTY_MANAGER:
        return False

    return (
        db.query(PropertyUserAccess)
        .filter(
            PropertyUserAccess.admin_user_id == user.id,
            PropertyUserAccess.property_id == property_id,
        )
        .first()
        is not None
    )


def can_write_in_organization(
    db: Session,
    user: AdminUser,
    organization_id: int,
) -> bool:
    if is_platform_owner(db, user):
        return True

    membership = get_membership_for_organization(db, user, organization_id)
    if membership is None:
        return False

    return membership.role in {ROLE_ORG_ADMIN, ROLE_PROPERTY_MANAGER}
