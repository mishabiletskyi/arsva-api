from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate


def get_tenants(db: Session, skip: int = 0, limit: int = 50) -> list[Tenant]:
    return (
        db.query(Tenant)
        .order_by(Tenant.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_tenant_by_id(db: Session, tenant_id: int) -> Tenant | None:
    return (
        db.query(Tenant)
        .filter(Tenant.id == tenant_id)
        .first()
    )


def get_tenant_by_external_id(db: Session, external_id: str) -> Tenant | None:
    return (
        db.query(Tenant)
        .filter(Tenant.external_id == external_id)
        .first()
    )


def create_tenant(db: Session, payload: TenantCreate) -> Tenant:
    if payload.external_id:
        existing_tenant = get_tenant_by_external_id(db, payload.external_id)
        if existing_tenant is not None:
            raise ValueError("Tenant with this external_id already exists")

    tenant = Tenant(**payload.model_dump())

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant


def update_tenant(db: Session, tenant: Tenant, payload: TenantUpdate) -> Tenant:
    update_data = payload.model_dump(exclude_unset=True)

    new_external_id = update_data.get("external_id")
    if new_external_id:
        existing_tenant = get_tenant_by_external_id(db, new_external_id)
        if existing_tenant is not None and existing_tenant.id != tenant.id:
            raise ValueError("Tenant with this external_id already exists")

    for field, value in update_data.items():
        setattr(tenant, field, value)

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant