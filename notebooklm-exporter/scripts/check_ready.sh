#!/usr/bin/env bash
set -euo pipefail

if ! command -v notebooklm >/dev/null 2>&1; then
  cat <<'EOF'
notebooklm CLI was not found.

Install it with:
  pip install "notebooklm-py[browser]"
  playwright install chromium

Then authenticate once with:
  notebooklm login
EOF
  exit 1
fi

echo "Found notebooklm: $(command -v notebooklm)"

TMP_OUTPUT="$(mktemp)"
trap 'rm -f "$TMP_OUTPUT"' EXIT

notebooklm auth check --test >"$TMP_OUTPUT" 2>&1 || true
cat "$TMP_OUTPUT"

if grep -q "✗ fail" "$TMP_OUTPUT" || grep -q "^Error:" "$TMP_OUTPUT"; then
  cat <<'EOF'
NotebookLM authentication is not ready.

Run:
  notebooklm login

Then retry this script.
EOF
  exit 1
fi

echo "NotebookLM authentication looks ready."
exit 0
