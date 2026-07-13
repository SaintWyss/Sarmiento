#!/usr/bin/env bash
set -Eeuo pipefail

readonly command_name="${1:-status}"
readonly device_id="${2:-}"
readonly runtime_dir="${XDG_RUNTIME_DIR:-/tmp}/sarmiento-workstation-${UID}"
readonly state_file="$runtime_dir/deskflow-was-active"
readonly preferred_unit="${SARMIENTO_DESKFLOW_UNIT:-deskflow-server.service}"

notify() {
  if command -v notify-send >/dev/null 2>&1; then
    notify-send --app-name=Sarmiento "Sarmiento" "$1" >/dev/null 2>&1 || true
  fi
}

valid_id() {
  [[ "$1" =~ ^[A-Za-z0-9_-]{3,64}$ ]]
}

unit_exists() {
  systemctl --user cat "$1" >/dev/null 2>&1
}

deskflow_unit() {
  if unit_exists "$preferred_unit"; then
    printf '%s\n' "$preferred_unit"
  elif unit_exists deskflow-client.service; then
    printf '%s\n' deskflow-client.service
  else
    printf '%s\n' "$preferred_unit"
  fi
}

enter_remote_mode() {
  local id="$1"
  local unit
  valid_id "$id" || { printf 'Invalid RustDesk ID\n' >&2; exit 2; }
  command -v rustdesk >/dev/null 2>&1 || { printf 'RustDesk is not installed\n' >&2; exit 1; }
  unit="$(deskflow_unit)"
  install -d -m 0700 "$runtime_dir"
  if systemctl --user is-active --quiet "$unit"; then
    printf '%s\n' "$unit" > "$state_file"
    systemctl --user stop "$unit"
  else
    : > "$state_file"
  fi
  notify "Modo remoto activo. Deskflow quedó pausado."
  rustdesk --connect "$id" >/dev/null 2>&1 &
}

enter_normal_mode() {
  local unit
  unit="$(deskflow_unit)"
  if unit_exists "$unit"; then
    systemctl --user start "$unit"
    notify "Modo integrado activo. Deskflow está disponible."
  else
    printf 'Deskflow user service was not found\n' >&2
    exit 1
  fi
  rm -f "$state_file"
}

show_status() {
  local unit deskflow rustdesk_state mode
  unit="$(deskflow_unit)"
  deskflow="$(systemctl --user is-active "$unit" 2>/dev/null || true)"
  if systemctl is-active --quiet rustdesk 2>/dev/null || pgrep -x rustdesk >/dev/null 2>&1; then
    rustdesk_state=active
  else
    rustdesk_state=inactive
  fi
  mode=remote
  [[ "$deskflow" == active ]] && mode=integrated
  printf 'mode=%s\ndeskflow_unit=%s\ndeskflow=%s\nrustdesk=%s\n' \
    "$mode" "$unit" "${deskflow:-unknown}" "${rustdesk_state:-unknown}"
}

case "$command_name" in
  normal) enter_normal_mode ;;
  notebook) enter_remote_mode "$device_id" ;;
  status) show_status ;;
  *)
    printf 'Usage: sarmiento-workstation {normal|notebook DEVICE_ID|status}\n' >&2
    exit 2
    ;;
esac
