from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OutboundCallJobCreate(BaseModel):
    organization_id: int | None = None
    property_id: int | None = None
    tenant_ids: list[int] = Field(default_factory=list)
    assistant_id: str | None = None
    phone_number_id: str | None = None
    dry_run: bool = True
    trigger_mode: str = "manual"
    max_tenants: int | None = None


class OutboundCallJobResponse(BaseModel):
    id: int
    organization_id: int | None = None
    property_id: int | None = None
    status: str
    trigger_mode: str
    dry_run: bool
    requested_by_admin_id: int | None = None
    total_candidates: int
    eligible_count: int
    blocked_count: int
    requested_count: int
    started_count: int
    failed_count: int
    note: str | None = None
    filters: dict[str, Any] | None = None
    policy_snapshot: dict[str, Any] | None = None
    result_summary: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
