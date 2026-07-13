#!/usr/bin/env bash
set -Eeuo pipefail
URL="${1:-http://localhost}"
curl -fsS "$URL/healthz" | grep -q '"status":"ok"'
curl -fsS "$URL/readyz" | grep -q '"status":"ready"'
curl -fsS "$URL/api/v1/config/public" | grep -q '"product":"Sarmiento"'
echo "Sarmiento smoke test passed at $URL"
