#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
TARGET="codex"
DEST=""

usage() {
  cat <<'EOF'
Usage: ./install_offline.sh [--target codex|claude|both] [--dest /path/to/skills]

Installs dify-agent-builder and dify-plugin-builder from this offline package.

Examples:
  ./install_offline.sh --target codex
  ./install_offline.sh --target claude
  ./install_offline.sh --target both
  ./install_offline.sh --dest ~/.codex/skills
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      TARGET="${2:-}"
      shift 2
      ;;
    --dest)
      DEST="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

install_to() {
  local dest="$1"
  mkdir -p "$dest"
  rm -rf "$dest/dify-agent-builder" "$dest/dify-plugin-builder"
  cp -R "$ROOT/dify-agent-builder" "$dest/"
  cp -R "$ROOT/dify-plugin-builder" "$dest/"
  echo "Installed to $dest"
}

if [ -n "$DEST" ]; then
  install_to "$(eval echo "$DEST")"
else
  case "$TARGET" in
    codex)
      install_to "$HOME/.codex/skills"
      ;;
    claude)
      install_to "$HOME/.claude/skills"
      ;;
    both)
      install_to "$HOME/.codex/skills"
      install_to "$HOME/.claude/skills"
      ;;
    *)
      echo "--target must be codex, claude, or both" >&2
      usage >&2
      exit 2
      ;;
  esac
fi

echo "Restart Codex/Claude to load the updated skills."
