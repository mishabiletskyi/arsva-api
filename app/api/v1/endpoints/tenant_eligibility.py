from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.compliance import TenantEligibilityResponse
from app.services.compliance_service import evaluate_tenant_eligibility
from app.services.tenant_service import get_tenant_by_id, get_tenants

router = APIRouter(prefix="/tenant-eligibility")


@router.get("", response_model=list[TenantEligibilityResponse], summary="Get tenant eligibility list")
def list_tenant_eligibility(
    organization_id: int | None = Query(default=None),
    property_id: int | None = Query(default=None),
    only_callable: bool = Query(default=False),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    tenants = get_tenants(
        db=db,
        current_user=current_user,
        organization_id=organization_id,
        property_id=property_id,
        include_archived=include_archived,
    )
    evaluations = [TenantEligibilityResponse(**evaluate_tenant_eligibility(db, tenant)) for tenant in tenants]
    if only_callable:
        evaluations = [item for item in evaluations if item.can_call_now]
    return evaluations


@router.get("/{tenant_id}", response_model=TenantEligibilityResponse, summary="Get tenant eligibility by ID")
def get_tenant_eligibility(
    tenant_id: int,
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    tenant = get_tenant_by_id(
        db=db,
        tenant_id=tenant_id,
        current_user=current_user,
        include_archived=include_archived,
    )

    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    return TenantEligibilityResponse(**evaluate_tenant_eligibility(db, tenant))
