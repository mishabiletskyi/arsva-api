from app.core.security import decode_access_token
from app.models.admin_user import AdminUser
from app.models.admin_user_membership import AdminUserMembership
from app.models.organization import Organization
from app.models.property import Property
from app.api.v1.endpoints.auth import settings


def _enable_manager_signup_for_tests():
    settings.manager_signup_enabled = True
    settings.manager_signup_code = "test-signup-code"


def test_register_manager_creates_user_membership_and_returns_token(client, db_session, seeded_data):
    _enable_manager_signup_for_tests()
    organization = seeded_data["organizations"]["org_1"]

    response = client.post(
        "/api/v1/auth/register-manager",
        json={
            "email": "new.manager@example.com",
            "password": "StrongPass123",
            "full_name": "New Manager",
            "organization_id": organization.id,
            "signup_code": "test-signup-code",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]

    token_payload = decode_access_token(payload["access_token"])
    user_id = int(token_payload["sub"])

    user = db_session.query(AdminUser).filter(AdminUser.id == user_id).first()
    assert user is not None
    assert user.email == "new.manager@example.com"
    assert user.is_superuser is False

    membership = (
        db_session.query(AdminUserMembership)
        .filter(
            AdminUserMembership.admin_user_id == user.id,
            AdminUserMembership.organization_id == organization.id,
        )
        .first()
    )
    assert membership is not None
    assert membership.role == "org_admin"


def test_register_manager_with_duplicate_email_returns_400(client, seeded_data):
    _enable_manager_signup_for_tests()
    response = client.post(
        "/api/v1/auth/register-manager",
        json={
            "email": seeded_data["users"]["org_admin"].email,
            "password": "StrongPass123",
            "organization_id": seeded_data["organizations"]["org_1"].id,
            "signup_code": "test-signup-code",
        },
    )
    assert response.status_code == 400


def test_register_manager_creates_organization_from_name(client, db_session):
    _enable_manager_signup_for_tests()
    response = client.post(
        "/api/v1/auth/register-manager",
        json={
            "email": "org.owner@example.com",
            "password": "StrongPass123",
            "full_name": "Org Owner",
            "organization_name": "Acme Living",
            "signup_code": "test-signup-code",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    token_payload = decode_access_token(payload["access_token"])
    user_id = int(token_payload["sub"])

    user = db_session.query(AdminUser).filter(AdminUser.id == user_id).first()
    assert user is not None

    organization = (
        db_session.query(Organization)
        .filter(Organization.name == "Acme Living")
        .first()
    )
    assert organization is not None
    assert organization.slug.startswith("acme-living")

    membership = (
        db_session.query(AdminUserMembership)
        .filter(
            AdminUserMembership.admin_user_id == user.id,
            AdminUserMembership.organization_id == organization.id,
        )
        .first()
    )
    assert membership is not None
    assert membership.role == "org_admin"

    property_row = (
        db_session.query(Property)
        .filter(Property.organization_id == organization.id)
        .first()
    )
    assert property_row is not None


def test_register_manager_without_signup_code_is_forbidden(client, seeded_data):
    _enable_manager_signup_for_tests()
    response = client.post(
        "/api/v1/auth/register-manager",
        json={
            "email": "manager.no.code@example.com",
            "password": "StrongPass123",
            "organization_id": seeded_data["organizations"]["org_1"].id,
        },
    )
    assert response.status_code == 403
