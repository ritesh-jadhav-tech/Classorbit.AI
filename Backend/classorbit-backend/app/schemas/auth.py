from pydantic import BaseModel, EmailStr, Field

from app.models.enums import RoleName
from app.schemas.user import UserRead


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)
    role: RoleName


class RegisterResponse(BaseModel):
    user: UserRead
    token: Token


class BootstrapAdminRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


class BootstrapAdminResponse(BaseModel):
    user_id: str
    email: EmailStr
    role: RoleName
    token: Token
