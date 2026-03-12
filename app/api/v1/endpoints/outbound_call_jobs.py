from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.outbound_call_job import OutboundCallJobCreate, OutboundCallJobResponse
from app.services.outbound_call_job_service import (
    create_outbound_call_job,
    get_outbound_call_job_by_id,
    get_outbound_call_jobs,
)

router = APIRouter(prefix="/outbound-call-jobs")


@router.get("", response_model=list[OutboundCallJobResponse], summary="Get outbound call jobs list")
def list_outbound_call_jobs(
    organization_id: int | None = Query(default=None),
    property_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    try:
        return get_outbound_call_jobs(
            db=db,
            current_user=current_user,
            organization_id=organization_id,
            property_id=property_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/{job_id}", response_model=OutboundCallJobResponse, summary="Get outbound call job by ID")
def get_outbound_call_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    job = get_outbound_call_job_by_id(db=db, job_id=job_id, current_user=current_user)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbound call job not found")

    return job


@router.post("", response_model=OutboundCallJobResponse, status_code=status.HTTP_201_CREATED, summary="Create outbound call job")
def create_outbound_call_job_endpoint(
    payload: OutboundCallJobCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    try:
        return create_outbound_call_job(db=db, payload=payload, current_user=current_user)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
