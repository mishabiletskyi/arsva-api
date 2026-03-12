from app.schemas.outbound_call_job import OutboundCallJobCreate
from app.schemas.tenant import TenantCreate
from app.services.outbound_call_job_service import create_outbound_call_job
from app.services.tenant_service import create_tenant


def test_auth_me_includes_role_ui_and_scope_for_manager(client, set_current_user, seeded_data):
    org_admin = seeded_data["users"]["org_admin"]
    property_1 = seeded_data["properties"]["property_1"]
    set_current_user(org_admin)

    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    payload = response.json()

    assert payload["role_ui"] == "manager"
    assert payload["current_organization"]["id"] == property_1.organization_id
    assert payload["available_properties"][0]["id"] == property_1.id
    assert payload["available_properties"][0]["organization_id"] == property_1.organization_id
    assert payload["available_properties"][0]["timezone"] == property_1.timezone
    assert "updated_at" in payload["available_properties"][0]
    assert payload["current_property_id"] == property_1.id


def test_auth_me_includes_owner_role_ui(client, set_current_user, seeded_data):
    platform_owner = seeded_data["users"]["platform_owner"]
    set_current_user(platform_owner)

    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    payload = response.json()
    assert payload["role_ui"] == "owner"
    assert payload["current_organization"] is not None


def test_manager_cannot_access_admin_users_module(client, set_current_user, seeded_data):
    org_admin = seeded_data["users"]["org_admin"]
    set_current_user(org_admin)

    response = client.get("/api/v1/admin-users")
    assert response.status_code == 403


def test_owner_can_access_admin_users_module(client, set_current_user, seeded_data):
    platform_owner = seeded_data["users"]["platform_owner"]
    set_current_user(platform_owner)

    response = client.get("/api/v1/admin-users")
    assert response.status_code == 200


def test_tenant_create_ignores_organization_id_and_uses_property_scope(db_session, seeded_data):
    org_admin = seeded_data["users"]["org_admin"]
    property_1 = seeded_data["properties"]["property_1"]
    org_2 = seeded_data["organizations"]["org_2"]

    tenant = create_tenant(
        db=db_session,
        current_user=org_admin,
        payload=TenantCreate(
            organization_id=org_2.id,  # ignored
            property_id=property_1.id,
            external_id="tenant-ignore-org",
            first_name="Scope",
            last_name="Test",
            phone_number="+15550002222",
            property_name=property_1.name,
            timezone=property_1.timezone,
        ),
    )

    assert tenant.organization_id == property_1.organization_id
    assert tenant.property_id == property_1.id


def test_outbound_create_ignores_payload_organization_id(db_session, seeded_data):
    org_admin = seeded_data["users"]["org_admin"]
    tenant = seeded_data["tenant"]
    org_2 = seeded_data["organizations"]["org_2"]

    job = create_outbound_call_job(
        db=db_session,
        current_user=org_admin,
        payload=OutboundCallJobCreate(
            organization_id=org_2.id,  # ignored
            property_id=tenant.property_id,
            tenant_ids=[tenant.id],
            dry_run=True,
            trigger_mode="manual",
            max_tenants=1,
        ),
    )

    assert job.organization_id == tenant.organization_id
    assert job.property_id == tenant.property_id


def test_property_filter_outside_scope_returns_403(client, set_current_user, seeded_data):
    org_admin = seeded_data["users"]["org_admin"]
    property_2 = seeded_data["properties"]["property_2"]
    set_current_user(org_admin)

    response = client.get("/api/v1/tenants", params={"property_id": property_2.id})
    assert response.status_code == 403
