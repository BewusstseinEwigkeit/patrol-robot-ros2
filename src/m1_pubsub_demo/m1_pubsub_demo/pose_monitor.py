"""W2 产出：订阅乌龟位姿并打印 / 统计的监控节点。

它是 circle_driver 的"订阅侧"，合起来就构成了 M1 检查点里
「画圆 + 打印位姿」两个节点。

除了打印，它还把统计结果落成 JSON（由 summary_json 参数指定），
这样 `scripts/acceptance.sh` 可以自动判断"乌龟到底动没动、画的是不是圆"，
而不是靠人眼看终端输出。

统计的数学部分在 `trajectory_stats.py`（纯 Python，无 ROS 依赖），
所以那部分逻辑可以用 pytest 直接验证。

用法：
    ros2 run m1_pubsub_demo pose_monitor
    ros2 run m1_pubsub_demo pose_monitor --ros-args -p run_seconds:=10.0 \
        -p summary_json:=/tmp/pose_summary.json
"""

from __future__ import annotations

import json
import os

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from turtlesim.msg import Pose

from m1_pubsub_demo.trajectory_stats import TrajectoryStats


class PoseMonitor(Node):
    """订阅 turtlesim 位姿，打印并统计运动轨迹。"""

    def __init__(self) -> None:
        super().__init__("pose_monitor")

        self.declare_parameter("pose_topic", "/turtle1/pose")
        self.declare_parameter("report_period", 1.0)  # 秒，打印间隔
        self.declare_parameter("run_seconds", 0.0)  # 0 = 一直跑
        self.declare_parameter("summary_json", "")  # 非空则写统计文件
        self.declare_parameter("print_every_sample", False)

        pose_topic = str(self.get_parameter("pose_topic").value)
        self.report_period = float(self.get_parameter("report_period").value)
        self.run_seconds = float(self.get_parameter("run_seconds").value)
        self.summary_json = str(self.get_parameter("summary_json").value)
        self.print_every_sample = bool(self.get_parameter("print_every_sample").value)

        self.stats = TrajectoryStats()
        self.last_pose: Pose | None = None
        self.started_at = self.get_clock().now()
        self._finished = False

        self.subscription = self.create_subscription(Pose, pose_topic, self.on_pose, 10)
        self.report_timer = self.create_timer(max(self.report_period, 0.2), self.on_report)

        self.get_logger().info(
            f"pose_monitor 启动：订阅 {pose_topic}，每 {self.report_period:.1f}s 汇报一次"
        )

    # ------------------------------------------------------------------
    def on_pose(self, msg: Pose) -> None:
        self.last_pose = msg
        self.stats.update(float(msg.x), float(msg.y), float(msg.theta))

        if self.print_every_sample:
            self.get_logger().info(
                f"x={msg.x:6.3f} y={msg.y:6.3f} theta={msg.theta:6.3f} "
                f"v={msg.linear_velocity:5.2f} w={msg.angular_velocity:5.2f}"
            )

    def on_report(self) -> None:
        if self._finished:
            return

        if self.run_seconds > 0.0:
            elapsed = (self.get_clock().now() - self.started_at).nanoseconds / 1e9
            if elapsed >= self.run_seconds:
                self.finish()
                return

        if self.last_pose is None:
            self.get_logger().warn("还没有收到位姿；turtlesim 起了吗？")
            return

        p = self.last_pose
        self.get_logger().info(
            f"[{self.stats.samples:4d} 帧] 位置=({p.x:5.2f}, {p.y:5.2f}) "
            f"朝向={p.theta:5.2f} rad | 累计路程={self.stats.distance:6.2f} "
            f"累计转角={self.stats.turn:6.2f} rad"
        )

    # ------------------------------------------------------------------
    def finish(self) -> None:
        self._finished = True
        payload = self.stats.to_dict()

        if self.summary_json:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(self.summary_json)), exist_ok=True)
                with open(self.summary_json, "w", encoding="utf-8", newline="\n") as fh:
                    json.dump(payload, fh, ensure_ascii=False, indent=2)
                self.get_logger().info(f"统计已写入 {self.summary_json}")
            except OSError as exc:
                self.get_logger().error(f"写统计文件失败：{exc}")

        self.get_logger().info(
            f"pose_monitor 结束：{payload['samples']} 帧，路程 {payload['path_length']} m，"
            f"转角 {payload['turn_angle']} rad，外接框宽高比 {payload['aspect_ratio']}"
        )
        rclpy.shutdown()


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = PoseMonitor()
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
