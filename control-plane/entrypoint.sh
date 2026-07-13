#!/bin/sh
set -eu
alembic upgrade head
exec uvicorn sarmiento.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="${SARMIENTO_FORWARDED_ALLOW_IPS:-127.0.0.1}"
