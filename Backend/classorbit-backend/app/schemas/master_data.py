from pydantic import BaseModel, Field

from app.schemas.common import TimestampedRead


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    code: str | None = Field(default=None, max_length=32)
    description: str | None = None
    status: str = "ACTIVE"


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    code: str | None = Field(default=None, max_length=32)
    description: str | None = None
    status: str | None = None


class DepartmentRead(TimestampedRead):
    name: str
    code: str | None = None
    description: str | None = None
    status: str


class FacultyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    email: str | None = Field(default=None, max_length=254)
    employee_code: str | None = Field(default=None, max_length=64)
    department_id: str | None = None
    user_id: str | None = None
    status: str = "ACTIVE"


class FacultyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    email: str | None = Field(default=None, max_length=254)
    employee_code: str | None = Field(default=None, max_length=64)
    department_id: str | None = None
    user_id: str | None = None
    status: str | None = None


class FacultyRead(TimestampedRead):
    name: str
    email: str | None = None
    employee_code: str | None = None
    department_id: str | None = None
    user_id: str | None = None
    status: str


class SubjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=220)
    code: str | None = Field(default=None, max_length=64)
    department_id: str | None = None
    status: str = "ACTIVE"


class SubjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=220)
    code: str | None = Field(default=None, max_length=64)
    department_id: str | None = None
    status: str | None = None


class SubjectRead(TimestampedRead):
    name: str
    code: str | None = None
    department_id: str | None = None
    status: str


class BuildingCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    code: str | None = Field(default=None, max_length=32)
    address: str | None = None


class BuildingUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    code: str | None = Field(default=None, max_length=32)
    address: str | None = None


class BuildingRead(TimestampedRead):
    name: str
    code: str | None = None
    address: str | None = None


class FloorCreate(BaseModel):
    building_id: str
    name: str = Field(min_length=1, max_length=100)
    level: int


class FloorUpdate(BaseModel):
    building_id: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    level: int | None = None


class FloorRead(TimestampedRead):
    building_id: str
    name: str
    level: int


class RoomTypeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None


class RoomTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None


class RoomTypeRead(TimestampedRead):
    name: str
    description: str | None = None


class ClassroomCreate(BaseModel):
    room_number: str = Field(min_length=1, max_length=80)
    display_name: str | None = Field(default=None, max_length=180)
    building_id: str | None = None
    floor_id: str | None = None
    room_type_id: str | None = None
    department_id: str | None = None
    capacity: int | None = Field(default=None, ge=0)
    facilities: list[str] = Field(default_factory=list)
    status: str = "ACTIVE"


class ClassroomUpdate(BaseModel):
    room_number: str | None = Field(default=None, min_length=1, max_length=80)
    display_name: str | None = Field(default=None, max_length=180)
    building_id: str | None = None
    floor_id: str | None = None
    room_type_id: str | None = None
    department_id: str | None = None
    capacity: int | None = Field(default=None, ge=0)
    facilities: list[str] | None = None
    status: str | None = None


class ClassroomRead(TimestampedRead):
    room_number: str
    display_name: str | None = None
    building_id: str | None = None
    floor_id: str | None = None
    room_type_id: str | None = None
    department_id: str | None = None
    capacity: int | None = None
    facilities: list[str]
    status: str
