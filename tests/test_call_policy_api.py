def test_get_call_policy_returns_defaults_when_missing(
    client,
    set_current_user,
    seeded_data,
):
    org_1 = seeded_data["organizations"]["org_1"]
    property_1 = seeded_data["properties"]["property_1"]
    org_admin = seeded_data["users"]["org_admin"]
    set_current_user(org_admin)

    response = client.get(
        "/api/v1/call-policy",
        params={"organization_id": org_1.id, "property_id": property_1.id},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["organization_id"] == org_1.id
    assert payload["property_id"] == property_1.id
    assert payload["min_hours_between_calls"] == 72
    assert payload["max_calls_7d"] == 2
    assert payload["max_calls_30d"] == 4
    assert payload["call_window_start"] == "08:00"
    assert payload["call_window_end"] == "21:00"
    assert payload["days_late_min"] == 3
    assert payload["days_late_max"] == 10
    assert payload["is_active"] is True
    assert payload["source"] == "default"


def test_put_call_policy_upsert_and_readback(
    client,
    set_current_user,
    seeded_data,
):
    org_1 = seeded_data["organizations"]["org_1"]
    property_1 = seeded_data["properties"]["property_1"]
    org_admin = seeded_data["users"]["org_admin"]
    set_current_user(org_admin)

    payload = {
        "organization_id": org_1.id,
        "property_id": property_1.id,
        "min_hours_between_calls": 24,
        "max_calls_7d": 7,
        "max_calls_30d": 20,
        "call_window_start": "06:30",
        "call_window_end": "22:00",
        "days_late_min": 1,
        "days_late_max": 15,
        "is_active": True,
    }
    response = client.put("/api/v1/call-policy", json=payload)
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["min_hours_between_calls"] == 24
    assert updated["max_calls_7d"] == 7
    assert updated["days_late_min"] == 1
    assert updated["days_late_max"] == 15
    assert updated["source"] == "custom"
    assert updated["updated_at"] is not None

    get_response = client.get(
        "/api/v1/call-policy",
        params={"organization_id": org_1.id, "property_id": property_1.id},
    )
    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["min_hours_between_calls"] == 24
    assert get_payload["call_window_start"] == "06:30"
    assert get_payload["call_window_end"] == "22:00"
    assert get_payload["source"] == "custom"


def test_put_call_policy_validation_errors(
    client,
    set_current_user,
    seeded_data,
):
    org_1 = seeded_data["organizations"]["org_1"]
    property_1 = seeded_data["properties"]["property_1"]
    org_admin = seeded_data["users"]["org_admin"]
    set_current_user(org_admin)

    payload = {
        "organization_id": org_1.id,
        "property_id": property_1.id,
        "min_hours_between_calls": 24,
        "max_calls_7d": 7,
        "max_calls_30d": 20,
        "call_window_start": "25:00",
        "call_window_end": "22:00",
        "days_late_min": 5,
        "days_late_max": 3,
        "is_active": True,
    }
    response = client.put("/api/v1/call-policy", json=payload)
    assert response.status_code == 422


def test_viewer_cannot_update_call_policy(
    client,
    set_current_user,
    seeded_data,
):
    org_1 = seeded_data["organizations"]["org_1"]
    property_1 = seeded_data["properties"]["property_1"]
    viewer = seeded_data["users"]["viewer"]
    set_current_user(viewer)

    payload = {
        "organization_id": org_1.id,
        "property_id": property_1.id,
        "min_hours_between_calls": 24,
        "max_calls_7d": 2,
        "max_calls_30d": 4,
        "call_window_start": "08:00",
        "call_window_end": "21:00",
        "days_late_min": 3,
        "days_late_max": 10,
        "is_active": True,
    }
    response = client.put("/api/v1/call-policy", json=payload)
    assert response.status_code == 403


def test_scope_isolation_for_call_policy_read(
    client,
    set_current_user,
    seeded_data,
):
    org_2 = seeded_data["organizations"]["org_2"]
    property_2 = seeded_data["properties"]["property_2"]
    org_admin = seeded_data["users"]["org_admin"]
    set_current_user(org_admin)

    response = client.get(
        "/api/v1/call-policy",
        params={"organization_id": org_2.id, "property_id": property_2.id},
    )
    assert response.status_code == 403
