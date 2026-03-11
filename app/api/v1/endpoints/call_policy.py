from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.call_policy import CallPolicyResponse, CallPolicyUpdateRequest
from app.services.access_service import can_access_property, can_manage_property
from app.services.call_policy_service import (
    get_effective_call_policy,
    upsert_call_policy,
)
from app.services.property_service import get_property_by_id

router = APIRouter(prefix="/call-policy")


@router.get("", response_model=CallPolicyResponse, summary="Get effective call policy by scope")
def get_call_policy(
    organization_id: int = Query(...),
    property_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    property_obj = get_property_by_id(db=db, property_id=property_id)
    if property_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    if property_obj.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="organization_id does not match the selected property",
        )

    if not can_access_property(
        db=db,
        user=current_user,
        organization_id=organization_id,
        property_id=property_id,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this scope")

    policy = get_effective_call_policy(
        db=db,
        organization_id=organization_id,
        property_id=property_id,
    )
    return CallPolicyResponse(**policy.as_dict())


@router.put("", response_model=CallPolicyResponse, summary="Upsert call policy by scope")
def put_call_policy(
    payload: CallPolicyUpdateRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    property_obj = get_property_by_id(db=db, property_id=payload.property_id)
    if property_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    if property_obj.organization_id != payload.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="organization_id does not match the selected property",
        )

    if not can_manage_property(
        db=db,
        user=current_user,
        organization_id=payload.organization_id,
        property_id=payload.property_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have write access to this scope",
        )

    policy = upsert_call_policy(db=db, payload=payload)
    effective = get_effective_call_policy(
        db=db,
        organization_id=policy.organization_id,
        property_id=policy.property_id,
    )
    return CallPolicyResponse(**effective.as_dict())
