#!/usr/bin/env bash
# 为【内网/离线】Dify 准备依赖 wheel(放进 plugin_dir/wheels/)。
# 用法: ./fetch_offline_wheels.sh <plugin_dir> [python_version] [platform]
# 平台要匹配你的 Dify 服务器(常见: manylinux2014_aarch64 即 ARM64, 或 manylinux2014_x86_64)。
set -e
DIR="${1:?用法: ./fetch_offline_wheels.sh <plugin_dir> [pyver] [platform]}"
PYVER="${2:-3.12}"
PLAT="${3:-manylinux2014_aarch64}"
mkdir -p "$DIR/wheels"
pip download "dify_plugin==0.4.1" -d "$DIR/wheels" \
  --only-binary=:all: --python-version "$PYVER" --platform "$PLAT" --implementation cp || {
  echo "⚠️ 某些包可能没有该平台 wheel。最稳的离线办法:从一个【已能在你 Dify 上离线安装的插件包】里直接拷 wheels/ 目录过来。"; }
# 切到离线 requirements
cat > "$DIR/requirements.txt" <<REQ
--no-index
--find-links=./wheels/
dify_plugin==0.4.1
REQ
echo "wheels 已下到 $DIR/wheels/ ($(ls "$DIR/wheels"/*.whl 2>/dev/null | wc -l | tr -d ' ') 个); requirements.txt 已切到离线模式"
