# 禹禹：ROS 2 Humble 桌面陪伴机器人

这是按最新方块桌宠需求新建的项目。运行环境是 **Ubuntu 22.04 + ROS 2 Humble + Gazebo Classic 11 + RViz 2**；原来的 Ubuntu 18.04 / Melodic 工程可继续保留。

## 文件结构

```text
yuyu_robot/
├── src/
│   ├── yuyu_description/       # 自主设计模型、控制器、RViz
│   │   ├── urdf/yuyu.urdf.xacro
│   │   ├── meshes/rounded_box.stl
│   │   ├── ros2_control/yuyu_control.yaml
│   │   └── rviz/yuyu_view.rviz
│   ├── yuyu_gazebo/            # 桌面世界、边界地图、一键启动
│   │   ├── worlds/desk.world
│   │   ├── maps/desk.yaml
│   │   ├── maps/desk.pgm
│   │   └── launch/{demo,demo_all}.launch.py
│   └── yuyu_bringup/           # 功能节点与配置
│       ├── scripts/           # 与需求同名的节点源码入口
│       ├── yuyu_bringup/      # 节点实现、独立规则与 Pillow 绘图
│       └── config/{quotes,nav2,slam}.yaml
├── tests/test_core.py
├── tools/install_dependencies.sh
├── tools/start.sh
├── tools/commands.sh
├── tools/generate_resources.py
└── docs/                     # 环境、测试、实现取舍与验证记录
```

三个包都有 `package.xml`、`setup.py`、`setup.cfg`、资源索引和 Python 包目录。屏幕使用 Humble 现有 `libgazebo_ros_video.so`，不需要另外编译 C++ 插件。

## 第一次准备：新虚拟机中的终端

目的：安装新版所需的软件。详细环境说明见 [新环境](docs/01_environment.md)。

把整个文件夹放到新 Ubuntu 的 `~/yuyu_robot`，然后打开 Ubuntu 终端：

```bash
cd ~/yuyu_robot
bash tools/install_dependencies.sh
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

预期：编译结束显示 `3 packages finished`。安装依赖只需做一次，修改代码后重新编译。

## 日常启动：只使用有明确用途的窗口

**主程序终端**：启动场景、传感器、导航、表情和行为；运行期间保持打开。

```bash
cd ~/yuyu_robot
bash tools/start.sh
```

预期自动出现：

- **Gazebo**：观察机器人在桌面上的物理运动，脸上显示动态图像。
- **RViz 2**：查看模型、激光、路径和 Face 图像面板。
- **YUYU-keyboard**：点进这个窗口后按 `i` 前进、`,` 后退、`j/l` 转向、`k` 停止。速度很慢是设计要求。

手动移动会取消正在执行的导航或舞蹈；键盘窗口空闲时持续发出的零速度不会抢占自动动作。

**指令终端**：再开一个 Ubuntu 终端，用于输入中文命令，不需要为每条命令新开窗口。

```bash
source /opt/ros/humble/setup.bash
source ~/yuyu_robot/install/setup.bash
export ROS_DOMAIN_ID=23
ros2 topic pub --once /command_text std_msgs/msg/String "data: '今天有点开心'"
```

预期：表情变开心，屏幕显示一句回应；系统音频可用时会播报。接着逐条测试：

```bash
ros2 topic pub --once /command_text std_msgs/msg/String "data: '禹禹，回去'"
ros2 topic pub --once /command_text std_msgs/msg/String "data: '禹禹，过来'"
ros2 topic pub --once /command_text std_msgs/msg/String "data: '禹禹，跳个舞'"
ros2 topic pub --once /command_text std_msgs/msg/String "data: '不想说'"
```

“不想说”会停止当前动作、终止播报并进入安静表情；发送“恢复说话”后恢复语音。简单关键词属于文本情绪规则，不是语音识别或心理状态识别。

更多命令见 [命令参考](tools/commands.sh)，逐项验收见 [测试流程](docs/02_tests.md)。

## 停止与常用启动选项

在**主程序终端**按 `Ctrl+C`，一起关闭所有节点；`ros2 topic echo` 中按 `Ctrl+C` 只结束查看。

```bash
# 没有虚拟机音频时，仍显示文字
bash tools/start.sh audio:=false
# 不打开键盘窗口
bash tools/start.sh keyboard:=false
# 桌上扫描特征不足时，先用已知桌面地图与仿真里程计完成确定性测试
bash tools/start.sh use_slam:=false
# 无图形测试（仍生成图像话题；Gazebo 屏幕需图形客户端才能看见）
bash tools/start.sh gui:=false rviz:=false keyboard:=false audio:=false use_slam:=false
```

标准启动命令等价于：

```bash
source /opt/ros/humble/setup.bash
source ~/yuyu_robot/install/setup.bash
export ROS_DOMAIN_ID=23
ros2 launch yuyu_gazebo demo_all.launch.py
```

不要再使用 ROS 1 的 `roscore`、`rostopic`、`roslaunch`、`catkin_make`；ROS 2 不需要单独开 roscore 窗口。

## 参数与实际能力

详细说明见 [需求修正与限制](docs/03_design.md)。主要几何尺寸在 xacro 开头，控制参数在 `yuyu_control.yaml`，导航参数在 `nav2.yaml`。

- 壳体 16×16×10 cm；带短腿、传感器和天线总高约 18 cm。耳机使最大宽度约 18.4 cm。
- 两个 2.5 cm 半径小轮藏于壳体下方，转速限制 1 rad/s，实际直行上限 0.025 m/s。
- 六种表情与中文文字叠加；文字总显示 3 秒，超过 15 字换行，超过三行在这 3 秒内分页。
- 四个下视传感器判断落差，低位前后测距补充矮障碍，顶部水平雷达用于扫描环境。
- Nav2 用包含桌沿和矮障碍的已知底图；SLAM 同时运行并提供 map→odom。桌上扫描特征少时不能据此保证可靠建图。
- 启用 SLAM 时自动选择 `desk_slam.world`，桌外增加四片竖直标定板供水平雷达扫描；它们不代替桌沿防护。`use_slam:=false` 使用原始桌面世界。
- “过来”暂去桌面中心，“回去”去 (-0.18, 0.08) m；还没有人脸位置输入。
- 心形舞最多 40×30 cm，放不下时缩小或拒绝；轮速限制使舞蹈需要几十秒到数分钟。
- 短腿、耳机和天线是固定装饰。没有俯仰关节，`curious` 使用表情变化，当前不会让整机前倾。
- 本版不包含真实麦克风识别、LLM、实物电机驱动或真实机器人防摔认证。

验证结果会记录在 [验证记录](docs/VALIDATION.md)，云环境检查不能替代你新虚拟机中的显示、音频与桌沿验收。
