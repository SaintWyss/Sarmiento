#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-$ROOT/backups/$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$DEST"
cd "$ROOT/infra"
docker compose exec -T db pg_dump -U sarmiento -d sarmiento --format=custom > "$DEST/postgres.dump"
docker run --rm -v sarmiento-rustdesk-data:/data:ro -v "$DEST:/backup" alpine:3.20 sh -c 'tar czf /backup/rustdesk-data.tar.gz -C /data .'
cp .env "$DEST/infra.env"
chmod 600 "$DEST/infra.env"
sha256sum "$DEST"/* > "$DEST/SHA256SUMS"
echo "Backup created at $DEST"
echo "Protect this directory: it contains application secrets and RustDesk server keys."
