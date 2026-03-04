from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.call_log import CallLogCreate, CallLogResponse, CallLogUpdate
from app.services.call_log_service import (
    create_call_log,
    get_call_log_by_id,
    get_call_logs,
    update_call_log,
)

router = APIRouter(prefix="/call-logs")


@router.get("", response_model=list[CallLogResponse], summary="Get call logs list")
def list_call_logs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    organization_id: int | None = Query(default=None),
    property_id: int | None = Query(default=None),
    tenant_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    return get_call_logs(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        organization_id=organization_id,
        property_id=property_id,
        tenant_id=tenant_id,
    )


@router.get("/{call_log_id}", response_model=CallLogResponse, summary="Get call log by ID")
def get_call_log(
    call_log_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    call_log = get_call_log_by_id(
        db=db,
        call_log_id=call_log_id,
        current_user=current_user,
    )

    if call_log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call log not found",
        )

    return call_log


@router.post("", response_model=CallLogResponse, status_code=status.HTTP_201_CREATED, summary="Create call log")
def create_call_log_endpoint(
    payload: CallLogCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    try:
        return create_call_log(
            db=db,
            payload=payload,
            current_user=current_user,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.put("/{call_log_id}", response_model=CallLogResponse, summary="Update call log")
def update_call_log_endpoint(
    call_log_id: int,
    payload: CallLogUpdate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    call_log = get_call_log_by_id(
        db=db,
        call_log_id=call_log_id,
        current_user=current_user,
    )

    if call_log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call log not found",
        )

    try:
        return update_call_log(
            db=db,
            call_log=call_log,
            payload=payload,
            current_user=current_user,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
