import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.models.organization import Organization
from app.models.property import Property
from app.schemas.auth import (
    AvailablePropertyResponse,
    CurrentOrganizationResponse,
    LoginRequest,
    ManagerRegisterRequest,
    MembershipScopeResponse,
    PropertyAccessScopeResponse,
    TokenResponse,
    UserMeResponse,
)
from app.services.access_service import (
    ROLE_ORG_ADMIN,
    ROLE_PROPERTY_MANAGER,
    ROLE_VIEWER,
    get_accessible_properties_for_organization,
    get_default_organization_id,
    get_active_memberships,
    get_active_property_accesses,
    is_platform_owner,
)
from app.services.auth_service import authenticate_admin, build_token_response, register_manager_user

router = APIRouter(prefix="/auth")
settings = get_settings()


def _resolve_role_ui(
    *,
    is_owner: bool,
    memberships: list,
) -> str:
    if is_owner:
        return "owner"

    roles = {item.role for item in memberships if item.is_active}
    if roles.intersection({ROLE_ORG_ADMIN, ROLE_PROPERTY_MANAGER}):
        return "manager"
    if ROLE_VIEWER in roles:
        return "viewer"

    return "manager" 


def _slugify_organization_name(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    if not normalized:
        raise ValueError("organization_name must contain letters or numbers")
    return normalized


def _ensure_organization_by_name(db: Session, organization_name: str) -> Organization:
    base_slug = _slugify_organization_name(organization_name)
    existing = (
        db.query(Organization)
        .filter(Organization.slug == base_slug, Organization.is_active.is_(True))
        .first()
    )
    if existing is not None:
        return existing

    slug = base_slug
    index = 2
    while db.query(Organization).filter(Organization.slug == slug).first() is not None:
        slug = f"{base_slug}-{index}"
        index += 1

    organization = Organization(
        name=organization_name.strip(),
        slug=slug,
        is_active=True,
    )
    db.add(organization)
    db.flush()

    default_property = Property(
        organization_id=organization.id,
        name="Default Property",
        timezone="America/New_York",
        is_active=True,
    )
    db.add(default_property)
    db.commit()
    db.refresh(organization)
    return organization


@router.post("/login", response_model=TokenResponse, summary="Login admin user")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_admin(db, payload.email, payload.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return build_token_response(user)


@router.post("/register-manager", response_model=TokenResponse, summary="Self-register manager user")
def register_manager(payload: ManagerRegisterRequest, db: Session = Depends(get_db)):
    if not settings.manager_signup_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager self-signup is disabled",
        )

    if not settings.manager_signup_code:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Manager self-signup is not configured",
        )

    if payload.signup_code != settings.manager_signup_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid signup code",
        )

    organization = None
    if payload.organization_id is not None:
        organization = (
            db.query(Organization)
            .filter(Organization.id == payload.organization_id, Organization.is_active.is_(True))
            .first()
        )
        if organization is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )
    elif payload.organization_slug:
        organization = (
            db.query(Organization)
            .filter(Organization.slug == payload.organization_slug.strip().lower(), Organization.is_active.is_(True))
            .first()
        )
        if organization is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )
    elif payload.organization_name:
        try:
            organization = _ensure_organization_by_name(db, payload.organization_name)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            )

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide organization_id, organization_slug, or organization_name",
        )

    try:
        user = register_manager_user(
            db=db,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            organization_id=organization.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return build_token_response(user)


@router.get("/me", response_model=UserMeResponse, summary="Get current admin user")
def me(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    memberships = get_active_memberships(db, current_user.id)
    property_accesses = get_active_property_accesses(db, current_user.id)
    owner = is_platform_owner(db, current_user)
    role_ui = _resolve_role_ui(is_owner=owner, memberships=list(memberships))

    current_organization = None
    available_properties: list[AvailablePropertyResponse] = []
    current_property_id: int | None = None

    default_organization_id = get_default_organization_id(db=db, user=current_user)
    if default_organization_id is not None:
        organization = (
            db.query(Organization)
            .filter(Organization.id == default_organization_id)
            .first()
        )
        if organization is not None:
            current_organization = CurrentOrganizationResponse(
                id=organization.id,
                name=organization.name,
            )
            available_property_rows = get_accessible_properties_for_organization(
                db=db,
                user=current_user,
                organization_id=organization.id,
            )
            available_properties = [
                AvailablePropertyResponse(
                    id=item.id,
                    organization_id=item.organization_id,
                    name=item.name,
                    timezone=item.timezone,
                    address_line=item.address_line,
                    city=item.city,
                    state=item.state,
                    is_active=item.is_active,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
                for item in available_property_rows
            ]
            if available_properties:
                current_property_id = available_properties[0].id

    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        is_platform_owner=owner,
        role_ui=role_ui,
        current_organization=current_organization,
        available_properties=available_properties,
        current_property_id=current_property_id,
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
