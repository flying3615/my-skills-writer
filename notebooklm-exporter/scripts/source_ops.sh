#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ACTION="${1:-}"
if [[ $# -gt 0 ]]; then
  shift
fi

NOTEBOOK=""
SOURCE_ID=""
CONTENT=""
QUERY=""
TITLE=""
NEW_TITLE=""
TYPE=""
MIME_TYPE=""
SEARCH_FROM="web"
MODE="fast"
IMPORT_ALL="false"
NO_WAIT="false"
OUTPUT=""
JSON="false"
YES="false"

usage() {
  cat <<'EOF'
Usage:
  source_ops.sh list --notebook <id> [--json]
  source_ops.sh get --notebook <id> --source <source-id>
  source_ops.sh guide --notebook <id> --source <source-id> [--json]
  source_ops.sh fulltext --notebook <id> --source <source-id> [--output <path>] [--json]
  source_ops.sh add --notebook <id> --content <url|file|text> [--type url|text|file|youtube] [--title <title>] [--mime-type <mime>]
  source_ops.sh research --notebook <id> --query <text> [--from web|drive] [--mode fast|deep] [--import-all] [--no-wait]
  source_ops.sh refresh --notebook <id> --source <source-id>
  source_ops.sh rename --notebook <id> --source <source-id> --new-title <title>
  source_ops.sh delete --notebook <id> --source <source-id> [--yes]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --notebook)
      NOTEBOOK="${2:-}"
      shift 2
      ;;
    --source)
      SOURCE_ID="${2:-}"
      shift 2
      ;;
    --content)
      CONTENT="${2:-}"
      shift 2
      ;;
    --query)
      QUERY="${2:-}"
      shift 2
      ;;
    --title)
      TITLE="${2:-}"
      shift 2
      ;;
    --new-title)
      NEW_TITLE="${2:-}"
      shift 2
      ;;
    --type)
      TYPE="${2:-}"
      shift 2
      ;;
    --mime-type)
      MIME_TYPE="${2:-}"
      shift 2
      ;;
    --from)
      SEARCH_FROM="${2:-}"
      shift 2
      ;;
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --import-all)
      IMPORT_ALL="true"
      shift
      ;;
    --no-wait)
      NO_WAIT="true"
      shift
      ;;
    --output)
      OUTPUT="${2:-}"
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

require_source() {
  if [[ -z "$SOURCE_ID" ]]; then
    echo "--source is required" >&2
    exit 1
  fi
}

case "$ACTION" in
  list)
    require_notebook
    ARGS=(source list -n "$NOTEBOOK")
    if [[ "$JSON" == "true" ]]; then
      ARGS+=(--json)
    fi
    notebooklm "${ARGS[@]}"
    ;;
  get)
    require_notebook
    require_source
    notebooklm source get -n "$NOTEBOOK" "$SOURCE_ID"
    ;;
  guide)
    require_notebook
    require_source
    ARGS=(source guide -n "$NOTEBOOK" "$SOURCE_ID")
    if [[ "$JSON" == "true" ]]; then
      ARGS+=(--json)
    fi
    notebooklm "${ARGS[@]}"
    ;;
  fulltext)
    require_notebook
    require_source
    ARGS=(source fulltext -n "$NOTEBOOK" "$SOURCE_ID")
    if [[ -n "$OUTPUT" ]]; then
      mkdir -p "$(dirname "$OUTPUT")"
      ARGS+=(--output "$OUTPUT")
    fi
    if [[ "$JSON" == "true" ]]; then
      ARGS+=(--json)
    fi
    notebooklm "${ARGS[@]}"
    ;;
  add)
    require_notebook
    if [[ -z "$CONTENT" ]]; then
      echo "--content is required" >&2
      exit 1
    fi
    ARGS=(source add -n "$NOTEBOOK" "$CONTENT")
    if [[ -n "$TYPE" ]]; then
      ARGS+=(--type "$TYPE")
    fi
    if [[ -n "$TITLE" ]]; then
      ARGS+=(--title "$TITLE")
    fi
    if [[ -n "$MIME_TYPE" ]]; then
      ARGS+=(--mime-type "$MIME_TYPE")
    fi
    if [[ "$JSON" == "true" ]]; then
      ARGS+=(--json)
    fi
    notebooklm "${ARGS[@]}"
    ;;
  research)
    require_notebook
    if [[ -z "$QUERY" ]]; then
      echo "--query is required" >&2
      exit 1
    fi
    ARGS=(source add-research -n "$NOTEBOOK" "$QUERY" --from "$SEARCH_FROM" --mode "$MODE")
    if [[ "$IMPORT_ALL" == "true" ]]; then
      ARGS+=(--import-all)
    fi
    if [[ "$NO_WAIT" == "true" ]]; then
      ARGS+=(--no-wait)
    fi
    notebooklm "${ARGS[@]}"
    ;;
  refresh)
    require_notebook
    require_source
    notebooklm source refresh -n "$NOTEBOOK" "$SOURCE_ID"
    ;;
  rename)
    require_notebook
    require_source
    if [[ -z "$NEW_TITLE" ]]; then
      echo "--new-title is required" >&2
      exit 1
    fi
    notebooklm source rename -n "$NOTEBOOK" "$SOURCE_ID" "$NEW_TITLE"
    ;;
  delete)
    require_notebook
    require_source
    ARGS=(source delete -n "$NOTEBOOK" "$SOURCE_ID")
    if [[ "$YES" == "true" ]]; then
      ARGS+=(--yes)
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
