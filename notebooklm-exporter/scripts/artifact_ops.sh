#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ACTION="${1:-}"
if [[ $# -gt 0 ]]; then
  shift
fi

NOTEBOOK=""
ARTIFACT_ID=""
TYPE=""
NEW_TITLE=""
EXPORT_TITLE=""
EXPORT_TYPE=""
TIMEOUT=""
INTERVAL=""
JSON="false"
YES="false"

usage() {
  cat <<'EOF'
Usage:
  artifact_ops.sh list --notebook <id> [--type <artifact-type>] [--json]
  artifact_ops.sh get --notebook <id> --artifact <artifact-id>
  artifact_ops.sh suggestions --notebook <id> [--json]
  artifact_ops.sh poll --notebook <id> --artifact <artifact-id>
  artifact_ops.sh wait --notebook <id> --artifact <artifact-id> [--timeout <seconds>] [--interval <seconds>]
  artifact_ops.sh rename --notebook <id> --artifact <artifact-id> --new-title <title>
  artifact_ops.sh delete --notebook <id> --artifact <artifact-id> [--yes]
  artifact_ops.sh export --notebook <id> --artifact <artifact-id> --title <title> --export-type docs|sheets
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --notebook)
      NOTEBOOK="${2:-}"
      shift 2
      ;;
    --artifact)
      ARTIFACT_ID="${2:-}"
      shift 2
      ;;
    --type)
      TYPE="${2:-}"
      shift 2
      ;;
    --new-title)
      NEW_TITLE="${2:-}"
      shift 2
      ;;
    --title)
      EXPORT_TITLE="${2:-}"
      shift 2
      ;;
    --export-type)
      EXPORT_TYPE="${2:-}"
      shift 2
      ;;
    --timeout)
      TIMEOUT="${2:-}"
      shift 2
      ;;
    --interval)
      INTERVAL="${2:-}"
      shift 2
      ;;
    --json)
      JSON="true"
      shift
      ;;
    --yes)
      YES="true"
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

if [[ "$ACTION" != "help" && "$ACTION" != "--help" && "$ACTION" != "-h" ]]; then
  "$SCRIPT_DIR/check_ready.sh" >/dev/null
fi

require_notebook() {
  if [[ -z "$NOTEBOOK" ]]; then
    echo "--notebook is required" >&2
    exit 1
  fi
}

require_artifact() {
  if [[ -z "$ARTIFACT_ID" ]]; then
    echo "--artifact is required" >&2
    exit 1
  fi
}

case "$ACTION" in
  list)
    require_notebook
    ARGS=(artifact list -n "$NOTEBOOK")
    if [[ -n "$TYPE" ]]; then
      ARGS+=(--type "$TYPE")
    fi
    if [[ "$JSON" == "true" ]]; then
      ARGS+=(--json)
    fi
    notebooklm "${ARGS[@]}"
    ;;
  get)
    require_notebook
    require_artifact
    notebooklm artifact get -n "$NOTEBOOK" "$ARTIFACT_ID"
    ;;
  suggestions)
    require_notebook
    ARGS=(artifact suggestions -n "$NOTEBOOK")
    if [[ "$JSON" == "true" ]]; then
      ARGS+=(--json)
    fi
    notebooklm "${ARGS[@]}"
    ;;
  poll)
    require_notebook
    require_artifact
    notebooklm artifact poll -n "$NOTEBOOK" "$ARTIFACT_ID"
    ;;
  wait)
    require_notebook
    require_artifact
    ARGS=(artifact wait -n "$NOTEBOOK" "$ARTIFACT_ID")
    if [[ -n "$TIMEOUT" ]]; then
      ARGS+=(--timeout "$TIMEOUT")
    fi
    if [[ -n "$INTERVAL" ]]; then
      ARGS+=(--interval "$INTERVAL")
    fi
    notebooklm "${ARGS[@]}"
    ;;
  rename)
    require_notebook
    require_artifact
    if [[ -z "$NEW_TITLE" ]]; then
      echo "--new-title is required" >&2
      exit 1
    fi
    notebooklm artifact rename -n "$NOTEBOOK" "$ARTIFACT_ID" "$NEW_TITLE"
    ;;
  delete)
    require_notebook
    require_artifact
    ARGS=(artifact delete -n "$NOTEBOOK" "$ARTIFACT_ID")
    if [[ "$YES" == "true" ]]; then
      ARGS+=(--yes)
    fi
    notebooklm "${ARGS[@]}"
    ;;
  export)
    require_notebook
    require_artifact
    if [[ -z "$EXPORT_TITLE" || -z "$EXPORT_TYPE" ]]; then
      echo "--title and --export-type are required" >&2
      exit 1
    fi
    notebooklm artifact export -n "$NOTEBOOK" "$ARTIFACT_ID" --title "$EXPORT_TITLE" --type "$EXPORT_TYPE"
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
