import os
from glob import glob

from setuptools import find_packages, setup

package_name = "m1_tf2_demo"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="patrol-robot-ros2",
    maintainer_email="maintainer@localhost",
    description="M1 W4: tf2 坐标树（world → odom → base_link → 传感器）",
    license="MIT",
    entry_points={
        "console_scripts": [
            "turtle_tf_broadcaster = m1_tf2_demo.turtle_tf_broadcaster:main",
            "tf_listener = m1_tf2_demo.tf_listener:main",
        ],
    },
)
