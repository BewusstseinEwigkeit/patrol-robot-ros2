#!/usr/bin/env bash
# W1：只用命令行把 turtlesim 玩一遍（一行代码都不写）。
#
# W1 的目标是"乌龟能用键盘 + 命令行两种方式控制"，这个脚本负责后半句。
# 它会按顺序演示 topic / node / service / param 四类命令，
# 每做一步都打印出"这条命令在干什么"。
#
# 前置：另开一个终端跑 `ros2 run turtlesim turtlesim_node`。
# 用法：
#   bash scripts/w1_console_circle.sh
set -uo pipefail

if [[ -f /opt/ros/humble/setup.bash ]]; then
  # shellcheck disable=SC1091
  source /opt/ros/humble/setup.bash
fi

say()  { printf '\n\033[1;36m▸ %s\033[0m\n' "$1"; }
note() { printf '  \033[2m%s\033[0m\n' "$1"; }
run()  { printf '  \033[33m$ %s\033[0m\n' "$*"; "$@"; }

if ! ros2 node list 2>/dev/null | grep -q "/turtlesim"; then
  echo "没看到 /turtlesim 节点。请先在另一个终端运行：" >&2
  echo "    ros2 run turtlesim turtlesim_node" >&2
  exit 1
fi

say "1) node —— 现在有哪些节点在跑"
run ros2 node list
note "turtlesim 是节点名；节点是"一个能干活的最小程序单元"。"

say "2) topic —— 节点之间靠什么传话"
run ros2 topic list
note "/turtle1/cmd_vel 是'速度指令'，/turtle1/pose 是'当前位置'。"
run ros2 topic info /turtle1/cmd_vel
note "Type 是消息类型；Publisher/Subscription count 告诉你谁在发、谁在收。"

say "3) 看一眼当前位姿"
run ros2 topic echo /turtle1/pose --once
note "x, y 是坐标，theta 是朝向（弧度）。turtlesim 的世界是 11x11 的方框。"

say "4) 命令行发速度：让乌龟画圆（5 秒）"
note "v=2 m/s，w=2 rad/s → 半径 r = v/w = 1 m。"
printf '  \033[33m$ ros2 topic pub -r 10 /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 2.0}, angular: {z: 2.0}}"\033[0m\n'
ros2 topic pub -r 10 /turtle1/cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 2.0}, angular: {z: 2.0}}" >/dev/null 2>&1 &
PUB_PID=$!
sleep 5
kill "$PUB_PID" 2>/dev/null
wait "$PUB_PID" 2>/dev/null
# 发一条零速度，让乌龟停下（很重要：不发它就一直转）
ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist "{}" >/dev/null 2>&1
note "停下来了。注意最后那条空 Twist —— 真车上忘记发零速度是要撞墙的。"

say "5) service —— 请求-应答式的操作"
run ros2 service list | head -5
note "和 topic 不同，service 是'我问一句，你答一句'。"
run ros2 service call /turtle1/teleport_absolute turtlesim/srv/TeleportAbsolute \
  "{x: 5.5, y: 5.5, theta: 0.0}"
note "乌龟被直接挪到了中心，不是开过去的。"
run ros2 service call /clear std_srvs/srv/Empty "{}"
note "清掉轨迹。"

say "6) param —— 节点的可调参数"
run ros2 param list /turtlesim
run ros2 param get /turtlesim background_r
run ros2 param set /turtlesim background_r 120
note "背景变绿了一点。param 适合放'不用重新编译就能改'的东西。"
run ros2 param set /turtlesim background_r 255

say "7) 收尾"
note "键盘控制（W1 的另一种方式）：ros2 run turtlesim turtle_teleop_key"
note "本工作区自己实现了一版：ros2 run m1_turtle_basics keyboard_teleop"
echo
echo "W1 命令行部分演示完毕。接下来跑：bash scripts/acceptance.sh w1"
