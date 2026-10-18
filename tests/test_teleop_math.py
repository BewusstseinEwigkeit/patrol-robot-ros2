"""键盘映射的单元测试（不依赖 ROS，也不需要 TTY）。

W1 的键盘遥控最容易出的错是"松手不停车"和"按到未知键就崩"。
这两个都在这里钉死。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for sub in ("m1_pubsub_demo", "m1_turtle_basics"):
    p = str(ROOT / "src" / sub)
    if p not in sys.path:
        sys.path.insert(0, p)

from m1_turtle_basics.teleop_math import (  # noqa: E402
    MOVE_KEYS,
    is_quit_key,
    twist_from_key,
)


class TestTwistFromKey(unittest.TestCase):
    def test_前进后退(self) -> None:
        self.assertEqual(twist_from_key("w").linear_x, 2.0)
        self.assertEqual(twist_from_key("s").linear_x, -2.0)

    def test_左转右转方向相反(self) -> None:
        self.assertGreater(twist_from_key("a").angular_z, 0)
        self.assertLess(twist_from_key("d").angular_z, 0)

    def test_空格急停(self) -> None:
        self.assertTrue(twist_from_key(" ").is_stop())

    def test_未知键返回零速度而不是抛异常(self) -> None:
        """终端里误按方向键、Ctrl 组合键不能把遥控程序搞崩。"""
        for key in ("\x1b", "[", "A", "z", "\t", "\x03"):
            t = twist_from_key(key)
            self.assertTrue(t.is_stop(), f"按键 {key!r} 应该停车")

    def test_自定义速度(self) -> None:
        self.assertEqual(twist_from_key("w", linear_speed=5.0).linear_x, 5.0)
        self.assertEqual(twist_from_key("a", angular_speed=1.5).angular_z, 1.5)

    def test_速度取绝对值避免方向反转(self) -> None:
        """即使调用方传了负数速度，w 也应该是前进、a 也应该是左转。"""
        self.assertGreater(twist_from_key("w", linear_speed=-3.0).linear_x, 0)
        self.assertGreater(twist_from_key("a", angular_speed=-3.0).angular_z, 0)


class TestQuitKey(unittest.TestCase):
    def test_q与ctrl_c退出(self) -> None:
        self.assertTrue(is_quit_key("q"))
        self.assertTrue(is_quit_key("\x03"))

    def test_其他键不退出(self) -> None:
        for key in MOVE_KEYS + ("x", "1"):
            self.assertFalse(is_quit_key(key))


if __name__ == "__main__":
    unittest.main()
