#!/usr/bin/env bash
set -Eeuo pipefail
[[ -d /Applications/RustDesk.app ]] || { echo "Install RustDesk in /Applications first."; exit 1; }
command -v osacompile >/dev/null || { echo "osacompile is required."; exit 1; }
APP="$HOME/Applications/Sarmiento Viewer.app"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
mkdir -p "$HOME/Applications"
cat > "$TMP/viewer.applescript" <<'APPLESCRIPT'
on open location theURL
  set prefixText to "sarmiento://connect/"
  if theURL does not start with prefixText then return
  set deviceId to text ((length of prefixText) + 1) thru -1 of theURL
  if deviceId contains "/" or deviceId contains ":" or deviceId contains " " then return
  do shell script "/Applications/RustDesk.app/Contents/MacOS/RustDesk --connect " & quoted form of deviceId & " >/dev/null 2>&1 &"
end open location
APPLESCRIPT
rm -rf "$APP"
osacompile -o "$APP" "$TMP/viewer.applescript"
PLIST="$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Add :CFBundleURLTypes array' "$PLIST"
/usr/libexec/PlistBuddy -c 'Add :CFBundleURLTypes:0 dict' "$PLIST"
/usr/libexec/PlistBuddy -c 'Add :CFBundleURLTypes:0:CFBundleURLName string Sarmiento' "$PLIST"
/usr/libexec/PlistBuddy -c 'Add :CFBundleURLTypes:0:CFBundleURLSchemes array' "$PLIST"
/usr/libexec/PlistBuddy -c 'Add :CFBundleURLTypes:0:CFBundleURLSchemes:0 string sarmiento' "$PLIST"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP"
echo "Registered sarmiento:// URL handler for this user."
