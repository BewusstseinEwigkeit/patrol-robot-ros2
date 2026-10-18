"""W1 产出：把"按了哪个键"翻译成速度指令的纯函数。

刻意与 ROS 解耦：不 import rclpy，所以可以用普通 pytest 直接验证，
不需要启动任何节点（`tests/test_teleop_math.py` 就是这么用的）。

按键约定（与 turtlesim 自带 teleop 保持一致）：
    w / s   前进 / 后退
    a / d   左转 / 右转
    空格    急停
    q       退出（由调用方处理）
"""

from __future__ import annotations

from dataclasses import dataclass

#: 支持的按键集合
MOVE_KEYS = ("w", "s", "a", "d", " ")


@dataclass(frozen=True)
class Twist:
    """与 geometry_msgs/Twist 的 (linear.x, angular.z) 对应的最小子集。"""

    linear_x: float = 0.0
    angular_z: float = 0.0

    def is_stop(self) -> bool:
        return self.linear_x == 0.0 and self.angular_z == 0.0


def twist_from_key(
    key: str,
    linear_speed: float = 2.0,
    angular_speed: float = 2.0,
) -> Twist:
    """把单个按键映射成速度指令。

    未知按键返回零速度（而不是抛异常），这样终端里按到方向键、
    Ctrl 组合键都不会让遥控程序崩掉。
    """
    if key == "w":
        return Twist(linear_x=abs(linear_speed), angular_z=0.0)
    if key == "s":
        return Twist(linear_x=-abs(linear_speed), angular_z=0.0)
    if key == "a":
        return Twist(linear_x=0.0, angular_z=abs(angular_speed))
    if key == "d":
        return Twist(linear_x=0.0, angular_z=-abs(angular_speed))
    if key == " ":
        return Twist()
    return Twist()


def is_quit_key(key: str) -> bool:
    """q 或 Ctrl-C（终端会给出 '\\x03'）。"""
    return key in ("q", "\x03")
