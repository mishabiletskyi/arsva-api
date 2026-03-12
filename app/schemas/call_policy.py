from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


TIME_HHMM_PATTERN = r"^([01][0-9]|2[0-3]):[0-5][0-9]$"


class CallPolicyUpdateRequest(BaseModel):
    organization_id: int | None = None
    property_id: int
    min_hours_between_calls: int = Field(ge=1, le=720)
    max_calls_7d: int = Field(ge=0, le=14)
    max_calls_30d: int = Field(ge=0, le=60)
    call_window_start: str = Field(pattern=TIME_HHMM_PATTERN)
    call_window_end: str = Field(pattern=TIME_HHMM_PATTERN)
    days_late_min: int = Field(ge=0)
    days_late_max: int = Field(ge=0)
    is_active: bool = True

    @field_validator("days_late_max")
    @classmethod
    def validate_days_late_range(cls, value: int, info):
        days_late_min = info.data.get("days_late_min")
        if days_late_min is not None and value < days_late_min:
            raise ValueError("days_late_max must be greater than or equal to days_late_min")
        return value

    @field_validator("call_window_end")
    @classmethod
    def validate_call_window_not_equal(cls, value: str, info):
        call_window_start = info.data.get("call_window_start")
        if call_window_start is not None and value == call_window_start:
            raise ValueError("call_window_start and call_window_end cannot be equal")
        return value


class CallPolicyResponse(BaseModel):
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
    updated_at: datetime | None = None
    source: str = "custom"

    model_config = ConfigDict(from_attributes=True)
