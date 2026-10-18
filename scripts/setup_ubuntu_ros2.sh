#!/usr/bin/env bash
# M1 W1：在 Ubuntu 22.04 上安装 ROS 2 Humble 并做基础配置。
#
# 设计原则：每一步都先判断"是不是已经做了"，所以这个脚本可以重复运行，
# 不会把已经装好的东西再装一遍。
#
# 用法：
#   bash scripts/setup_ubuntu_ros2.sh              # 完整安装
#   bash scripts/setup_ubuntu_ros2.sh --check      # 只检查，不改系统
#   bash scripts/setup_ubuntu_ros2.sh --mirror tsinghua   # 用清华镜像加速
#
# 注意：需要 sudo 权限。第一次跑请把终端开大一点，留意报错。
set -uo pipefail

MIRROR="${MIRROR:-official}"
CHECK_ONLY=0
ROS_DISTRO_NAME="humble"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) CHECK_ONLY=1; shift ;;
    --mirror) MIRROR="${2:-official}"; shift 2 ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "未知参数：$1"; exit 2 ;;
  esac
done

ok()   { printf '  \033[32m[OK]\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m[!!]\033[0m %s\n' "$1"; }
fail() { printf '  \033[31m[XX]\033[0m %s\n' "$1"; }
step() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }

# ---------------------------------------------------------------- 环境前提
step "0. 检查系统前提"
if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  echo "  发行版：${PRETTY_NAME:-未知}"
  if [[ "${VERSION_ID:-}" != "22.04" ]]; then
    warn "本项目按 Ubuntu 22.04 设计；当前是 ${VERSION_ID:-未知}。"
    warn "24.04 请把下面的 humble 换成 jazzy，其余流程一致。"
  fi
else
  fail "读不到 /etc/os-release，确认这是 Linux 机器吗？"
  exit 1
fi
echo "  架构：$(uname -m)  内核：$(uname -r)"

if [[ "$CHECK_ONLY" == "1" ]]; then
  step "只检查模式"
  command -v ros2 >/dev/null 2>&1 && ok "ros2 已安装：$(ros2 --version 2>/dev/null | head -1)" || warn "ros2 未安装"
  exit 0
fi

# ---------------------------------------------------------------- 1 locale
step "1. 设置 UTF-8 locale（ROS 2 要求）"
if locale 2>/dev/null | grep -qi 'utf-\?8'; then
  ok "当前 locale 已是 UTF-8"
else
  sudo apt-get update -qq
  sudo apt-get install -y locales
  sudo locale-gen en_US en_US.UTF-8
  sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
  export LANG=en_US.UTF-8
  ok "locale 已设置（重开终端后生效）"
fi

# ---------------------------------------------------------------- 2 apt 源
step "2. 配置 apt 源与密钥"
sudo apt-get install -y software-properties-common curl gnupg lsb-release

KEYRING=/usr/share/keyrings/ros-archive-keyring.gpg
if [[ -f "$KEYRING" ]]; then
  ok "ROS 密钥已存在，跳过"
else
  if [[ "$MIRROR" == "tsinghua" ]]; then
    curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
      | gpg --dearmor | sudo tee "$KEYRING" >/dev/null
  else
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
      -o "$KEYRING"
  fi
  ok "ROS 密钥已安装"
fi

if [[ "$MIRROR" == "tsinghua" ]]; then
  APT_LINE="deb [arch=$(dpkg --print-architecture) signed-by=$KEYRING] https://mirrors.tuna.tsinghua.edu.cn/ros2/ubuntu $(. /etc/os-release && echo "$UBUNTU_CODENAME") main"
else
  APT_LINE="deb [arch=$(dpkg --print-architecture) signed-by=$KEYRING] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo "$UBUNTU_CODENAME") main"
fi
echo "$APT_LINE" | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null
ok "已写入 /etc/apt/sources.list.d/ros2.list（镜像：$MIRROR）"

sudo apt-get update -qq || warn "apt update 有报错，继续尝试安装"

# ---------------------------------------------------------------- 3 安装
step "3. 安装 ros-${ROS_DISTRO_NAME}-desktop 与构建工具"
if [[ -d "/opt/ros/${ROS_DISTRO_NAME}" ]]; then
  ok "/opt/ros/${ROS_DISTRO_NAME} 已存在，跳过安装"
else
  sudo apt-get install -y "ros-${ROS_DISTRO_NAME}-desktop" \
    python3-colcon-common-extensions python3-rosdep python3-argcomplete
  ok "ROS 2 ${ROS_DISTRO_NAME} 安装完成"
fi

step "4. 初始化 rosdep"
if [[ -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  ok "rosdep 已初始化"
else
  sudo rosdep init || warn "rosdep init 失败（可能网络问题，稍后手动重试）"
  rosdep update || warn "rosdep update 失败"
fi

step "5. 写入 ~/.bashrc（幂等）"
BASHRC_LINE="source /opt/ros/${ROS_DISTRO_NAME}/setup.bash"
if grep -qF "$BASHRC_LINE" "$HOME/.bashrc" 2>/dev/null; then
  ok "~/.bashrc 已包含 source 语句"
else
  {
    echo ""
    echo "# --- ROS 2 ${ROS_DISTRO_NAME} (patrol-robot-ros2 添加) ---"
    echo "$BASHRC_LINE"
    echo "source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash 2>/dev/null || true"
    echo "# --- end ---"
  } >> "$HOME/.bashrc"
  ok "已追加到 ~/.bashrc"
fi

step "完成"
cat <<'EOF'
接下来请新开一个终端（或执行 source ~/.bashrc），然后运行：

    bash scripts/check_env.sh        # 环境自检
    bash scripts/build.sh            # 编译本工作区

如果 check_env.sh 里有红色的 [XX]，先解决它再往下走。
EOF
