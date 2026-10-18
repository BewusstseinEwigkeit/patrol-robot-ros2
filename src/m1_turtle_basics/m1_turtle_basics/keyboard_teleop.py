"""W1 产出：自己实现的键盘遥控节点（不依赖 turtlesim 自带 teleop）。

为什么要自己写一遍：
`ros2 run turtlesim turtle_teleop_key` 能跑，但它是黑盒。自己写一遍会强制你
想清楚三件事——按键怎么读、速度怎么发、松手后谁来停车。这三件事在
M5 的"手动摆车测试"里会原样再出现一次。

安全设计：如果 key_timeout 秒内没有新按键，自动发布零速度（松手即停），
否则乌龟会带着最后一次的速度一直跑下去。

用法（必须在真实终端里跑，管道里没有 TTY）：
    ros2 run m1_turtle_basics keyboard_teleop
    ros2 run m1_turtle_basics keyboard_teleop --ros-args -p linear_speed:=3.0 -p key_timeout:=0.5
"""

from __future__ import annotations

import os
import sys
import threading

import rclpy
from geometry_msgs.msg import Twist as TwistMsg
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from m1_turtle_basics.teleop_math import is_quit_key, twist_from_key


class KeyboardTeleop(Node):
    def __init__(self) -> None:
        super().__init__("keyboard_teleop")

        self.declare_parameter("linear_speed", 2.0)
        self.declare_parameter("angular_speed", 2.0)
        self.declare_parameter("key_timeout", 0.3)  # 秒；0 表示不自动停车
        self.declare_parameter("cmd_vel_topic", "/turtle1/cmd_vel")

        self.linear_speed = float(self.get_parameter("linear_speed").value)
        self.angular_speed = float(self.get_parameter("angular_speed").value)
        self.key_timeout = float(self.get_parameter("key_timeout").value)
        topic = str(self.get_parameter("cmd_vel_topic").value)

        self.publisher = self.create_publisher(TwistMsg, topic, 10)
        self._last_key_time = self.get_clock().now()
        self._moving = False

        if self.key_timeout > 0.0:
            self.create_timer(0.1, self._check_timeout)

        self.get_logger().info(
            "键盘遥控已就绪：w 前进 / s 后退 / a 左转 / d 右转 / 空格 急停 / q 退出"
        )

    # ------------------------------------------------------------------
    def handle_key(self, key: str) -> bool:
        """处理一个按键；返回 False 表示要退出。"""
        if is_quit_key(key):
            return False

        t = twist_from_key(key, self.linear_speed, self.angular_speed)
        msg = TwistMsg()
        msg.linear.x = t.linear_x
        msg.angular.z = t.angular_z
        self.publisher.publish(msg)

        self._last_key_time = self.get_clock().now()
        self._moving = not t.is_stop()
        return True

    def _check_timeout(self) -> None:
        if not self._moving:
            return
        idle = (self.get_clock().now() - self._last_key_time).nanoseconds / 1e9
        if idle >= self.key_timeout:
            self.publisher.publish(TwistMsg())
            self._moving = False

    def stop(self) -> None:
        self.publisher.publish(TwistMsg())
        self._moving = False


# ----------------------------------------------------------------------
def read_key() -> str:
    """从终端读一个字符（cbreak 模式，不需要回车）。"""
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main(args: list[str] | None = None) -> None:
    if os.name == "nt":
        print(
            "keyboard_teleop 依赖 termios 读单键，只能在 Linux / macOS 上运行。\n"
            "Windows 上请用 WSL 或直接在 Ubuntu 里跑。",
            file=sys.stderr,
        )
        raise SystemExit(2)

    if not sys.stdin.isatty():
        print(
            "keyboard_teleop 需要在真实终端里运行（当前 stdin 不是 TTY）。\n"
            "如果只是想验证控制链路，请改用：bash scripts/acceptance.sh w1",
            file=sys.stderr,
        )
        raise SystemExit(2)

    rclpy.init(args=args)
    node = KeyboardTeleop()

    # 在一个后台线程里 spin，主线程留给阻塞式读键
    executor_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    executor_thread.start()

    try:
        while rclpy.ok():
            if not node.handle_key(read_key()):
                break
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        executor_thread.join(timeout=1.0)


if __name__ == "__main__":
    main()
