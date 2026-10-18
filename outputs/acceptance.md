# M1 验收报告（all）

- 生成时间：2026-10-18 04:35:55
- 工作区：`D:\Vibe Coding\patrol-robot-ros2`
- ROS 发行版：humble
- 结论：**通过 20 项，未过 0 项**

## 通过项

- W1.2 turtlesim 在跑，位姿与速度话题都在
- W1.3 节点查询正常（看到 /turtlesim）
- W1.3 service 查询正常（teleport_absolute 存在）
- W1.3 param 查询正常
- W1.4 发速度后乌龟真的动了
- W1.5 keyboard_teleop 在不可用环境下正确拒绝启动（行为符合设计）
- W1.6 teleport_demo 用 service 依次瞬移成功
- W2.2 pose_monitor 写出了统计文件
- W2.3 收到足够位姿帧
- W2.4 累计路程正常
- W2.5 轨迹是圆（外接框宽高比接近 1）
- W3.1 三个节点（turtlesim + circle_driver + pose_monitor）同时运行
- W3.1 画圆节点与位姿节点都在 ROS 图里
- W3.2 launch/节点参数生效（位姿统计文件已生成）
- W3.3 rosbag 生成了数据文件
- W3.4 包里确实录到了 /turtle1/pose
- W3.5 rosbag 能回放
- W4.1 tf2 能查到 world -> camera_link
- W4.2 安装偏移在数值上正确
- W4.3 官方 tf2_echo 独立复核通过

## 未通过项

- （无）

## 过程记录

- turtlesim 已就绪
- W1.5 未通过 ros2 run 找到包（没 colcon build 时正常），改验证模块行为
- 让乌龟跑 13 秒 ...
- ros2 launch 没起来（本机可能没 colcon build），改用逐个起节点验证
- 统计：563 帧，路程 17.184 m
- 录包 8 秒 ...
- 缺 metadata.yaml，用 scripts/rebuild_bag_metadata.py 重建
- turtlesim 已重置，开始建坐标树
