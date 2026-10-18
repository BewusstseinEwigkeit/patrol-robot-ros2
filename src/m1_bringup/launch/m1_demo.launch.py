"""W3 产出：一条 launch 拉起「画圆 + 打印位姿（+ 可选录包）」全流程。

这正是 M1 月末检查点要求的那句话：
「不看教程能独立做出 launch 拉起 画圆 + 打印位姿 + 录包 三个节点」。

它把 W1/W2 里一个个手敲的命令固化成一个可复现的入口，顺便演示 launch 的
三件核心能力：
1. **DeclareLaunchArgument**：把半径、速度、时长变成命令行可覆盖的参数
2. **Node(parameters=[...])**：把参数转发给具体节点（等价于 --ros-args -p）
3. **IfCondition / TimerAction**：按条件启动、延迟启动（录包要等话题起来）

用法：
    ros2 launch m1_bringup m1_demo.launch.py
    ros2 launch m1_bringup m1_demo.launch.py radius:=2.0 run_seconds:=10.0
    ros2 launch m1_bringup m1_demo.launch.py record:=true bag_dir:=/tmp/m1_bags
"""

from __future__ import annotations

import os

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    LogInfo,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    default_bag_dir = os.path.join(os.path.expanduser("~"), ".ros", "m1_bags")

    args = [
        DeclareLaunchArgument("radius", default_value="1.0", description="圆周半径（米）"),
        DeclareLaunchArgument("linear_speed", default_value="2.0", description="线速度 m/s"),
        DeclareLaunchArgument("run_seconds", default_value="0.0", description="跑多久后自动停；0=一直跑"),
        DeclareLaunchArgument("report_period", default_value="1.0", description="位姿打印间隔（秒）"),
        DeclareLaunchArgument("record", default_value="false", description="是否录制 rosbag"),
        DeclareLaunchArgument("bag_dir", default_value=default_bag_dir, description="rosbag 输出目录"),
        DeclareLaunchArgument("summary_json", default_value="", description="位姿统计输出路径；空=不写"),
    ]

    radius = LaunchConfiguration("radius")
    linear_speed = LaunchConfiguration("linear_speed")
    run_seconds = LaunchConfiguration("run_seconds")
    report_period = LaunchConfiguration("report_period")
    record = LaunchConfiguration("record")
    bag_dir = LaunchConfiguration("bag_dir")
    summary_json = LaunchConfiguration("summary_json")

    turtlesim = Node(
        package="turtlesim",
        executable="turtlesim_node",
        name="turtlesim",
        output="screen",
    )

    circle_driver = Node(
        package="m1_pubsub_demo",
        executable="circle_driver",
        name="circle_driver",
        output="screen",
        parameters=[
            {
                "radius": radius,
                "linear_speed": linear_speed,
                "run_seconds": run_seconds,
            }
        ],
    )

    pose_monitor = Node(
        package="m1_pubsub_demo",
        executable="pose_monitor",
        name="pose_monitor",
        output="screen",
        parameters=[
            {
                "report_period": report_period,
                "run_seconds": run_seconds,
                "summary_json": summary_json,
            }
        ],
    )

    # 录包：等 2 秒让话题先出现，否则 rosbag 会因为"话题不存在"报警告
    record_bag = TimerAction(
        period=2.0,
        actions=[
            LogInfo(msg="开始录制 rosbag（Ctrl-C 结束整条 launch 时会自动收尾）"),
            ExecuteProcess(
                cmd=[
                    "ros2", "bag", "record",
                    "-o", bag_dir,
                    "/turtle1/cmd_vel",
                    "/turtle1/pose",
                    "/turtle1/color_sensor",
                ],
                output="screen",
                condition=IfCondition(record),
            ),
        ],
    )

    return LaunchDescription(
        [
            *args,
            LogInfo(msg="m1_demo 启动：turtlesim + circle_driver + pose_monitor"),
            turtlesim,
            circle_driver,
            pose_monitor,
            record_bag,
        ]
    )
