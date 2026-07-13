#!/usr/bin/env bash
set -Eeuo pipefail
URL=""; TOKEN=""; ALIAS="$(scutil --get ComputerName 2>/dev/null || hostname)"; PASSWORD=""; RUSTDESK_ID=""
usage(){ echo "Usage: sudo $0 --url https://control.example.com --token TOKEN [--alias NAME] [--password PASSWORD] [--rustdesk-id ID]"; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --url) URL="$2"; shift 2;; --token) TOKEN="$2"; shift 2;; --alias) ALIAS="$2"; shift 2;;
    --password) PASSWORD="$2"; shift 2;; --rustdesk-id) RUSTDESK_ID="$2"; shift 2;;
    -h|--help) usage; exit 0;; *) echo "Unknown argument: $1"; usage; exit 2;;
  esac
done
[[ -n "$URL" && -n "$TOKEN" ]] || { usage; exit 2; }
[[ $EUID -eq 0 ]] || { echo "Run with sudo."; exit 1; }
[[ -x /Applications/RustDesk.app/Contents/MacOS/RustDesk ]] || { echo "Install RustDesk in /Applications first."; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }
install -d -m 0755 /opt/sarmiento /etc/sarmiento
curl -fsSL "${URL%/}/agent/sarmiento_agent.py" -o /opt/sarmiento/sarmiento_agent.py
chmod 0755 /opt/sarmiento/sarmiento_agent.py
args=(--config /etc/sarmiento/agent.json enroll --url "$URL" --token "$TOKEN" --alias "$ALIAS")
[[ -n "$RUSTDESK_ID" ]] && args+=(--rustdesk-id "$RUSTDESK_ID")
[[ -n "$PASSWORD" ]] && args+=(--password "$PASSWORD")
PATH="/Applications/RustDesk.app/Contents/MacOS:$PATH" python3 /opt/sarmiento/sarmiento_agent.py "${args[@]}"
cat > /Library/LaunchDaemons/com.saintwyss.sarmiento.agent.plist <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.saintwyss.sarmiento.agent</string>
<key>ProgramArguments</key><array><string>/usr/bin/python3</string><string>/opt/sarmiento/sarmiento_agent.py</string><string>--config</string><string>/etc/sarmiento/agent.json</string><string>run</string></array>
<key>EnvironmentVariables</key><dict><key>PATH</key><string>/Applications/RustDesk.app/Contents/MacOS:/usr/local/bin:/usr/bin:/bin</string></dict>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
<key>StandardOutPath</key><string>/var/log/sarmiento-agent.log</string>
<key>StandardErrorPath</key><string>/var/log/sarmiento-agent.log</string>
</dict></plist>
PLIST
launchctl bootout system/com.saintwyss.sarmiento.agent 2>/dev/null || true
launchctl bootstrap system /Library/LaunchDaemons/com.saintwyss.sarmiento.agent.plist
echo "Sarmiento agent installed. Grant RustDesk Screen Recording and Accessibility permissions in System Settings."
