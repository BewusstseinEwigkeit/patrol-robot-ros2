"""W1 产出：用 service 让乌龟"瞬移"着走正方形。

W1 的目标里有「topic / node / service / param 命令全敲一遍」。
topic 已经在 circle_driver / keyboard_teleop 里练过，这个节点专门练 **service**：
调用 `/turtle1/teleport_absolute` 把乌龟直接放到指定坐标，而不是发速度让它开过去。

两者区别值得记住：
- topic：异步、持续、单向（发速度，不关心结果）
- service：同步、一次性、有应答（请求"放到 (x,y)"，服务端回"放好了"）
M4 之后向底盘要"当前电量""充电功率"时，用的就是 service 这一类请求-应答模式。

用法：
    ros2 run m1_turtle_basics teleport_demo
    ros2 run m1_turtle_basics teleport_demo --ros-args -p side:=4.0 -p dwell_seconds:=0.8
"""

from __future__ import annotations

import math
import time

import rclpy
from rclpy.node import Node
from std_srvs.srv import Empty
from turtlesim.srv import TeleportAbsolute


class TeleportDemo(Node):
    def __init__(self) -> None:
        super().__init__("teleport_demo")

        self.declare_parameter("center_x", 5.5)
        self.declare_parameter("center_y", 5.5)
        self.declare_parameter("side", 3.0)
        self.declare_parameter("dwell_seconds", 1.0)
        self.declare_parameter("clear_first", True)

        self.center_x = float(self.get_parameter("center_x").value)
        self.center_y = float(self.get_parameter("center_y").value)
        self.side = float(self.get_parameter("side").value)
        self.dwell = float(self.get_parameter("dwell_seconds").value)
        self.clear_first = bool(self.get_parameter("clear_first").value)

        self.teleport_client = self.create_client(
            TeleportAbsolute, "/turtle1/teleport_absolute"
        )
        self.clear_client = self.create_client(Empty, "/clear")

    # ------------------------------------------------------------------
    def corners(self) -> list[tuple[float, float, float]]:
        """正方形四个顶点，theta 指向下一个顶点（看起来像在"转弯"）。"""
        h = self.side / 2.0
        pts = [
            (self.center_x - h, self.center_y - h),
            (self.center_x + h, self.center_y - h),
            (self.center_x + h, self.center_y + h),
            (self.center_x - h, self.center_y + h),
        ]
        out: list[tuple[float, float, float]] = []
        for i, (x, y) in enumerate(pts):
            nx, ny = pts[(i + 1) % len(pts)]
            theta = math.atan2(ny - y, nx - x)
            out.append((x, y, theta))
        return out

    def wait_for(self, client, name: str, timeout: float = 5.0) -> bool:
        if client.wait_for_service(timeout_sec=timeout):
            return True
        self.get_logger().error(f"等待服务 {name} 超时；turtlesim 起了吗？")
        return False

    def teleport(self, x: float, y: float, theta: float) -> bool:
        req = TeleportAbsolute.Request()
        req.x, req.y, req.theta = x, y, theta
        future = self.teleport_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
        if future.result() is None:
            self.get_logger().error(f"teleport 到 ({x:.2f},{y:.2f}) 失败")
            return False
        self.get_logger().info(f"瞬移到 ({x:5.2f}, {y:5.2f})，朝向 {theta:5.2f} rad")
        return True

    def clear(self) -> None:
        future = self.clear_client.call_async(Empty.Request())
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = TeleportDemo()

    ok = node.wait_for(node.teleport_client, "/turtle1/teleport_absolute")
    if ok and node.clear_first and node.wait_for(node.clear_client, "/clear", 2.0):
        node.clear()

    if ok:
        try:
            for x, y, theta in node.corners():
                if not node.teleport(x, y, theta):
                    break
                time.sleep(node.dwell)
        except KeyboardInterrupt:
            pass

    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()


if __name__ == "__main__":
    main()
