from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.models.call_log import CallLog
from app.models.tenant import Tenant
from app.services.call_policy_service import EffectiveCallPolicy, get_effective_call_policy


def _resolve_tenant_timezone(tenant: Tenant) -> ZoneInfo | None:
    timezone_name = tenant.timezone or "America/New_York"
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return None


def _parse_hhmm(value: str) -> time | None:
    try:
        hour_part, minute_part = value.split(":", maxsplit=1)
        return time(hour=int(hour_part), minute=int(minute_part))
    except (ValueError, AttributeError):
        return None


def _is_within_window(local_now: datetime, start_hhmm: str, end_hhmm: str) -> bool:
    start = _parse_hhmm(start_hhmm)
    end = _parse_hhmm(end_hhmm)
    if start is None or end is None:
        return False

    current = local_now.time()

    if start < end:
        return start <= current < end

    return current >= start or current < end


def evaluate_tenant_eligibility(
    db: Session,
    tenant: Tenant,
    policy: EffectiveCallPolicy | None = None,
    now_utc: datetime | None = None,
) -> dict:
    policy = policy or get_effective_call_policy(
        db=db,
        organization_id=tenant.organization_id,
        property_id=tenant.property_id,
    )
    now_utc = now_utc or datetime.now(timezone.utc)

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

    delinquency_ineligible = tenant.days_late < policy.days_late_min or tenant.days_late > policy.days_late_max
    if delinquency_ineligible:
        blocked_reasons.append("delinquency_ineligible")

    timezone_info = _resolve_tenant_timezone(tenant)
    state_restriction = timezone_info is None
    if state_restriction:
        blocked_reasons.append("state_restriction")

    outside_call_window = False
    if timezone_info is not None:
        local_now = now_utc.astimezone(timezone_info)
        outside_call_window = not _is_within_window(
            local_now=local_now,
            start_hhmm=policy.call_window_start,
            end_hhmm=policy.call_window_end,
        )

    if outside_call_window:
        blocked_reasons.append("outside_call_window")

    if not policy.is_active:
        blocked_reasons.append("call_policy_inactive")

    seven_day_window_start = now_utc - timedelta(days=7)
    thirty_day_window_start = now_utc - timedelta(days=30)
    minimum_gap_start = now_utc - timedelta(hours=policy.min_hours_between_calls)

    call_frequency_limited = False
    call_logs_query = db.query(CallLog).filter(CallLog.tenant_id == tenant.id)

    if policy.max_calls_7d == 0:
        call_frequency_limited = True
        blocked_reasons.append("call_frequency_limit_7d")
    else:
        recent_calls_7_days_count = (
            call_logs_query
            .filter(CallLog.created_at >= seven_day_window_start)
            .count()
        )
        if recent_calls_7_days_count >= policy.max_calls_7d:
            call_frequency_limited = True
            blocked_reasons.append("call_frequency_limit_7d")

    if policy.max_calls_30d == 0:
        call_frequency_limited = True
        blocked_reasons.append("call_frequency_limit_30d")
    else:
        recent_calls_30_days_count = (
            call_logs_query
            .filter(CallLog.created_at >= thirty_day_window_start)
            .count()
        )
        if recent_calls_30_days_count >= policy.max_calls_30d:
            call_frequency_limited = True
            blocked_reasons.append("call_frequency_limit_30d")

    recent_calls_min_gap_count = (
        call_logs_query
        .filter(CallLog.created_at >= minimum_gap_start)
        .count()
    )
    if recent_calls_min_gap_count > 0:
        call_frequency_limited = True
        minimum_gap_minutes = max(1, int(round(policy.min_hours_between_calls * 60)))
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
        "policy_source": policy.source,
    }
