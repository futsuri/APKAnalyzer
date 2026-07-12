#!/usr/bin/env bash
# Запуск APK Analyzer через Docker.
#
# Usage:
#   ./run_analyzer.sh /path/to/app.apk                         # статика (по умолчанию)
#   ./run_analyzer.sh /path/to/app.apk --mode dynamic \
#       --package com.example                                  # динамика
#   ./run_analyzer.sh /path/to/app.apk --mode full \
#       --package com.example                                  # оба режима
#
# Опции после APK пробрасываются в main.py как есть (--mode/--package/--debug).

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: ./run_analyzer.sh /path/to/file.apk [--mode static|dynamic|full] [--package <pkg>] [--emulator-host <host>]"
  exit 1
fi

APK_FILE="$1"
shift
EXTRA_ARGS=("$@")

if command -v realpath >/dev/null 2>&1; then
  APK_FILE="$(realpath "$APK_FILE")"
else
  APK_FILE="$(cd "$(dirname "$APK_FILE")" && pwd)/$(basename "$APK_FILE")"
fi

if [[ ! -f "$APK_FILE" ]]; then
  echo "APK file not found: $APK_FILE"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$SCRIPT_DIR/data"
APK_DIR="$(dirname "$APK_FILE")"
APK_NAME="$(basename "$APK_FILE")"

mkdir -p "$DATA_DIR"

# Определяем режим: выбираем Dockerfile по --mode (default: static)
MODE="static"
for ((i=0; i<${#EXTRA_ARGS[@]}; i++)); do
  if [[ "${EXTRA_ARGS[$i]}" == "--mode" ]] && [[ $((i+1)) -lt ${#EXTRA_ARGS[@]} ]]; then
    MODE="${EXTRA_ARGS[$((i+1))]}"
    break
  fi
done

if [[ "$MODE" == "static" ]]; then
  IMAGE_TAG="apk-analyzer-static"
  DOCKERFILE="Dockerfile.static"
elif [[ "$MODE" == "dynamic" || "$MODE" == "full" ]]; then
  IMAGE_TAG="apk-analyzer-dynamic"
  DOCKERFILE="Dockerfile.dynamic"
else
  echo "Unknown mode: $MODE"
  exit 1
fi

echo "Building image: $IMAGE_TAG (Dockerfile: $DOCKERFILE)"
docker build -t "$IMAGE_TAG" -f "$SCRIPT_DIR/$DOCKERFILE" "$SCRIPT_DIR"

docker run --rm \
  -v "$DATA_DIR:/app/data" \
  -v "$APK_DIR:/app/input:ro" \
  -e EMULATOR_HOST="${EMULATOR_HOST:-android-emulator}" \
  "$IMAGE_TAG" "/app/input/$APK_NAME" "${EXTRA_ARGS[@]}"
