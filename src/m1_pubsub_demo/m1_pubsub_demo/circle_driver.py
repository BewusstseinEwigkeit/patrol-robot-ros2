"""W2 产出：让 turtlesim 里的乌龟沿指定半径画圆的驱动节点。

这是 M1「不看教程能独立写出发布节点」的核心产出物。它只做一件事：
以固定频率向 /turtle1/cmd_vel 发布 geometry_msgs/Twist。

圆周运动的物理关系（记住这一条就够）：
    v = 线速度 (m/s)，w = 角速度 (rad/s)，半径 r = v / w
所以只要给定 r 和 v，就能反推 w = v / r。

用法示例：
    ros2 run m1_pubsub_demo circle_driver --ros-args -p radius:=1.0 -p linear_speed:=2.0
    ros2 run m1_pubsub_demo circle_driver --ros-args -p run_seconds:=8.0   # 跑 8 秒自动停
"""

from __future__ import annotations

import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from m1_pubsub_demo.circle_motion import angular_speed_for, radius_from


class CircleDriver(Node):
    """按半径参数持续发布圆周运动速度指令。"""

    def __init__(self) -> None:
        super().__init__("circle_driver")

        # --- 参数 ---------------------------------------------------------
        # radius 是最直观的输入；angular_speed 显式给出时可以覆盖 radius 的推导。
        self.declare_parameter("radius", 1.0)
        self.declare_parameter("linear_speed", 2.0)
        self.declare_parameter("angular_speed", 0.0)  # 0 表示由 radius 推导
        self.declare_parameter("publish_rate", 20.0)
        self.declare_parameter("run_seconds", 0.0)  # 0 表示一直跑
        self.declare_parameter("cmd_vel_topic", "/turtle1/cmd_vel")

        self.radius = float(self.get_parameter("radius").value)
        self.linear_speed = float(self.get_parameter("linear_speed").value)
        angular_override = float(self.get_parameter("angular_speed").value)
        rate = float(self.get_parameter("publish_rate").value)
        self.run_seconds = float(self.get_parameter("run_seconds").value)
        topic = str(self.get_parameter("cmd_vel_topic").value)

        if self.radius <= 0.0 and angular_override == 0.0:
            self.get_logger().warn("radius<=0 且未指定 angular_speed，回退到 radius=1.0")
            self.radius = 1.0

        self.angular_speed = angular_speed_for(
            self.linear_speed, self.radius, angular_override
        )

        self.publisher = self.create_publisher(Twist, topic, 10)
        self.timer = self.create_timer(1.0 / max(rate, 1.0), self.on_timer)

        self.started_at = self.get_clock().now()
        self.stopped = False

        self.get_logger().info(
            f"circle_driver 启动：v={self.linear_speed:.3f} m/s, "
            f"w={self.angular_speed:.3f} rad/s, "
            f"实际半径≈{radius_from(self.linear_speed, self.angular_speed):.3f} m, "
            f"话题={topic}"
        )

    # ------------------------------------------------------------------
    def on_timer(self) -> None:
        if self.stopped:
            return

        # 到点自动停：验收脚本靠这个参数避免手动杀进程
        if self.run_seconds > 0.0:
            elapsed = (self.get_clock().now() - self.started_at).nanoseconds / 1e9
            if elapsed >= self.run_seconds:
                self.stop()
                return

        msg = Twist()
        msg.linear.x = self.linear_speed
        msg.angular.z = self.angular_speed
        self.publisher.publish(msg)

    def stop(self) -> None:
        """发一条零速度并停表，让乌龟真正停下。"""
        if self.stopped:
            return
        self.stopped = True
        self.publisher.publish(Twist())
        if self.timer is not None:
            self.timer.cancel()
        self.get_logger().info(
            f"circle_driver 结束：共运行 {self.run_seconds:.1f}s，已发布零速度。"
        )
        # 请求退出 spin；main() 里捕获 ExternalShutdownException。
        rclpy.shutdown()


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = CircleDriver()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
