from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.services.organization_service import (
    create_organization,
    get_organization_by_id,
    get_organizations,
    update_organization,
)

router = APIRouter(prefix="/organizations")


@router.get("", response_model=list[OrganizationResponse], summary="Get organizations list")
def list_organizations(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    return get_organizations(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


@router.get("/{organization_id}", response_model=OrganizationResponse, summary="Get organization by ID")
def get_organization(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    organization = get_organization_by_id(
        db=db,
        organization_id=organization_id,
        current_user=current_user,
    )

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return organization


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED, summary="Create organization")
def create_organization_endpoint(
    payload: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    try:
        return create_organization(
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


@router.put("/{organization_id}", response_model=OrganizationResponse, summary="Update organization")
def update_organization_endpoint(
    organization_id: int,
    payload: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    organization = get_organization_by_id(
        db=db,
        organization_id=organization_id,
        current_user=current_user,
    )

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    try:
        return update_organization(
            db=db,
            organization=organization,
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
