# 在 VMware 另建 Ubuntu 22.04

目的：给 ROS 2 Humble 提供匹配的系统，旧 Melodic 虚拟机继续保留。

1. 在 **Windows 浏览器**下载 [Ubuntu 22.04 官方桌面镜像](https://releases.ubuntu.com/22.04/)，选 amd64 Desktop ISO。
2. 在 **VMware 主窗口**选“创建新的虚拟机”，使用刚下载的 ISO；新名称可写 `ubuntu-22-humble-yuyu`。不要覆盖旧虚拟机磁盘。
3. 建议分配 4 核、8 GB 内存、60 GB 或更大磁盘。若主机资源较少，可先 4 GB，运行时关闭旧虚拟机；Gazebo 与 RViz 同时运行会较慢。
4. 完成 Ubuntu 安装并登录。安装 VMware 桌面工具便于复制文件与调整分辨率：

```bash
sudo apt update
sudo apt install open-vm-tools-desktop unzip
```

5. 把本项目压缩包复制进**新 Ubuntu 的主目录**，用文件管理器解压，使目录为 `~/yuyu_robot`。若包名多一层文件夹，打开里面有 `src`、`tools` 的那一层。
6. 在这个目录右键“在终端打开”，按 README 的安装与编译步骤执行。所有项目命令都在新 Ubuntu 中输入；不要在 Windows PowerShell 或原 Ubuntu 18.04 里执行。

预期：`lsb_release -ds` 显示 Ubuntu 22.04，`source /opt/ros/humble/setup.bash` 后 `echo $ROS_DISTRO` 显示 humble。

如果 Gazebo 在 VMware 黑屏或崩溃，先关闭仿真，在**主程序终端**执行 `export LIBGL_ALWAYS_SOFTWARE=1` 再启动。软件渲染较慢；也可检查 VMware 显示设置中的 3D 加速。先做基础图形验证，再调整虚拟机性能。

依赖安装需要网络，安装失败应根据报错修复软件源或网络；不要关闭 apt 签名或 TLS 验证。Gazebo Classic 已停止上游维护，这里按需求固定使用 11，不与新 Gazebo Sim 混用。
