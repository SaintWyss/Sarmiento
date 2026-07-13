#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo "Run with sudo."; exit 1; }
command -v rustdesk >/dev/null || { echo "Install RustDesk first."; exit 1; }
base_url="${1:-}"
install -d -m 0755 /opt/sarmiento-viewer
if [[ -n "$base_url" ]]; then
  curl -fsSL "${base_url%/}/viewer/sarmiento-open.sh" -o /opt/sarmiento-viewer/sarmiento-open.sh
else
  install -m 0755 "$(dirname "$0")/sarmiento-open.sh" /opt/sarmiento-viewer/sarmiento-open.sh
fi
chmod 0755 /opt/sarmiento-viewer/sarmiento-open.sh
cat > /usr/share/applications/sarmiento-viewer.desktop <<'EOF'
[Desktop Entry]
Name=Sarmiento Viewer
Comment=Open a Sarmiento remote connection in RustDesk
Exec=/opt/sarmiento-viewer/sarmiento-open.sh %u
Terminal=false
Type=Application
NoDisplay=true
MimeType=x-scheme-handler/sarmiento;
EOF
command -v update-desktop-database >/dev/null && update-desktop-database /usr/share/applications || true
xdg-mime default sarmiento-viewer.desktop x-scheme-handler/sarmiento 2>/dev/null || true
echo "Registered sarmiento:// URL handler."
