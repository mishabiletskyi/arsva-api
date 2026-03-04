from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.admin_user import (
    AdminUserCreate,
    AdminUserMembershipAssignment,
    AdminUserMembershipResponse,
    AdminUserResponse,
    AdminUserUpdate,
    PropertyAccessAssignment,
    PropertyUserAccessResponse,
)
from app.services.admin_user_service import (
    create_admin_user_record,
    get_admin_user_by_id,
    get_admin_users,
    replace_admin_user_memberships,
    replace_admin_user_property_accesses,
    update_admin_user_record,
)

router = APIRouter(prefix="/admin-users")


@router.get("", response_model=list[AdminUserResponse], summary="Get admin users list")
def list_admin_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    try:
        return get_admin_users(
            db=db,
            current_user=current_user,
            skip=skip,
            limit=limit,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )


@router.get("/{admin_user_id}", response_model=AdminUserResponse, summary="Get admin user by ID")
def get_admin_user(
    admin_user_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    try:
        admin_user = get_admin_user_by_id(
            db=db,
            admin_user_id=admin_user_id,
            current_user=current_user,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if admin_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found",
        )

    return admin_user


@router.post("", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED, summary="Create admin user")
def create_admin_user_endpoint(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    try:
        return create_admin_user_record(
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


@router.put("/{admin_user_id}", response_model=AdminUserResponse, summary="Update admin user")
def update_admin_user_endpoint(
    admin_user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    try:
        admin_user = get_admin_user_by_id(
            db=db,
            admin_user_id=admin_user_id,
            current_user=current_user,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if admin_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found",
        )

    try:
        return update_admin_user_record(
            db=db,
            admin_user=admin_user,
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


@router.get(
    "/{admin_user_id}/memberships",
    response_model=list[AdminUserMembershipResponse],
    summary="Get admin user memberships",
)
def list_admin_user_memberships(
    admin_user_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    try:
        admin_user = get_admin_user_by_id(
            db=db,
            admin_user_id=admin_user_id,
            current_user=current_user,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if admin_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found",
        )

    return admin_user.memberships


@router.put(
    "/{admin_user_id}/memberships",
    response_model=list[AdminUserMembershipResponse],
    summary="Replace admin user memberships",
)
def replace_admin_user_memberships_endpoint(
    admin_user_id: int,
    payload: list[AdminUserMembershipAssignment],
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    try:
        admin_user = get_admin_user_by_id(
            db=db,
            admin_user_id=admin_user_id,
            current_user=current_user,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if admin_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found",
        )

    try:
        return replace_admin_user_memberships(
            db=db,
            admin_user=admin_user,
            memberships=payload,
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


@router.get(
    "/{admin_user_id}/property-accesses",
    response_model=list[PropertyUserAccessResponse],
    summary="Get admin user property accesses",
)
def list_admin_user_property_accesses(
    admin_user_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    try:
        admin_user = get_admin_user_by_id(
            db=db,
            admin_user_id=admin_user_id,
            current_user=current_user,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if admin_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found",
        )

    return admin_user.property_accesses


@router.put(
    "/{admin_user_id}/property-accesses",
    response_model=list[PropertyUserAccessResponse],
    summary="Replace admin user property accesses",
)
def replace_admin_user_property_accesses_endpoint(
    admin_user_id: int,
    payload: list[PropertyAccessAssignment],
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    try:
        admin_user = get_admin_user_by_id(
            db=db,
            admin_user_id=admin_user_id,
            current_user=current_user,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if admin_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found",
        )

    try:
        return replace_admin_user_property_accesses(
            db=db,
            admin_user=admin_user,
            property_accesses=payload,
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
