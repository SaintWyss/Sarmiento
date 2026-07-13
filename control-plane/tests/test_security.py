from datetime import UTC, datetime

import jwt
import pytest

from sarmiento.security import (
    decode_session_token,
    hash_password,
    hash_token,
    issue_session_token,
    verify_password,
)


def test_password_hash_roundtrip():
    encoded = hash_password("a-long-and-secure-password")
    assert verify_password("a-long-and-secure-password", encoded)
    assert not verify_password("wrong-password", encoded)


def test_password_rejects_short_values():
    with pytest.raises(ValueError):
        hash_password("short")


def test_token_hash_is_stable_and_peppered():
    assert hash_token("abc", "pepper") == hash_token("abc", "pepper")
    assert hash_token("abc", "pepper") != hash_token("abc", "other")


def test_session_token_roundtrip():
    secret = "x" * 32
    token = issue_session_token(
        user_id="owner-id",
        username="owner",
        session_version=1,
        secret=secret,
        ttl_minutes=30,
        now=datetime.now(UTC),
    )
    payload = decode_session_token(token, secret)
    assert payload["sub"] == "owner-id"
    with pytest.raises(jwt.PyJWTError):
        decode_session_token(token, "y" * 32)


def test_enrollment_token_consumption_uses_postgres_row_lock():
    from sqlalchemy.dialects import postgresql

    from sarmiento.services import enrollment_token_for_update_statement

    statement = enrollment_token_for_update_statement("digest")
    compiled = str(statement.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in compiled
