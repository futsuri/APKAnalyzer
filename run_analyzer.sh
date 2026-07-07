#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: ./run_analyzer.sh /path/to/file.apk"
  exit 1
fi

APK_FILE="$(realpath "$1")"
if [[ ! -f "$APK_FILE" ]]; then
  echo "APK file not found: $APK_FILE"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$SCRIPT_DIR/data"
APK_DIR="$(dirname "$APK_FILE")"
APK_NAME="$(basename "$APK_FILE")"

mkdir -p "$DATA_DIR"

docker build -t apk-analyzer "$SCRIPT_DIR"
docker run --rm \
  -v "$DATA_DIR:/app/data" \
  -v "$APK_DIR:/app/input:ro" \
  apk-analyzer "/app/input/$APK_NAME"
