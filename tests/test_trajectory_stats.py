"""轨迹统计的单元测试（不依赖 ROS）。

重点验证两件在真机上非常容易出错的事：
1. **角度回绕**：theta 从 +3.14 跳到 -3.14 时，累计转角只应该增加 0.01 左右，
   而不是 6.28。这是里程计/姿态积分里最经典的 bug。
2. **外接框宽高比**：圆周运动的轨迹外接框接近正方形，用它来判定"画的是圆"。
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for sub in ("m1_pubsub_demo", "m1_turtle_basics"):
    p = str(ROOT / "src" / sub)
    if p not in sys.path:
        sys.path.insert(0, p)

from m1_pubsub_demo.trajectory_stats import (  # noqa: E402
    TrajectoryStats,
    aspect_ratio,
    bbox,
    normalize_angle,
    path_length,
)


class TestNormalizeAngle(unittest.TestCase):
    def test_常见值不变(self) -> None:
        for a in (0.0, 1.0, -1.0, math.pi - 0.001):
            self.assertAlmostEqual(normalize_angle(a), a)

    def test_大于pi折回(self) -> None:
        self.assertAlmostEqual(normalize_angle(math.pi + 0.1), -math.pi + 0.1, places=9)

    def test_小于负pi折回(self) -> None:
        self.assertAlmostEqual(normalize_angle(-math.pi - 0.1), math.pi - 0.1, places=9)

    def test_多圈折回(self) -> None:
        self.assertAlmostEqual(normalize_angle(4 * math.pi + 0.5), 0.5, places=9)


class TestPathLength(unittest.TestCase):
    def test_三点折线(self) -> None:
        self.assertAlmostEqual(path_length([(0, 0), (3, 4), (3, 4)]), 5.0)

    def test_空和单点(self) -> None:
        self.assertEqual(path_length([]), 0.0)
        self.assertEqual(path_length([(1, 1)]), 0.0)


class TestBbox(unittest.TestCase):
    def test_基本外接框(self) -> None:
        self.assertEqual(bbox([(1, 2), (-1, 5), (3, 0)]), (-1, 3, 0, 5))

    def test_空列表抛异常(self) -> None:
        with self.assertRaises(ValueError):
            bbox([])


class TestAspectRatio(unittest.TestCase):
    def test_圆周轨迹接近1(self) -> None:
        """采样一整圈，外接框宽高比应该非常接近 1。"""
        pts = [(math.cos(t), math.sin(t)) for t in [i * 0.05 for i in range(126)]]
        self.assertAlmostEqual(aspect_ratio(pts), 1.0, places=2)

    def test_纯直线运动比值极端(self) -> None:
        pts = [(float(i), 0.0) for i in range(10)]
        self.assertEqual(aspect_ratio(pts), 0.0)  # 高度为 0


class TestTrajectoryStats(unittest.TestCase):
    def test_累加路程与转角(self) -> None:
        s = TrajectoryStats()
        s.update(0.0, 0.0, 0.0)
        s.update(3.0, 4.0, 1.0)
        self.assertEqual(s.samples, 2)
        self.assertAlmostEqual(s.distance, 5.0)
        self.assertAlmostEqual(s.turn, 1.0)

    def test_角度回绕不会算爆(self) -> None:
        """+3.14 → -3.14 只差 0.003，不是 6.28。"""
        s = TrajectoryStats()
        s.update(0.0, 0.0, math.pi - 0.0015)
        s.update(0.0, 0.0, -math.pi + 0.0015)
        self.assertLess(s.turn, 0.01)

    def test_圆周一圈的统计量(self) -> None:
        s = TrajectoryStats()
        radius, steps = 2.0, 720
        for i in range(steps + 1):
            t = 2.0 * math.pi * i / steps
            s.update(radius * math.cos(t), radius * math.sin(t), t)
        # 路程 ≈ 周长
        self.assertAlmostEqual(s.distance, 2 * math.pi * radius, delta=0.05)
        # 转角 ≈ 2π
        self.assertAlmostEqual(s.turn, 2 * math.pi, delta=0.05)
        # 外接框接近正方形
        self.assertAlmostEqual(s.ratio(), 1.0, places=2)

    def test_to_dict_空对象不崩(self) -> None:
        d = TrajectoryStats().to_dict()
        self.assertEqual(d["samples"], 0)
        self.assertIsNone(d["bbox"]["min_x"])
        self.assertIsNone(d["last_pose"])

    def test_to_dict_结构完整(self) -> None:
        s = TrajectoryStats()
        s.update(1.0, 2.0, 0.5)
        d = s.to_dict()
        self.assertEqual(d["samples"], 1)
        self.assertEqual(d["last_pose"]["x"], 1.0)
        self.assertIn("aspect_ratio", d)


if __name__ == "__main__":
    unittest.main()
