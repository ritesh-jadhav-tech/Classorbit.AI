from pydantic import BaseModel, EmailStr, Field

from app.models.enums import AccountStatus, RoleName
from app.schemas.common import TimestampedRead


class RoleRead(TimestampedRead):
    name: RoleName
    description: str | None = None


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)
    role: RoleName = RoleName.FACULTY
    department_id: str | None = None


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    role: RoleName | None = None
    department_id: str | None = None
    status: AccountStatus | None = None


class UserRead(TimestampedRead):
    name: str
    email: EmailStr
    status: AccountStatus
    role: RoleRead
    department_id: str | None = None
