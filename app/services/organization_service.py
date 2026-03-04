from sqlalchemy.orm import Session

from app.models.admin_user import AdminUser
from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate, OrganizationUpdate
from app.services.access_service import can_access_organization, is_platform_owner


def get_organizations(
    db: Session,
    current_user: AdminUser,
    skip: int = 0,
    limit: int = 50,
) -> list[Organization]:
    query = db.query(Organization).order_by(Organization.name.asc())

    if is_platform_owner(db, current_user):
        return query.offset(skip).limit(limit).all()

    organizations = query.all()
    scoped_organizations = [
        organization
        for organization in organizations
        if can_access_organization(
            db=db,
            user=current_user,
            organization_id=organization.id,
        )
    ]

    return scoped_organizations[skip : skip + limit]


def get_organization_by_id(
    db: Session,
    organization_id: int,
    current_user: AdminUser,
) -> Organization | None:
    organization = (
        db.query(Organization)
        .filter(Organization.id == organization_id)
        .first()
    )

    if organization is None:
        return None

    if is_platform_owner(db, current_user):
        return organization

    if not can_access_organization(
        db=db,
        user=current_user,
        organization_id=organization.id,
    ):
        return None

    return organization


def get_organization_by_slug(db: Session, slug: str) -> Organization | None:
    normalized_slug = slug.strip().lower()

    return (
        db.query(Organization)
        .filter(Organization.slug == normalized_slug)
        .first()
    )


def create_organization(
    db: Session,
    payload: OrganizationCreate,
    current_user: AdminUser,
) -> Organization:
    if not is_platform_owner(db, current_user):
        raise PermissionError("Only platform owners can create organizations")

    normalized_slug = payload.slug.strip().lower()

    existing_organization = get_organization_by_slug(db, normalized_slug)
    if existing_organization is not None:
        raise ValueError("Organization with this slug already exists")

    organization = Organization(
        name=payload.name.strip(),
        slug=normalized_slug,
        is_active=payload.is_active,
    )

    db.add(organization)
    db.commit()
    db.refresh(organization)

    return organization


def update_organization(
    db: Session,
    organization: Organization,
    payload: OrganizationUpdate,
    current_user: AdminUser,
) -> Organization:
    if not is_platform_owner(db, current_user):
        raise PermissionError("Only platform owners can update organizations")

    update_data = payload.model_dump(exclude_unset=True)

    if "slug" in update_data and update_data["slug"] is not None:
        normalized_slug = update_data["slug"].strip().lower()

        existing_organization = get_organization_by_slug(db, normalized_slug)
        if existing_organization is not None and existing_organization.id != organization.id:
            raise ValueError("Organization with this slug already exists")

        update_data["slug"] = normalized_slug

    if "name" in update_data and update_data["name"] is not None:
        update_data["name"] = update_data["name"].strip()

    for field, value in update_data.items():
        setattr(organization, field, value)

    db.add(organization)
    db.commit()
    db.refresh(organization)

    return organization
