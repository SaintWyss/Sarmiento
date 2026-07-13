#!/usr/bin/env bash
set -Eeuo pipefail

readonly test_dir="$(mktemp -d)"
trap 'rm -rf "$test_dir"' EXIT
readonly bin_dir="$test_dir/bin"
readonly calls="$test_dir/calls"
mkdir -p "$bin_dir" "$test_dir/runtime"
: > "$calls"

cat > "$bin_dir/rustdesk" <<'EOF'
#!/usr/bin/env bash
printf 'rustdesk %s\n' "$*" >> "$CALLS"
EOF

cat > "$bin_dir/notify-send" <<'EOF'
#!/usr/bin/env bash
printf 'notify %s\n' "$*" >> "$CALLS"
EOF

cat > "$bin_dir/systemctl" <<'EOF'
#!/usr/bin/env bash
printf 'systemctl %s\n' "$*" >> "$CALLS"
case "$*" in
  "--user cat deskflow-server.service") exit 0 ;;
  "--user is-active --quiet deskflow-server.service") exit 0 ;;
  "--user is-active deskflow-server.service") printf 'active\n'; exit 0 ;;
  "is-active --quiet rustdesk") exit 0 ;;
  "--user stop deskflow-server.service") exit 0 ;;
  "--user start deskflow-server.service") exit 0 ;;
esac
exit 1
EOF

chmod +x "$bin_dir"/*
export PATH="$bin_dir:$PATH"
export CALLS="$calls"
export XDG_RUNTIME_DIR="$test_dir/runtime"

wait_for_call() {
  local expected="$1"
  local attempt
  for attempt in {1..40}; do
    grep -Fxq "$expected" "$calls" && return 0
    sleep 0.025
  done
  echo "timed out waiting for: $expected" >&2
  return 1
}

if bash viewer/sarmiento-open.sh 'https://invalid.example' 2>/dev/null; then
  echo "invalid URI unexpectedly succeeded" >&2
  exit 1
else
  [[ $? -eq 2 ]]
fi

bash viewer/sarmiento-open.sh 'sarmiento://connect/123456789'
wait_for_call 'rustdesk --connect 123456789'

: > "$calls"
bash viewer/sarmiento-workstation.sh notebook 123456789
wait_for_call 'systemctl --user stop deskflow-server.service'
wait_for_call 'rustdesk --connect 123456789'

: > "$calls"
bash viewer/sarmiento-workstation.sh normal
wait_for_call 'systemctl --user start deskflow-server.service'

status="$(bash viewer/sarmiento-workstation.sh status)"
grep -Fx 'mode=integrated' <<<"$status"
grep -Fx 'deskflow=active' <<<"$status"
grep -Fx 'rustdesk=active' <<<"$status"

echo "viewer tests passed"
