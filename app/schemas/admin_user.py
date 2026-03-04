from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AdminUserBase(BaseModel):
    email: str
    full_name: str | None = None
    is_active: bool = True
    is_superuser: bool = False


class AdminUserCreate(AdminUserBase):
    password: str = Field(min_length=6)


class AdminUserUpdate(BaseModel):
    email: str | None = None
    full_name: str | None = None
    password: str | None = Field(default=None, min_length=6)
    is_active: bool | None = None
    is_superuser: bool | None = None


class AdminUserMembershipAssignment(BaseModel):
    organization_id: int
    role: str
    is_active: bool = True


class PropertyAccessAssignment(BaseModel):
    property_id: int


class AdminUserMembershipResponse(BaseModel):
    id: int
    organization_id: int
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PropertyUserAccessResponse(BaseModel):
    id: int
    property_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserResponse(AdminUserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    memberships: list[AdminUserMembershipResponse] = Field(default_factory=list)
    property_accesses: list[PropertyUserAccessResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
