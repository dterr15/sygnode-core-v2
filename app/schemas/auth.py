from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6)


class RegisterRequest(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8)
    name: str = Field(..., max_length=255)
    rut_organizacion: str = Field(..., max_length=12)
    nombre_organizacion: str = Field(..., max_length=255)
    city: str | None = None


class LoginResponse(BaseModel):
    user: "UserBrief"
    organization: "OrgBrief"


class UserBrief(BaseModel):
    id: str
    email: str
    name: str
    role: str

    model_config = {"from_attributes": True}


class OrgBrief(BaseModel):
    id: str
    rut: str
    name: str
    subscription_status: str

    model_config = {"from_attributes": True}


LoginResponse.model_rebuild()
