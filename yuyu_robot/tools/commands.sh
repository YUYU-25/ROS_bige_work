#!/usr/bin/env bash
# 演示命令参考，不要直接执行整个文件；在“指令”终端逐条执行。
# source /opt/ros/humble/setup.bash
# source ~/yuyu_robot/install/setup.bash
# export ROS_DOMAIN_ID=23

# 任务 1：键盘窗口接收按键；i 前进，逗号后退，j/l 转向，k 停止。
# 已有自动打开的 YUYU-keyboard 就使用它；下面命令仅在 keyboard:=false 时手动启动。
# ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/teleop_cmd_vel -p speed:=0.02 -p turn:=0.25 -p repeat_rate:=10.0 -p key_timeout:=0.3

# 任务 2：负面指令优先匹配；过来目前指向桌面中心，回去指向待命点。
# ros2 topic pub --once /command_text std_msgs/msg/String "data: '禹禹，回去'"
# ros2 topic pub --once /command_text std_msgs/msg/String "data: '禹禹，过来'"
# ros2 topic pub --once /command_text std_msgs/msg/String "data: '今天有点烦'"
# ros2 topic pub --once /command_text std_msgs/msg/String "data: '禹禹，跳个舞'"
# ros2 topic pub --once /command_text std_msgs/msg/String "data: '不想说'"
# ros2 topic pub --once /command_text std_msgs/msg/String "data: '恢复说话'"
# ros2 topic pub --once /command_text std_msgs/msg/String "data: '停下'"

# 屏幕独立测试：happy/care/sleepy/curious/silent/dance。
# ros2 topic pub --once /face_expr std_msgs/msg/String "data: 'curious'"
# ros2 topic pub --once /face_text std_msgs/msg/String "data: '你好呀，我是禹禹！'"
# ros2 topic pub --once /speak_text std_msgs/msg/String "data: '今天也一起慢慢来。'"

# 心形舞独立触发或停止，仍经过防护出口。
# ros2 topic pub --once /dance_start std_msgs/msg/Bool 'data: true'
# ros2 topic pub --once /dance_start std_msgs/msg/Bool 'data: false'

# 检查：只允许 velocity_mux 成为 /cmd_vel 发布者。
# ros2 topic info /cmd_vel --verbose
# ros2 topic echo /behavior_state
# ros2 topic echo /safety_status
# ros2 control list_controllers
# 在查看输出的“指令”终端按 Ctrl+C 只结束查看，不会结束主程序。
echo '这是命令参考文件，请打开阅读注释中的命令，按用途逐条执行。'
