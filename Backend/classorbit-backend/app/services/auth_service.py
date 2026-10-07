from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.init_db import ensure_default_roles
from app.models.enums import AccountStatus, RoleName
from app.models.user import Role, User


class AuthError(ValueError):
    pass


def get_role(db: Session, role_name: RoleName) -> Role:
    role = db.execute(select(Role).where(Role.name == role_name)).scalar_one_or_none()
    if role is None:
        ensure_default_roles(db)
        role = db.execute(select(Role).where(Role.name == role_name)).scalar_one()
    return role


def create_user(
    db: Session,
    *,
    name: str,
    email: str,
    password: str,
    role_name: RoleName,
    department_id: str | None = None,
) -> User:
    existing = db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()
    if existing:
        raise AuthError("A user with this email already exists.")
    role = get_role(db, role_name)
    user = User(
        name=name,
        email=email.lower(),
        password_hash=hash_password(password),
        role=role,
        department_id=department_id,
        status=AccountStatus.ACTIVE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password.")
    if user.status != AccountStatus.ACTIVE:
        raise AuthError("This user account is not active.")
    return user


def token_for_user(user: User) -> str:
    return create_access_token(subject=user.id, extra_claims={"role": user.role_name.value, "email": user.email})
