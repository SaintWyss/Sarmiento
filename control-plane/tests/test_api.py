from pathlib import Path

from fastapi.testclient import TestClient

from sarmiento.config import Settings
from sarmiento.main import create_app


def make_client(tmp_path: Path) -> TestClient:
    settings = Settings(
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
    return TestClient(create_app(settings))


def csrf_headers(client: TestClient) -> dict[str, str]:
    return {"X-Sarmiento-CSRF": client.cookies.get("sarmiento_csrf")}


def login(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "santiago", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200, response.text
    return response


def issue_enrollment(client: TestClient) -> str:
    response = client.post(
        "/api/v1/enrollment-tokens",
        json={"label": "office-pc"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 201, response.text
    return response.json()["token"]


def enroll(client: TestClient, enrollment_token: str):
    response = client.post(
        "/api/v1/agents/enroll",
        json={
            "enrollment_token": enrollment_token,
            "rustdesk_id": "123456789",
            "alias": "Office PC",
            "hostname": "office",
            "platform": "Windows",
            "architecture": "AMD64",
            "agent_version": "1.0.0",
            "rustdesk_version": "1.4.9",
            "metadata": {"cpu_count": 8},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_full_owner_enrollment_and_heartbeat_flow(tmp_path):
    with make_client(tmp_path) as client:
        assert client.get("/healthz").status_code == 200
        login(client)
        token = issue_enrollment(client)
        enrollment = enroll(client, token)

        repeated = client.post(
            "/api/v1/agents/enroll",
            json={
                "enrollment_token": token,
                "rustdesk_id": "987654321",
                "alias": "Other",
            },
        )
        assert repeated.status_code == 410

        heartbeat = client.post(
            "/api/v1/agents/heartbeat",
            headers={"Authorization": f"Bearer {enrollment['agent_token']}"},
            json={
                "rustdesk_id": "123456789",
                "hostname": "office-renamed",
                "platform": "Windows",
                "architecture": "AMD64",
                "agent_version": "1.0.0",
                "rustdesk_version": "1.4.9",
                "metadata": {"boot_id": "abc"},
            },
        )
        assert heartbeat.status_code == 200, heartbeat.text

        devices = client.get("/api/v1/devices")
        assert devices.status_code == 200
        body = devices.json()
        assert len(body) == 1
        assert body[0]["online"] is True
        assert body[0]["hostname"] == "office-renamed"
        assert body[0]["connect_uri"] == "sarmiento://connect/123456789"

        stats = client.get("/api/v1/stats")
        assert stats.json()["online_devices"] == 1


def test_csrf_and_device_management(tmp_path):
    with make_client(tmp_path) as client:
        login(client)
        forbidden = client.post("/api/v1/enrollment-tokens", json={})
        assert forbidden.status_code == 403

        enrollment = enroll(client, issue_enrollment(client))
        device_id = enrollment["device_id"]
        patched = client.patch(
            f"/api/v1/devices/{device_id}",
            headers=csrf_headers(client),
            json={"alias": "Main workstation", "tags": ["Home", "trusted", "home"]},
        )
        assert patched.status_code == 200
        assert patched.json()["tags"] == ["home", "trusted"]

        rotated = client.post(
            f"/api/v1/devices/{device_id}/rotate-token", headers=csrf_headers(client)
        )
        assert rotated.status_code == 200
        assert rotated.json()["agent_token"].startswith("sat_")

        old_heartbeat = client.post(
            "/api/v1/agents/heartbeat",
            headers={"Authorization": f"Bearer {enrollment['agent_token']}"},
            json={"rustdesk_id": "123456789"},
        )
        assert old_heartbeat.status_code == 401

        revoked = client.post(
            f"/api/v1/devices/{device_id}/revoke", headers=csrf_headers(client)
        )
        assert revoked.status_code == 200
        assert revoked.json()["revoked_at"] is not None

        audit = client.get("/api/v1/audit")
        actions = {event["action"] for event in audit.json()}
        assert "device.enrolled" in actions
        assert "device.updated" in actions
        assert "device.credential_rotated" in actions
        assert "device.revoked" in actions


def test_login_failure_and_logout(tmp_path):
    with make_client(tmp_path) as client:
        bad = client.post(
            "/api/v1/auth/login", json={"username": "santiago", "password": "wrong"}
        )
        assert bad.status_code == 401
        login(client)
        response = client.post("/api/v1/auth/logout", headers=csrf_headers(client))
        assert response.status_code == 204
        assert client.get("/api/v1/auth/me").status_code == 401


def test_password_change_invalidates_existing_session(tmp_path):
    with make_client(tmp_path) as client:
        login(client)
        changed = client.post(
            "/api/v1/auth/change-password",
            headers=csrf_headers(client),
            json={
                "current_password": "correct-horse-battery-staple",
                "new_password": "a-new-password-that-is-long-enough",
            },
        )
        assert changed.status_code == 204, changed.text
        assert client.get("/api/v1/auth/me").status_code == 401
        old_login = client.post(
            "/api/v1/auth/login",
            json={"username": "santiago", "password": "correct-horse-battery-staple"},
        )
        assert old_login.status_code == 401
        new_login = client.post(
            "/api/v1/auth/login",
            json={"username": "santiago", "password": "a-new-password-that-is-long-enough"},
        )
        assert new_login.status_code == 200
