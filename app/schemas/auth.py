from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)


class ManagerRegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)
    full_name: str | None = None
    organization_id: int | None = None
    organization_slug: str | None = None
    organization_name: str | None = None
    signup_code: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MembershipScopeResponse(BaseModel):
    organization_id: int
    role: str
    is_active: bool


class PropertyAccessScopeResponse(BaseModel):
    property_id: int


class CurrentOrganizationResponse(BaseModel):
    id: int
    name: str


class AvailablePropertyResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    timezone: str
    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserMeResponse(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    is_active: bool
    is_superuser: bool
    is_platform_owner: bool
    role_ui: str
    current_organization: CurrentOrganizationResponse | None = None
    available_properties: list[AvailablePropertyResponse]
    current_property_id: int | None = None
    memberships: list[MembershipScopeResponse]
    property_accesses: list[PropertyAccessScopeResponse]
