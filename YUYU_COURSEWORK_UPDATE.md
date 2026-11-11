# 禹禹 0.3.0 课程更新下载

[点击下载更新包 ZIP（约215KB）](https://github.com/YUYU-25/ROS_bige_work/raw/refs/heads/delivery/yuyu-humble/yuyu_coursework_v0.3.0_20261111.zip)

SHA256：`5e76ad1b0b6e4c548f21996c0620275de93301514cf85333819c35ad0a3d38d2`

此包为已安装情绪修复和书房场景工程的离线增量更新。请先下载到 Windows，再按下面步骤传入 Ubuntu、安装和编译。

# 0.3.0 课程技术补齐

本更新针对老师实施方案的四项任务。机器人外形和原书房美术资源保持原样；新增独立课程模式，不把已知桌面底图描述成SLAM成果。

## 功能

- **在线建图与导航同时运行**：`slam_toolbox`扫描匹配生成`/map`与`map→odom`，Nav2全局/局部代价地图实际加载`/map`。已知桌沿底图作为附加保护层，防止水平雷达把桌外当作可行驶地面。
- **两种感知参与控制**：原四路下视测距防跌；新增摄像头颜色区域识别停车。使用真实`/camera/image_raw`像素，不读取物品坐标、模型名或Gazebo真值来识别。
- **里程设置**：网页展开“看见与行动”，设置2～30厘米，选择前进或后退；按融合里程计反馈闭环停车，而非按时间估算。受阻、反馈失效、视觉拦截、叫停与手动接管会取消任务。
- **条件触发响应**：启用视觉停车后，连续三帧发现足够大的红色连通区域，取消自动运动并播报/显示提示；目标移开不会自行续走，需要新指令。关闭视觉监测也不会恢复旧任务。
- **观察入口**：网页提供真实摄像头画面、视觉状态、定距反馈与在线地图更新计数。默认不启用视觉停车，避免普通红色生活物品无意触发。

视觉算法是颜色阈值与连通区域检测，并非通用物体识别。网页文字输入不冒充麦克风语音识别；原Vosk入口仍需另装模型和实际录音验收。

## 安装：先下载到Windows，再传到Ubuntu

前提：之前的情绪修复和书房场景已安装。虚拟机不需要下载网络文件，不需要Git，也不增加现有ROS/Pillow依赖。

在原主程序终端按Ctrl+C结束仿真；另开的Gazebo/RViz也先退出。保留Windows的SSH网页转发终端。

1. Windows下载`yuyu_coursework_v0.3.0_20261111.zip`到“下载”目录。
2. 在**新开的Windows PowerShell**执行，IP变化时改成当前虚拟机IP：

```powershell
scp "$env:USERPROFILE\Downloads\yuyu_coursework_v0.3.0_20261111.zip" yuyu@192.168.174.159:/home/yuyu/
```

3. 在Ubuntu终端执行：

```bash
python3 -m zipfile -e ~/yuyu_coursework_v0.3.0_20261111.zip ~/yuyu_coursework_update &&
python3 ~/yuyu_coursework_update/install_update.py ~/yuyu_robot &&
cd ~/yuyu_robot &&
source tools/env.sh &&
colcon build --symlink-install &&
source tools/env.sh &&
ros2 pkg executables yuyu_bringup | grep vision_control_node &&
echo '课程更新已安装并编译，下一步启动课程模式'
```

安装器核对完整文件校验和与原版本，先备份再替换；遇到用户自改文件会停止，不覆盖。备份位于`~/yuyu_backups/coursework_.../`。编译失败时先保留完整输出，不能把资源复制成功当作编译成功。

回退方法：将下列路径替换为安装器输出的实际备份目录，执行后重新编译：

```bash
python3 ~/yuyu_coursework_update/install_update.py --rollback ~/yuyu_backups/coursework_实际目录
```

## VMware启动：保留之前有效的双终端渲染方式

**Ubuntu主程序终端**：

```bash
cd ~/yuyu_robot &&
source tools/env.sh &&
env -u LIBGL_DRI3_DISABLE LIBGL_ALWAYS_SOFTWARE=1 bash tools/start_coursework.sh \
  gui:=false rviz:=false keyboard:=false open_browser:=false
```

**Ubuntu第二个终端**：

```bash
source ~/yuyu_robot/tools/env.sh
unset LIBGL_ALWAYS_SOFTWARE LIBGL_DRI3_DISABLE
export GAZEBO_MODEL_PATH="$(ros2 pkg prefix yuyu_description)/share:${GAZEBO_MODEL_PATH:-}"
ros2 launch gazebo_ros gzclient.launch.py &
ros2 run rviz2 rviz2 -d "$(ros2 pkg prefix yuyu_description)/share/yuyu_description/rviz/yuyu_coursework.rviz" -f map --ros-args -p use_sim_time:=true &
```

两个Ubuntu终端保留。Windows原SSH转发PowerShell保持开启，浏览器打开`http://127.0.0.1:18765`并按F5刷新。转发断开时用新的PowerShell运行：

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:18765:127.0.0.1:8765 yuyu@192.168.174.159
```

需要展示键盘控制时，另开Ubuntu终端：

```bash
source ~/yuyu_robot/tools/env.sh
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/teleop_cmd_vel -p speed:=0.05 -p turn:=0.65 -p repeat_rate:=10.0 -p key_timeout:=0.3
```

按`i`前进、`,`后退、`j/l`转向、`k`停车。不要把速度直接发往`/cmd_vel`绕过保护。

原陪伴模式继续用`bash tools/start.sh`，其默认仍使用已知地图。非VMware环境也可直接`ros2 launch yuyu_gazebo coursework.launch.py`统一启动全套节点。

## 简短验收与报告取证

1. 在RViz“Online SLAM Map”观察实时生成的地图，同时发送“回去”“过来”导航；运行期间地图与位姿继续更新。不要加载原已知地图截图冒充实时建图。
2. 展开网页“看见与行动”，在空位设8厘米，前进、后退后观察实际停车与距离反馈；若被保护打断，以“已中止”处理，不算距离完成。
3. 启用视觉停车，观察摄像头中的红色物品；看见后停车并提示。移开目标后保持停止，再重新发指令。识别依据颜色，红色书籍/杯子等都可能触发。
4. 防跌已有实际下视传感器测试。日常场景还有坐标边界和桌边挡沿，不能把被这些保护拦停的录像当成下视传感器触发；若要单独展示下视防跌，用原无挡边专项场景与对应脚本记录真实`/cliff/*`变化。

导出当前SLAM地图作为报告附件：

```bash
source ~/yuyu_robot/tools/env.sh
ros2 run nav2_map_server map_saver_cli -f ~/yuyu_slam_report --ros-args -p use_sim_time:=true -p save_map_timeout:=10.0
```

将生成`~/yuyu_slam_report.pgm`和`.yaml`。该命令已在独立Gazebo仿真中实际导出成功。

## 算法说明要点

定距进度取起点朝向上的里程计位移投影：`s = d[(x-x0)cosθ0+(y-y0)sinθ0]`，`d=±1`表示前后方向。剩余距离`e=L-s`，速度随`e`减小；偏航误差闭环修正，达到3毫米阈值后请求零速度。该阈值不是对实体/所有虚拟机误差的保证。

视觉将图像缩小至最多80×60；红色条件为`R≥70, R≥1.55G, R≥1.55B, R-min(G,B)≥40`，取最大四连通区域，占图像≥1.5%且连续三帧触发。五帧未检出可清除目标状态，但不会恢复被取消的动作。启用时图像失效超过0.8秒则保持停车。

SLAM缩小了Karto相关搜索范围与角度步长以适应16厘米机器人，采用5毫米栅格；书房模式为已经可见的书柜背板、立板与窗玻璃加入桌外物理扫描面。扫描几何不依赖不可见的预制地图，也不向产品控制器发布Gazebo真值。

## 验证记录与边界

独立Ubuntu22.04、ROS2 Humble、Gazebo11环境：三包编译通过；61项测试中58通过、3跳过（宿主缺少对应ROS消息/离线音频依赖）；浏览器距离±8厘米、视觉开关、停止、390像素布局通过。

真实Gazebo+SLAM+Nav2测量：设定±8厘米，真值位移分别0.078131米、0.078066米；“回去”“过来”真值目标误差0.022013米、0.018544米；导航时分别收到12次、12次在线地图更新；抽样地图定位与真值位置差最大约1.4厘米。真实渲染红色目标通过摄像头触发停车，移除后不续走。真值服务只在测试脚本里用于断言与放置测试标记。

补充验收中，一次导航收到9张地图，其中4种不同内容，占用栅格从841增至877，证实导航时地图内容发生实际变化；运行参数也确认全局和局部代价地图的`slam_layer.map_topic`均为`/map`，扫描匹配启用。

数据见`docs/coursework-physical-results.json`、`docs/coursework-map-content-results.json`；摄像头与地图图片为本次实际仿真输出，不是Blender概念预览。首次静止扫描尚未积累多角度观测时，地图占用点可能不足；运动后已验收。日志仍可出现部分TF时间窗导致的扫描丢弃，不能据此声称零丢帧或任意场景可靠。当前验证范围是这套书房/小桌面场景；没有替用户确认VMware安装和负载表现。


为兼容Mesa/SVGA的原生地图纹理着色器问题，课程RViz默认用`/online_map_marker`显示由真实`/map`逐格转换的彩色网格；它只改变显示方式，地图原点、尺寸和各栅格类别保持一致，导航仍使用原始`/map`。原生Map显示保留为可选项。实际ROS检查已验证显示网格的坐标原点和总面积与源地图一致。


最终课程模式已在补齐原项目依赖的中文字体后重新编译和进行真实运动验收。Gazebo客户端与RViz同时运行时已捕获真实地图/模型画面，见`docs/previews/coursework-rviz-live.png`。云端软件OpenGL下，RViz被定时结束时仍出现底层内存退出异常；运行时地图已显示，此项不作为VMware显卡稳定性或帧率的验收。VMware继续采用此前有效的服务端软件渲染、客户端硬件渲染方式。

控制器启动为加载和切换服务增加60秒等待，避免负载大时默认10秒超时后重复加载；启动阶段需等网页显示传感器就绪再发运动指令。
