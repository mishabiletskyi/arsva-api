from app.models.csv_import import CsvImport
from app.models.tenant import Tenant


def test_delete_csv_import_soft_deletes_only_history_record(client, db_session, set_current_user, seeded_data):
    org_admin = seeded_data["users"]["org_admin"]
    tenant = seeded_data["tenant"]
    property_1 = seeded_data["properties"]["property_1"]
    set_current_user(org_admin)

    csv_import = CsvImport(
        organization_id=tenant.organization_id,
        property_id=tenant.property_id,
        original_file_name="tenants.csv",
        stored_file_name="imports/test.csv",
        status="completed",
        total_rows=1,
        imported_rows=1,
        failed_rows=0,
        uploaded_by_admin_id=org_admin.id,
    )
    db_session.add(csv_import)
    db_session.commit()
    db_session.refresh(csv_import)

    tenant_count_before = db_session.query(Tenant).count()

    delete_response = client.delete(f"/api/v1/csv-imports/{csv_import.id}")
    assert delete_response.status_code == 204

    list_response = client.get(
        "/api/v1/csv-imports",
        params={"organization_id": tenant.organization_id, "property_id": property_1.id},
    )
    assert list_response.status_code == 200
    listed_ids = [item["id"] for item in list_response.json()]
    assert csv_import.id not in listed_ids

    detail_response = client.get(f"/api/v1/csv-imports/{csv_import.id}")
    assert detail_response.status_code == 404

    db_session.refresh(csv_import)
    assert csv_import.deleted_at is not None
    assert csv_import.deleted_by_admin_id == org_admin.id
    assert db_session.query(Tenant).count() == tenant_count_before
