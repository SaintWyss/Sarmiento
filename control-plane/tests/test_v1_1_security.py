from datetime import UTC, datetime
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from sarmiento.config import Settings
from sarmiento.main import create_app
from sarmiento.security import (
    decode_session_token,
    generate_totp_secret,
    issue_session_token,
    totp_code,
    verify_totp,
)


def make_client(tmp_path: Path, **overrides) -> TestClient:
    data = dict(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        owner_username="santiago",
        owner_password="correct-horse-battery-staple",
        session_secret="test-secret-that-is-definitely-at-least-32-bytes",
        token_pepper="test-token-pepper-that-is-long-enough",
        csrf_enabled=True,
        static_dir=str(tmp_path / "missing-front"),
        allowed_hosts="testserver,localhost",
        rustdesk_server="desk.example.test",
        rustdesk_key="PUBLIC_KEY",
    )
    data.update(overrides)
    return TestClient(create_app(Settings(**data)))


def csrf_headers(client: TestClient) -> dict[str, str]:
    return {"X-Sarmiento-CSRF": client.cookies.get("sarmiento_csrf")}


def test_session_requires_issuer_and_audience():
    secret = "x" * 32
    token = issue_session_token(
        user_id="owner-id",
        username="owner",
        session_version=1,
        secret=secret,
        ttl_minutes=30,
    )
    assert decode_session_token(token, secret)["sub"] == "owner-id"
    wrong = jwt.encode(
        {"sub": "owner-id", "type": "session", "exp": datetime.now(UTC).timestamp() + 30},
        secret,
        algorithm="HS256",
    )
    with pytest.raises(jwt.PyJWTError):
        decode_session_token(wrong, secret)


def test_totp_replay_protection():
    secret = generate_totp_secret()
    now = datetime.now(UTC)
    step = int(now.timestamp()) // 30
    code = totp_code(secret, step)
    assert verify_totp(secret, code, now=now) == step
    assert verify_totp(secret, code, now=now, last_used_step=step) is None


def test_mfa_login_and_recovery_code(tmp_path):
    with make_client(tmp_path) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "santiago", "password": "correct-horse-battery-staple"},
        )
        assert login.status_code == 200, login.text
        setup = client.post("/api/v1/auth/mfa/setup", headers=csrf_headers(client))
        assert setup.status_code == 200, setup.text
        body = setup.json()
        step = int(datetime.now(UTC).timestamp()) // 30
        code = totp_code(body["secret"], step)
        enabled = client.post(
            "/api/v1/auth/mfa/enable",
            headers=csrf_headers(client),
            json={"secret": body["secret"], "code": code},
        )
        assert enabled.status_code == 200, enabled.text
        recovery = enabled.json()["recovery_codes"][0]
        assert client.get("/api/v1/auth/me").status_code == 401

        missing = client.post(
            "/api/v1/auth/login",
            json={"username": "santiago", "password": "correct-horse-battery-staple"},
        )
        assert missing.status_code == 401
        recovered = client.post(
            "/api/v1/auth/login",
            json={
                "username": "santiago",
                "password": "correct-horse-battery-staple",
                "verification_code": recovery,
            },
        )
        assert recovered.status_code == 200, recovered.text
        assert recovered.json()["mfa_enabled"] is True

        reused = client.post(
            "/api/v1/auth/login",
            json={
                "username": "santiago",
                "password": "correct-horse-battery-staple",
                "verification_code": recovery,
            },
        )
        assert reused.status_code == 401


def test_persistent_login_lockout(tmp_path):
    with make_client(tmp_path, login_lockout_attempts=3) as client:
        for _ in range(3):
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "santiago", "password": "wrong-password"},
            )
            assert response.status_code == 401
        locked = client.post(
            "/api/v1/auth/login",
            json={"username": "santiago", "password": "correct-horse-battery-staple"},
        )
        assert locked.status_code == 429
        assert "Retry-After" in locked.headers


def test_request_body_limit(tmp_path):
    with make_client(tmp_path, max_request_body_bytes=16384) as client:
        oversized = client.post(
            "/api/v1/auth/login",
            content=b"x" * 17000,
            headers={"content-type": "application/json"},
        )
        assert oversized.status_code == 413
