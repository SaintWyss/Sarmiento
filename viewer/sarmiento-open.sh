#!/usr/bin/env bash
set -Eeuo pipefail

readonly uri="${1:-}"
readonly workstation_default="/opt/sarmiento-viewer/sarmiento-workstation.sh"

fail() {
  printf '%s\n' "$1" >&2
  exit "${2:-1}"
}

valid_id() {
  [[ "$1" =~ ^[A-Za-z0-9_-]{3,64}$ ]]
}

workstation_command() {
  if [[ -x "$workstation_default" ]]; then
    printf '%s\n' "$workstation_default"
    return
  fi
  command -v sarmiento-workstation || true
}

case "$uri" in
  sarmiento://connect/*)
    id="${uri#sarmiento://connect/}"
    valid_id "$id" || fail "Invalid Sarmiento device ID" 2
    rustdesk="$(command -v rustdesk || true)"
    [[ -n "$rustdesk" ]] || fail "RustDesk is not installed"
    exec "$rustdesk" --connect "$id"
    ;;
  sarmiento://workstation/normal)
    workstation="$(workstation_command)"
    [[ -n "$workstation" ]] || fail "Sarmiento Workstation is not installed"
    exec "$workstation" normal
    ;;
  sarmiento://workstation/notebook/*)
    id="${uri#sarmiento://workstation/notebook/}"
    valid_id "$id" || fail "Invalid Sarmiento device ID" 2
    workstation="$(workstation_command)"
    [[ -n "$workstation" ]] || fail "Sarmiento Workstation is not installed"
    exec "$workstation" notebook "$id"
    ;;
  sarmiento://workstation/status)
    workstation="$(workstation_command)"
    [[ -n "$workstation" ]] || fail "Sarmiento Workstation is not installed"
    exec "$workstation" status
    ;;
  *)
    fail "Invalid Sarmiento URI" 2
    ;;
esac
