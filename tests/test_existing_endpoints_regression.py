def test_existing_scoped_endpoints_still_work(client, set_current_user, seeded_data):
    org_admin = seeded_data["users"]["org_admin"]
    tenant = seeded_data["tenant"]
    set_current_user(org_admin)

    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    me_payload = me_response.json()
    assert me_payload["id"] == org_admin.id
    assert me_payload["email"] == org_admin.email
    assert isinstance(me_payload["memberships"], list)
    assert isinstance(me_payload["property_accesses"], list)

    tenants_response = client.get(
        "/api/v1/tenants",
        params={
            "organization_id": tenant.organization_id,
            "property_id": tenant.property_id,
        },
    )
    assert tenants_response.status_code == 200
    tenants_payload = tenants_response.json()
    assert isinstance(tenants_payload, list)
    assert len(tenants_payload) == 1
    assert tenants_payload[0]["id"] == tenant.id

    eligibility_response = client.get(
        "/api/v1/tenant-eligibility",
        params={
            "organization_id": tenant.organization_id,
            "property_id": tenant.property_id,
        },
    )
    assert eligibility_response.status_code == 200
    eligibility_payload = eligibility_response.json()
    assert isinstance(eligibility_payload, list)
    assert eligibility_payload[0]["tenant_id"] == tenant.id
    assert "can_call_now" in eligibility_payload[0]

    jobs_response = client.get("/api/v1/outbound-call-jobs")
    assert jobs_response.status_code == 200
    assert isinstance(jobs_response.json(), list)
