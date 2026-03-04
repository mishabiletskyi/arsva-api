from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.auth import (
    LoginRequest,
    MembershipScopeResponse,
    PropertyAccessScopeResponse,
    TokenResponse,
    UserMeResponse,
)
from app.services.access_service import (
    get_active_memberships,
    get_active_property_accesses,
    is_platform_owner,
)
from app.services.auth_service import authenticate_admin, build_token_response

router = APIRouter(prefix="/auth")


@router.post("/login", response_model=TokenResponse, summary="Login admin user")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_admin(db, payload.email, payload.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return build_token_response(user)


@router.get("/me", response_model=UserMeResponse, summary="Get current admin user")
def me(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    memberships = get_active_memberships(db, current_user.id)
    property_accesses = get_active_property_accesses(db, current_user.id)

    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        is_platform_owner=is_platform_owner(db, current_user),
        memberships=[
            MembershipScopeResponse(
                organization_id=item.organization_id,
                role=item.role,
                is_active=item.is_active,
            )
            for item in memberships
        ],
        property_accesses=[
            PropertyAccessScopeResponse(property_id=item.property_id)
            for item in property_accesses
        ],
    )
