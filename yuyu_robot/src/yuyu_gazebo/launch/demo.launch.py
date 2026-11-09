"""基础模型与桌面：先单独验证物理、传感器和屏幕。"""
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import xacro


def generate_launch_description():
    desc = get_package_share_directory('yuyu_description')
    gazebo = get_package_share_directory('yuyu_gazebo')
    gui, rviz, keyboard = [LaunchConfiguration(n) for n in ('gui', 'rviz', 'keyboard')]
    robot = xacro.process_file(os.path.join(desc, 'urdf/yuyu.urdf.xacro')).toxml()
    spawn = Node(package='gazebo_ros', executable='spawn_entity.py',
                 arguments=['-entity', 'yuyu', '-topic', 'robot_description', '-z', '0.752'],
                 output='screen')
    js = Node(package='controller_manager', executable='spawner',
              arguments=['joint_state_broadcaster', '--controller-manager-timeout', '90'])
    drive = Node(package='controller_manager', executable='spawner',
                 arguments=['diffbot_base_controller', '--controller-manager-timeout', '90'])
    sim = {'use_sim_time': True}
    actions = [
        # package:// 在 SDF 中转换为 model://，Gazebo 必须能找到包的上级 share 目录。
        SetEnvironmentVariable('GAZEBO_MODEL_PATH', os.path.dirname(desc)+os.pathsep+
                               os.environ.get('GAZEBO_MODEL_PATH','')),
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('keyboard', default_value='false'),
        DeclareLaunchArgument('safety_frame', default_value='odom'),
        DeclareLaunchArgument('rviz_frame', default_value='base_footprint'),
        DeclareLaunchArgument('world', default_value=os.path.join(gazebo, 'worlds/desk.world')),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('gazebo_ros'), 'launch/gazebo.launch.py')),
            launch_arguments={'world': LaunchConfiguration('world'), 'gui': gui,
                              'verbose': 'false'}.items()),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[sim, {'robot_description': robot}], output='screen'),
        # 必须先注册事件，再启动 spawn，否则进程过快结束可能漏掉事件。
        RegisterEventHandler(OnProcessExit(target_action=spawn, on_exit=[js])),
        RegisterEventHandler(OnProcessExit(target_action=js, on_exit=[drive])),
        spawn,
        Node(package='yuyu_bringup', executable='face_display_node', parameters=[sim]),
        Node(package='yuyu_bringup', executable='range_adapter_node', parameters=[sim]),
        Node(package='yuyu_bringup', executable='edge_guard_node', parameters=[sim,
             {'safety_frame':LaunchConfiguration('safety_frame')}]),
        Node(package='yuyu_bringup', executable='velocity_mux_node', parameters=[sim]),
        Node(package='rviz2', executable='rviz2', condition=IfCondition(rviz),
             arguments=['-d', os.path.join(desc, 'rviz/yuyu_view.rviz'),
                        '-f',LaunchConfiguration('rviz_frame')], parameters=[sim]),
        # 键盘程序需要交互式终端，直接作为后台节点启动收不到按键。
        Node(package='teleop_twist_keyboard', executable='teleop_twist_keyboard',
             name='yuyu_keyboard', prefix='xterm -T YUYU-keyboard -e',
             condition=IfCondition(keyboard), output='screen',
             parameters=[{'speed': 0.02, 'turn': 0.25, 'repeat_rate': 10.0, 'key_timeout': 0.3}],
             remappings=[('cmd_vel', '/teleop_cmd_vel')]),
    ]
    return LaunchDescription(actions)
