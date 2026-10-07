from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdTimestampMixin
from app.models.enums import AccountStatus, RoleName


class Role(Base, IdTimestampMixin):
    __tablename__ = "roles"

    name: Mapped[RoleName] = mapped_column(Enum(RoleName, native_enum=False), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base, IdTimestampMixin):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, native_enum=False), default=AccountStatus.ACTIVE, nullable=False
    )
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), nullable=False)
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id"))

    role: Mapped[Role] = relationship(back_populates="users")
    department: Mapped["Department | None"] = relationship(back_populates="users")
    faculty_profile: Mapped["Faculty | None"] = relationship(back_populates="user")

    @property
    def role_name(self) -> RoleName:
        return self.role.name
