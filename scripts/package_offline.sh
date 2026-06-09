#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

STAMP="$(date +%Y%m%d-%H%M%S)"
REV="$(git rev-parse --short HEAD 2>/dev/null || echo local)"
OUT_DIR="$ROOT/dist"
STAGE="$OUT_DIR/dify-builder-skills-offline-$STAMP-$REV"
ZIP_PATH="$STAGE.zip"

rm -rf "$STAGE" "$ZIP_PATH"
mkdir -p "$STAGE"

cp -R dify-agent-builder "$STAGE/"
cp -R dify-plugin-builder "$STAGE/"
cp OFFLINE_INSTALL.md "$STAGE/"
cp install_offline.sh "$STAGE/"
cp README.md "$STAGE/"
cp LICENSE "$STAGE/"

find "$STAGE" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$STAGE" -name '*.pyc' -delete
find "$STAGE" -name '.DS_Store' -delete
find "$STAGE" -name '*.difypkg' -delete

(cd "$OUT_DIR" && zip -qr "$(basename "$ZIP_PATH")" "$(basename "$STAGE")")

echo "$ZIP_PATH"
