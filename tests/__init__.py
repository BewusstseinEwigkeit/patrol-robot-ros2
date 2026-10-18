"""patrol-robot-ros2 的离线单元测试。

这些测试刻意不依赖 ROS：它们验证的是**算法和映射逻辑**（圆周公式、轨迹统计、
按键映射）。这样即使 ROS 还没装好，也能先确认这部分是对的。

运行方式（任选其一）：

    # 1) 直接跑，不装 ROS 也行
    python3 -m unittest discover -s tests -t . -v

    # 2) 在 ROS 环境里跑（colcon test 会调用它）
    colcon test --packages-select m1_pubsub_demo m1_turtle_basics
"""
