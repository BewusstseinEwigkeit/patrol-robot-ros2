import os
from glob import glob

from setuptools import find_packages, setup

package_name = "m1_bringup"

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
    description="M1 W3: 一条 launch 拉起画圆 + 位姿打印 + 可选录包",
    license="MIT",
    entry_points={"console_scripts": []},
)
