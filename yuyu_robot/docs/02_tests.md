# 按目的逐项测试

所有指令在 **指令终端**执行。先按 README source 两个 setup 并设置 `ROS_DOMAIN_ID=23`。主程序终端一直保持运行。

| 顺序 | 目的 | 操作 | 预期 |
|---|---|---|---|
| 1 | 确认轮子控制器可用 | `ros2 control list_controllers` | 两个控制器都是 active |
| 2 | 确认防护具备数据 | `ros2 topic echo /safety_status --once` | ready 为 true，四个 edges 为 false |
| 3 | 确认只有一个最终速度发布者 | `ros2 topic info /cmd_vel --verbose` | 发布者只有 velocity_mux |
| 4 | 确认六种脸可切换 | 用下面的表情命令 | Face 面板和 Gazebo 脸一起变化 |
| 5 | 确认中文与清除 | 发布 face_text | 中文正常，3 秒后消失 |
| 6 | 确认文本情绪 | 发布“今天有点烦” | care 表情、随机金句 |
| 7 | 确认静音与恢复 | 播报时发“不想说”，再发“恢复说话” | 当前音频结束，安静期间文字可显示 |
| 8 | 确认低速移动 | YUYU-keyboard 点入后 i/k | 前进/停止；没有按键后也会超时停止 |
| 9 | 确认导航 | 先“回去”，到达后“过来” | 状态 NAVIGATING→INTERACTING→IDLE |
| 10 | 确认舞蹈 | 当前位置安全后发“跳个舞” | 发布 Dance Path，逐点跟随，完成停车 |
| 11 | 确认优先停车 | 舞蹈中发“停下” | 舞蹈取消，cmd_vel 归零 |

```bash
ros2 topic pub --once /face_expr std_msgs/msg/String "data: 'care'"
ros2 topic pub --once /face_expr std_msgs/msg/String "data: 'sleepy'"
ros2 topic pub --once /face_expr std_msgs/msg/String "data: 'curious'"
ros2 topic pub --once /face_expr std_msgs/msg/String "data: 'silent'"
ros2 topic pub --once /face_expr std_msgs/msg/String "data: 'dance'"
ros2 topic pub --once /face_expr std_msgs/msg/String "data: 'happy'"
ros2 topic pub --once /face_text std_msgs/msg/String "data: '你好呀，我是禹禹！'"
```

**RViz 视角**：点工具栏 Move Camera，把鼠标放进三维画面，左键拖动旋转，中键拖动平移，滚轮缩放。Views 面板选 Orbit。完整启动默认使用 `map`，可勾选 Desk Boundary Map 查看桌沿；基础模型启动使用 `base_footprint`。只看外观时可临时取消 LaserScan。

**防摔测试分两层**：正常移动时，已知桌沿边界会先阻止继续向外；这不等于四个下视传感器已经在桌外测过。真正落差测试应在虚拟环境暂停物理后，通过 Gazebo 模型属性把机器人靠近边缘，确认前侧下视测距从约 0.038 m 变大/无穷，再恢复物理观察立即停车，并在后方安全时先后退再转向。不要关闭所有防护然后长时间向外开。四边都要测，后侧不安全时不应继续后退。

若传感器超时或通信中断，预期为零速度。暂停仿真时传感器数据会变旧，这时保护暂停运动是正常行为；恢复后等待新数据。

检查状态时使用：

```bash
ros2 topic echo /behavior_state
# Ctrl+C 退出当前查看，再执行下一条
ros2 topic echo /motion_status
```

基础节点自动检查（不需要 ROS）与 ROS 冒烟检查脚本见 tests。记录结果时分清“已编译”“节点通信通过”“实际物理移动通过”“虚拟机显示通过”。

自动验收命令均在项目根目录执行，ROS 测试前先启动主程序并 source 环境：

```bash
# 规则与绘图，运行时不会驱动机器人
python3 -m unittest discover -s tests -p test_core.py -v
# 小范围前进与转向反馈；让机器人处于桌面中央
python3 tests/ros_motion_check.py
# 回去→过来→完整心形舞，可能需要数分钟
python3 tests/ros_behavior_test.py
# 仅仿真：主动放到前桌沿检查落差恢复。完成后必须重启主程序。
python3 tests/ros_edge_check.py
```

`ros_smoke.py` 用于刚启动、尚未操作的场景，自动检查图像、传感器和正向位移。每次做改变位置的测试前先确认当前场景和前后空隙，避免把不同测试留下的位置当成初始条件。
