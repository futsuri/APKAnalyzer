#!/bin/bash
if [ -z "$1" ]; then
    echo "Usage: ./run_analyzer.sh <path_to_apk> [additional_arguments]"
    echo "Example: ./run_analyzer.sh app.apk --debug"
    exit 1
fi

APK_PATH=$(realpath "$1")
if [ ! -f "$APK_PATH" ]; then
    echo "Error: APK file does not exist at $APK_PATH"
    exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "=========================================================="
echo "[1/2] Building Docker image 'apk-analyzer'..."
echo "=========================================================="
docker build -t apk-analyzer "$SCRIPT_DIR"

if [ $? -ne 0 ]; then
    echo "Error: Failed to build Docker image."
    exit 1
fi

shift
ARGS="$@"

echo ""
echo "=========================================================="
echo "[2/2] Running analysis on $APK_PATH..."
echo "=========================================================="
docker run --rm -it -v "$(pwd)/data:/app/data" -v "$APK_PATH:/app/input.apk" apk-analyzer /app/input.apk $ARGS
