#!/usr/bin/env bash
set -Eeuo pipefail

[[ $EUID -eq 0 ]] || { echo "Run with sudo."; exit 1; }
command -v rustdesk >/dev/null || { echo "Install RustDesk first."; exit 1; }

readonly base_url="${1:-}"
readonly source_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
readonly install_dir="/opt/sarmiento-viewer"

if [[ -n "$base_url" && ! "$base_url" =~ ^https?://[A-Za-z0-9._:-]+$ ]]; then
  echo "Invalid Sarmiento URL." >&2
  exit 2
fi

install -d -m 0755 "$install_dir"
if [[ -n "$base_url" ]]; then
  curl -fsSL "${base_url%/}/viewer/sarmiento-open.sh" -o "$install_dir/sarmiento-open.sh"
  curl -fsSL "${base_url%/}/viewer/sarmiento-workstation.sh" -o "$install_dir/sarmiento-workstation.sh"
else
  install -m 0755 "$source_dir/sarmiento-open.sh" "$install_dir/sarmiento-open.sh"
  install -m 0755 "$source_dir/sarmiento-workstation.sh" "$install_dir/sarmiento-workstation.sh"
fi
chmod 0755 "$install_dir/sarmiento-open.sh" "$install_dir/sarmiento-workstation.sh"

cat > /usr/share/applications/sarmiento-viewer.desktop <<'EOF'
[Desktop Entry]
Name=Sarmiento Viewer
Comment=Control local para conexiones Sarmiento
Exec=/opt/sarmiento-viewer/sarmiento-open.sh %u
Terminal=false
Type=Application
NoDisplay=true
MimeType=x-scheme-handler/sarmiento;
Categories=Network;RemoteAccess;
EOF

if [[ -n "$base_url" ]]; then
  escaped_url="${base_url//%/%%}"
  cat > /usr/share/applications/sarmiento.desktop <<EOF
[Desktop Entry]
Name=Sarmiento
Comment=Controlá tus computadoras desde una sola interfaz
Exec=xdg-open $escaped_url
Terminal=false
Type=Application
Categories=Network;RemoteAccess;
StartupNotify=true
EOF
fi

command -v update-desktop-database >/dev/null && update-desktop-database /usr/share/applications || true

desktop_user="${SUDO_USER:-}"
if [[ -n "$desktop_user" && "$desktop_user" != root ]] && command -v runuser >/dev/null; then
  runuser -u "$desktop_user" -- xdg-mime default sarmiento-viewer.desktop x-scheme-handler/sarmiento 2>/dev/null || true
else
  xdg-mime default sarmiento-viewer.desktop x-scheme-handler/sarmiento 2>/dev/null || true
fi

echo "Installed the Sarmiento application and registered the sarmiento:// handler."
