from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings

settings = get_settings()

password_hash = PasswordHash.recommended()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    default_ttl_minutes = max(180, settings.jwt_access_token_expire_minutes)
    ttl_minutes = expires_minutes or default_ttl_minutes

    issued_at = datetime.now(timezone.utc)
    expire = issued_at + timedelta(minutes=ttl_minutes)

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": issued_at,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError as exc:
        raise exc
