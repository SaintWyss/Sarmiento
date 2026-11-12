import importlib.util
import subprocess
from pathlib import Path

import pytest


def load_agent_module():
    path = Path(__file__).resolve().parents[2] / "agent" / "sarmiento_agent.py"
    spec = importlib.util.spec_from_file_location("sarmiento_agent_under_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_agent_accepts_https_and_loopback_http():
    agent = load_agent_module()
    assert agent.validate_service_url("https://control.example.com") == "https://control.example.com"
    assert agent.validate_service_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000"


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://control.example.com/file",
        "http://control.example.com",
        "https://user:password@control.example.com",
        "https://control.example.com/#fragment",
        "not-a-url",
    ],
)
def test_agent_rejects_unsafe_control_plane_urls(url):
    agent = load_agent_module()
    with pytest.raises(RuntimeError):
        agent.validate_service_url(url)


def test_rustdesk_version_empty_output_returns_unknown(monkeypatch):
    agent = load_agent_module()
    monkeypatch.setattr(agent, "run_rustdesk", lambda *args, **kwargs: "")
    assert agent.rustdesk_version() == "unknown"


def test_rustdesk_version_timeout_returns_unknown(monkeypatch):
    agent = load_agent_module()

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("rustdesk", 30)

    monkeypatch.setattr(agent, "run_rustdesk", timeout)
    assert agent.rustdesk_version() == "unknown"
