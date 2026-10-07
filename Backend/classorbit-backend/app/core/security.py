from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings


PASSWORD_HASH_PREFIX = "$classorbit-bcrypt-sha256$"


def _password_digest(password: str) -> bytes:
    return hashlib.sha256(password.encode("utf-8")).digest()


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        if password_hash.startswith(PASSWORD_HASH_PREFIX):
            bcrypt_hash = password_hash.removeprefix(PASSWORD_HASH_PREFIX).encode("ascii")
            return bcrypt.checkpw(_password_digest(plain_password), bcrypt_hash)

        # Compatibility for accounts created with the previous passlib/bcrypt setup.
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False


def hash_password(password: str) -> str:
    bcrypt_hash = bcrypt.hashpw(_password_digest(password), bcrypt.gensalt()).decode("ascii")
    return f"{PASSWORD_HASH_PREFIX}{bcrypt_hash}"


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expires_at}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise ValueError("Invalid authentication token") from exc
