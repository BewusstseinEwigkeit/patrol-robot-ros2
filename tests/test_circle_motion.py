"""圆周运动公式的单元测试（不依赖 ROS，任何 Python 3.10+ 都能跑）。

运行：
    cd patrol-robot-ros2
    PYTHONPATH=src/m1_pubsub_demo:src/m1_turtle_basics python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

# 让测试既能被 colcon 的 pytest 收集，也能直接 python -m unittest 跑
ROOT = Path(__file__).resolve().parent.parent
for sub in ("m1_pubsub_demo", "m1_turtle_basics"):
    p = str(ROOT / "src" / sub)
    if p not in sys.path:
        sys.path.insert(0, p)

from m1_pubsub_demo.circle_motion import (  # noqa: E402
    angular_speed_for,
    expected_period,
    radius_from,
)


class TestAngularSpeed(unittest.TestCase):
    def test_经典例子_v2_r1(self) -> None:
        """turtlesim 官方例子里 v=2, r=1，所以 w 应该是 2。"""
        self.assertAlmostEqual(angular_speed_for(2.0, 1.0), 2.0)

    def test_半径越大转得越慢(self) -> None:
        self.assertLess(angular_speed_for(2.0, 4.0), angular_speed_for(2.0, 1.0))

    def test_显式角速度优先(self) -> None:
        """给了 angular_override 就不看半径，便于复现固定参数。"""
        self.assertAlmostEqual(angular_speed_for(2.0, 1.0, angular_override=0.5), 0.5)

    def test_非法半径抛异常(self) -> None:
        with self.assertRaises(ValueError):
            angular_speed_for(2.0, 0.0)
        with self.assertRaises(ValueError):
            angular_speed_for(2.0, -1.0)


class TestRadiusRoundTrip(unittest.TestCase):
    def test_推导与反推一致(self) -> None:
        for radius in (0.5, 1.0, 1.5, 3.0):
            w = angular_speed_for(2.0, radius)
            self.assertAlmostEqual(radius_from(2.0, w), radius, places=9)

    def test_角速度为零时半径无穷(self) -> None:
        self.assertEqual(radius_from(2.0, 0.0), float("inf"))


class TestPeriod(unittest.TestCase):
    def test_一圈时间(self) -> None:
        """v=2 m/s，r=1 m → 周长 2π ≈ 6.283 m → 约 3.14 s。"""
        self.assertAlmostEqual(expected_period(2.0, 1.0), math.pi, places=6)

    def test_线速度为零抛异常(self) -> None:
        with self.assertRaises(ValueError):
            expected_period(0.0, 1.0)


if __name__ == "__main__":
    unittest.main()
