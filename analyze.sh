#!/usr/bin/env bash
# analyze.sh — статика + динамика за один вызов.
#
# Usage:
#   ./analyze.sh /path/to/app.apk com.example.package
#
# Что происходит:
#   1. Собираются оба образа (apk-analyzer-static, apk-analyzer-dynamic) — кэшируется.
#   2. Поднимается эмулятор (долгоживущий сервис, frida-server внутри).
#   3. Статический анализ  → data/output/static/
#   4. Динамический анализ → data/output/dynamic/   (best-effort)
#
# Статика и динамика независимы: если эмулятор/frida недоступны,
# динамический отчёт будет содержать errors, но статика отработает полностью.

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: ./analyze.sh /path/to/app.apk com.example.package"
  exit 1
fi

APK_FILE="$1"
PACKAGE="$2"

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
APK_DIR="$(dirname "$APK_FILE")"
APK_NAME="$(basename "$APK_FILE")"

cd "$SCRIPT_DIR"

echo "📦 Build образов (кэшируется после первого прогона)..."
docker compose build apk-analyzer-static apk-analyzer-dynamic

echo "📱 Подъём эмулятора (долгоживущий сервис)..."
docker compose up -d android-emulator

echo ""
echo "🔬 [1/2] Статический анализ..."
docker compose run --rm \
  -v "$APK_DIR:/app/input:ro" \
  apk-analyzer-static "/app/input/$APK_NAME"

echo ""
echo "🎣 [2/2] Динамический анализ (best-effort)..."
docker compose run --rm \
  -v "$APK_DIR:/app/input:ro" \
  apk-analyzer-dynamic \
  "/app/input/$APK_NAME" --mode dynamic --package "$PACKAGE" \
  || echo "⚠️  Динамика завершилась с ошибкой — отчёт с errors в data/output/dynamic/. Статика отработала полностью."

echo ""
echo "✅ Готово."
echo "   Статика:  data/output/static/   (*_report.md/json/html)"
echo "   Динамика: data/output/dynamic/  (*_report.md/json/html, значения замаскированы)"
echo "             + <apk>_raw_values.json (немаскированные, технический файл)"
