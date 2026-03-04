from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DashboardTaskBase(BaseModel):
    organization_id: int
    property_id: int
    title: str
    note: str | None = None
    status: str = "pending"


class DashboardTaskCreate(DashboardTaskBase):
    pass


class DashboardTaskUpdate(BaseModel):
    title: str | None = None
    note: str | None = None
    status: str | None = None


class DashboardTaskResponse(DashboardTaskBase):
    id: int
    created_by_admin_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
