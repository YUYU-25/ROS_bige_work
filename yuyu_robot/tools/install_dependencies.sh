#!/usr/bin/env bash
# 用途：只在新 Ubuntu 22.04 虚拟机安装 Humble 和本项目依赖。
set -euo pipefail
source /etc/os-release
if [[ "$ID" != ubuntu || "$VERSION_ID" != 22.04 ]]; then
  echo '请在新 Ubuntu 22.04 环境执行；不要在原来的 Ubuntu 18.04 中执行。' >&2
  exit 1
fi
sudo apt-get update
sudo apt-get install -y curl gnupg lsb-release software-properties-common locales
sudo add-apt-repository -y universe
sudo locale-gen en_US en_US.UTF-8
if [[ ! -f /opt/ros/humble/setup.bash ]]; then
  if ! apt-cache show ros-humble-desktop >/dev/null 2>&1; then
    curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /tmp/yuyu-ros.key
    sudo install -m 0644 /tmp/yuyu-ros.key /usr/share/keyrings/ros-archive-keyring.gpg
    printf 'deb [arch=%s signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] https://packages.ros.org/ros2/ubuntu jammy main\n' "$(dpkg --print-architecture)" | sudo tee /etc/apt/sources.list.d/yuyu-ros2.list >/dev/null
    sudo apt-get update
  fi
  sudo apt-get install -y ros-humble-desktop
fi
sudo apt-get install -y python3-colcon-common-extensions python3-pil python3-yaml \
  fonts-noto-cjk espeak xterm \
  ros-humble-xacro ros-humble-gazebo-ros-pkgs ros-humble-gazebo-ros2-control \
  ros-humble-ros2-controllers ros-humble-navigation2 ros-humble-nav2-bringup \
  ros-humble-slam-toolbox ros-humble-teleop-twist-keyboard ros-humble-rviz2
echo '安装结束。下一步：source /opt/ros/humble/setup.bash，然后 colcon build。'
