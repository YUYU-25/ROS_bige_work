# 禹禹：ROS 2 Humble 桌面陪伴机器人

本分支是 Ubuntu 22.04 / ROS 2 Humble 版项目的独立交付。

## 下载完整项目

**[点击这里下载 yuyu_robot_humble.zip](https://github.com/YUYU-25/ROS_bige_work/raw/refs/heads/delivery/yuyu-humble/yuyu_robot_humble.zip)**

也可以点击本页面绿色 **Code → Download ZIP** 下载整个分支，解压后取其中的 `yuyu_robot` 文件夹。

- [浏览完整源码与安装说明](yuyu_robot/README.md)
- [安装新环境](yuyu_robot/docs/01_environment.md)
- [验证记录与测试范围](yuyu_robot/docs/VALIDATION.md)
- [逐步测试](yuyu_robot/docs/02_tests.md)

原始项目压缩包包含 59 个文件，大小 593291 字节。

SHA-256：`97a0e77350a2cfd9877844b82de280079468cda3ed65b907aaf37c7d898c9a71`

## 在新 Ubuntu 中运行

把 `yuyu_robot_humble.zip` 复制到 Ubuntu 主目录，然后逐条执行：

```bash
sudo apt install -y unzip
unzip ~/yuyu_robot_humble.zip -d ~
cd ~/yuyu_robot
bash tools/install_dependencies.sh
source /opt/ros/humble/setup.bash
colcon build --symlink-install
bash tools/start.sh
```

第一次需要安装依赖并编译；日常在项目目录运行 `bash tools/start.sh`。启动脚本统一打开 Gazebo、RViz 和键盘控制窗口。

环境安装遇到错误时先处理报错，再继续下一步。
