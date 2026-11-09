#!/usr/bin/env python3
"""生成可复现的模型网格、桌面地图与包安装元数据，不依赖 ROS。"""
import math
import struct
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def write(path, text):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


def rounded_mesh():
    # 单位超椭球，xacro 按 xyz 缩放；圆润方块而非简单叠圆柱。
    def sp(x, e):
        return math.copysign(abs(x)**e, x)
    def point(u, v):
        return (0.5*sp(math.cos(u), .32)*sp(math.cos(v), .32),
                0.5*sp(math.cos(u), .32)*sp(math.sin(v), .32),
                0.5*sp(math.sin(u), .32))
    triangles = []
    for i in range(48):
        for j in range(96):
            a, b = -math.pi/2+math.pi*i/48, -math.pi/2+math.pi*(i+1)/48
            c, d = 2*math.pi*j/96, 2*math.pi*(j+1)/96
            p, q, r, s = point(a,c), point(a,d), point(b,d), point(b,c)
            triangles.extend(((p,q,r), (p,r,s)))
    p = ROOT/'src/yuyu_description/meshes/rounded_box.stl'
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('wb') as f:
        f.write(b'YUYU original rounded superellipsoid'.ljust(80, b' '))
        f.write(struct.pack('<I', len(triangles)))
        for triangle in triangles:
            a,b,c = triangle
            u,v = [b[k]-a[k] for k in range(3)], [c[k]-a[k] for k in range(3)]
            n = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
            length = math.sqrt(sum(x*x for x in n)) or 1
            f.write(struct.pack('<12fH', *(x/length for x in n), *a,*b,*c,0))


def package(name, dependencies, executables=None):
    base = 'src/'+name
    write(base+'/resource/'+name, '')
    write(base+'/'+name+'/__init__.py', '"""禹禹项目资源包。"""\n') if name != 'yuyu_bringup' else None
    deps = ''.join('  <exec_depend>%s</exec_depend>\n' % d for d in dependencies)
    extra = '<gazebo_ros gazebo_model_path="${prefix}/.."/>' if name == 'yuyu_description' else ''
    write(base+'/package.xml', '''<?xml version="1.0"?>
<package format="3">
  <name>%s</name><version>0.1.0</version>
  <description>YUYU desktop companion robot, original ROS 2 Humble simulation.</description>
  <maintainer email="maintainer@example.com">YUYU project</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_python</buildtool_depend>
%s  <export><build_type>ament_python</build_type>%s</export>
</package>
''' % (name, deps, extra))
    entries = executables or {}
    write(base+'/setup.py', '''from pathlib import Path
from setuptools import setup, find_packages

package_name = '%s'
# 保留各级资源目录，避免 colcon 安装后找不到 launch、网格或配置。
data_files = [('share/ament_index/resource_index/packages', ['resource/'+package_name]),
              ('share/'+package_name, ['package.xml'])]
for folder in ('launch', 'urdf', 'meshes', 'rviz', 'ros2_control', 'worlds', 'config', 'maps'):
    root = Path(folder)
    if root.exists():
        parents = sorted({p.parent for p in root.rglob('*') if p.is_file()})
        for parent in parents:
            data_files.append(('share/'+package_name+'/'+str(parent),
                               [str(p) for p in sorted(parent.iterdir()) if p.is_file()]))
setup(name=package_name, version='0.1.0', packages=find_packages(),
      data_files=data_files, install_requires=['setuptools'], zip_safe=True,
      maintainer='YUYU project', maintainer_email='maintainer@example.com',
      description='YUYU desktop robot', license='Apache-2.0',
      entry_points={'console_scripts': %s})
''' % (name, repr([key+' = '+value for key,value in entries.items()])))
    write(base+'/setup.cfg', '[develop]\nscript_dir=$base/lib/'+name+'\n[install]\ninstall_scripts=$base/lib/'+name+'\n')


def desk_map():
    # 黑色为障碍：桌外、杯子、笔盒和台灯底座；不把“无回波”当安全区域。
    w,h,res = 130,90,.01
    pixels = bytearray()
    for row in range(h):
        y = -.45+(h-row-.5)*res
        for col in range(w):
            x = -.65+(col+.5)*res
            occupied = (abs(x) > .49 or abs(y) > .29 or
                        math.hypot(x-.2,y-.1) < .04 or
                        (abs(x+.2)<.075 and abs(y+.15)<.025) or
                        math.hypot(x-.35,y+.2)<.045)
            pixels.append(0 if occupied else 254)
    p = ROOT/'src/yuyu_gazebo/maps/desk.pgm'
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(('P5\n%d %d\n255\n' % (w,h)).encode()+pixels)
    write('src/yuyu_gazebo/maps/desk.yaml', yaml.safe_dump(dict(
        image='desk.pgm', mode='trinary', resolution=res, origin=[-.65,-.45,0.],
        negate=0, occupied_thresh=.65, free_thresh=.25),sort_keys=False))


def mapping_world():
    # 顶部雷达看不到矮物品，SLAM 版在桌外增加不参与防摔的竖直标定板。
    source=(ROOT/'src/yuyu_gazebo/worlds/desk.world').read_text(encoding='utf-8')
    panels=[]
    for name,x,y,sx,sy in [('north',0,.48,1.36,.012),('south',0,-.48,1.36,.012),
                          ('east',.68,0,.012,.96),('west',-.68,0,.012,.96)]:
        panels.append('''<model name="slam_board_%s"><static>true</static><pose>%s %s .875 0 0 0</pose>
<link name="panel"><collision name="c"><geometry><box><size>%s %s .25</size></box></geometry></collision>
<visual name="v"><geometry><box><size>%s %s .25</size></box></geometry><transparency>.88</transparency><cast_shadows>false</cast_shadows><material><ambient>.14 .17 .20 1</ambient><diffuse>.25 .29 .34 1</diffuse></material></visual></link></model>'''
                      % (name,x,y,sx,sy,sx,sy))
    write('src/yuyu_gazebo/worlds/desk_slam.world',source.replace('</world>',
          '\n<!-- 桌外标定背景，不是桌沿挡墙。 -->\n'+'\n'.join(panels)+'\n</world>'))


if __name__ == '__main__':
    package('yuyu_description', ['xacro','robot_state_publisher','controller_manager',
            'joint_state_broadcaster','diff_drive_controller','gazebo_ros2_control'])
    package('yuyu_gazebo', ['yuyu_description','yuyu_bringup','gazebo_ros','gazebo_plugins',
            'rviz2','nav2_bringup','nav2_map_server','slam_toolbox','teleop_twist_keyboard',
            'xterm','launch_ros'])
    names = dict(voice_emotion_node='voice_main', face_display_node='face_main',
                 tts_node='tts_main', edge_guard_node='edge_main', velocity_mux_node='mux_main',
                 behavior_manager_node='behavior_main', dance_node='dance_main',
                 range_adapter_node='range_main')
    package('yuyu_bringup', ['rclpy','std_msgs','geometry_msgs','nav_msgs','sensor_msgs',
            'nav2_msgs','tf2_ros','ament_index_python','python3-yaml','python3-pil','fonts-noto-cjk','espeak'],
            {name:'yuyu_bringup.nodes:'+main for name,main in names.items()})
    for name, main in names.items():
        write('src/yuyu_bringup/scripts/'+name+'.py',
              '#!/usr/bin/env python3\n"""源码入口；安装后使用 ros2 run yuyu_bringup '+name+'。"""\n'
              'from yuyu_bringup.nodes import '+main+'\n\nif __name__ == "__main__":\n    '+main+'()\n')
    rounded_mesh()
    desk_map()
    mapping_world()
