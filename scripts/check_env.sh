#!/usr/bin/env bash
# M1 W1 检查点：ROS 2 环境自检。
#
# 这个脚本回答一个问题：「我现在可以开始做 M1 了吗？」
# 每一项都会明确给出 OK / XX，最后用退出码表示整体是否通过。
#
# 用法：
#   bash scripts/check_env.sh
#   bash scripts/check_env.sh --quiet    # 只输出失败项
set -uo pipefail

QUIET=0
[[ "${1:-}" == "--quiet" ]] && QUIET=1

PASS=0
FAIL=0

ok()   { PASS=$((PASS+1)); [[ "$QUIET" == "1" ]] || printf '  \033[32m[OK]\033[0m %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  \033[31m[XX]\033[0m %s\n' "$1"; }
info() { [[ "$QUIET" == "1" ]] || printf '       %s\n' "$1"; }
step() { [[ "$QUIET" == "1" ]] || printf '\n\033[1m== %s ==\033[0m\n' "$1"; }

# 找一下工作区根目录（本脚本在 <root>/scripts 下）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(dirname "$SCRIPT_DIR")"

step "1. ROS 2 本体"
if command -v ros2 >/dev/null 2>&1; then
  ok "ros2 命令可用：$(command -v ros2)"
else
  bad "找不到 ros2 命令"
  info "先跑 bash scripts/setup_ubuntu_ros2.sh，再 source /opt/ros/humble/setup.bash"
fi

if [[ -n "${ROS_DISTRO:-}" ]]; then
  ok "ROS_DISTRO=${ROS_DISTRO}"
  [[ "$ROS_DISTRO" == "humble" ]] || info "本项目按 humble 写的，其他版本大多数命令通用"
else
  bad "ROS_DISTRO 未设置（说明没 source setup.bash）"
fi

step "2. 关键功能包"
for pkg in turtlesim tf2_ros tf2_tools rosbag2 launch launch_ros rclpy; do
  if ros2 pkg prefix "$pkg" >/dev/null 2>&1; then
    ok "包存在：$pkg"
  else
    bad "缺包：$pkg"
  fi
done

step "3. 命令行工具"
for tool in colcon ros2; do
  if command -v "$tool" >/dev/null 2>&1; then
    ok "$tool 可用"
  else
    bad "$tool 不可用"
  fi
done

step "4. Python"
if command -v python3 >/dev/null 2>&1; then
  ok "python3 $(python3 -V 2>&1 | awk '{print $2}')"
else
  bad "找不到 python3"
fi
if python3 -c 'import rclpy' >/dev/null 2>&1; then
  ok "python3 能 import rclpy"
else
  bad "python3 不能 import rclpy（通常还是没 source setup.bash）"
fi

step "5. 本工作区"
if [[ -d "$WS_ROOT/src" ]]; then
  pkg_count=$(find "$WS_ROOT/src" -name package.xml | wc -l | tr -d ' ')
  ok "找到 src/，含 $pkg_count 个 ROS 包"
else
  bad "在 $WS_ROOT 下找不到 src/"
fi
if [[ -f "$WS_ROOT/install/setup.bash" ]]; then
  ok "已经编译过（install/setup.bash 存在）"
else
  info "还没编译；下一步执行 bash scripts/build.sh"
fi

step "结果"
if [[ "$FAIL" -eq 0 ]]; then
  printf '  \033[32m全部通过\033[0m（%d 项）。可以开始 W1 的实操了。\n' "$PASS"
  exit 0
else
  printf '  \033[31m%d 项未通过\033[0m（通过 %d 项）。请先解决上面标 [XX] 的问题。\n' "$FAIL" "$PASS"
  exit 1
fi
