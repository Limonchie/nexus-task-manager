"""
Пароли (bcrypt) и JWT (access/refresh).
Password hashing (bcrypt) and JWT creation/decoding. Bcrypt обрезает ввод до 72 байт.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings


def _to_bytes(password: str) -> bytes:
    # bcrypt принимает не более 72 байт / bcrypt accepts at most 72 bytes
    return password.encode("utf-8")[:72]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Сверка пароля с хешем. Check plain password against stored hash."""
    return bcrypt.checkpw(_to_bytes(plain_password), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """Хеш для сохранения в БД. Hash for storing in DB."""
    salt = bcrypt.gensalt(rounds=get_settings().bcrypt_rounds)
    return bcrypt.hashpw(_to_bytes(password), salt).decode("utf-8")


def create_access_token(subject: str | int, extra_claims: dict[str, Any] | None = None) -> str:
    """Access JWT, sub = user id. В payload есть type=access для отличия от refresh."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {"sub": str(subject), "exp": expire, "type": "access"}
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str | int) -> str:
    """Refresh JWT, живёт дольше. Used to issue new access without re-login."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict[str, Any] | None:
    """Декодирует JWT, возвращает payload или None при ошибке/истечении."""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
