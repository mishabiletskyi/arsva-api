from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CallLogBase(BaseModel):
    tenant_id: int
    vapi_call_id: str | None = None
    call_outcome: str | None = None
    script_version: str | None = None
    transcript: str | None = None
    recording_url: str | None = None
    opt_out_detected: bool = False
    expected_payment_date: date | None = None
    duration_seconds: int | None = None
    raw_payload: str | None = None


class CallLogCreate(CallLogBase):
    pass


class CallLogUpdate(BaseModel):
    call_outcome: str | None = None
    script_version: str | None = None
    transcript: str | None = None
    recording_url: str | None = None
    opt_out_detected: bool | None = None
    expected_payment_date: date | None = None
    duration_seconds: int | None = None
    raw_payload: str | None = None


class CallLogResponse(CallLogBase):
    id: int
    organization_id: int
    property_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
