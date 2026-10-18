from setuptools import find_packages, setup

package_name = "m1_pubsub_demo"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="patrol-robot-ros2",
    maintainer_email="maintainer@localhost",
    description="M1 W2: 发布/订阅节点（turtlesim 画圆 + 位姿监控）",
    license="MIT",
    entry_points={
        "console_scripts": [
            "circle_driver = m1_pubsub_demo.circle_driver:main",
            "pose_monitor = m1_pubsub_demo.pose_monitor:main",
        ],
    },
)
