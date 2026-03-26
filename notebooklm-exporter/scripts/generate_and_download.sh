#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ARTIFACT=""
NOTEBOOK=""
DESCRIPTION=""
OUTPUT=""
LANGUAGE=""
WAIT="true"
DOWNLOAD_FORMAT=""
REPORT_FORMAT=""
APPEND_TEXT=""
SOURCE_IDS=()

usage() {
  cat <<'EOF'
Usage:
  generate_and_download.sh --artifact <type> --notebook <id> [options]

Options:
  --artifact <audio|video|cinematic-video|slide-deck|quiz|flashcards|infographic|data-table|mind-map|report>
  --notebook <id>             Full notebook UUID is recommended
  --description <text>        Natural-language generation prompt
  --source <source-id>        Limit generation to one source; repeatable
  --language <lang>           Language code
  --report-format <format>    briefing-doc|study-guide|blog-post|custom
  --append <text>             Extra instructions for built-in report formats
  --format <fmt>              Download format for slide-deck/quiz/flashcards
  --output <path>             If set, download after generation
  --no-wait                   Start generation without waiting

Examples:
  generate_and_download.sh --artifact video --notebook 750a23df-fd98-4954-b9c4-71f16c3ee937 --description "make it concise" --output ./out/video.mp4
  generate_and_download.sh --artifact report --notebook 750a23df-fd98-4954-b9c4-71f16c3ee937 --report-format study-guide --append "for beginners" --output ./out/report.md
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --artifact)
      ARTIFACT="${2:-}"
      shift 2
      ;;
    --notebook)
      NOTEBOOK="${2:-}"
      shift 2
      ;;
    --description)
      DESCRIPTION="${2:-}"
      shift 2
      ;;
    --source)
      SOURCE_IDS+=("${2:-}")
      shift 2
      ;;
    --language)
      LANGUAGE="${2:-}"
      shift 2
      ;;
    --report-format)
      REPORT_FORMAT="${2:-}"
      shift 2
      ;;
    --append)
      APPEND_TEXT="${2:-}"
      shift 2
      ;;
    --format)
      DOWNLOAD_FORMAT="${2:-}"
      shift 2
      ;;
    --output)
      OUTPUT="${2:-}"
      shift 2
      ;;
    --no-wait)
      WAIT="false"
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

if [[ -z "$ARTIFACT" || -z "$NOTEBOOK" ]]; then
  usage >&2
  exit 1
fi

"$SCRIPT_DIR/check_ready.sh" >/dev/null

ARGS=(generate "$ARTIFACT" -n "$NOTEBOOK")

if [[ -n "$DESCRIPTION" ]]; then
  ARGS+=("$DESCRIPTION")
fi
if [[ -n "$LANGUAGE" ]]; then
  ARGS+=(--language "$LANGUAGE")
fi
for source_id in "${SOURCE_IDS[@]}"; do
  ARGS+=(-s "$source_id")
done
if [[ "$WAIT" == "true" ]]; then
  ARGS+=(--wait)
fi

if [[ "$ARTIFACT" == "report" ]]; then
  if [[ -n "$REPORT_FORMAT" ]]; then
    ARGS+=(--format "$REPORT_FORMAT")
  fi
  if [[ -n "$APPEND_TEXT" ]]; then
    ARGS+=(--append "$APPEND_TEXT")
  fi
fi

echo "Generating $ARTIFACT in notebook $NOTEBOOK..."
notebooklm "${ARGS[@]}"

if [[ -z "$OUTPUT" ]]; then
  echo "Generation started. No download path provided."
  exit 0
fi

mkdir -p "$(dirname "$OUTPUT")"

DOWNLOAD_ARGS=(download "$ARTIFACT" -n "$NOTEBOOK")

case "$ARTIFACT" in
  slide-deck)
    if [[ -n "$DOWNLOAD_FORMAT" ]]; then
      DOWNLOAD_ARGS+=(--format "$DOWNLOAD_FORMAT")
    fi
    ;;
  quiz|flashcards)
    if [[ -n "$DOWNLOAD_FORMAT" ]]; then
      DOWNLOAD_ARGS+=(--format "$DOWNLOAD_FORMAT")
    fi
    ;;
esac

DOWNLOAD_ARGS+=("$OUTPUT")

echo "Downloading $ARTIFACT to $OUTPUT..."
notebooklm "${DOWNLOAD_ARGS[@]}"
echo "Saved $ARTIFACT to $OUTPUT"
