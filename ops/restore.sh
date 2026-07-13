#!/usr/bin/env bash
set -Eeuo pipefail
[[ $# -eq 1 ]] || { echo "Usage: $0 BACKUP_DIRECTORY"; exit 2; }
BACKUP="$(cd "$1" && pwd)"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$BACKUP/postgres.dump" && -f "$BACKUP/rustdesk-data.tar.gz" ]] || { echo "Invalid backup"; exit 1; }
cd "$BACKUP" && sha256sum -c SHA256SUMS
cd "$ROOT/infra"
docker compose up -d db
docker compose exec -T db dropdb -U sarmiento --if-exists sarmiento
docker compose exec -T db createdb -U sarmiento sarmiento
cat "$BACKUP/postgres.dump" | docker compose exec -T db pg_restore -U sarmiento -d sarmiento --clean --if-exists
docker run --rm -v sarmiento-rustdesk-data:/data -v "$BACKUP:/backup:ro" alpine:3.20 sh -c 'rm -rf /data/* && tar xzf /backup/rustdesk-data.tar.gz -C /data'
echo "Restore completed. Run: make up"
