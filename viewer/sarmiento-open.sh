#!/usr/bin/env bash
set -Eeuo pipefail
uri="${1:-}"
id="${uri#sarmiento://connect/}"
[[ "$uri" == sarmiento://connect/* && "$id" =~ ^[A-Za-z0-9_-]{3,64}$ ]] || { echo "Invalid Sarmiento URI" >&2; exit 2; }
rustdesk="$(command -v rustdesk || true)"
[[ -n "$rustdesk" ]] || { echo "RustDesk is not installed" >&2; exit 1; }
exec "$rustdesk" --connect "$id"
