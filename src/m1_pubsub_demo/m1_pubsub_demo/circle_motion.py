"""圆周运动的纯计算部分：不 import rclpy，可以直接用 pytest 验证。

圆周运动只有一条公式要记：

    v = w * r      →      w = v / r      →      r = v / w

其中 v 是线速度 (m/s)，w 是角速度 (rad/s)，r 是半径 (m)。
M5 之后让真车走圆弧、M6 让车绕充电桩做微调时，用的还是这条公式。
"""

from __future__ import annotations


def angular_speed_for(
    linear_speed: float,
    radius: float,
    angular_override: float = 0.0,
) -> float:
    """由线速度和半径求角速度。

    显式给了 angular_override（非 0）时优先用它，方便直接复现某个已知的
    turtlesim 示例（例如 v=2, w=2 → r=1）。
    """
    if angular_override != 0.0:
        return angular_override
    if radius <= 0.0:
        raise ValueError(f"radius 必须为正数，收到 {radius}")
    return linear_speed / radius


def radius_from(linear_speed: float, angular_speed: float) -> float:
    """由线速度和角速度反推半径；角速度为 0（直线）时返回 inf。"""
    if angular_speed == 0.0:
        return float("inf")
    return linear_speed / angular_speed


def expected_period(linear_speed: float, radius: float) -> float:
    """跑完一整圈需要的时间（秒）：周长 / 线速度。"""
    import math

    if linear_speed <= 0.0:
        raise ValueError(f"linear_speed 必须为正数，收到 {linear_speed}")
    return 2.0 * math.pi * radius / linear_speed
