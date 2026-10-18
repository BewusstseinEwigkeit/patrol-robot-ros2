"""轨迹统计的纯计算部分：不 import rclpy，可以直接用 pytest 验证。

把这段逻辑从 `pose_monitor.py` 里拆出来，是为了让"统计对不对"这件事
可以在**任何** Python 环境里验证，而不必先装好 ROS。
M2 之后算里程计误差、M7 用 evo 评估轨迹时，你会需要同一类计算，
到时候可以直接复用这个模块。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


def normalize_angle(a: float) -> float:
    """把角度归一到 (-pi, pi]。

    必须做这一步：turtlesim 的 theta 会在 pi 和 -pi 之间跳变，
    不归一的话"累计转角"会莫名其妙多出 2pi。
    """
    while a > math.pi:
        a -= 2.0 * math.pi
    while a <= -math.pi:
        a += 2.0 * math.pi
    return a


def path_length(points: list[tuple[float, float]]) -> float:
    """折线总长度。"""
    total = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        total += math.hypot(x1 - x0, y1 - y0)
    return total


def bbox(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    """返回 (min_x, max_x, min_y, max_y)；空列表抛 ValueError。"""
    if not points:
        raise ValueError("points 为空，无法计算外接框")
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), max(xs), min(ys), max(ys)


def aspect_ratio(points: list[tuple[float, float]]) -> float:
    """外接框宽高比。圆周运动的轨迹接近正方形，所以这个值应该接近 1。

    这是 `acceptance.sh` 判断"乌龟画的是不是圆"的依据。
    """
    min_x, max_x, min_y, max_y = bbox(points)
    w = max_x - min_x
    h = max_y - min_y
    if h == 0:
        return 0.0
    return w / h


@dataclass
class TrajectoryStats:
    """增量式轨迹统计：每来一帧位姿就 update 一次。"""

    samples: int = 0
    distance: float = 0.0
    turn: float = 0.0
    min_x: float = math.inf
    max_x: float = -math.inf
    min_y: float = math.inf
    max_y: float = -math.inf
    last: tuple[float, float, float] | None = None  # (x, y, theta)
    history: list[tuple[float, float]] = field(default_factory=list)

    def update(self, x: float, y: float, theta: float) -> None:
        self.samples += 1
        self.min_x, self.max_x = min(self.min_x, x), max(self.max_x, x)
        self.min_y, self.max_y = min(self.min_y, y), max(self.max_y, y)
        self.history.append((x, y))

        if self.last is not None:
            lx, ly, ltheta = self.last
            self.distance += math.hypot(x - lx, y - ly)
            self.turn += abs(normalize_angle(theta - ltheta))

        self.last = (x, y, theta)

    # ---------------------------------------------------------------
    def width(self) -> float:
        return 0.0 if self.samples == 0 else self.max_x - self.min_x

    def height(self) -> float:
        return 0.0 if self.samples == 0 else self.max_y - self.min_y

    def ratio(self) -> float:
        h = self.height()
        return 0.0 if h == 0 else self.width() / h

    def to_dict(self) -> dict:
        empty = self.samples == 0
        return {
            "samples": self.samples,
            "path_length": round(self.distance, 4),
            "turn_angle": round(self.turn, 4),
            "bbox": {
                "min_x": None if empty else round(self.min_x, 4),
                "max_x": None if empty else round(self.max_x, 4),
                "min_y": None if empty else round(self.min_y, 4),
                "max_y": None if empty else round(self.max_y, 4),
            },
            "aspect_ratio": round(self.ratio(), 4),
            "last_pose": None
            if self.last is None
            else {"x": round(self.last[0], 4), "y": round(self.last[1], 4), "theta": round(self.last[2], 4)},
        }
