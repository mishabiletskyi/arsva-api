from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.property import PropertyCreate, PropertyResponse, PropertyUpdate
from app.services.property_service import (
    create_property,
    get_properties,
    get_property_for_user,
    update_property,
)

router = APIRouter(prefix="/properties")


@router.get("", response_model=list[PropertyResponse], summary="Get properties list")
def list_properties(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    organization_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    return get_properties(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        organization_id=organization_id,
    )


@router.get("/{property_id}", response_model=PropertyResponse, summary="Get property by ID")
def get_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    property_obj = get_property_for_user(
        db=db,
        user=current_user,
        property_id=property_id,
    )

    if property_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    return property_obj


@router.post("", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED, summary="Create property")
def create_property_endpoint(
    payload: PropertyCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    try:
        return create_property(
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


@router.put("/{property_id}", response_model=PropertyResponse, summary="Update property")
def update_property_endpoint(
    property_id: int,
    payload: PropertyUpdate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    property_obj = get_property_for_user(
        db=db,
        user=current_user,
        property_id=property_id,
    )

    if property_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    try:
        return update_property(
            db=db,
            property_obj=property_obj,
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
