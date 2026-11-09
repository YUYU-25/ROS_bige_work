# 禹禹：ROS 2 Humble 完整项目下载

本分支提供 Ubuntu 22.04 + ROS 2 Humble 项目。

- 直接下载：打开 `yuyu_robot_humble.zip`，点击 GitHub 的 Download raw file 按钮。
- 浏览源代码：打开 `yuyu_robot/` 目录。
- 环境、编译、启动：见 `yuyu_robot/README.md`。

压缩包包含 59 个文件，大小 593291 字节。
SHA-256：`97a0e77350a2cfd9877844b82de280079468cda3ed65b907aaf37c7d898c9a71`。

复制压缩包到新 Ubuntu 的主目录后，执行：

```bash
sudo apt install -y unzip
unzip ~/yuyu_robot_humble.zip -d ~
cd ~/yuyu_robot
bash tools/install_dependencies.sh
source /opt/ros/humble/setup.bash
colcon build --symlink-install
bash tools/start.sh
```

原 ROS 1 工程继续保留。此分支用于单独交付 Humble 版。
