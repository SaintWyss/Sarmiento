#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import os
import secrets
from pathlib import Path
from urllib.parse import quote_plus, urlparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate infra/.env for Sarmiento")
    parser.add_argument("--site-address", default="http://localhost")
    parser.add_argument("--rustdesk-server", default="localhost")
    parser.add_argument("--owner", default="owner")
    parser.add_argument("--owner-password")
    parser.add_argument("--output", type=Path, default=Path("infra/.env"))
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists() and not args.force:
        raise SystemExit(f"{args.output} already exists; use --force to replace it")
    generated_password = False
    password = args.owner_password
    if not password and os.isatty(0):
        password = getpass.getpass("Owner password (minimum 12 characters): ")
        confirmation = getpass.getpass("Repeat owner password: ")
        if password != confirmation:
            raise SystemExit("Passwords do not match")
    if not password:
        password = secrets.token_urlsafe(22)
        generated_password = True
    if len(password) < 12:
        raise SystemExit("Owner password must contain at least 12 characters")

    db_password = secrets.token_urlsafe(28)
    session_secret = secrets.token_urlsafe(48)
    token_pepper = secrets.token_urlsafe(48)
    site = args.site_address.rstrip("/")
    parsed = urlparse(site if "://" in site else f"https://{site}")
    hostname = parsed.hostname or "localhost"
    secure = parsed.scheme == "https"
    database_url = (
        f"postgresql+psycopg://sarmiento:{quote_plus(db_password)}@db:5432/sarmiento"
    )
    values = {
        "POSTGRES_PASSWORD": db_password,
        "SARMIENTO_DATABASE_URL": database_url,
        "SARMIENTO_ENVIRONMENT": "production",
        "SARMIENTO_OWNER_USERNAME": args.owner,
        "SARMIENTO_OWNER_PASSWORD": password,
        "SARMIENTO_SESSION_SECRET": session_secret,
        "SARMIENTO_TOKEN_PEPPER": token_pepper,
        "SARMIENTO_SITE_ADDRESS": site,
        "SARMIENTO_PUBLIC_BASE_URL": site,
        "SARMIENTO_COOKIE_SECURE": str(secure).lower(),
        "SARMIENTO_ALLOWED_ORIGINS": site,
        "SARMIENTO_ALLOWED_HOSTS": f"{hostname},localhost,127.0.0.1",
        "SARMIENTO_RUSTDESK_SERVER": args.rustdesk_server,
        "SARMIENTO_LOGIN_LOCKOUT_ATTEMPTS": "5",
        "SARMIENTO_LOGIN_LOCKOUT_MINUTES": "15",
        "SARMIENTO_MAX_REQUEST_BODY_BYTES": "65536",
        "SARMIENTO_MAX_RATE_LIMIT_BUCKETS": "10000",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
    os.chmod(args.output, 0o600)
    print(f"Created {args.output} with mode 0600")
    if generated_password:
        print("Generated owner password (store it now):")
        print(password)
    print(
        "After the owner exists and you changed the password in the panel, "
        "you may blank SARMIENTO_OWNER_PASSWORD in infra/.env."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
