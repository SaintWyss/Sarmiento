from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import jwt
from cryptography.fernet import Fernet, InvalidToken

PASSWORD_SCHEME = "scrypt"
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SESSION_ISSUER = "sarmiento"
SESSION_AUDIENCE = "sarmiento-control-plane"
TOTP_PERIOD_SECONDS = 30
TOTP_DIGITS = 6


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


DUMMY_PASSWORD_HASH = hash_password("sarmiento-dummy-password-never-valid")


def generate_token(prefix: str, size: int = 32) -> str:
    return f"{prefix}_{secrets.token_urlsafe(size)}"


def derive_token(prefix: str, *, subject: str, nonce: str, pepper: str) -> str:
    """Derive a retry-safe secret without storing the raw token at rest."""
    material = f"{prefix}:{subject}:{nonce}".encode()
    digest = hmac.new(pepper.encode("utf-8"), material, hashlib.sha256).digest()
    return f"{prefix}_{_b64(digest)}"


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
        "iss": SESSION_ISSUER,
        "aud": SESSION_AUDIENCE,
        "sub": user_id,
        "username": username,
        "type": "session",
        "session_version": session_version,
        "iat": issued_at,
        "nbf": issued_at,
        "exp": issued_at + timedelta(minutes=ttl_minutes),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_session_token(token: str, secret: str) -> dict[str, Any]:
    payload = jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        audience=SESSION_AUDIENCE,
        issuer=SESSION_ISSUER,
        options={
            "require": [
                "iss",
                "aud",
                "sub",
                "type",
                "session_version",
                "iat",
                "nbf",
                "exp",
                "jti",
            ]
        },
    )
    if payload.get("type") != "session" or not payload.get("sub"):
        raise jwt.InvalidTokenError("invalid session token")
    return payload


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(24)


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _decode_totp_secret(secret: str) -> bytes:
    normalized = secret.strip().replace(" ", "").upper()
    return base64.b32decode(normalized + "=" * (-len(normalized) % 8), casefold=True)


def totp_code(secret: str, step: int, digits: int = TOTP_DIGITS) -> str:
    digest = hmac.new(
        _decode_totp_secret(secret),
        struct.pack(">Q", step),
        hashlib.sha1,
    ).digest()  # nosec B324 - required by RFC 6238 interoperability
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(value % (10**digits)).zfill(digits)


def verify_totp(
    secret: str,
    code: str,
    *,
    now: datetime | None = None,
    window: int = 1,
    last_used_step: int | None = None,
) -> int | None:
    candidate = code.strip().replace(" ", "")
    if len(candidate) != TOTP_DIGITS or not candidate.isdigit():
        return None
    moment = now or datetime.now(UTC)
    current_step = int(moment.timestamp()) // TOTP_PERIOD_SECONDS
    for delta in range(-window, window + 1):
        step = current_step + delta
        if last_used_step is not None and step <= last_used_step:
            continue
        if hmac.compare_digest(totp_code(secret, step), candidate):
            return step
    return None


def totp_provisioning_uri(secret: str, account: str, issuer: str = "Sarmiento") -> str:
    label = quote(f"{issuer}:{account}")
    return (
        f"otpauth://totp/{label}?secret={quote(secret)}&issuer={quote(issuer)}"
        f"&algorithm=SHA1&digits={TOTP_DIGITS}&period={TOTP_PERIOD_SECONDS}"
    )


def _fernet(pepper: str) -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(pepper.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_secret(secret: str, pepper: str) -> str:
    return _fernet(pepper).encrypt(secret.encode("utf-8")).decode("ascii")


def decrypt_secret(encrypted: str, pepper: str) -> str:
    try:
        return _fernet(pepper).decrypt(encrypted.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise ValueError("Unable to decrypt MFA secret") from exc


def generate_recovery_codes(count: int = 10) -> list[str]:
    codes: list[str] = []
    for _ in range(count):
        raw = secrets.token_hex(6).upper()
        codes.append(f"{raw[:4]}-{raw[4:8]}-{raw[8:]}")
    return codes


def normalize_recovery_code(code: str) -> str:
    return "".join(character for character in code.upper() if character.isalnum())


def hash_recovery_code(code: str, pepper: str) -> str:
    return hash_token(f"recovery:{normalize_recovery_code(code)}", pepper)
