#! /bin/bash

# 获取脚本的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 切换到脚本所在的目录
cd "$SCRIPT_DIR" || { echo "Failed to change directory to $SCRIPT_DIR"; exit 1; }

# 打印当前工作目录（可选）
echo "Current working directory: $(pwd)"

echo "Start pull"
/usr/bin/git pull
/usr/bin/python3 ~/workfolder/house_app/house_app.py
