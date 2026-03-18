from app.schemas.call_policy import CallPolicyUpdateRequest
from app.schemas.outbound_call_job import OutboundCallJobCreate
from app.services.call_policy_service import upsert_call_policy
from app.services.outbound_call_job_service import create_outbound_call_job


def test_outbound_job_response_includes_counts_filters_and_result_summary(db_session, seeded_data):
    tenant = seeded_data["tenant"]
    org_admin = seeded_data["users"]["org_admin"]

    tenant.timezone = "UTC"
    db_session.add(tenant)
    db_session.commit()

    upsert_call_policy(
        db=db_session,
        payload=CallPolicyUpdateRequest(
            organization_id=tenant.organization_id,
            property_id=tenant.property_id,
            min_hours_between_calls=24,
            max_calls_7d=10,
            max_calls_30d=20,
            call_window_start="00:00",
            call_window_end="23:59",
            days_late_min=0,
            days_late_max=30,
            is_active=True,
        ),
    )

    job = create_outbound_call_job(
        db=db_session,
        payload=OutboundCallJobCreate(
            organization_id=tenant.organization_id,
            property_id=tenant.property_id,
            tenant_ids=[tenant.id],
            dry_run=True,
            trigger_mode="manual",
            max_tenants=1,
        ),
        current_user=org_admin,
    )

    assert job.status == "previewed"
    assert job.total_candidates == 1
    assert job.eligible_count == 1
    assert job.blocked_count == 0
    assert job.requested_count == 1
    assert job.started_count == 0
    assert job.failed_count == 0
    assert job.note == "Preview only; no outbound calls sent."
    assert job.filters["organization_id"] == tenant.organization_id
    assert job.filters["property_id"] == tenant.property_id
    assert job.filters["effective_max_tenants"] == 1

    assert "requested_count" in job.result_summary
    assert "started_count" in job.result_summary
    assert "failed_count" in job.result_summary
    assert "note" in job.result_summary
    assert "dispatch_errors" in job.result_summary
    assert "dispatched_calls" in job.result_summary
    assert job.result_summary["requested_count"] == 1
    assert job.result_summary["started_count"] == 0
    assert job.result_summary["failed_count"] == 0
    assert isinstance(job.policy_snapshot, dict)
    assert "scopes" in job.policy_snapshot
    assert len(job.policy_snapshot["scopes"]) == 1
