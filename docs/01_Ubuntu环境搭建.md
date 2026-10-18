# 01 · Ubuntu 22.04 上装 ROS 2 Humble

> 目标：让 `ros2 --version` 之外的每一条基础命令都能跑起来，并且**重复执行不会出错**。
> 对应 W1 的第一句话：「装 Ubuntu 22.04 + ROS 2 Humble」。

---

## 0. 先确认三件事

```bash
# 1) 是 22.04 吗？（24.04 请把 humble 换成 jazzy）
lsb_release -a

# 2) 磁盘够吗？（ROS desktop 装完约 3–4 GB，加上 build 目录留 15 GB 比较稳）
df -h /opt /home

# 3) 网络通吗？（下面这条是 ROS 官方源，通不了就走第 4 节的镜像）
curl -sI https://packages.ros.org/ros2/ubuntu | head -1
```

如果第 3 条卡住或超时，直接跳到第 4 节用国内镜像。

---

## 1. 一键脚本（推荐）

```bash
cd "/media/<你的用户名>/Data/Vibe Coding/patrol-robot-ros2"
bash scripts/setup_ubuntu_ros2.sh                 # 官方源
bash scripts/setup_ubuntu_ros2.sh --mirror tsinghua   # 清华镜像（国内推荐）
bash scripts/setup_ubuntu_ros2.sh --check         # 只检查，不动系统
```

脚本每一步都会先判断"是不是已经做过"，所以可以放心重复跑。

---

## 2. 手动分步（想搞明白每一步在干什么时用）

### 2.1 语言环境

```bash
sudo apt update && sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
```

> 为什么要这步：ROS 2 的日志和工具链默认按 UTF-8 处理中文路径与日志；
> locale 是 POSIX 时会看到一堆 `UnicodeEncodeError`。

### 2.2 加软件源和密钥

```bash
sudo apt install -y software-properties-common curl gnupg lsb-release

sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt update
```

### 2.3 安装

```bash
sudo apt install -y ros-humble-desktop \
  python3-colcon-common-extensions python3-rosdep python3-argcomplete
```

- `ros-humble-desktop`：含 rviz2、demo 节点、turtlesim，够用一整个 M1；
- `colcon`：编译工作区的工具；
- `rosdep`：自动装依赖（M4 编 VINS-Fusion 时会重度依赖它）。

### 2.4 让每个新终端自动生效

```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### 2.5 rosdep 初始化

```bash
sudo rosdep init
rosdep update
```

> `rosdep update` 走 GitHub，国内容易超时。失败不影响 M1，等编 VINS 时再处理
> （那时可以设 `ROS_DISTRO` 或用离线 rosdep 缓存）。

---

## 3. 验证

```bash
cd "/media/<你的用户名>/Data/Vibe Coding/patrol-robot-ros2"
bash scripts/check_env.sh
```

全绿之后，开两个终端试试最经典的乌龟：

```bash
# 终端 1
ros2 run turtlesim turtlesim_node

# 终端 2
ros2 run turtlesim turtle_teleop_key     # 用方向键控制
```

能看到乌龟窗口、能用方向键开动，W1 的环境部分就完成了。

---

## 4. 国内网络：换镜像源

清华的 ROS 2 镜像：

```bash
sudo sed -i 's|http://packages.ros.org/ros2/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ros2/ubuntu|' \
  /etc/apt/sources.list.d/ros2.list
sudo apt update
```

中科大：

```bash
sudo sed -i 's|http://packages.ros.org/ros2/ubuntu|https://mirrors.ustc.edu.cn/ros2/ubuntu|' \
  /etc/apt/sources.list.d/ros2.list
sudo apt update
```

> 密钥（keyring）不用换，换的只是下载地址。

---

## 5. 常见错误对照表

| 报错 | 原因 | 处理 |
|---|---|---|
| `E: 无法定位软件包 ros-humble-desktop` | 源没加成功，或 codename 不对 | `cat /etc/apt/sources.list.d/ros2.list` 确认最后是 `jammy main` |
| `NO_PUBKEY ...` | 密钥没装上 | 重跑 2.2 的 curl 那一行 |
| `ros2: command not found` | 没 source | `source /opt/ros/humble/setup.bash` |
| `ModuleNotFoundError: rclpy` | 用了系统 python 而不是 ROS 的 | 确认先 source 再跑 python |
| `rosdep update` 超时 | GitHub 被墙 | 挂代理，或先跳过（M1 不需要） |
| `Could not find a package configuration file ... turtlesim` | 没装 desktop 版 | `sudo apt install ros-humble-turtlesim` |
| 编译报 `SetuptoolsDeprecationWarning` | setuptools 版本提示 | 警告可忽略，不影响运行 |

---

## 6. 双系统特有的两件事

### 6.1 D 盘在 Ubuntu 下挂在哪

本项目放在 Windows 的 `D:\Vibe Coding\` 下，Ubuntu 里对应：

```text
/media/<你的用户名>/Data/Vibe Coding/patrol-robot-ros2
```

如果挂载点名字不是 `Data`，用 `lsblk -f` 找，或者用文件管理器的"其他位置"点一下
对应分区，它就会出现在 `/media/<你的用户名>/` 下面。

**在 Windows 里改过文件后，Ubuntu 侧可能看不到**：说明 Windows 是"快速启动/休眠"状态，
NTFS 分区没有干净卸载。解决：Windows 里彻底关机（不是重启），或者关掉快速启动。

### 6.2 系统时间差 8 小时

Windows 默认把硬件时钟当本地时间，Ubuntu 当 UTC，切系统后时间会错。

Ubuntu 侧让硬件时钟用本地时间（和 Windows 一致）：

```bash
timedatectl set-local-rtc 1 --adjust-system-clock
```

> 副作用：Ubuntu 下时间显示正常，但某些日志时间戳会"看起来"偏。
> 也可以反过来改 Windows 注册表（`RealTimeIsUniversal=1`），两边选一个即可。
> 时间不对会直接影响 rosbag 的时间戳和 tf2 的查询，**别跳过这一步**。

---

## 7. 下一步

环境好了之后：

```bash
bash scripts/build.sh
source install/setup.bash
bash scripts/acceptance.sh w1
```

然后看 `docs/02_逐周任务与验收.md` 的 W1 部分。
