#!/bin/bash
# WenCe AI Linux 打包脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================"
echo "  WenCe AI Linux 打包脚本"
echo "======================================"

# 使用 Python 打包脚本
python3 build.py

echo ""
echo "打包完成！"
echo "运行: ./dist/wence_ai"
