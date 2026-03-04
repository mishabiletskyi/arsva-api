from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MembershipScopeResponse(BaseModel):
    organization_id: int
    role: str
    is_active: bool


class PropertyAccessScopeResponse(BaseModel):
    property_id: int


class UserMeResponse(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    is_active: bool
    is_superuser: bool
    is_platform_owner: bool
    memberships: list[MembershipScopeResponse]
    property_accesses: list[PropertyAccessScopeResponse]
