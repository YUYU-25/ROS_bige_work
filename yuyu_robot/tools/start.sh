#!/usr/bin/env bash
# 用途：在“主程序”终端一键启动，退出时在这个终端按 Ctrl+C。
set -eo pipefail
project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/humble/setup.bash
if [[ ! -f "$project_dir/install/setup.bash" ]]; then
  echo '尚未编译，请先在项目目录运行 colcon build --symlink-install。' >&2
  exit 1
fi
source "$project_dir/install/setup.bash"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-23}"
exec ros2 launch yuyu_gazebo demo_all.launch.py "$@"
