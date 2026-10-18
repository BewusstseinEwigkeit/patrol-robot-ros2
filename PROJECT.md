# PROJECT.md — patrol-robot-ros2

## 用途

「校园巡检机器人无线充电对位系统」项目 **M1（全员共同月：Linux + ROS 2 实操）** 的实训与验收工作区。

面向三个人（定位线 / 视觉对位线 / 平台集成线）共用，目标是让 M1 月末检查点
「不看教程能独立做出 launch 拉起 画圆 + 打印位姿 + 录包 三个节点」有一个**可以直接照着跑通、并能自动验收**的落点。

本目录不替代任何人的自学，它提供三样东西：

1. **可运行的正确代码**：W1–W4 每一周的产出物，都能在本机真实跑起来，不是伪代码。
2. **自动验收**：`scripts/acceptance.sh` 一条命令检查当周检查点是否真的达标，避免"看起来会了"。
3. **踩坑记录**：把已经踩过的坑（CRLF、conda 激活、rosbag 权限、tf2 时间戳等）提前写成条目，省掉重复试错。

## 当前状态

- 状态：**active**（2026-10-18 建立）
- 已完成：项目骨架、M1 四周代码、环境脚本、验收脚本、操作手册
- 验证状态：见 `docs/04_验证边界说明.md`（逐项标注「本机真实跑通 / 静态检查 / 未验证」）

## 技术栈

| 项 | 选择 | 说明 |
|---|---|---|
| 操作系统 | Ubuntu 22.04 LTS | 项目既定环境（Windows 双系统，`D:\Vibe Coding` 在 Ubuntu 下是 `/media/<你的用户名>/Data/Vibe Coding`） |
| ROS | ROS 2 Humble | LTS，与项目计划一致 |
| 语言 | Python 3.10（rclpy） | M1 阶段统一用 Python，避免 C++ 编译分散精力 |
| 构建 | colcon | |
| 工具 | tf2 / rosbag2 / launch / rqt | |

## 输入 / 输出

- 输入：`D:\QQ_Message\巡检机器人项目技术栈与三人计划.md`（团队计划表，2026-10-13）
- 输出：可运行的 ROS 2 工作区（`src/`）、验收报告（`outputs/`）、运行证据（`evidence/`）

## 启动 / 测试命令

Ubuntu 22.04 下：

```bash
cd "/media/<你的用户名>/Data/Vibe Coding/patrol-robot-ros2"

# 1) 首次：装 ROS 2 Humble（已装可跳过）
bash scripts/setup_ubuntu_ros2.sh

# 2) 每个新终端：激活环境
source /opt/ros/humble/setup.bash

# 3) 环境自检（W1 检查点）
bash scripts/check_env.sh

# 4) 编译
bash scripts/build.sh

# 5) 当周验收
bash scripts/acceptance.sh w1     # 或 w2 / w3 / w4 / all
```

Windows 侧（本机没有 ROS，只用于查看和编辑文件）：

```powershell
# 只看文件、跑不了 ROS 节点
Get-ChildItem "D:\Vibe Coding\patrol-robot-ros2"
```

## 目录结构

```text
patrol-robot-ros2/
├─ PROJECT.md              # 本文件
├─ docs/                   # 操作手册、逐周任务、踩坑日志、验证边界
├─ scripts/                # 环境搭建、自检、编译、验收
│   ├─ setup_ubuntu_ros2.sh   # 装 ROS 2 Humble（幂等）
│   ├─ check_env.sh           # 环境自检
│   ├─ build.sh               # colcon 编译
│   ├─ w1_console_circle.sh   # W1：纯命令行控制乌龟演示
│   ├─ acceptance.sh          # 验收入口（bash 薄包装）
│   ├─ acceptance.py          # 验收实现（rclpy 直读 ROS 图，跨平台）
│   └─ rebuild_bag_metadata.py # 从 .db3 重建 rosbag 的 metadata.yaml（被强杀后救包）
├─ src/                    # ROS 2 包（colcon 工作区）
│   ├─ m1_turtle_basics/   # W1：命令行控制 turtlesim + 键盘遥控
│   ├─ m1_pubsub_demo/     # W2：发布/订阅节点（画圆 + 位姿打印）
│   ├─ m1_bringup/         # W3：launch 文件、参数、rosbag 录放
│   └─ m1_tf2_demo/        # W4：tf2 坐标树（world→odom→base_link→sensor）
├─ tests/                  # 离线单元测试（不依赖 ROS 也能跑的部分）
├─ outputs/                # 验收报告
└─ evidence/               # 真实运行证据（终端日志、录包信息）
```

## 验证状态（一句话版）

在真实的 ROS 2 Humble 上跑过：31 项单元测试、9 个模块导入、
W1–W4 共 **20 项验收全部通过**，含"轨迹外接框 3.0×3.0 = 设定直径"
和"tf2 安装偏移 (0.150, 0.000, 0.100) = 设定值"两处数值级校验。
未验证项（colcon 安装、launch 端到端、交互式键盘）逐条列在
`docs/04_验证边界说明.md` 第 3 节，并给了补验方法。

## 与项目计划的对应

| 计划周 | 计划内容 | 本工作区落点 | 验收命令 |
|---|---|---|---|
| W1 | 装 Ubuntu+ROS2；命令行/git；turtlesim；topic/node/service/param | `scripts/setup_ubuntu_ros2.sh`、`scripts/check_env.sh`、`src/m1_turtle_basics` | `acceptance.sh w1` |
| W2 | 建包、写发布/订阅节点、colcon build | `src/m1_pubsub_demo` | `acceptance.sh w2` |
| W3 | launch、参数传递、rosbag 录制与回放 | `src/m1_bringup` | `acceptance.sh w3` |
| W4 | tf2 broadcaster/listener、月末综合验收 | `src/m1_tf2_demo` | `acceptance.sh w4` |

## 相关项目

- `quartus-lab2-trolley`（数电实验，无关但同为用户课程线）
- 上游计划文件：`D:\QQ_Message\巡检机器人项目技术栈与三人计划.md`
- 团队后续会用到：VINS-Fusion、robot_localization、evo（M4–M7，本工作区只预留坐标树规范）

## 最后更新

2026-10-18
