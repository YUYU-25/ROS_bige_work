"""一键启动；初始状态静止，收到文本或键盘输入后才移动。"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('yuyu_gazebo')
    cfg = os.path.join(get_package_share_directory('yuyu_bringup'), 'config')
    sim = {'use_sim_time': True}
    use_slam = LaunchConfiguration('use_slam')
    world = PathJoinSubstitution([share, 'worlds', PythonExpression([
        "'desk_slam.world' if '", use_slam, "'.lower() in ('true','1') else 'desk.world'"])])
    actions = [DeclareLaunchArgument('gui', default_value='true'),
               DeclareLaunchArgument('rviz', default_value='true'),
               DeclareLaunchArgument('keyboard', default_value='true'),
               DeclareLaunchArgument('audio', default_value='true'),
               DeclareLaunchArgument('use_slam', default_value='true'),
               IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(share, 'launch/demo.launch.py')),
                    launch_arguments={**{n: LaunchConfiguration(n) for n in ('gui','rviz','keyboard')},
                                      'world':world,'safety_frame':'map','rviz_frame':'map'}.items()),
               # 已知桌沿地图独立于 SLAM；激光看不到桌沿时也不能把桌外当路。
               Node(package='nav2_map_server', executable='map_server', name='desk_map_server',
                    parameters=[sim, {'yaml_filename': os.path.join(share, 'maps/desk.yaml'),
                                      'topic_name': 'desk_map', 'frame_id': 'map'}]),
               Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
                    name='desk_map_lifecycle', parameters=[sim, {'autostart': True,
                    'node_names': ['desk_map_server']}]),
               Node(package='slam_toolbox', executable='async_slam_toolbox_node',
                    name='slam_toolbox', condition=IfCondition(use_slam),
                    parameters=[os.path.join(cfg, 'slam.yaml'), sim], output='screen'),
               # 关闭 SLAM 时使用已知地图与轮式里程计；此模式不校正打滑漂移。
               Node(package='tf2_ros', executable='static_transform_publisher',
                    arguments=['--frame-id','map','--child-frame-id','odom'],
                    condition=UnlessCondition(use_slam)),
               Node(package='yuyu_bringup', executable='voice_emotion_node', parameters=[sim]),
               Node(package='yuyu_bringup', executable='behavior_manager_node', parameters=[sim]),
               Node(package='yuyu_bringup', executable='dance_node', parameters=[sim]),
               Node(package='yuyu_bringup', executable='tts_node', parameters=[sim,
                    {'audio': LaunchConfiguration('audio')}]),
    ]
    # 完整导航服务与生命周期，不只启动 planner/controller 两个孤立节点。
    nav_nodes = [('nav2_controller','controller_server'), ('nav2_planner','planner_server'),
                 ('nav2_smoother','smoother_server'), ('nav2_behaviors','behavior_server'),
                 ('nav2_bt_navigator','bt_navigator'), ('nav2_waypoint_follower','waypoint_follower'),
                 ('nav2_velocity_smoother','velocity_smoother')]
    for package, executable in nav_nodes:
        remaps = [('cmd_vel','/nav_raw_cmd_vel')]
        if executable == 'velocity_smoother':
            remaps += [('cmd_vel_smoothed','/nav_cmd_vel')]
        actions.append(Node(package=package, executable=executable, name=executable,
                            parameters=[os.path.join(cfg,'nav2.yaml'),sim],
                            remappings=remaps, output='screen'))
    actions.append(Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
                        name='navigation_lifecycle', parameters=[sim, {'autostart':True,
                        'node_names':[name for _,name in nav_nodes], 'bond_timeout': 10.0}]))
    return LaunchDescription(actions)
