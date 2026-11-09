from pathlib import Path
from setuptools import setup, find_packages

package_name = 'yuyu_bringup'
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
      entry_points={'console_scripts': ['voice_emotion_node = yuyu_bringup.nodes:voice_main', 'face_display_node = yuyu_bringup.nodes:face_main', 'tts_node = yuyu_bringup.nodes:tts_main', 'edge_guard_node = yuyu_bringup.nodes:edge_main', 'velocity_mux_node = yuyu_bringup.nodes:mux_main', 'behavior_manager_node = yuyu_bringup.nodes:behavior_main', 'dance_node = yuyu_bringup.nodes:dance_main', 'range_adapter_node = yuyu_bringup.nodes:range_main']})
