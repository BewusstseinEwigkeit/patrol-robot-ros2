# 05 · 在 Windows 上也能跑 ROS 2（可选，但有好处）

> 目标环境是 Ubuntu 22.04。但你在 Windows 侧写代码、看文档的时候，
> 如果手边就能跑一次节点，会省掉大量"切系统重启"的时间。
> 这份文档说明本机已经装好的 Windows 版 ROS 2 怎么用。

---

## 1. 已经装好了什么

2026-10-18 在 Windows 上装了一套 **RoboStack 版的 ROS 2 Humble**：

| 项 | 值 |
|---|---|
| 位置 | `C:\ros2\envs\humble` |
| 包管理器 | micromamba（`C:\_ros2_verify\micromamba.exe`） |
| 已装包 | ros-base、turtlesim、tf2_ros/tf2_tools、rosbag2、ros2bag、demo-nodes-py、colcon |
| 体积 | 约 6.8 GB |

它是**真正的 ROS 2 Humble**，不是模拟器：rclpy、话题、服务、tf2、rosbag2 的
行为与 Ubuntu 版一致。本工作区的 W1–W4 代码就是在这上面跑通并验收的
（见 `docs/04_验证边界说明.md`）。

## 2. 怎么用

打开 PowerShell，先设两个环境变量：

```powershell
$env:MAMBA_ROOT_PREFIX = 'C:\ros2'
$mm = 'C:\_ros2_verify\micromamba.exe'
```

然后任何命令都通过 `micromamba run` 执行：

```powershell
# 看 ROS 版本
& $mm run -p 'C:\ros2\envs\humble' ros2 pkg list

# 起乌龟（会弹出一个窗口）
& $mm run -p 'C:\ros2\envs\humble' ros2 run turtlesim turtlesim_node

# 另开一个 PowerShell 窗口，让工作区里的代码动起来
$env:PYTHONPATH = 'D:\Vibe Coding\patrol-robot-ros2\src\m1_pubsub_demo'
& $mm run -p 'C:\ros2\envs\humble' python -m m1_pubsub_demo.circle_driver --ros-args -p radius:=1.5
```

跑整套验收：

```powershell
& $mm run -p 'C:\ros2\envs\humble' python 'D:\Vibe Coding\patrol-robot-ros2\scripts\acceptance.py' all
```

## 3. Windows 侧特有的三个坑

这三条都在 `docs/03_踩坑日志.md` 里有详细版本，这里给结论：

### 3.1 `ros2 node list` 这类命令会挂住

`ros2` CLI 的部分子命令依赖 `ros2 daemon`，在 Windows 上会卡死不返回。

- **绕过**：加 `--no-daemon`，例如 `ros2 node list --no-daemon`
- **更好的办法**：本工作区的 `scripts/acceptance.py` 干脆不用 CLI，
  直接建一个 rclpy 节点去读 ROS 图，又快又稳。

### 3.2 多网卡导致发现不稳定

本机同时有物理网卡和 Clash 的 TUN 虚拟网卡，DDS 的多播发现会时灵时不灵
（表现为"话题明明在，节点列表却是空的"）。

```powershell
$env:ROS_LOCALHOST_ONLY = '1'   # 单机练习场景下最稳
```

`acceptance.py` 在 Windows 上会自动设这个变量，Ubuntu 侧不动它
（保留多机通信能力）。

### 3.3 `colcon build` 会挂住

Windows + RoboStack 组合下的已知问题，与包本身无关（同样的包
`python setup.py build` 手动跑是成功的）。

- **绕过**：不编译，直接用 `PYTHONPATH` + `python -m <模块>` 运行。
  `acceptance.py` 检测不到 `ros2 run` 可执行文件时会自动走这条路。
- **真正的构建验证**：留给 Ubuntu。

## 4. 什么时候该切到 Ubuntu

| 任务 | Windows | Ubuntu |
|---|---|---|
| 读代码、写代码、改文档 | ✅ 推荐 | ✅ |
| 跑节点、验算法逻辑 | ✅ | ✅ |
| `colcon build` | ❌ | ✅ |
| `ros2 launch`（端到端） | ❌ | ✅ |
| rosbag 的 `metadata.yaml` | ❌ | ✅ |
| 键盘遥控（termios） | ❌ | ✅ |
| rviz2 可视化 | ❌ | ✅ |
| 接真实相机 / IMU / 底盘 | ❌ | ✅ |

一句话：**逻辑在 Windows 上验，系统集成在 Ubuntu 上验。**

## 5. 想删掉的话

这套环境完全独立，删掉不影响项目：

```powershell
Remove-Item 'C:\ros2' -Recurse -Force          # 约 6.8 GB
Remove-Item 'C:\_ros2_verify' -Recurse -Force  # micromamba 与验证脚本
```

删之前记得：项目里的代码、文档、证据都在 `D:\Vibe Coding\patrol-robot-ros2`，
不受影响。
