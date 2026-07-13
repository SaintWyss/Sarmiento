#!/usr/bin/env python3
"""Sarmiento agent for Linux/macOS. Uses only the Python standard library."""
from __future__ import annotations

import argparse
import json
import os
import platform
import random
import re
import shutil
import socket
import ssl
import string
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
DEFAULT_CONFIG = Path(os.environ.get("SARMIENTO_AGENT_CONFIG", "/etc/sarmiento/agent.json"))


def log(message: str) -> None:
    print(f"[sarmiento-agent] {message}", flush=True)


def request_json(url: str, *, method: str = "GET", body: dict | None = None, token: str | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json", "User-Agent": f"SarmientoAgent/{VERSION}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=20, context=context) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(payload).get("detail", payload)
        except json.JSONDecodeError:
            detail = payload
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach Sarmiento: {exc.reason}") from exc


def rustdesk_executable() -> str:
    candidates = [
        shutil.which("rustdesk"),
        "/usr/bin/rustdesk",
        "/usr/local/bin/rustdesk",
        "/Applications/RustDesk.app/Contents/MacOS/RustDesk",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    raise RuntimeError("RustDesk is not installed or is not available in PATH")


def run_rustdesk(*args: str, required: bool = True) -> str:
    command = [rustdesk_executable(), *args]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    output = (result.stdout or result.stderr).strip()
    if required and result.returncode != 0:
        raise RuntimeError(f"RustDesk command failed ({result.returncode}): {output}")
    return output


def detect_rustdesk_id(explicit: str | None = None) -> str:
    if explicit:
        return explicit.strip()
    env = os.environ.get("SARMIENTO_RUSTDESK_ID")
    if env:
        return env.strip()
    output = run_rustdesk("--get-id")
    match = re.search(r"[A-Za-z0-9_-]{3,64}", output)
    if not match:
        raise RuntimeError(f"Could not detect RustDesk ID from output: {output!r}")
    return match.group(0)


def rustdesk_version() -> str:
    try:
        return run_rustdesk("--version", required=False).splitlines()[0][:40] or "unknown"
    except Exception:
        return "unknown"


def random_password(length: int = 18) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.SystemRandom().choice(alphabet) for _ in range(length))


def configure_rustdesk(server: str, key: str, password: str | None) -> None:
    if server:
        run_rustdesk("--option", "custom-rendezvous-server", server)
    if key:
        run_rustdesk("--option", "key", key)
    if password:
        run_rustdesk("--password", password)
    if platform.system() == "Linux" and shutil.which("systemctl"):
        subprocess.run(["systemctl", "restart", "rustdesk"], check=False, timeout=30)


def metadata() -> dict[str, Any]:
    data: dict[str, Any] = {
        "python": platform.python_version(),
        "os_release": platform.release(),
        "os_version": platform.version()[:200],
    }
    boot_id = Path("/proc/sys/kernel/random/boot_id")
    if boot_id.exists():
        data["boot_id"] = boot_id.read_text().strip()
    try:
        data["local_ip"] = socket.gethostbyname(socket.gethostname())
    except OSError:
        pass
    return data


def payload(rustdesk_id: str) -> dict[str, Any]:
    return {
        "rustdesk_id": rustdesk_id,
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "architecture": platform.machine(),
        "agent_version": VERSION,
        "rustdesk_version": rustdesk_version(),
        "metadata": metadata(),
    }


def save_config(path: Path, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def load_config(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Agent is not enrolled; config missing at {path}") from exc


def enroll(args: argparse.Namespace) -> None:
    base_url = args.url.rstrip("/")
    permanent_password = args.password or random_password()
    public = request_json(f"{base_url}/api/v1/config/public")
    configure_rustdesk(public.get("rustdesk_server", ""), public.get("rustdesk_key", ""), permanent_password)
    rustdesk_id = detect_rustdesk_id(args.rustdesk_id)
    body = payload(rustdesk_id)
    body.update({"enrollment_token": args.token, "alias": args.alias or socket.gethostname()})
    result = request_json(f"{base_url}/api/v1/agents/enroll", method="POST", body=body)
    config = {
        "base_url": base_url,
        "device_id": result["device_id"],
        "agent_token": result["agent_token"],
        "rustdesk_id": rustdesk_id,
        "heartbeat_interval_seconds": result.get("heartbeat_interval_seconds", 30),
    }
    save_config(args.config, config)
    log(f"Enrolled device {rustdesk_id} as {config['device_id']}")
    print("\nRustDesk permanent password (store it in your password manager):")
    print(permanent_password)
    print()


def heartbeat_once(config_path: Path) -> None:
    config = load_config(config_path)
    request_json(
        f"{config['base_url']}/api/v1/agents/heartbeat",
        method="POST",
        body=payload(config["rustdesk_id"]),
        token=config["agent_token"],
    )


def run_loop(config_path: Path) -> None:
    config = load_config(config_path)
    interval = max(15, int(config.get("heartbeat_interval_seconds", 30)))
    failures = 0
    log(f"Starting heartbeat loop every {interval}s")
    while True:
        try:
            heartbeat_once(config_path)
            failures = 0
            time.sleep(interval)
        except KeyboardInterrupt:
            return
        except Exception as exc:
            failures += 1
            delay = min(300, max(interval, 2 ** min(failures, 8)))
            log(f"Heartbeat failed: {exc}; retrying in {delay}s")
            time.sleep(delay)


def replace_token(config_path: Path, token: str) -> None:
    config = load_config(config_path)
    config["agent_token"] = token
    save_config(config_path, config)
    log("Agent credential updated")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Sarmiento device agent")
    root.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    sub = root.add_subparsers(dest="command", required=True)
    enroll_cmd = sub.add_parser("enroll")
    enroll_cmd.add_argument("--url", required=True)
    enroll_cmd.add_argument("--token", required=True)
    enroll_cmd.add_argument("--alias")
    enroll_cmd.add_argument("--rustdesk-id")
    enroll_cmd.add_argument("--password")
    sub.add_parser("once")
    sub.add_parser("run")
    replace = sub.add_parser("replace-token")
    replace.add_argument("token")
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "enroll":
            enroll(args)
        elif args.command == "once":
            heartbeat_once(args.config)
        elif args.command == "run":
            run_loop(args.config)
        elif args.command == "replace-token":
            replace_token(args.config, args.token)
        return 0
    except Exception as exc:
        log(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
