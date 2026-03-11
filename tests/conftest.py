from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.base  # noqa: F401
from app.api.deps.auth import get_current_user
from app.core.database import Base, get_db
from app.main import app
from app.models.admin_user import AdminUser
from app.models.admin_user_membership import AdminUserMembership
from app.models.organization import Organization
from app.models.property import Property
from app.models.property_user_access import PropertyUserAccess
from app.models.tenant import Tenant


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def set_current_user():
    def _set(user: AdminUser):
        app.dependency_overrides[get_current_user] = lambda: user

    return _set


@pytest.fixture()
def seeded_data(db_session: Session):
    org_1 = Organization(name="Org One", slug="org-one")
    org_2 = Organization(name="Org Two", slug="org-two")
    db_session.add_all([org_1, org_2])
    db_session.flush()

    property_1 = Property(
        organization_id=org_1.id,
        name="Property One",
        timezone="America/New_York",
    )
    property_2 = Property(
        organization_id=org_2.id,
        name="Property Two",
        timezone="America/Chicago",
    )
    db_session.add_all([property_1, property_2])
    db_session.flush()

    platform_owner = AdminUser(
        email="owner@example.com",
        full_name="Owner",
        hashed_password="hashed",
        is_active=True,
        is_superuser=True,
    )
    org_admin = AdminUser(
        email="org-admin@example.com",
        full_name="Org Admin",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
    )
    viewer = AdminUser(
        email="viewer@example.com",
        full_name="Viewer",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
    )
    other_org_admin = AdminUser(
        email="other-org-admin@example.com",
        full_name="Other Org Admin",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
    )
    db_session.add_all([platform_owner, org_admin, viewer, other_org_admin])
    db_session.flush()

    db_session.add_all(
        [
            AdminUserMembership(
                admin_user_id=org_admin.id,
                organization_id=org_1.id,
                role="org_admin",
                is_active=True,
            ),
            AdminUserMembership(
                admin_user_id=viewer.id,
                organization_id=org_1.id,
                role="viewer",
                is_active=True,
            ),
            AdminUserMembership(
                admin_user_id=other_org_admin.id,
                organization_id=org_2.id,
                role="org_admin",
                is_active=True,
            ),
        ]
    )
    db_session.flush()

    db_session.add(
        PropertyUserAccess(
            admin_user_id=viewer.id,
            property_id=property_1.id,
        )
    )

    tenant = Tenant(
        organization_id=org_1.id,
        property_id=property_1.id,
        external_id="tenant-1",
        first_name="John",
        last_name="Doe",
        phone_number="+15550001111",
        property_name=property_1.name,
        timezone="America/New_York",
        rent_due_date=date(2026, 3, 1),
        days_late=5,
        consent_status=True,
        is_suppressed=False,
        opt_out_flag=False,
        eviction_status=False,
        is_archived=False,
        notes="seed tenant",
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    return {
        "organizations": {"org_1": org_1, "org_2": org_2},
        "properties": {"property_1": property_1, "property_2": property_2},
        "users": {
            "platform_owner": platform_owner,
            "org_admin": org_admin,
            "viewer": viewer,
            "other_org_admin": other_org_admin,
        },
        "tenant": tenant,
    }
