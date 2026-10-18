"""W4 产出：tf2 坐标树（world → odom → base_link → 传感器）。

这个 launch 就是 M1 月末综合验收要拉起的东西：turtlesim 一动，
整棵坐标树跟着动，`tf_listener` 就能实时报出相机在世界坐标系下的位置。

坐标树设计（和后面 M3–M6 的真实机器人保持一致，先熟悉结构）：

    world                      ← 全局固定坐标系（地图/场地）
      └─ odom                  ← 里程计原点（静态，EKF 修正漂移的地方）
           └─ base_link        ← 车体中心（由 turtle_tf_broadcaster 发布，会动）
                ├─ imu_link    ← IMU 安装位置（静态）
                └─ camera_link ← 相机安装位置（静态）

装法对照：真车上 `base_link → camera_link` 的平移量就是你拿尺子量出来的安装位置。
这里先写成 (0.15, 0, 0.10)，等你真装相机时把这三个数字换掉即可。

用法：
    ros2 launch m1_tf2_demo m1_tf2.launch.py
    ros2 run tf2_tools view_frames        # 生成 frames.pdf 看整棵树
    ros2 run tf2_ros tf2_echo world camera_link
"""

from __future__ import annotations

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _num(value: object) -> object:
    """数值转成字符串给命令行；LaunchConfiguration 原样交给 launch 做替换。

    直接对 LaunchConfiguration 调 str() 会得到它的 repr 而不是运行时的值，
    这是写 launch 参数时最常见的坑之一。

    注意：不要试图 `from launch.substitutions import Substitution` 来判断类型——
    Humble 的 launch.substitutions 并没有导出这个基类，会直接 ImportError。
    这里用"是数值就转字符串、其余原样传"的写法，既简单又跨版本安全。
    """
    if isinstance(value, (int, float)):
        return str(value)
    return value


def _static_tf(name: str, parent: str, child: str, xyz: tuple[object, object, object], yaw: float = 0.0) -> Node:
    """封装 tf2_ros 的静态坐标发布器（Humble 的命名参数写法）。"""
    x, y, z = xyz
    return Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name=name,
        output="screen",
        arguments=[
            "--x", _num(x), "--y", _num(y), "--z", _num(z),
            "--roll", "0.0", "--pitch", "0.0", "--yaw", str(yaw),
            "--frame-id", parent,
            "--child-frame-id", child,
        ],
    )


def generate_launch_description() -> LaunchDescription:
    args = [
        DeclareLaunchArgument("camera_x", default_value="0.15", description="相机在车体前方的安装距离"),
        DeclareLaunchArgument("camera_z", default_value="0.10", description="相机安装高度"),
    ]

    return LaunchDescription(
        [
            *args,
            LogInfo(msg="m1_tf2 启动：world → odom → base_link → imu_link / camera_link"),

            # 1) 乌龟本体（提供 /turtle1/pose）
            Node(package="turtlesim", executable="turtlesim_node", name="turtlesim", output="screen"),

            # 2) 固定不动的两个坐标系
            _static_tf("static_world_to_odom", "world", "odom", (0.0, 0.0, 0.0)),

            # 3) 车体会动的那一跳
            Node(
                package="m1_tf2_demo",
                executable="turtle_tf_broadcaster",
                name="turtle_tf_broadcaster",
                output="screen",
                parameters=[{"parent_frame": "odom", "child_frame": "base_link"}],
            ),

            # 4) 车上的两个传感器（静态安装）
            _static_tf("static_imu", "base_link", "imu_link", (0.0, 0.0, 0.05)),
            _static_tf(
                "static_camera", "base_link", "camera_link",
                (LaunchConfiguration("camera_x"), 0.0, LaunchConfiguration("camera_z")),
            ),

            # 5) 查询者：把树里的答案打印出来
            Node(
                package="m1_tf2_demo",
                executable="tf_listener",
                name="tf_listener",
                output="screen",
                parameters=[{"target_frame": "world", "source_frame": "camera_link"}],
            ),
        ]
    )
