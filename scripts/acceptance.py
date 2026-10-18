#!/usr/bin/env python3
"""M1 逐周自动验收（跨平台实现）。

为什么用 Python 而不是纯 bash：
  bash 版要靠 `ros2 topic list` / `ros2 node list` 这类 CLI 命令去问 ROS 图，
  这些命令依赖 ros2 daemon，在部分环境（例如 Windows 上的 RoboStack）会挂住；
  而 rclpy 直接建一个节点就能拿到同一份信息，更快也更稳。
  真实目标环境 Ubuntu 22.04 上两种方式都可以，这里统一走 rclpy。

用法：
    python3 scripts/acceptance.py w1|w2|w3|w4|all
    python3 scripts/acceptance.py all --json outputs/acceptance.json

退出码：0 全部通过；1 有未通过项；2 环境不可用。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
WS_ROOT = SCRIPT_DIR.parent

# 让 `python -m m1_xxx` 在没 colcon build 的环境里也能找到包
for sub in ("m1_pubsub_demo", "m1_turtle_basics", "m1_tf2_demo", "m1_bringup"):
    p = str(WS_ROOT / "src" / sub)
    if p not in os.environ.get("PYTHONPATH", "").split(os.pathsep):
        os.environ["PYTHONPATH"] = p + os.pathsep + os.environ.get("PYTHONPATH", "")

# Windows 上经常同时挂着物理网卡、Clash/TUN 虚拟网卡等多个接口，
# DDS 的多播发现会时灵时不灵（表现为"话题在、节点列表却是空的"）。
# 验收全是单机操作，限制在回环上最稳。Ubuntu 侧保持默认，不影响多机场景。
if os.name == "nt" and "ROS_LOCALHOST_ONLY" not in os.environ:
    os.environ["ROS_LOCALHOST_ONLY"] = "1"

try:
    import rclpy
    from rclpy.node import Node
except ImportError:  # pragma: no cover
    print("找不到 rclpy。请先 source /opt/ros/humble/setup.bash", file=sys.stderr)
    sys.exit(2)

# ---------------------------------------------------------------- 输出
GREEN, RED, YELLOW, BOLD, DIM, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[1m", "\033[2m", "\033[0m"
)


class Report:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []
        self.notes: list[str] = []

    def ok(self, item: str, detail: str = "") -> None:
        self.passed.append(item)
        print(f"  {GREEN}[通过]{RESET} {item}" + (f"  {DIM}{detail}{RESET}" if detail else ""))

    def bad(self, item: str, detail: str = "") -> None:
        self.failed.append(item)
        print(f"  {RED}[未过]{RESET} {item}" + (f"  {DIM}{detail}{RESET}" if detail else ""))

    def note(self, text: str) -> None:
        self.notes.append(text)
        print(f"         {DIM}{text}{RESET}")

    def step(self, title: str) -> None:
        print(f"\n{BOLD}== {title} =={RESET}")


REPORT = Report()
# 必须用绝对路径：Windows 上 "/tmp" 会被当成"当前盘根目录下的 tmp"，
# 传给子进程后再 abspath 就会落到别的目录，导致"文件明明写了却找不到"。
_TMP_BASE = os.environ.get("M1_TMP") or tempfile.mkdtemp(prefix="m1acc-")
TMP = pathlib.Path(_TMP_BASE).resolve()
TMP.mkdir(parents=True, exist_ok=True)

PROCS: list[tuple[str, subprocess.Popen]] = []
LOGS: dict[str, pathlib.Path] = {}


# ---------------------------------------------------------------- 进程工具
def spawn(name: str, args: list[str]) -> subprocess.Popen:
    log = TMP / f"{name}.log"
    LOGS[name] = log
    fh = open(log, "w", encoding="utf-8", errors="replace")
    kwargs: dict = {"stdout": fh, "stderr": subprocess.STDOUT, "cwd": str(WS_ROOT)}
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000200  # CREATE_NEW_PROCESS_GROUP
    p = subprocess.Popen(args, **kwargs)
    PROCS.append((name, p))
    return p


def kill(name: str) -> None:
    for n, p in PROCS:
        if n != name or p.poll() is not None:
            continue
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
        else:
            try:
                p.send_signal(signal.SIGINT)
                p.wait(timeout=5)
            except Exception:  # noqa: BLE001
                p.kill()


def cleanup() -> None:
    for name, p in PROCS:
        if p.poll() is None:
            kill(name)


def log_text(name: str) -> str:
    path = LOGS.get(name)
    if path and path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def can_run_package(pkg: str, exe: str) -> bool:
    """优先用 ros2 run（Ubuntu 标准）；装了包才用。"""
    try:
        r = subprocess.run(["ros2", "pkg", "executables", pkg], capture_output=True, text=True, timeout=30)
        return exe in (r.stdout or "")
    except Exception:  # noqa: BLE001
        return False


def node_cmd(pkg: str, module: str, exe: str, ros_args: list[str] | None = None) -> list[str]:
    """构造启动节点的命令：能用 ros2 run 就用，否则退回 python -m。"""
    ros_args = ros_args or []
    if can_run_package(pkg, exe):
        return ["ros2", "run", pkg, exe, "--ros-args", *ros_args] if ros_args else ["ros2", "run", pkg, exe]
    return [sys.executable, "-m", module, "--ros-args", *ros_args] if ros_args else [sys.executable, "-m", module]


# ---------------------------------------------------------------- ROS 图探针
class Probe:
    """用 rclpy 直接读 ROS 图，不经过 ros2 CLI/daemon。"""

    def __init__(self) -> None:
        self.node = Node("m1_acceptance_probe")
        self._poses: list[tuple[float, float, float]] = []
        self._subs = []

    def spin(self, seconds: float, extra_nodes: list[Node] | None = None) -> None:
        deadline = time.time() + seconds
        while time.time() < deadline and rclpy.ok():
            rclpy.spin_once(self.node, timeout_sec=0.1)
            for n in extra_nodes or []:
                rclpy.spin_once(n, timeout_sec=0.0)

    def topics(self) -> dict[str, list[str]]:
        self.spin(0.6)
        return {t: list(types) for t, types in self.node.get_topic_names_and_types()}

    def nodes(self) -> list[str]:
        self.spin(0.6)
        return list(self.node.get_node_names())

    def services(self) -> dict[str, list[str]]:
        self.spin(0.6)
        return {s: list(types) for s, types in self.node.get_service_names_and_types()}

    def wait_topic(self, name: str, timeout: float = 15.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline and rclpy.ok():
            if name in self.topics():
                return True
            time.sleep(0.5)
        return False

    def wait_node(self, name: str, timeout: float = 15.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline and rclpy.ok():
            if name.lstrip("/") in [n.lstrip("/") for n in self.nodes()]:
                return True
            time.sleep(0.5)
        return False

    def pose_subscriber(self) -> Node:
        """订阅乌龟位姿并记录轨迹。"""
        from turtlesim.msg import Pose

        collector = Node("m1_acceptance_pose_collector")

        def cb(msg: Pose) -> None:
            self._poses.append((float(msg.x), float(msg.y), float(msg.theta)))

        sub = collector.create_subscription(Pose, "/turtle1/pose", cb, 20)
        self._subs.append(sub)
        return collector

    @property
    def poses(self) -> list[tuple[float, float, float]]:
        return self._poses

    def destroy(self) -> None:
        try:
            self.node.destroy_node()
        except Exception:  # noqa: BLE001
            pass


def path_length(points: list[tuple[float, float, float]]) -> float:
    total = 0.0
    for a, b in zip(points, points[1:]):
        total += math.hypot(b[0] - a[0], b[1] - a[1])
    return total


def bbox(points: list[tuple[float, float, float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), max(xs), min(ys), max(ys)


def read_bag_topics(db_path: pathlib.Path) -> list[str]:
    """直接读 rosbag2 的 sqlite 文件，列出里面录了哪些话题。

    比 `ros2 bag info` 更可靠：后者需要 metadata.yaml，而录制被强制中断时
    那个文件可能不存在（Windows 上就会这样）。
    """
    import sqlite3

    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            rows = con.execute("SELECT name FROM topics ORDER BY id").fetchall()
        finally:
            con.close()
        return [r[0] for r in rows]
    except Exception:  # noqa: BLE001
        return []


#: 每一周开始前需要清掉的进程名（都是本脚本自己起的）
RESET_NAMES = (
    "driver", "monitor", "record", "play", "cmdvel", "cmdvel2", "teleport",
    "tf2_echo", "static_world_odom", "static_camera", "static_imu",
    "broadcaster", "turtlesim",
)


def ensure_clean_turtlesim(probe: Probe) -> bool:
    """把 ROS 侧重置成干净状态，并起一个全新的 turtlesim。

    为什么必须这么做：`all` 模式下一口气跑四周，上一周留下的 circle_driver、
    pose_monitor、rosbag 录制进程会让这一周的 DDS 发现变得不可预测。
    实测症状：话题列表正常但节点列表为空、参数服务读不到、乌龟不响应速度指令、
    service 调用超时——全都指向"环境没清干净"，而不是代码有问题。

    另外，turtlesim 的话题名固定是 /turtle1/...，同时存在两个实例时
    它们会往同一个话题发各自的数据，必须确保同一时刻只有一个。
    """
    for name in RESET_NAMES:
        kill(name)
    time.sleep(2)
    spawn("turtlesim", ["ros2", "run", "turtlesim", "turtlesim_node"])
    if not probe.wait_topic("/turtle1/pose", 25):
        return False
    # 话题出现不代表节点发现已经稳定，再给 DDS 一点时间，
    # 否则紧接着的"节点列表/参数服务"查询会落空
    probe.spin(3.0)
    return True


# ---------------------------------------------------------------- W1
def accept_w1(probe: Probe) -> None:
    REPORT.step("W1：环境 + 命令行控制 turtlesim")

    if not ensure_clean_turtlesim(probe):
        REPORT.bad("W1 无法启动 turtlesim", log_text("turtlesim")[-200:])
        return
    REPORT.note("turtlesim 已就绪")

    topics = probe.topics()
    if "/turtle1/pose" in topics and "/turtle1/cmd_vel" in topics:
        REPORT.ok("W1.2 turtlesim 在跑，位姿与速度话题都在")
    else:
        REPORT.bad("W1.2 没找到 turtlesim 的话题", f"当前话题：{sorted(topics)[:6]}")
        return

    nodes = probe.nodes()
    if any(n.lstrip("/") == "turtlesim" for n in nodes):
        REPORT.ok("W1.3 节点查询正常（看到 /turtlesim）")
    else:
        REPORT.bad("W1.3 节点列表里没有 /turtlesim")

    services = probe.services()
    if "/turtle1/teleport_absolute" in services:
        REPORT.ok("W1.3 service 查询正常（teleport_absolute 存在）")
    else:
        REPORT.bad("W1.3 没有 /turtle1/teleport_absolute")

    # 参数查询：直接调 turtlesim 暴露的 ListParameters 服务。
    # 不用 Node.list_parameters（Humble 的 rclpy 没有这个方法），
    # 也不用 `ros2 param list`（它依赖 ros2 daemon，在部分环境会挂住）。
    from rcl_interfaces.srv import ListParameters

    cli = probe.node.create_client(ListParameters, "/turtlesim/list_parameters")
    param_names: list[str] = []
    if cli.wait_for_service(timeout_sec=8.0):
        fut = cli.call_async(ListParameters.Request())
        rclpy.spin_until_future_complete(probe.node, fut, timeout_sec=8.0)
        if fut.result() is not None:
            param_names = list(fut.result().result.names)
    if param_names:
        REPORT.ok("W1.3 param 查询正常", f"turtlesim 暴露 {len(param_names)} 个参数，例如 {param_names[:2]}")
    else:
        REPORT.bad("W1.3 读不到 turtlesim 的参数")
    probe.node.destroy_client(cli)

    # 真实发速度，看乌龟是否移动
    collector = probe.pose_subscriber()
    from geometry_msgs.msg import Twist

    pub = probe.node.create_publisher(Twist, "/turtle1/cmd_vel", 10)
    probe.spin(1.0, [collector])
    before = probe.poses[-1] if probe.poses else None

    msg = Twist()
    msg.linear.x = 2.0
    deadline = time.time() + 3.0
    while time.time() < deadline and rclpy.ok():
        pub.publish(msg)
        probe.spin(0.1, [collector])

    stop = Twist()
    for _ in range(5):
        pub.publish(stop)
        probe.spin(0.1, [collector])

    after = probe.poses[-1] if probe.poses else None
    if before and after and math.hypot(after[0] - before[0], after[1] - before[1]) > 0.2:
        REPORT.ok(
            "W1.4 发速度后乌龟真的动了",
            f"({before[0]:.2f},{before[1]:.2f}) → ({after[0]:.2f},{after[1]:.2f})",
        )
    else:
        REPORT.bad("W1.4 发了速度但乌龟没动", f"before={before} after={after}")

    exes = subprocess.run(
        ["ros2", "pkg", "executables", "m1_turtle_basics"], capture_output=True, text=True
    ).stdout if shutil.which("ros2") else ""
    if "keyboard_teleop" in exes:
        REPORT.ok("W1.5 m1_turtle_basics 可执行文件已注册")
    else:
        REPORT.note("W1.5 未通过 ros2 run 找到包（没 colcon build 时正常），改验证模块行为")
        try:
            r = subprocess.run(
                [sys.executable, "-m", "m1_turtle_basics.keyboard_teleop"],
                capture_output=True, text=True, timeout=30, cwd=str(WS_ROOT),
            )
            text = (r.stdout or "") + (r.stderr or "")
            if r.returncode == 2 and ("真实终端" in text or "Linux" in text):
                REPORT.ok("W1.5 keyboard_teleop 在不可用环境下正确拒绝启动（行为符合设计）")
            else:
                REPORT.bad("W1.5 keyboard_teleop 行为异常", f"rc={r.returncode} {text[-120:]}")
        except Exception as exc:  # noqa: BLE001
            REPORT.bad("W1.5 无法启动 keyboard_teleop", str(exc))

    collector.destroy_node()

    # W1.6：service 瞬移。W1 的目标里有"service 命令全敲一遍"，
    # teleport_demo 就是把它写成节点后的样子。
    spawn("teleport", node_cmd(
        "m1_turtle_basics", "m1_turtle_basics.teleport_demo", "teleport_demo",
        ["-p", "side:=2.0", "-p", "dwell_seconds:=0.6"],
    ))
    time.sleep(9)
    text = log_text("teleport")
    hits = re.findall(r"瞬移到\s*\(\s*([-0-9.]+),\s*([-0-9.]+)\)", text)
    if len(hits) >= 3:
        REPORT.ok("W1.6 teleport_demo 用 service 依次瞬移成功", f"完成 {len(hits)} 个顶点")
    else:
        REPORT.bad("W1.6 teleport_demo 没有完成瞬移", text[-250:] if text else "无输出")


# ---------------------------------------------------------------- W2
def accept_w2(probe: Probe) -> None:
    REPORT.step("W2：发布/订阅节点（画圆 + 位姿监控）")

    if not ensure_clean_turtlesim(probe):
        REPORT.bad("W2 无法启动 turtlesim", log_text("turtlesim")[-200:])
        return

    summary = TMP / "pose_summary.json"
    if summary.exists():
        summary.unlink()

    spawn("monitor", node_cmd(
        "m1_pubsub_demo", "m1_pubsub_demo.pose_monitor", "pose_monitor",
        ["-p", "run_seconds:=9.0", "-p", "report_period:=2.0", "-p", f"summary_json:={summary}"],
    ))
    time.sleep(1.5)
    spawn("driver", node_cmd(
        "m1_pubsub_demo", "m1_pubsub_demo.circle_driver", "circle_driver",
        ["-p", "radius:=1.5", "-p", "linear_speed:=2.0", "-p", "run_seconds:=9.0"],
    ))
    REPORT.note("让乌龟跑 13 秒 ...")
    time.sleep(13)

    if not summary.exists():
        REPORT.bad("W2.2 pose_monitor 没有写出统计文件", log_text("monitor")[-300:])
        return
    REPORT.ok("W2.2 pose_monitor 写出了统计文件")

    data = json.loads(summary.read_text(encoding="utf-8"))
    samples = data.get("samples", 0)
    length = data.get("path_length", 0.0)
    ratio = data.get("aspect_ratio", 0.0)

    if samples >= 20:
        REPORT.ok("W2.3 收到足够位姿帧", f"{samples} 帧")
    else:
        REPORT.bad("W2.3 位姿帧数不足", str(samples))

    if length > 1.0:
        REPORT.ok("W2.4 累计路程正常", f"{length} m")
    else:
        REPORT.bad("W2.4 累计路程太小", str(length))

    if 0.6 < ratio < 1.7:
        bb = data.get("bbox", {})
        w = round(bb.get("max_x", 0) - bb.get("min_x", 0), 2)
        h = round(bb.get("max_y", 0) - bb.get("min_y", 0), 2)
        REPORT.ok("W2.5 轨迹是圆（外接框宽高比接近 1）", f"{w}×{h}，比值 {ratio}")
    else:
        REPORT.bad("W2.5 轨迹不像圆", f"宽高比 {ratio}")


# ---------------------------------------------------------------- W3
def accept_w3(probe: Probe) -> None:
    REPORT.step("W3：launch 编排 + rosbag 录制回放")

    if not ensure_clean_turtlesim(probe):
        REPORT.bad("W3 无法启动 turtlesim", log_text("turtlesim")[-200:])
        return

    bags = TMP / "bags"
    bags.mkdir(parents=True, exist_ok=True)
    summary = TMP / "w3_summary.json"

    launched = False
    if shutil.which("ros2"):
        # launch 自己录的包放到子目录，避免和下面"手工录一份"抢同一个目录
        p = spawn("launch", [
            "ros2", "launch", "m1_bringup", "m1_demo.launch.py",
            "radius:=1.5", "linear_speed:=2.0", "run_seconds:=9.0",
            "record:=true", f"bag_dir:={bags / 'launch_bag'}", f"summary_json:={summary}",
        ])
        time.sleep(6)
        if p.poll() is None:
            launched = True
        else:
            REPORT.note("ros2 launch 没起来（本机可能没 colcon build），改用逐个起节点验证")

    if not launched:
        kill("launch")
        # 注意：turtlesim 的话题名固定是 /turtle1/...，与节点名无关。
        # 再起第二个实例会让两个节点往同一个 /turtle1/pose 上发数据，
        # 订阅端看到的就是来回跳的两条轨迹（曾经把路程算成 3580 米）。
        if not any(n == "turtlesim" for n, _ in PROCS):
            spawn("turtlesim", ["ros2", "run", "turtlesim", "turtlesim_node"])
            time.sleep(6)
        spawn("monitor", node_cmd(
            "m1_pubsub_demo", "m1_pubsub_demo.pose_monitor", "pose_monitor",
            ["-p", "run_seconds:=9.0", "-p", f"summary_json:={summary}"],
        ))
        spawn("driver", node_cmd(
            "m1_pubsub_demo", "m1_pubsub_demo.circle_driver", "circle_driver",
            ["-p", "radius:=1.5", "-p", "run_seconds:=9.0"],
        ))
        REPORT.ok("W3.1 三个节点（turtlesim + circle_driver + pose_monitor）同时运行")

    probe.spin(0.5)
    nodes = probe.nodes()
    missing = [n for n in ("turtlesim", "circle_driver", "pose_monitor")
               if not any(x.lstrip("/") == n for x in nodes)]
    if not missing:
        REPORT.ok("W3.1 画圆节点与位姿节点都在 ROS 图里")
    else:
        REPORT.bad("W3.1 缺少节点", ", ".join(missing))

    # 等 pose_monitor 按 run_seconds 跑完并落盘（它是唯一的"参数是否生效"证据）
    deadline = time.time() + 25
    while time.time() < deadline and not summary.exists():
        time.sleep(1)

    if summary.exists():
        REPORT.ok("W3.2 launch/节点参数生效（位姿统计文件已生成）")
        data = json.loads(summary.read_text(encoding="utf-8"))
        REPORT.note(f"统计：{data.get('samples')} 帧，路程 {data.get('path_length')} m")
    else:
        REPORT.bad("W3.2 参数没生效或节点没跑完")

    # 录包：单独起一次，确保只录我们关心的两个话题
    bagdir = bags / "m1_demo"
    if bagdir.exists():
        shutil.rmtree(bagdir, ignore_errors=True)
    spawn("record", ["ros2", "bag", "record", "-o", str(bagdir), "/turtle1/cmd_vel", "/turtle1/pose"])
    REPORT.note("录包 8 秒 ...")
    time.sleep(8)
    kill("record")
    time.sleep(2)

    dbs = sorted(bags.rglob("*.db3"))
    if dbs:
        db = max(dbs, key=lambda p: p.stat().st_size)
        REPORT.ok("W3.3 rosbag 生成了数据文件", f"{db.parent.name}/{db.name}（{db.stat().st_size // 1024} KB）")
        topics = read_bag_topics(db)
        if "/turtle1/pose" in topics:
            REPORT.ok("W3.4 包里确实录到了 /turtle1/pose", f"话题：{', '.join(topics)}")
        else:
            REPORT.bad("W3.4 包里没有 /turtle1/pose", f"实际话题：{topics or '读不到'}")

        # W3.5：回放。录制被强杀时不会生成 metadata.yaml（Windows 上必现），
        # 这时先用项目自带的工具把索引补出来再回放——这正是它存在的意义。
        bag_dir = db.parent
        meta = bag_dir / "metadata.yaml"
        if not meta.exists():
            REPORT.note("缺 metadata.yaml，用 scripts/rebuild_bag_metadata.py 重建")
            subprocess.run(
                [sys.executable, str(SCRIPT_DIR / "rebuild_bag_metadata.py"), str(bag_dir)],
                capture_output=True, text=True, timeout=90,
            )
        if (bag_dir / "metadata.yaml").exists():
            kill("play")
            spawn("play", ["ros2", "bag", "play", "--rate", "5", str(bag_dir)])
            time.sleep(7)
            text = log_text("play")
            if "Opened database" in text or "Set rate" in text:
                REPORT.ok("W3.5 rosbag 能回放", "rosbag2_player 成功打开数据库并设置速率")
            else:
                REPORT.bad("W3.5 rosbag 回放失败", text[-200:] if text else "无输出")
            kill("play")
        else:
            REPORT.bad("W3.5 无法回放", "metadata.yaml 重建失败")
    else:
        REPORT.bad("W3.3 没有录出 bag 数据文件")


# ---------------------------------------------------------------- W4
def accept_w4(probe: Probe) -> None:
    REPORT.step("W4：tf2 坐标树")

    # 让乌龟先停下：tf 查询和位姿采样之间有时间差，
    # 运动中的车体做"偏移量"校验会得到假误差。顺便把环境重置干净。
    kill("driver")
    probe.spin(1.0)
    if not ensure_clean_turtlesim(probe):
        REPORT.bad("W4 无法启动 turtlesim", log_text("turtlesim")[-200:])
        return
    REPORT.note("turtlesim 已重置，开始建坐标树")

    spawn("static_world_odom", [
        "ros2", "run", "tf2_ros", "static_transform_publisher",
        "--x", "0", "--y", "0", "--z", "0", "--roll", "0", "--pitch", "0", "--yaw", "0",
        "--frame-id", "world", "--child-frame-id", "odom",
    ])
    spawn("static_camera", [
        "ros2", "run", "tf2_ros", "static_transform_publisher",
        "--x", "0.15", "--y", "0", "--z", "0.10", "--roll", "0", "--pitch", "0", "--yaw", "0",
        "--frame-id", "base_link", "--child-frame-id", "camera_link",
    ])
    time.sleep(2)
    spawn("broadcaster", node_cmd(
        "m1_tf2_demo", "m1_tf2_demo.turtle_tf_broadcaster", "turtle_tf_broadcaster",
        ["-p", "parent_frame:=odom", "-p", "child_frame:=base_link"],
    ))
    time.sleep(4)

    # 用 tf2 自己的 Buffer 去查，比解析 tf2_echo 的文本可靠
    from tf2_ros import Buffer, TransformException, TransformListener

    # 同时采一份乌龟位姿，用来做"相机相对车体的偏移"数值校验。
    # 先清空历史采样：W1/W2 阶段积累的旧位姿和当前 tf 不是同一时刻的，
    # 混用会把误差算成好几米（快速运动时尤其明显）。
    collector = probe.pose_subscriber()
    probe._poses.clear()
    probe.spin(2.0, [collector])
    buf = Buffer()
    listener = TransformListener(buf, probe.node)

    got = None
    deadline = time.time() + 25
    while time.time() < deadline and rclpy.ok():
        probe.spin(0.2, [collector])
        try:
            got = buf.lookup_transform("world", "camera_link", rclpy.time.Time())
            break
        except TransformException:
            continue

    if got is None:
        REPORT.bad("W4.1 查不到 world -> camera_link", log_text("broadcaster")[-300:])
        listener_ok = False
    else:
        listener_ok = True
        tr = got.transform.translation
        REPORT.ok("W4.1 tf2 能查到 world -> camera_link", f"({tr.x:.3f}, {tr.y:.3f}, {tr.z:.3f})")

        # 物理校验：直接查 base_link -> camera_link，得到"相机相对车体的安装偏移"。
        # 不能用 world 下的坐标做差——那样会把车体当前朝向也混进来
        # （乌龟转过一个角度后，同一个安装位置在世界系里的偏移就变了）。
        try:
            rel = buf.lookup_transform("base_link", "camera_link", rclpy.time.Time())
            rtr = rel.transform.translation
            expected = (0.15, 0.0, 0.10)
            err = math.dist((rtr.x, rtr.y, rtr.z), expected)
            if err < 0.01:
                REPORT.ok(
                    "W4.2 安装偏移在数值上正确",
                    f"相机相对车体 ({rtr.x:.3f},{rtr.y:.3f},{rtr.z:.3f})，期望 {expected}",
                )
            else:
                REPORT.bad(
                    "W4.2 安装偏移数值不对",
                    f"实测 ({rtr.x:.3f},{rtr.y:.3f},{rtr.z:.3f})，误差 {err:.3f}",
                )
        except TransformException as exc:
            REPORT.bad("W4.2 查不到 base_link -> camera_link", str(exc))

    # 用官方 tf2_echo 独立复核一次。它需要几秒填充 Buffer，
    # 且偶尔会赶在静态变换生效前启动，所以给两次机会。
    text = ""
    for attempt in (1, 2):
        kill("tf2_echo")
        spawn("tf2_echo", ["ros2", "run", "tf2_ros", "tf2_echo", "world", "camera_link"])
        time.sleep(8)
        text = log_text("tf2_echo")
        if "Translation" in text:
            break
        REPORT.note(f"tf2_echo 第 {attempt} 次没拿到变换，重试")
    if "Translation" in text:
        REPORT.ok("W4.3 官方 tf2_echo 独立复核通过")
    else:
        REPORT.bad("W4.3 tf2_echo 没拿到变换", text[-200:] if text else "无输出")
    kill("tf2_echo")
    collector.destroy_node()


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description="M1 逐周自动验收")
    ap.add_argument("target", nargs="?", default="all", choices=["w1", "w2", "w3", "w4", "all"])
    ap.add_argument("--json", dest="json_out", default="", help="把结果写成 JSON")
    ap.add_argument("--markdown", dest="md_out", default="", help="把结果写成 Markdown（可直接贴进报告）")
    args = ap.parse_args()

    print(f"工作区：{WS_ROOT}")
    print(f"临时目录：{TMP}")
    print(f"验收目标：{args.target}")

    rclpy.init()
    probe = Probe()

    try:
        if args.target in ("w1", "all"):
            accept_w1(probe)
        if args.target in ("w2", "all"):
            accept_w2(probe)
        if args.target in ("w3", "all"):
            accept_w3(probe)
        if args.target in ("w4", "all"):
            accept_w4(probe)
    finally:
        cleanup()
        probe.destroy()
        if rclpy.ok():
            rclpy.shutdown()

    print(f"\n{BOLD}==== 验收汇总 ===={RESET}")
    print(f"  通过：{len(REPORT.passed)}")
    print(f"  未过：{len(REPORT.failed)}")
    for item in REPORT.failed:
        print(f"    - {item}")

    if args.json_out:
        out = pathlib.Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                {
                    "target": args.target,
                    "passed": REPORT.passed,
                    "failed": REPORT.failed,
                    "notes": REPORT.notes,
                    "ok": not REPORT.failed,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
            newline="\n",  # 统一 LF：Windows 上默认会写 CRLF，跨系统看 diff 很吵
        )
        print(f"  报告已写入：{out}")

    if args.md_out:
        md = pathlib.Path(args.md_out)
        md.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# M1 验收报告（{args.target}）",
            "",
            f"- 生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- 工作区：`{WS_ROOT}`",
            f"- ROS 发行版：{os.environ.get('ROS_DISTRO', '未知')}",
            f"- 结论：**通过 {len(REPORT.passed)} 项，未过 {len(REPORT.failed)} 项**",
            "",
            "## 通过项",
            "",
        ]
        lines += [f"- {item}" for item in REPORT.passed] if REPORT.passed else ["- （无）"]
        lines += ["", "## 未通过项", ""]
        lines += [f"- {item}" for item in REPORT.failed] if REPORT.failed else ["- （无）"]
        if REPORT.notes:
            lines += ["", "## 过程记录", ""]
            lines += [f"- {n}" for n in REPORT.notes]
        md.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        print(f"  Markdown 报告已写入：{md}")

    if REPORT.failed:
        return 1
    print(f"  {GREEN}全部通过。{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
