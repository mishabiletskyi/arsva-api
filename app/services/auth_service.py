from sqlalchemy.orm import Session

from app.models.admin_user_membership import AdminUserMembership
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.admin_user import AdminUser
from app.models.organization import Organization


def get_admin_by_email(db: Session, email: str) -> AdminUser | None:
    normalized_email = email.strip().lower()

    return (
        db.query(AdminUser)
        .filter(AdminUser.email == normalized_email)
        .first()
    )


def get_admin_by_id(db: Session, admin_user_id: int) -> AdminUser | None:
    return (
        db.query(AdminUser)
        .filter(AdminUser.id == admin_user_id)
        .first()
    )


def authenticate_admin(db: Session, email: str, password: str) -> AdminUser | None:
    user = get_admin_by_email(db, email)

    if user is None:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


def create_admin_user(
    db: Session,
    email: str,
    password: str,
    full_name: str | None = None,
    is_superuser: bool = True,
) -> AdminUser:
    normalized_email = email.strip().lower()

    existing_user = get_admin_by_email(db, normalized_email)
    if existing_user is not None:
        raise ValueError("Admin user with this email already exists")

    user = AdminUser(
        email=normalized_email,
        full_name=full_name,
        hashed_password=get_password_hash(password),
        is_active=True,
        is_superuser=is_superuser,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def build_token_response(user: AdminUser) -> dict:
    access_token = create_access_token(subject=str(user.id))

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


def register_manager_user(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str | None,
    organization_id: int,
) -> AdminUser:
    normalized_email = email.strip().lower()

    existing_user = get_admin_by_email(db, normalized_email)
    if existing_user is not None:
        raise ValueError("Admin user with this email already exists")

    organization = (
        db.query(Organization)
        .filter(Organization.id == organization_id, Organization.is_active.is_(True))
        .first()
    )
    if organization is None:
        raise ValueError("Organization not found")

    user = AdminUser(
        email=normalized_email,
        full_name=full_name.strip() if full_name else None,
        hashed_password=get_password_hash(password),
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.flush()

    membership = AdminUserMembership(
        admin_user_id=user.id,
        organization_id=organization.id,
        role="org_admin",
        is_active=True,
    )
    db.add(membership)
    db.commit()
    db.refresh(user)

    return user
