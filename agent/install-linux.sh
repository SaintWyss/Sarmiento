#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="1.4.9"
URL=""
TOKEN=""
ALIAS="$(hostname)"
RUSTDESK_ID=""
PASSWORD=""
SKIP_RUSTDESK=0

usage(){ echo "Usage: $0 --url https://sarmiento.example --token TOKEN [--alias NAME] [--rustdesk-id ID] [--password PASSWORD] [--skip-rustdesk-install]"; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --url) URL="$2"; shift 2;;
    --token) TOKEN="$2"; shift 2;;
    --alias) ALIAS="$2"; shift 2;;
    --rustdesk-id) RUSTDESK_ID="$2"; shift 2;;
    --password) PASSWORD="$2"; shift 2;;
    --skip-rustdesk-install) SKIP_RUSTDESK=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown argument: $1"; usage; exit 2;;
  esac
done
[[ -n "$URL" && -n "$TOKEN" ]] || { usage; exit 2; }
[[ $EUID -eq 0 ]] || { echo "Run as root (sudo)."; exit 1; }
command -v curl >/dev/null || { echo "curl is required"; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }

install_rustdesk(){
  [[ $SKIP_RUSTDESK -eq 1 ]] && return 0
  command -v rustdesk >/dev/null && return 0
  . /etc/os-release
  arch="$(uname -m)"
  case "$arch" in x86_64|amd64) asset_arch="x86_64";; aarch64|arm64) asset_arch="aarch64";; *) echo "Unsupported architecture: $arch"; exit 1;; esac
  temp="$(mktemp -d)"; trap 'rm -rf "$temp"' EXIT
  if [[ "${ID:-}" =~ ^(ubuntu|debian|linuxmint|pop)$ || "${ID_LIKE:-}" == *debian* ]]; then
    asset="rustdesk-${VERSION}-${asset_arch}.deb"
    curl -fL "https://github.com/rustdesk/rustdesk/releases/download/${VERSION}/${asset}" -o "$temp/$asset"
    apt-get update -qq
    apt-get install -y "$temp/$asset"
  elif [[ "${ID:-}" =~ ^(fedora|rhel|centos|rocky|almalinux)$ || "${ID_LIKE:-}" == *rhel* ]]; then
    asset="rustdesk-${VERSION}-0.${asset_arch}.rpm"
    curl -fL "https://github.com/rustdesk/rustdesk/releases/download/${VERSION}/${asset}" -o "$temp/$asset"
    if command -v dnf >/dev/null; then dnf install -y "$temp/$asset"; else yum localinstall -y "$temp/$asset"; fi
  else
    echo "RustDesk is not installed and this distribution is not supported by the automatic installer."
    echo "Install RustDesk ${VERSION}, then rerun with --skip-rustdesk-install."
    exit 1
  fi
}

install_rustdesk
install -d -m 0755 /opt/sarmiento /etc/sarmiento
curl -fsSL "$URL/agent/sarmiento_agent.py" -o /opt/sarmiento/sarmiento_agent.py
chmod 0755 /opt/sarmiento/sarmiento_agent.py
curl -fsSL "$URL/agent/systemd/sarmiento-agent.service" -o /etc/systemd/system/sarmiento-agent.service

args=(--config /etc/sarmiento/agent.json enroll --url "$URL" --token "$TOKEN" --alias "$ALIAS")
[[ -n "$RUSTDESK_ID" ]] && args+=(--rustdesk-id "$RUSTDESK_ID")
[[ -n "$PASSWORD" ]] && args+=(--password "$PASSWORD")
python3 /opt/sarmiento/sarmiento_agent.py "${args[@]}"
systemctl daemon-reload
systemctl enable --now sarmiento-agent.service
systemctl --no-pager --full status sarmiento-agent.service || true
echo "Sarmiento agent installed."
