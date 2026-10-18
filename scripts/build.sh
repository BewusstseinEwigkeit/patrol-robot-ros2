#!/usr/bin/env bash
# 编译本工作区。第一次编译后，每个新终端都要 source install/setup.bash。
#
# 用法：
#   bash scripts/build.sh                 # 全量编译
#   bash scripts/build.sh --packages-select m1_pubsub_demo
#   bash scripts/build.sh --clean         # 先删掉 build/ install/ log/ 再编译
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$WS_ROOT"

CLEAN=0
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --clean) CLEAN=1; shift ;;
    *) EXTRA_ARGS+=("$1"); shift ;;
  esac
done

if ! command -v colcon >/dev/null 2>&1; then
  echo "找不到 colcon。先装：sudo apt install python3-colcon-common-extensions" >&2
  exit 1
fi

if [[ "$CLEAN" == "1" ]]; then
  echo "清理 build/ install/ log/ ..."
  rm -rf build install log
fi

echo "工作区：$WS_ROOT"
echo "开始编译（第一次会慢一点，之后就快了）..."
colcon build \
  --event-handlers console_direct+ \
  --cmake-args -DCMAKE_BUILD_TYPE=Release \
  "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"

status=$?
if [[ $status -ne 0 ]]; then
  echo "" >&2
  echo "编译失败。常见原因：" >&2
  echo "  1) 忘了 source /opt/ros/humble/setup.bash" >&2
  echo "  2) setup.py 的 entry_points 里模块名写错" >&2
  echo "  3) package.xml 缺 exec_depend" >&2
  exit $status
fi

echo ""
echo "编译完成。请在当前终端执行："
echo "    source install/setup.bash"
echo "然后可以跑：bash scripts/acceptance.sh w2"
