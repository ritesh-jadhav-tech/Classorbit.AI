from sqlalchemy.orm import Session

from app.models.enums import RoleName
from app.models.user import Role


def ensure_default_roles(db: Session) -> None:
    existing = {role.name for role in db.query(Role).all()}
    for role_name in RoleName:
        if role_name not in existing:
            db.add(Role(name=role_name, description=f"{role_name.value.replace('_', ' ').title()} role"))
    db.commit()
