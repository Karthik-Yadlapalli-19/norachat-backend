import hashlib
import hmac
import secrets

import uuid
from datetime import timedelta

import jwt

from app.models.base import utcnow

from app.core.config import settings

ALGORITHM = "HS256"



def generate_otp() -> str:
    """Random 6-digit code, e.g. '048213'."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_value(value: str) -> str:
    """One-way hash, keyed with our secret. Used for OTPs and refresh tokens."""
    return hmac.new(
        settings.jwt_secret.encode(),
        value.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_hash(value: str, hashed: str) -> bool:
    """Check a plain value against a stored hash."""
    return hmac.compare_digest(hash_value(value), hashed)




def create_access_token(user_id: uuid.UUID) -> str:
    now = utcnow()
    payload = {
        "sub": str(user_id),                  # who the token belongs to
        "type": "access",
        "iat": now,                           # issued at
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID | None:
    """Returns the user ID if the token is valid, otherwise None."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:                    # bad signature, expired, malformed
        return None

    if payload.get("type") != "access":
        return None
    return uuid.UUID(payload["sub"])


def generate_refresh_token() -> str:
    """Long random string, NOT a JWT. Stored hashed so it can be revoked."""
    return secrets.token_urlsafe(32)