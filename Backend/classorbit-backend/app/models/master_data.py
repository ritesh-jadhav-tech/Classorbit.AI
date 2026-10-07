from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdTimestampMixin


class Department(Base, IdTimestampMixin):
    __tablename__ = "departments"

    name: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)
    code: Mapped[str | None] = mapped_column(String(32), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="department")
    faculty: Mapped[list["Faculty"]] = relationship(back_populates="department")
    subjects: Mapped[list["Subject"]] = relationship(back_populates="department")
    classrooms: Mapped[list["Classroom"]] = relationship(back_populates="department")
    timetables: Mapped[list["Timetable"]] = relationship(back_populates="department")


class Faculty(Base, IdTimestampMixin):
    __tablename__ = "faculty"

    name: Mapped[str] = mapped_column(String(180), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    employee_code: Mapped[str | None] = mapped_column(String(64), unique=True)
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id"))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)

    department: Mapped[Department | None] = relationship(back_populates="faculty")
    user: Mapped["User | None"] = relationship(back_populates="faculty_profile")
    timetable_entries: Mapped[list["TimetableEntry"]] = relationship(back_populates="faculty")


class Subject(Base, IdTimestampMixin):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("name", "department_id", name="uq_subject_name_department"),)

    name: Mapped[str] = mapped_column(String(220), nullable=False)
    code: Mapped[str | None] = mapped_column(String(64))
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id"))
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)

    department: Mapped[Department | None] = relationship(back_populates="subjects")
    timetable_entries: Mapped[list["TimetableEntry"]] = relationship(back_populates="subject")


class Building(Base, IdTimestampMixin):
    __tablename__ = "buildings"

    name: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)
    code: Mapped[str | None] = mapped_column(String(32), unique=True)
    address: Mapped[str | None] = mapped_column(Text)

    floors: Mapped[list["Floor"]] = relationship(back_populates="building", cascade="all, delete-orphan")
    classrooms: Mapped[list["Classroom"]] = relationship(back_populates="building")


class Floor(Base, IdTimestampMixin):
    __tablename__ = "floors"
    __table_args__ = (UniqueConstraint("building_id", "level", name="uq_floor_building_level"),)

    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)

    building: Mapped[Building] = relationship(back_populates="floors")
    classrooms: Mapped[list["Classroom"]] = relationship(back_populates="floor")


class RoomType(Base, IdTimestampMixin):
    __tablename__ = "room_types"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    classrooms: Mapped[list["Classroom"]] = relationship(back_populates="room_type")


class Classroom(Base, IdTimestampMixin):
    __tablename__ = "classrooms"

    room_number: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(180), unique=True)
    building_id: Mapped[str | None] = mapped_column(ForeignKey("buildings.id"))
    floor_id: Mapped[str | None] = mapped_column(ForeignKey("floors.id"))
    room_type_id: Mapped[str | None] = mapped_column(ForeignKey("room_types.id"))
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id"))
    capacity: Mapped[int | None] = mapped_column(Integer)
    facilities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)

    building: Mapped[Building | None] = relationship(back_populates="classrooms")
    floor: Mapped[Floor | None] = relationship(back_populates="classrooms")
    room_type: Mapped[RoomType | None] = relationship(back_populates="classrooms")
    department: Mapped[Department | None] = relationship(back_populates="classrooms")
    timetable_entries: Mapped[list["TimetableEntry"]] = relationship(back_populates="classroom")
    allocations: Mapped[list["ClassroomAllocation"]] = relationship(back_populates="classroom")
