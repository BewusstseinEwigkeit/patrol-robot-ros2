"""W4 产出：查询 tf2 坐标树，回答"相机在世界坐标系的哪里"。

broadcaster 负责"把关系写进树"，listener 负责"从树里问出答案"。
M4 之后你会反复问类似的问题：
- 视觉同学说"桩在相机前方 1.2 米"，换算成车体坐标系是哪个方向？（M4 接口）
- 里程计说车在 (3.1, 0.4)，相机装在车头 0.15 米，那相机在哪？（本节点）

查询用 `lookup_transform(target_frame, source_frame, time)`：
    "把 source 表达的坐标，换算到 target 坐标系里"。
参数顺序最容易记反，记成 **"我要在 target 里看 source"**。

用法：
    ros2 run m1_tf2_demo tf_listener
    ros2 run m1_tf2_demo tf_listener --ros-args -p target_frame:=world -p source_frame:=camera_link
"""

from __future__ import annotations

import math

import rclpy
from rclpy.node import Node
from tf2_ros import Buffer, TransformException, TransformListener


class TfListener(Node):
    def __init__(self) -> None:
        super().__init__("tf_listener")

        self.declare_parameter("target_frame", "world")
        self.declare_parameter("source_frame", "camera_link")
        self.declare_parameter("report_period", 1.0)
        self.declare_parameter("timeout_seconds", 0.2)

        self.target_frame = str(self.get_parameter("target_frame").value)
        self.source_frame = str(self.get_parameter("source_frame").value)
        period = float(self.get_parameter("report_period").value)
        self.timeout = float(self.get_parameter("timeout_seconds").value)

        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.create_timer(max(period, 0.2), self.on_timer)

        self.get_logger().info(
            f"tf_listener 启动：每 {period:.1f}s 查询 {self.source_frame} 在 {self.target_frame} 下的位姿"
        )

    def on_timer(self) -> None:
        try:
            # 不传时间戳时默认查"最新可用"的变换
            tf = self.buffer.lookup_transform(
                self.target_frame,
                self.source_frame,
                rclpy.time.Time(),
                timeout=rclpy.duration.Duration(seconds=self.timeout),
            )
        except TransformException as exc:
            self.get_logger().warn(
                f"查不到 {self.source_frame} -> {self.target_frame}：{exc.__class__.__name__}: {exc}"
            )
            return

        tr = tf.transform.translation
        rot = tf.transform.rotation
        yaw = math.atan2(
            2.0 * (rot.w * rot.z + rot.x * rot.y),
            1.0 - 2.0 * (rot.y * rot.y + rot.z * rot.z),
        )
        self.get_logger().info(
            f"{self.source_frame} 在 {self.target_frame} 下："
            f"({tr.x:6.3f}, {tr.y:6.3f}, {tr.z:6.3f})，yaw={yaw:6.3f} rad"
        )


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = TfListener()
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


if __name__ == "__main__":
    main()
