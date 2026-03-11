from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import tuple_
from sqlalchemy.orm import Session

from app.models.call_policy import CallPolicy
from app.schemas.call_policy import CallPolicyUpdateRequest

DEFAULT_MIN_HOURS_BETWEEN_CALLS = 72
DEFAULT_MAX_CALLS_7D = 2
DEFAULT_MAX_CALLS_30D = 4
DEFAULT_CALL_WINDOW_START = "08:00"
DEFAULT_CALL_WINDOW_END = "21:00"
DEFAULT_DAYS_LATE_MIN = 3
DEFAULT_DAYS_LATE_MAX = 10
DEFAULT_POLICY_ACTIVE = True


@dataclass(frozen=True)
class EffectiveCallPolicy:
    organization_id: int
    property_id: int
    min_hours_between_calls: int
    max_calls_7d: int
    max_calls_30d: int
    call_window_start: str
    call_window_end: str
    days_late_min: int
    days_late_max: int
    is_active: bool
    updated_at: datetime | None
    source: str

    def as_dict(self) -> dict:
        return {
            "organization_id": self.organization_id,
            "property_id": self.property_id,
            "min_hours_between_calls": self.min_hours_between_calls,
            "max_calls_7d": self.max_calls_7d,
            "max_calls_30d": self.max_calls_30d,
            "call_window_start": self.call_window_start,
            "call_window_end": self.call_window_end,
            "days_late_min": self.days_late_min,
            "days_late_max": self.days_late_max,
            "is_active": self.is_active,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "source": self.source,
        }


def _build_default_policy(organization_id: int, property_id: int) -> EffectiveCallPolicy:
    return EffectiveCallPolicy(
        organization_id=organization_id,
        property_id=property_id,
        min_hours_between_calls=DEFAULT_MIN_HOURS_BETWEEN_CALLS,
        max_calls_7d=DEFAULT_MAX_CALLS_7D,
        max_calls_30d=DEFAULT_MAX_CALLS_30D,
        call_window_start=DEFAULT_CALL_WINDOW_START,
        call_window_end=DEFAULT_CALL_WINDOW_END,
        days_late_min=DEFAULT_DAYS_LATE_MIN,
        days_late_max=DEFAULT_DAYS_LATE_MAX,
        is_active=DEFAULT_POLICY_ACTIVE,
        updated_at=None,
        source="default",
    )


def _from_model(policy: CallPolicy) -> EffectiveCallPolicy:
    return EffectiveCallPolicy(
        organization_id=policy.organization_id,
        property_id=policy.property_id,
        min_hours_between_calls=policy.min_hours_between_calls,
        max_calls_7d=policy.max_calls_7d,
        max_calls_30d=policy.max_calls_30d,
        call_window_start=policy.call_window_start,
        call_window_end=policy.call_window_end,
        days_late_min=policy.days_late_min,
        days_late_max=policy.days_late_max,
        is_active=policy.is_active,
        updated_at=policy.updated_at,
        source="custom",
    )


def get_call_policy_by_scope(
    db: Session,
    organization_id: int,
    property_id: int,
) -> CallPolicy | None:
    return (
        db.query(CallPolicy)
        .filter(
            CallPolicy.organization_id == organization_id,
            CallPolicy.property_id == property_id,
        )
        .first()
    )


def get_effective_call_policy(
    db: Session,
    organization_id: int,
    property_id: int,
) -> EffectiveCallPolicy:
    policy = get_call_policy_by_scope(
        db=db,
        organization_id=organization_id,
        property_id=property_id,
    )
    if policy is None:
        return _build_default_policy(
            organization_id=organization_id,
            property_id=property_id,
        )
    return _from_model(policy)


def get_effective_call_policy_map(
    db: Session,
    scopes: set[tuple[int, int]],
) -> dict[tuple[int, int], EffectiveCallPolicy]:
    if not scopes:
        return {}

    existing = (
        db.query(CallPolicy)
        .filter(
            tuple_(CallPolicy.organization_id, CallPolicy.property_id).in_(scopes),
        )
        .all()
    )
    existing_by_scope = {
        (item.organization_id, item.property_id): _from_model(item)
        for item in existing
    }

    result: dict[tuple[int, int], EffectiveCallPolicy] = {}
    for scope in scopes:
        result[scope] = existing_by_scope.get(scope) or _build_default_policy(*scope)

    return result


def upsert_call_policy(
    db: Session,
    payload: CallPolicyUpdateRequest,
) -> CallPolicy:
    policy = get_call_policy_by_scope(
        db=db,
        organization_id=payload.organization_id,
        property_id=payload.property_id,
    )

    if policy is None:
        policy = CallPolicy(
            organization_id=payload.organization_id,
            property_id=payload.property_id,
        )

    policy.min_hours_between_calls = payload.min_hours_between_calls
    policy.max_calls_7d = payload.max_calls_7d
    policy.max_calls_30d = payload.max_calls_30d
    policy.call_window_start = payload.call_window_start
    policy.call_window_end = payload.call_window_end
    policy.days_late_min = payload.days_late_min
    policy.days_late_max = payload.days_late_max
    policy.is_active = payload.is_active

    db.add(policy)
    db.commit()
    db.refresh(policy)

    return policy


def build_policy_snapshot(
    policies: list[EffectiveCallPolicy],
) -> dict:
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "default_behavior": "fallback_defaults_when_missing",
        "inactive_policy_behavior": "block_outbound",
        "scopes": [policy.as_dict() for policy in policies],
    }
