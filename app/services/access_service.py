from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.admin_user import AdminUser
from app.models.admin_user_membership import AdminUserMembership
from app.models.organization import Organization
from app.models.property import Property
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


def get_default_organization_id(
    db: Session,
    user: AdminUser,
) -> int | None:
    if is_platform_owner(db, user):
        memberships = get_active_memberships(db, user.id)
        if memberships:
            return sorted({item.organization_id for item in memberships})[0]

        first_org = (
            db.query(Organization.id)
            .order_by(Organization.id.asc())
            .first()
        )
        return first_org[0] if first_org is not None else None

    organization_ids = get_accessible_organization_ids(db, user)
    if not organization_ids:
        return None
    return organization_ids[0]


def resolve_organization_scope(
    db: Session,
    user: AdminUser,
    organization_id: int | None = None,
) -> int | None:
    if organization_id is not None:
        if is_platform_owner(db, user):
            return organization_id

        if can_access_organization(db=db, user=user, organization_id=organization_id):
            return organization_id

        raise PermissionError("You do not have access to this organization")

    return get_default_organization_id(db=db, user=user)


def get_accessible_properties_for_organization(
    db: Session,
    user: AdminUser,
    organization_id: int,
) -> list[Property]:
    query = (
        db.query(Property)
        .filter(Property.organization_id == organization_id)
        .order_by(Property.name.asc())
    )

    if is_platform_owner(db, user):
        return query.all()

    membership = get_membership_for_organization(db=db, user=user, organization_id=organization_id)
    if membership is None:
        return []

    if membership.role == ROLE_ORG_ADMIN:
        return query.all()

    property_ids = get_accessible_property_ids(
        db=db,
        user=user,
        organization_id=organization_id,
    )
    if not property_ids:
        return []

    return query.filter(Property.id.in_(property_ids)).all()


def get_property_in_scope(
    db: Session,
    user: AdminUser,
    property_id: int,
    organization_id: int | None = None,
    require_manage: bool = False,
) -> Property:
    property_obj = (
        db.query(Property)
        .filter(Property.id == property_id)
        .first()
    )
    if property_obj is None:
        raise ValueError("Property not found")

    effective_organization_id = organization_id if organization_id is not None else property_obj.organization_id

    if property_obj.organization_id != effective_organization_id:
        raise ValueError("organization_id does not match the selected property")

    has_access = can_manage_property(
        db=db,
        user=user,
        organization_id=effective_organization_id,
        property_id=property_obj.id,
    ) if require_manage else can_access_property(
        db=db,
        user=user,
        organization_id=effective_organization_id,
        property_id=property_obj.id,
    )

    if not has_access:
        raise PermissionError("You do not have access to this property")

    return property_obj
