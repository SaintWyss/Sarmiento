#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/sarmiento-desktop"
APP_IMAGE="$APP_DIR/Sarmiento.AppImage"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$DESKTOP_DIR/ar.saintwyss.sarmiento.desktop"

uninstall() {
  rm -f "$APP_IMAGE" "$DESKTOP_FILE"
  rmdir "$APP_DIR" 2>/dev/null || true
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
  fi
  echo "Sarmiento Desktop fue eliminado. Deskflow, RustDesk y el agente no se modificaron."
}

if [[ "${1:-}" == "--uninstall" ]]; then
  uninstall
  exit 0
fi

SOURCE="${1:-}"
if [[ -z "$SOURCE" ]]; then
  shopt -s nullglob
  candidates=(src-tauri/target/release/bundle/appimage/*.AppImage)
  shopt -u nullglob
  if [[ ${#candidates[@]} -ne 1 ]]; then
    echo "Uso: $0 /ruta/Sarmiento.AppImage" >&2
    echo "También podés ejecutarlo desde desktop/ después de npm run desktop:build." >&2
    exit 2
  fi
  SOURCE="${candidates[0]}"
fi

if [[ ! -f "$SOURCE" ]]; then
  echo "No existe el AppImage: $SOURCE" >&2
  exit 2
fi

install -Dm755 "$SOURCE" "$APP_IMAGE"
install -d -m755 "$DESKTOP_DIR"

cat >"$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Sarmiento
Comment=Controlá tus equipos, pantallas y sesiones remotas
Exec=$APP_IMAGE %U
Icon=ar.saintwyss.sarmiento
Terminal=false
Categories=Network;RemoteAccess;Utility;
MimeType=x-scheme-handler/sarmiento;
StartupNotify=true
StartupWMClass=Sarmiento
EOF

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi
if command -v xdg-mime >/dev/null 2>&1; then
  xdg-mime default ar.saintwyss.sarmiento.desktop x-scheme-handler/sarmiento
fi

echo "Sarmiento Desktop instalado en $APP_IMAGE"
echo "Abrilo desde el menú de KDE. No hace falta usar la terminal para operarlo."

