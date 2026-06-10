#!/usr/bin/env bash
# 把插件目录打包成 .difypkg。
# 用法: ./pack_plugin.sh <plugin_dir> [output.difypkg]
#
# 致命坑(本脚本已规避): 必须用 `zip -D` 不写目录条目。否则 Dify 安装报
#   "read tools: is a directory" —— 守护进程会把 tools/ 这个目录条目当文件读。
set -e
DIR="${1:?用法: ./pack_plugin.sh <plugin_dir> [output.difypkg]}"
OUT="${2:-$(basename "$DIR").difypkg}"
# 解析为绝对路径,兼容相对/绝对输出
DIR="$(cd "$DIR" && pwd)"
case "$OUT" in
  /*) OUTABS="$OUT" ;;
  *)  OUTABS="$(pwd)/$OUT" ;;
esac
cd "$DIR"
if [ "${DIFY_ALLOW_ONLINE_DEPS:-}" != "1" ]; then
  REQ_ACTIVE="$(grep -v '^[[:space:]]*#' requirements.txt 2>/dev/null || true)"
  if ! printf '%s\n' "$REQ_ACTIVE" | grep -q -- '--no-index' || ! printf '%s\n' "$REQ_ACTIVE" | grep -q -- '--find-links=./wheels/'; then
    echo "ERROR: 内网交付要求离线依赖。先运行 prepare_offline_plugin.py 或 fetch_offline_wheels.sh，把 requirements.txt 切到 --no-index 模式。" >&2
    exit 2
  fi
  WHEEL_COUNT=$(find wheels -maxdepth 1 -name '*.whl' 2>/dev/null | wc -l | tr -d ' ')
  if [ "$WHEEL_COUNT" = "0" ]; then
    echo "ERROR: 内网交付要求 wheels/*.whl 随包交付。先复制已验证 wheels/，或运行 fetch_offline_wheels.sh。" >&2
    exit 2
  fi
fi
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -name '*.pyc' -delete; find . -name '.DS_Store' -delete
rm -f "$OUTABS"
zip -D -r -q "$OUTABS" . -x '*.pyc' '*/__pycache__/*'
DIRS=$(unzip -l "$OUTABS" | awk '$4 ~ /\/$/' | wc -l | tr -d ' ')
ROOT=$(unzip -l "$OUTABS" | grep -c ' manifest.yaml$' || true)
echo "built $OUTABS  (目录条目=$DIRS,必须为0; manifest在根=$ROOT)"
[ "$DIRS" = "0" ] || { echo "⚠️ 目录条目不为0,安装会报 read ... is a directory!"; exit 1; }
