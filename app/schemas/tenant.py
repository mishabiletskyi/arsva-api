from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class TenantBase(BaseModel):
    external_id: str | None = None
    organization_id: int
    property_id: int
    first_name: str
    last_name: str | None = None
    phone_number: str
    property_name: str | None = None
    timezone: str = "America/New_York"
    rent_due_date: date | None = None
    days_late: int = 0
    consent_status: bool = False
    consent_timestamp: datetime | None = None
    consent_source: str | None = None
    consent_document_version: str | None = None
    opt_out_flag: bool = False
    opt_out_timestamp: datetime | None = None
    eviction_status: bool = False
    is_suppressed: bool = False
    notes: str | None = None


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    external_id: str | None = None
    organization_id: int | None = None
    property_id: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    property_name: str | None = None
    timezone: str | None = None
    rent_due_date: date | None = None
    days_late: int | None = None
    consent_status: bool | None = None
    consent_timestamp: datetime | None = None
    consent_source: str | None = None
    consent_document_version: str | None = None
    opt_out_flag: bool | None = None
    opt_out_timestamp: datetime | None = None
    eviction_status: bool | None = None
    is_suppressed: bool | None = None
    notes: str | None = None


class TenantResponse(TenantBase):
    id: int
    is_archived: bool
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
