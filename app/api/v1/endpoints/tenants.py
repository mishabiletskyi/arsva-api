from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate
from app.services.tenant_service import (
    create_tenant,
    get_tenant_by_id,
    get_tenants,
    update_tenant,
)

router = APIRouter(prefix="/tenants")


@router.get("", response_model=list[TenantResponse], summary="Get tenants list")
def list_tenants(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    return get_tenants(db=db, skip=skip, limit=limit)


@router.get("/{tenant_id}", response_model=TenantResponse, summary="Get tenant by ID")
def get_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    tenant = get_tenant_by_id(db=db, tenant_id=tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    return tenant


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED, summary="Create tenant")
def create_tenant_endpoint(
    payload: TenantCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    try:
        return create_tenant(db=db, payload=payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.put("/{tenant_id}", response_model=TenantResponse, summary="Update tenant")
def update_tenant_endpoint(
    tenant_id: int,
    payload: TenantUpdate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    tenant = get_tenant_by_id(db=db, tenant_id=tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    try:
        return update_tenant(db=db, tenant=tenant, payload=payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )