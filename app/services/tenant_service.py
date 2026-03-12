from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.admin_user import AdminUser
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate
from app.services.access_service import (
    can_access_property,
    can_manage_property,
    get_property_in_scope,
    is_platform_owner,
    resolve_organization_scope,
)
from app.services.property_service import get_property_by_id


def _can_read_tenant(db: Session, current_user: AdminUser, tenant: Tenant) -> bool:
    if is_platform_owner(db, current_user):
        return True

    return can_access_property(
        db=db,
        user=current_user,
        organization_id=tenant.organization_id,
        property_id=tenant.property_id,
    )


def _can_write_tenant(db: Session, current_user: AdminUser, tenant: Tenant) -> bool:
    if is_platform_owner(db, current_user):
        return True

    return can_manage_property(
        db=db,
        user=current_user,
        organization_id=tenant.organization_id,
        property_id=tenant.property_id,
    )


def get_tenants(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    current_user: AdminUser | None = None,
    organization_id: int | None = None,
    property_id: int | None = None,
    include_archived: bool = False,
) -> list[Tenant]:
    effective_organization_id = organization_id
    if current_user is not None:
        effective_organization_id = resolve_organization_scope(
            db=db,
            user=current_user,
            organization_id=organization_id,
        )

        if property_id is not None:
            scoped_property = get_property_in_scope(
                db=db,
                user=current_user,
                property_id=property_id,
                organization_id=None,
                require_manage=False,
            )
            effective_organization_id = scoped_property.organization_id

    query = db.query(Tenant)

    if effective_organization_id is not None:
        query = query.filter(Tenant.organization_id == effective_organization_id)

    if property_id is not None:
        query = query.filter(Tenant.property_id == property_id)

    if not include_archived:
        query = query.filter(Tenant.is_archived.is_(False))

    tenants = query.order_by(Tenant.created_at.desc()).all()

    if current_user is None:
        return tenants[skip : skip + limit]

    filtered_tenants = [
        tenant
        for tenant in tenants
        if _can_read_tenant(db=db, current_user=current_user, tenant=tenant)
    ]

    return filtered_tenants[skip : skip + limit]


def get_tenant_by_id(
    db: Session,
    tenant_id: int,
    current_user: AdminUser | None = None,
    include_archived: bool = False,
) -> Tenant | None:
    query = db.query(Tenant).filter(Tenant.id == tenant_id)
    if not include_archived:
        query = query.filter(Tenant.is_archived.is_(False))

    tenant = query.first()

    if tenant is None:
        return None

    if current_user is None:
        return tenant

    if not _can_read_tenant(db=db, current_user=current_user, tenant=tenant):
        return None

    return tenant


def get_tenant_by_external_id(
    db: Session,
    external_id: str,
    current_user: AdminUser | None = None,
    include_archived: bool = False,
) -> Tenant | None:
    query = db.query(Tenant).filter(Tenant.external_id == external_id)
    if not include_archived:
        query = query.filter(Tenant.is_archived.is_(False))

    tenant = query.first()

    if tenant is None:
        return None

    if current_user is None:
        return tenant

    if not _can_read_tenant(db=db, current_user=current_user, tenant=tenant):
        return None

    return tenant


def create_tenant(
    db: Session,
    payload: TenantCreate,
    current_user: AdminUser | None = None,
) -> Tenant:
    if payload.external_id:
        existing_tenant = (
            db.query(Tenant)
            .filter(Tenant.external_id == payload.external_id)
            .first()
        )
        if existing_tenant is not None:
            raise ValueError("Tenant with this external_id already exists")

    property_obj = get_property_by_id(db=db, property_id=payload.property_id)
    if property_obj is None:
        raise ValueError("Property not found")

    if current_user is not None:
        property_obj = get_property_in_scope(
            db=db,
            user=current_user,
            property_id=payload.property_id,
            organization_id=None,
            require_manage=True,
        )

    tenant_data = payload.model_dump()
    tenant_data["organization_id"] = property_obj.organization_id
    tenant = Tenant(**tenant_data)

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant


def update_tenant(
    db: Session,
    tenant: Tenant,
    payload: TenantUpdate,
    current_user: AdminUser | None = None,
) -> Tenant:
    if current_user is not None and not _can_write_tenant(
        db=db,
        current_user=current_user,
        tenant=tenant,
    ):
        raise PermissionError("You do not have access to update this tenant")

    update_data = payload.model_dump(exclude_unset=True)
    update_data.pop("organization_id", None)

    new_external_id = update_data.get("external_id")
    if new_external_id:
        existing_tenant = (
            db.query(Tenant)
            .filter(Tenant.external_id == new_external_id)
            .first()
        )
        if existing_tenant is not None and existing_tenant.id != tenant.id:
            raise ValueError("Tenant with this external_id already exists")

    if "property_id" in update_data:
        property_obj = get_property_by_id(db=db, property_id=update_data["property_id"])
        if property_obj is None:
            raise ValueError("Property not found")

        if current_user is not None:
            property_obj = get_property_in_scope(
                db=db,
                user=current_user,
                property_id=property_obj.id,
                require_manage=True,
            )

        update_data["organization_id"] = property_obj.organization_id

    for field, value in update_data.items():
        setattr(tenant, field, value)

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant


def archive_tenant(
    db: Session,
    tenant: Tenant,
    current_user: AdminUser,
) -> Tenant:
    if not _can_write_tenant(db=db, current_user=current_user, tenant=tenant):
        raise PermissionError("You do not have access to archive this tenant")

    if tenant.is_archived:
        return tenant

    tenant.is_archived = True
    tenant.archived_at = datetime.now(timezone.utc)

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant


def restore_tenant(
    db: Session,
    tenant: Tenant,
    current_user: AdminUser,
) -> Tenant:
    if not _can_write_tenant(db=db, current_user=current_user, tenant=tenant):
        raise PermissionError("You do not have access to restore this tenant")

    if not tenant.is_archived:
        return tenant

    tenant.is_archived = False
    tenant.archived_at = None

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant


def suppress_tenant(
    db: Session,
    tenant: Tenant,
    current_user: AdminUser,
) -> Tenant:
    if not _can_write_tenant(db=db, current_user=current_user, tenant=tenant):
        raise PermissionError("You do not have access to suppress this tenant")

    if tenant.is_suppressed:
        return tenant

    tenant.is_suppressed = True
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant


def unsuppress_tenant(
    db: Session,
    tenant: Tenant,
    current_user: AdminUser,
) -> Tenant:
    if not _can_write_tenant(db=db, current_user=current_user, tenant=tenant):
        raise PermissionError("You do not have access to unsuppress this tenant")

    if not tenant.is_suppressed:
        return tenant

    tenant.is_suppressed = False
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant
