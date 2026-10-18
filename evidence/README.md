# evidence · 运行证据说明

这个目录放的是**真实运行留下的原始文件**，不是手工写的说明。任何一条结论都可以
顺着这里的文件回溯。

## acceptance/ · 验收脚本的原始输出

由 `scripts/acceptance.py --json` 生成，是逐周验收的机器可读结果。

| 文件 | 产生方式 | 关键结果 |
|---|---|---|
| `acceptance_all.json` | `python3 scripts/acceptance.py all --json ...` | **20 项全部通过** |
| `acceptance_w1.json` | `... w1` | 7 项通过 |
| `acceptance_w2.json` | `... w2` | 4 项通过 |
| `acceptance_w3.json` | `... w3` | 6 项通过 |
| `acceptance_w4.json` | `... w4` | 3 项通过 |
| `w2_result.json` | 早期独立验证脚本 | 616 帧、路程 15.52 m、外接框 3.0×3.0 |
| `w4_result.json` | 早期独立验证脚本 | tf2 链路 + 官方 tf2_echo 复核 |
| `bag_result.json` | rosbag 录制/回放验证 | db3 写入成功、话题确认 |

## live-runs/ · 节点自身的日志

| 文件 | 内容 |
|---|---|
| `pose_monitor.log` | 位姿监控节点真实输出（帧数、路程、转角） |
| `circle_driver.log` | 画圆节点真实输出（v/w/半径） |
| `w2_pose_summary.json` | 位姿统计落盘文件（轨迹外接框 3.0×3.0，宽高比 1.0） |
| `w4_listener.log` | tf2 查询节点输出（相机在世界系下的坐标） |
| `w4_tf2_echo.log` | 官方 `tf2_echo` 的独立复核输出 |
| `w4_broadcaster.log` | tf 广播节点输出（发布次数与坐标） |

## screenshots/ · 视觉证据

| 文件 | 内容 |
|---|---|
| `w2_画圆_真实截图.png` | turtlesim 窗口的真实截图：蓝色背景上一个完整的白色圆，乌龟停在圆上。由 `circle_driver`（`radius:=1.5`）驱动画出的轨迹，用 `PrintWindow` 只截该窗口，未包含桌面其他内容 |

## 怎么自己复现

见 `docs/04_验证边界说明.md` 的"复现步骤"一节。
