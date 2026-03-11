from datetime import datetime, timedelta, timezone

from app.models.call_log import CallLog
from app.schemas.call_policy import CallPolicyUpdateRequest
from app.services.call_policy_service import upsert_call_policy
from app.services.compliance_service import evaluate_tenant_eligibility


def test_daily_policy_allows_retry_after_24h(db_session, seeded_data):
    tenant = seeded_data["tenant"]
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

    db_session.add(
        CallLog(
            organization_id=tenant.organization_id,
            property_id=tenant.property_id,
            tenant_id=tenant.id,
            created_at=datetime.now(timezone.utc) - timedelta(hours=25),
        )
    )
    db_session.commit()

    result = evaluate_tenant_eligibility(db=db_session, tenant=tenant)
    assert result["can_call_now"] is True
    assert "minimum_gap_1440m" not in result["blocked_reasons"]


def test_weekly_policy_blocks_within_min_gap(db_session, seeded_data):
    tenant = seeded_data["tenant"]
    tenant.timezone = "UTC"
    db_session.add(tenant)
    db_session.commit()

    upsert_call_policy(
        db=db_session,
        payload=CallPolicyUpdateRequest(
            organization_id=tenant.organization_id,
            property_id=tenant.property_id,
            min_hours_between_calls=168,
            max_calls_7d=10,
            max_calls_30d=20,
            call_window_start="00:00",
            call_window_end="23:59",
            days_late_min=0,
            days_late_max=30,
            is_active=True,
        ),
    )

    db_session.add(
        CallLog(
            organization_id=tenant.organization_id,
            property_id=tenant.property_id,
            tenant_id=tenant.id,
            created_at=datetime.now(timezone.utc) - timedelta(hours=36),
        )
    )
    db_session.commit()

    result = evaluate_tenant_eligibility(db=db_session, tenant=tenant)
    assert result["can_call_now"] is False
    assert "minimum_gap_10080m" in result["blocked_reasons"]


def test_days_late_range_is_dynamic(db_session, seeded_data):
    tenant = seeded_data["tenant"]
    tenant.days_late = 5
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
            days_late_min=6,
            days_late_max=8,
            is_active=True,
        ),
    )

    result = evaluate_tenant_eligibility(db=db_session, tenant=tenant)
    assert result["can_call_now"] is False
    assert "delinquency_ineligible" in result["blocked_reasons"]


def test_call_window_respects_tenant_timezone(db_session, seeded_data):
    tenant = seeded_data["tenant"]
    tenant.timezone = "Europe/Kiev"
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
            call_window_start="08:00",
            call_window_end="09:00",
            days_late_min=0,
            days_late_max=30,
            is_active=True,
        ),
    )

    result = evaluate_tenant_eligibility(
        db=db_session,
        tenant=tenant,
        now_utc=datetime(2026, 3, 10, 4, 30, tzinfo=timezone.utc),  # 06:30 in Kyiv
    )
    assert result["can_call_now"] is False
    assert "outside_call_window" in result["blocked_reasons"]


def test_inactive_policy_blocks_outbound(db_session, seeded_data):
    tenant = seeded_data["tenant"]
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
            is_active=False,
        ),
    )

    result = evaluate_tenant_eligibility(db=db_session, tenant=tenant)
    assert result["can_call_now"] is False
    assert "call_policy_inactive" in result["blocked_reasons"]
