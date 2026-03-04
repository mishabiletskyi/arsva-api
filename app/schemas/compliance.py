from pydantic import BaseModel


class TenantEligibilityResponse(BaseModel):
    tenant_id: int
    organization_id: int
    property_id: int
    can_call_now: bool
    blocked_reasons: list[str]
    consent_required: bool
    suppressed: bool
    outside_call_window: bool
    state_restriction: bool
    call_frequency_limited: bool
    delinquency_ineligible: bool
    opted_out: bool
    eviction_blocked: bool
    archived: bool
