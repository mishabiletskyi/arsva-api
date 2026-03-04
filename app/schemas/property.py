from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PropertyBase(BaseModel):
    organization_id: int
    name: str
    timezone: str = "America/New_York"
    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    is_active: bool = True


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    name: str | None = None
    timezone: str | None = None
    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    is_active: bool | None = None


class PropertyResponse(PropertyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
