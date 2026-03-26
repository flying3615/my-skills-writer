#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ARTIFACT=""
NOTEBOOK=""
OUTPUT=""
OUTPUT_DIR=""
ARTIFACT_ID=""
NAME_FILTER=""
DOWNLOAD_FORMAT=""
ALL_ARTIFACTS="false"
ALL_MEDIA="false"
LATEST="false"
EARLIEST="false"
DRY_RUN="false"
FORCE="false"
NO_CLOBBER="false"

usage() {
  cat <<'EOF'
Usage:
  download_artifact.sh --artifact <type> --notebook <id> [options]
  download_artifact.sh --all-media --notebook <id> --output-dir <dir>

Options:
  --artifact <audio|video|cinematic-video|slide-deck|quiz|flashcards|infographic|data-table|mind-map|report>
  --notebook <id>             Full notebook UUID is recommended
  --artifact-id <id>          Download by artifact ID
  --name <text>               Fuzzy-match artifact title
  --output <path>             Target file path
  --output-dir <dir>          Target directory for --all or --all-media
  --all                       Download all matching artifacts
  --all-media                 Download latest audio/video/infographic into output dir
  --latest                    Download latest artifact
  --earliest                  Download earliest artifact
  --format <fmt>              slide-deck: pdf|pptx; quiz/flashcards: json|markdown|html
  --dry-run                   Preview without downloading
  --force                     Overwrite existing files
  --no-clobber                Skip existing files
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
    --artifact-id)
      ARTIFACT_ID="${2:-}"
      shift 2
      ;;
    --name)
      NAME_FILTER="${2:-}"
      shift 2
      ;;
    --output)
      OUTPUT="${2:-}"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    --all)
      ALL_ARTIFACTS="true"
      shift
      ;;
    --all-media)
      ALL_MEDIA="true"
      shift
      ;;
    --latest)
      LATEST="true"
      shift
      ;;
    --earliest)
      EARLIEST="true"
      shift
      ;;
    --format)
      DOWNLOAD_FORMAT="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN="true"
      shift
      ;;
    --force)
      FORCE="true"
      shift
      ;;
    --no-clobber)
      NO_CLOBBER="true"
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

if [[ -z "$NOTEBOOK" ]]; then
  echo "--notebook is required" >&2
  exit 1
fi

download_one() {
  local artifact="$1"
  shift
  local args=(download "$artifact" -n "$NOTEBOOK")
  while [[ $# -gt 0 ]]; do
    args+=("$1")
    shift
  done
  notebooklm "${args[@]}"
}

if [[ "$ALL_MEDIA" == "true" ]]; then
  if [[ -z "$OUTPUT_DIR" ]]; then
    echo "--output-dir is required with --all-media" >&2
    exit 1
  fi

  mkdir -p "$OUTPUT_DIR"

  if ! download_one audio "$OUTPUT_DIR/audio.mp3"; then
    echo "Audio download skipped or failed." >&2
  fi
  if ! download_one video "$OUTPUT_DIR/video.mp4"; then
    echo "Video download skipped or failed." >&2
  fi
  if ! download_one infographic "$OUTPUT_DIR/infographic.png"; then
    echo "Infographic download skipped or failed." >&2
  fi

  echo "Batch download finished in $OUTPUT_DIR"
  exit 0
fi

if [[ -z "$ARTIFACT" ]]; then
  echo "--artifact is required unless --all-media is used" >&2
  exit 1
fi

ARGS=()

if [[ -n "$ARTIFACT_ID" ]]; then
  ARGS+=(-a "$ARTIFACT_ID")
fi
if [[ -n "$NAME_FILTER" ]]; then
  ARGS+=(--name "$NAME_FILTER")
fi
if [[ "$ALL_ARTIFACTS" == "true" ]]; then
  ARGS+=(--all)
elif [[ "$EARLIEST" == "true" ]]; then
  ARGS+=(--earliest)
else
  if [[ "$LATEST" == "true" ]]; then
    ARGS+=(--latest)
  fi
fi
if [[ "$DRY_RUN" == "true" ]]; then
  ARGS+=(--dry-run)
fi
if [[ "$FORCE" == "true" ]]; then
  ARGS+=(--force)
fi
if [[ "$NO_CLOBBER" == "true" ]]; then
  ARGS+=(--no-clobber)
fi

case "$ARTIFACT" in
  slide-deck)
    if [[ -n "$DOWNLOAD_FORMAT" ]]; then
      ARGS+=(--format "$DOWNLOAD_FORMAT")
    fi
    ;;
  quiz|flashcards)
    if [[ -n "$DOWNLOAD_FORMAT" ]]; then
      ARGS+=(--format "$DOWNLOAD_FORMAT")
    fi
    ;;
esac

TARGET_PATH=""
if [[ -n "$OUTPUT" ]]; then
  mkdir -p "$(dirname "$OUTPUT")"
  TARGET_PATH="$OUTPUT"
elif [[ -n "$OUTPUT_DIR" ]]; then
  mkdir -p "$OUTPUT_DIR"
  TARGET_PATH="$OUTPUT_DIR"
fi

if [[ -n "$TARGET_PATH" ]]; then
  ARGS+=("$TARGET_PATH")
fi

download_one "$ARTIFACT" "${ARGS[@]}"

if [[ -n "$TARGET_PATH" && "$DRY_RUN" != "true" ]]; then
  echo "Saved $ARTIFACT to $TARGET_PATH"
fi
