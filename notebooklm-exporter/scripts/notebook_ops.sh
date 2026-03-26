#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ACTION="${1:-}"
if [[ $# -gt 0 ]]; then
  shift
fi

NOTEBOOK=""
JSON="false"
TOPICS="false"

usage() {
  cat <<'EOF'
Usage:
  notebook_ops.sh list
  notebook_ops.sh status
  notebook_ops.sh summary --notebook <id> [--topics]
  notebook_ops.sh metadata --notebook <id> [--json]

Notes:
  - Prefer the full notebook UUID. Prefix support can be inconsistent for shared notebooks.
  - status shows the current notebook context; other commands accept --notebook.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --notebook)
      NOTEBOOK="${2:-}"
      shift 2
      ;;
    --json)
      JSON="true"
      shift
      ;;
    --topics)
      TOPICS="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

"$SCRIPT_DIR/check_ready.sh" >/dev/null

case "$ACTION" in
  list)
    notebooklm list
    ;;
  status)
    notebooklm status
    ;;
  summary)
    if [[ -z "$NOTEBOOK" ]]; then
      echo "--notebook is required for summary" >&2
      exit 1
    fi
    ARGS=(summary -n "$NOTEBOOK")
    if [[ "$TOPICS" == "true" ]]; then
      ARGS+=(--topics)
    fi
    notebooklm "${ARGS[@]}"
    ;;
  metadata)
    if [[ -z "$NOTEBOOK" ]]; then
      echo "--notebook is required for metadata" >&2
      exit 1
    fi
    ARGS=(metadata -n "$NOTEBOOK")
    if [[ "$JSON" == "true" ]]; then
      ARGS+=(--json)
    fi
    notebooklm "${ARGS[@]}"
    ;;
  ""|-h|--help|help)
    usage
    ;;
  *)
    echo "Unknown action: $ACTION" >&2
    usage >&2
    exit 1
    ;;
esac
