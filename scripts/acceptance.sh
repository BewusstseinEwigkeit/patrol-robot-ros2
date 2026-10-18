#!/usr/bin/env bash
# M1 逐周自动验收（bash 入口）。
#
# 真正的检查逻辑在 scripts/acceptance.py 里：
#   - 它用 rclpy 直接读 ROS 图，不依赖 `ros2 topic list` 这类需要 ros2 daemon 的命令
#     （daemon 在部分环境下会挂住）；
#   - 检测不到 colcon 安装出来的可执行文件时，会自动退回 `python -m <模块>` 启动节点，
#     所以即使还没编译，也能先验证代码本身。
#
# 用法：
#   bash scripts/acceptance.sh w1|w2|w3|w4|all
#   bash scripts/acceptance.sh all --json outputs/acceptance.json
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$WS_ROOT"

export PYTHONPATH="$WS_ROOT/src/m1_pubsub_demo:$WS_ROOT/src/m1_turtle_basics:$WS_ROOT/src/m1_tf2_demo:$WS_ROOT/src/m1_bringup:${PYTHONPATH:-}"

if [[ -f /opt/ros/humble/setup.bash ]]; then
  # shellcheck disable=SC1091
  source /opt/ros/humble/setup.bash
fi
if [[ -f "$WS_ROOT/install/setup.bash" ]]; then
  # shellcheck disable=SC1091
  source "$WS_ROOT/install/setup.bash"
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "找不到 python3；请先确认 ROS 2 已安装并 source 过 setup.bash" >&2
  exit 2
fi

exec python3 "$SCRIPT_DIR/acceptance.py" "$@"
