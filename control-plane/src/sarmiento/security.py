from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

PASSWORD_SCHEME = "scrypt"
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Owner password must contain at least 12 characters")
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32
    )
    return f"{PASSWORD_SCHEME}${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(derived)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt, expected = encoded.split("$", 5)
        if scheme != PASSWORD_SCHEME:
            return False
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_unb64(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=32,
        )
        return hmac.compare_digest(derived, _unb64(expected))
    except (ValueError, TypeError):
        return False


# Always perform one scrypt verification on failed logins, even when the owner
# does not exist. This keeps username enumeration from gaining a cheap timing
# signal. The value is generated once per process and can never authenticate.
DUMMY_PASSWORD_HASH = hash_password("sarmiento-dummy-password-never-valid")


def generate_token(prefix: str, size: int = 32) -> str:
    return f"{prefix}_{secrets.token_urlsafe(size)}"


def hash_token(token: str, pepper: str) -> str:
    return hmac.new(pepper.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def issue_session_token(
    *,
    user_id: str,
    username: str,
    session_version: int,
    secret: str,
    ttl_minutes: int,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(UTC)
    payload = {
        "sub": user_id,
        "username": username,
        "type": "session",
        "session_version": session_version,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=ttl_minutes),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_session_token(token: str, secret: str) -> dict[str, Any]:
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    if payload.get("type") != "session" or not payload.get("sub"):
        raise jwt.InvalidTokenError("invalid session token")
    return payload


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(24)
