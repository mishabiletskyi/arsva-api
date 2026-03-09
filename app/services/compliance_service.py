from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.call_log import CallLog
from app.models.tenant import Tenant


def _resolve_tenant_timezone(tenant: Tenant) -> ZoneInfo | None:
    timezone_name = tenant.timezone or "America/New_York"
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return None


def evaluate_tenant_eligibility(db: Session, tenant: Tenant) -> dict:
    settings = get_settings()
    blocked_reasons: list[str] = []

    consent_required = not tenant.consent_status
    if consent_required:
        blocked_reasons.append("consent_required")

    opted_out = tenant.opt_out_flag
    if opted_out:
        blocked_reasons.append("opted_out")

    suppressed = tenant.is_suppressed
    if suppressed:
        blocked_reasons.append("suppressed")

    eviction_blocked = tenant.eviction_status
    if eviction_blocked:
        blocked_reasons.append("eviction_blocked")

    archived = tenant.is_archived
    if archived:
        blocked_reasons.append("archived")

    delinquency_ineligible = (
        tenant.days_late < settings.pilot_min_days_late
        or tenant.days_late > settings.pilot_max_days_late
    )
    if delinquency_ineligible:
        blocked_reasons.append("delinquency_ineligible")

    timezone_info = _resolve_tenant_timezone(tenant)
    state_restriction = timezone_info is None
    if state_restriction:
        blocked_reasons.append("state_restriction")

    outside_call_window = False
    now_utc = datetime.now(timezone.utc)
    if timezone_info is not None:
        local_now = now_utc.astimezone(timezone_info)
        outside_call_window = not (
            settings.call_window_start_hour <= local_now.hour < settings.call_window_end_hour
        )

    if outside_call_window:
        blocked_reasons.append("outside_call_window")

    call_logs = (
        db.query(CallLog)
        .filter(CallLog.tenant_id == tenant.id)
        .order_by(CallLog.created_at.desc())
        .all()
    )
    seven_day_window_start = now_utc - timedelta(days=7)
    thirty_day_window_start = now_utc - timedelta(days=30)
    minimum_gap_start = now_utc - timedelta(hours=settings.min_hours_between_calls)

    recent_calls_7_days = [log for log in call_logs if log.created_at >= seven_day_window_start]
    recent_calls_30_days = [log for log in call_logs if log.created_at >= thirty_day_window_start]
    recent_calls_min_gap = [log for log in call_logs if log.created_at >= minimum_gap_start]

    call_frequency_limited = False
    if len(recent_calls_7_days) >= settings.max_calls_7_days:
        call_frequency_limited = True
        blocked_reasons.append("call_frequency_limit_7d")

    if len(recent_calls_30_days) >= settings.max_calls_30_days:
        call_frequency_limited = True
        blocked_reasons.append("call_frequency_limit_30d")

    if recent_calls_min_gap:
        call_frequency_limited = True
        minimum_gap_minutes = max(1, int(round(settings.min_hours_between_calls * 60)))
        blocked_reasons.append(f"minimum_gap_{minimum_gap_minutes}m")

    can_call_now = not blocked_reasons

    return {
        "tenant_id": tenant.id,
        "organization_id": tenant.organization_id,
        "property_id": tenant.property_id,
        "can_call_now": can_call_now,
        "blocked_reasons": blocked_reasons,
        "consent_required": consent_required,
        "suppressed": suppressed,
        "outside_call_window": outside_call_window,
        "state_restriction": state_restriction,
        "call_frequency_limited": call_frequency_limited,
        "delinquency_ineligible": delinquency_ineligible,
        "opted_out": opted_out,
        "eviction_blocked": eviction_blocked,
        "archived": archived,
    }
