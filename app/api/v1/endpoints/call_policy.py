from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.call_policy import CallPolicyResponse, CallPolicyUpdateRequest
from app.services.access_service import get_property_in_scope, resolve_organization_scope
from app.services.call_policy_service import (
    get_effective_call_policy,
    upsert_call_policy,
)

router = APIRouter(prefix="/call-policy")


@router.get("", response_model=CallPolicyResponse, summary="Get effective call policy by scope")
def get_call_policy(
    organization_id: int | None = Query(default=None),
    property_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    try:
        effective_organization_id = resolve_organization_scope(
            db=db,
            user=current_user,
            organization_id=organization_id,
        )
        property_obj = get_property_in_scope(
            db=db,
            user=current_user,
            property_id=property_id,
            organization_id=None,
            require_manage=False,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    policy = get_effective_call_policy(
        db=db,
        organization_id=property_obj.organization_id,
        property_id=property_obj.id,
    )
    return CallPolicyResponse(**policy.as_dict())


@router.put("", response_model=CallPolicyResponse, summary="Upsert call policy by scope")
def put_call_policy(
    payload: CallPolicyUpdateRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    try:
        effective_organization_id = resolve_organization_scope(
            db=db,
            user=current_user,
            organization_id=payload.organization_id,
        )
        property_obj = get_property_in_scope(
            db=db,
            user=current_user,
            property_id=payload.property_id,
            organization_id=None,
            require_manage=True,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    policy_payload = payload.model_copy(update={"organization_id": property_obj.organization_id})
    policy = upsert_call_policy(db=db, payload=policy_payload)
    effective = get_effective_call_policy(
        db=db,
        organization_id=policy.organization_id,
        property_id=policy.property_id,
    )
    return CallPolicyResponse(**effective.as_dict())
