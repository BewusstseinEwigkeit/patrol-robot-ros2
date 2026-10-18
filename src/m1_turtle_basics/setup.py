from setuptools import find_packages, setup

package_name = "m1_turtle_basics"

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
    description="M1 W1: 键盘遥控 + service 瞬移（turtlesim 基础）",
    license="MIT",
    entry_points={
        "console_scripts": [
            "keyboard_teleop = m1_turtle_basics.keyboard_teleop:main",
            "teleport_demo = m1_turtle_basics.teleport_demo:main",
        ],
    },
)
