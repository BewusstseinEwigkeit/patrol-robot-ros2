"""W4 产出：把 turtlesim 的 2D 位姿发布成标准机器人坐标树。

这是 M1 里最"面向定位线"的一个节点。它做的是 M3–M6 会反复出现的事：
**把某个传感器/算法算出来的位姿，翻译成 tf2 的父子坐标系关系。**

它发布的关系（标准机器人坐标树的最小形态）：

    world ──(静态)──> odom ──(本节点)──> base_link

- `world → odom`：由 launch 里的 static_transform_publisher 发布，表示"里程计原点"
  在真实系统里这一跳是 EKF/robot_localization 修正漂移的地方（M6 会用到）。
- `odom → base_link`：本节点发布，代表"里程计说车在哪"。
  这里直接用 turtlesim 的位姿当真值，所以看起来是完美的；真车上它会漂。

注意两个容易踩的点：
1. **一个 child frame 只能有一个父**。turtlesim 里 odom→base_link 由本节点独占，
   不要再写第二个节点发同一个父子关系，否则 tf 树会互相打架。
2. **时间戳要用节点时钟**。tf2 默认不接受"未来"的变换；用
   `node.get_clock().now().to_msg()` 而不是 `time.time()`。

用法：
    ros2 run m1_tf2_demo turtle_tf_broadcaster
    ros2 run m1_tf2_demo turtle_tf_broadcaster --ros-args -p parent_frame:=odom -p child_frame:=base_link
"""

from __future__ import annotations

import math

import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from tf2_ros import TransformBroadcaster
from turtlesim.msg import Pose


def yaw_to_quaternion(yaw: float) -> tuple[float, float, float, float]:
    """绕 z 轴转 yaw 的四元数 (x, y, z, w)。

    纯 2D 场景里只有这一种旋转，手写比调 tf_transformations 更清楚。
    """
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


class TurtleTfBroadcaster(Node):
    def __init__(self) -> None:
        super().__init__("turtle_tf_broadcaster")

        self.declare_parameter("pose_topic", "/turtle1/pose")
        self.declare_parameter("parent_frame", "odom")
        self.declare_parameter("child_frame", "base_link")

        pose_topic = str(self.get_parameter("pose_topic").value)
        self.parent_frame = str(self.get_parameter("parent_frame").value)
        self.child_frame = str(self.get_parameter("child_frame").value)

        self.broadcaster = TransformBroadcaster(self)
        self.create_subscription(Pose, pose_topic, self.on_pose, 10)
        self.published = 0

        self.get_logger().info(
            f"turtle_tf_broadcaster 启动：{self.parent_frame} -> {self.child_frame}"
            f"（来自 {pose_topic}）"
        )

    def on_pose(self, msg: Pose) -> None:
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = self.parent_frame
        t.child_frame_id = self.child_frame

        # turtlesim 的坐标是 2D 的 (x, y, theta)；z 恒为 0
        t.transform.translation.x = float(msg.x)
        t.transform.translation.y = float(msg.y)
        t.transform.translation.z = 0.0

        qx, qy, qz, qw = yaw_to_quaternion(float(msg.theta))
        t.transform.rotation.x = qx
        t.transform.rotation.y = qy
        t.transform.rotation.z = qz
        t.transform.rotation.w = qw

        self.broadcaster.sendTransform(t)
        self.published += 1
        if self.published % 50 == 1:
            self.get_logger().info(
                f"已发布 {self.published} 次 tf："
                f"({msg.x:.2f}, {msg.y:.2f}, yaw={msg.theta:.2f})"
            )


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = TurtleTfBroadcaster()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
