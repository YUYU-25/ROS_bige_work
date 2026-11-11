# 0.4.0 看见人后，面向人说话

本页配套离线包：[`yuyu_people_v0.4.0_20261111.zip`](./yuyu_people_v0.4.0_20261111.zip)，校验文件：[`SHA256`](./yuyu_people_v0.4.0_20261111.zip.sha256)。下载后按下文在Windows传入Ubuntu，不必让虚拟机联网下载。

此更新安装在已经验收的0.3.0课程版本上。保留机器人模型、书房、SLAM/Nav2、定距、红色视觉停车、桌沿保护与原有语音设置；新增坐在书桌外的仿真人物、离线人脸检测和两种摄像头入口。没有增加云端识别服务。

## 两种入口与实际能力

| 入口 | 可以做什么 | 朝向控制 |
| --- | --- | --- |
| 场景人物 | 从Gazebo机器人摄像头的真实RGB像素检测正面人脸，出现时问候 | 原地转向，把人脸移到画面中央；可以在普通回复播报前调整朝向 |
| Windows真人摄像头 | 经浏览器授权后发送缩小的实时画面，在Ubuntu本地检测人脸并问候；继续通过原文字/语音入口聊天 | 电脑摄像头固定，不随机器人转动，因此本模式保持机身朝向 |

检测的是人脸的存在与图像位置，不知道人物姓名，不做身份识别、表情判断、唇读或说话人确认。多人时选择检测得分最高的候选，不能保证选中正在说话的人。侧脸、遮挡、逆光、过小的人脸仍可能漏检。

真正让实体机器人朝真人转动，需要摄像头装在机身上并接入其图像话题，或完成电脑摄像头与机器人之间的空间标定。未标定的Windows摄像头方向不能直接控制Gazebo机身。当前模型没有头部俯仰关节，调整的是机身水平方向。

“过来”“回去”仍是原有桌面导航目标；本更新没有把人脸检测宣传为追踪人走动或导航到真人身边。

## 安装：Windows下载，传到Ubuntu，离线编译

主程序终端Ctrl+C停止仿真，另开的Gazebo/RViz也退出。Windows网页SSH转发窗口可以保留。

1. 将`yuyu_people_v0.4.0_20261111.zip`下载到Windows的“下载”目录。
2. 新开Windows PowerShell执行（先将命令中的“Ubuntu用户名”和“虚拟机IP”替换为自己的实际值）：

```powershell
scp "$env:USERPROFILE\Downloads\yuyu_people_v0.4.0_20261111.zip" Ubuntu用户名@虚拟机IP:~/
```

3. Ubuntu终端执行：

```bash
python3 -m zipfile -e ~/yuyu_people_v0.4.0_20261111.zip ~/yuyu_people_update &&
python3 ~/yuyu_people_update/install_update.py ~/yuyu_robot &&
cd ~/yuyu_robot &&
source tools/env.sh &&
colcon build --symlink-install &&
source tools/env.sh &&
python3 -c 'import cv2; from yuyu_bringup.person import FaceDetector; print("OpenCV", cv2.__version__)' &&
ros2 pkg executables yuyu_bringup | grep person_control_node
```

模型、纹理与检测器随包提供，不需要Git、Blender或联网下载模型。完整Gazebo/ROS依赖通常已有OpenCV，本次原生Humble环境确认已有4.5.4。若出现`No module named cv2`，该虚拟机缺少`python3-opencv`；这时保留报错，不把安装完成当成检测已可用。

安装器逐项核对原版本和内容校验和，完整预检后备份再替换；用户自改文件会停止安装。备份在`~/yuyu_backups/people_.../`。需要回退时使用实际备份目录，随后重新编译：

```bash
python3 ~/yuyu_people_update/install_update.py --rollback ~/yuyu_backups/people_实际目录
```

## 启动：沿用已解决VMware卡顿的方式

Ubuntu主程序终端：

```bash
cd ~/yuyu_robot &&
source tools/env.sh &&
env -u LIBGL_DRI3_DISABLE LIBGL_ALWAYS_SOFTWARE=1 bash tools/start_coursework.sh \
  gui:=false rviz:=false keyboard:=false open_browser:=false
```

Ubuntu第二个终端：

```bash
source ~/yuyu_robot/tools/env.sh
unset LIBGL_ALWAYS_SOFTWARE LIBGL_DRI3_DISABLE
export GAZEBO_MODEL_PATH="$(ros2 pkg prefix yuyu_description)/share:${GAZEBO_MODEL_PATH:-}"
ros2 launch gazebo_ros gzclient.launch.py &
ros2 run rviz2 rviz2 -d "$(ros2 pkg prefix yuyu_description)/share/yuyu_description/rviz/yuyu_coursework.rviz" -f map --ros-args -p use_sim_time:=true &
```

新的课程模式默认加载`study_people.world`。旧`study_slam.world`仍保留；人物是静态环境模型，位于桌外，不改变机器人外形与桌面活动范围。

Windows原SSH转发窗口保持打开；若已关闭，在PowerShell执行：

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:18765:127.0.0.1:8765 Ubuntu用户名@虚拟机IP
```

浏览器打开`http://127.0.0.1:18765`，按Ctrl+F5更新网页资源。这个localhost地址也允许浏览器请求真人摄像头；普通局域网HTTP地址通常不允许。

## 使用和简短验收

页面向下展开“看见你，听你说”。默认关闭人物互动，避免启动时自行转向或开启Windows摄像头。

1. **场景人物**：点击“开启场景人物互动”。在摄像头预览中看到桌外人物的正面，状态出现“已检测到场景人脸”；点击“看向人物”，观察机器人原地转向和“已经面向说话对象”。
2. **回应前朝向**：保留“回应前先面向场景人物”勾选，轻微转开后输入一句日常聊天。普通回复最多等待约10秒尝试朝向；找不到人会先停稳再正常回复，不会假称已看向人。导航、舞蹈、定距运行期间普通聊天不抢占当前运动。
3. **叫停**：转向期间点击“停在这里”或输入“停下”；确认机身停止，等待朝向的旧回复不会在稍后突然播报。手动方向键接管、静音、视觉拦停、传感器故障也会取消转向。
4. **真人摄像头**：点击“开启真人摄像头”，在Windows浏览器权限弹窗允许摄像头。正面看向摄像头，状态出现“已检测到人脸”，机器人问候；此模式不会驱动仿真机身转动。
5. **关闭**：点击“关闭人物互动”后浏览器摄像头指示灯应熄灭，预览消失。禁止权限、没有摄像头或被其他应用占用时会显示错误，不能算真人摄像头已验收。

“看向人物”在未看到人时最多原地搜索一圈，并有18秒期限；普通回复不做完整转圈搜索，只使用最近30秒内的图像方向作为提示。提示不能当作成功依据，必须重新在画面中检测并对齐人脸。目标丢失后立即请求零转速，约0.8秒仍未重现则取消；帧超过1.2秒失效也停止。受保护拦停时不自动重试运动。

## 报告可以使用的技术说明

图像最多缩到400×300，采用局部对比度CLAHE和OpenCV Haar级联，单线程、最多约3Hz，连续两次检测才确认。Haar权重阈值2用于排除低分候选，不能描述成概率或识别准确率。

人脸框中心`u=x+w/2`归一化到[0,1]。机器人相机水平视场角`α=1.15rad`，目标偏角`e=atan((1-2u)tan(α/2))`。视觉闭环输出`v=0`、`ω=clip(1.4e, ±0.32rad/s)`，小误差约2°内请求零速；两个不同图像序号均对齐才确认完成。搜索或返回最近方向时角速度不超过0.45rad/s。

数据流：`/camera/image_raw`或`/operator_camera/image_raw` → `person_control_node` → `/person_status` → 行为协调器`FACING` → 原有速度仲裁和安全出口。普通回复通过`/attention_speech_request`、`/attention_speech_ready`协调，恢复说话先立即解除静音，再决定是否等待朝向。

产品节点不读取Gazebo人物名、人物真值坐标或预置角度来“识别人”。只有独立测试脚本调用真值服务测量误差、移走测试人物。

## 摄像头数据与素材

Windows模式仅在用户点击并授权后取视频，不请求麦克风；画面约每550毫秒缩小为JPEG，经当前本地SSH转发到Ubuntu。服务器只保留RAM中的最新待处理帧，不把真人照片写入磁盘或设置文件；状态接口只有框、方向和检测状态。关闭、页面离开或连接失效会停止本页面的视频采集；冻结的视频帧不会重复提交成新帧。现有语音录音管理是独立功能。

场景人物是原创2628三角面低模，脸部纹理引用**NASA公开照片**，不是用户照片；纹理原始字节保持不变，通过网格UV选择脸部区域。来源、作者与许可见`src/yuyu_description/meshes/person/SOURCES.md`。OpenCV模型与原许可在`src/yuyu_bringup/config/person/`。

## 验证记录

宿主71项测试中67通过、4因缺少对应ROS/OpenCV/音频环境跳过；原生Ubuntu22.04/Humble环境另运行10项人物互动测试全部通过，其中包括真实OpenCV、公用照片、实际Gazebo帧与空白负例。三包colcon编译通过。

浏览器自动化通过场景模式、转向请求、合成动态摄像头上传、关闭释放摄像头并停止上传、390像素宽度及无JS异常检查；这不等于已在用户Windows摄像头硬件上验收。

最终Gazebo实测：初始人脸偏角约20.6°，朝向人物的真值误差约0.16°，转向过程平移4.4毫米；轻微转开后普通回复等待约5.08秒并在视觉对齐之后释放。叫停取消转向与待播报文本；移走人物后约1.60秒进入停止状态（含图像检测与观察等待）。公用照片通过真实HTTP→ROS→检测器后检出并问候，未产生机身转向，关闭会话后旧帧被拒绝。这些数值是一次仿真实测，不是实体或所有硬件的精度/时延保证。

Gazebo视觉闭环与真实HTTP/ROS链路的数据见`docs/person-physical-results.json`。`docs/previews/person-camera-initial.png`、`person-camera-centered.png`是实际机器人摄像头画面，不是概念预览。语音测试使用文字播报出口验证顺序，未替代用户扬声器听感验收。原有0.3.0建图、导航等测量保存在原文档，未将旧测量说成本次重新验收。

软件渲染、长时间运行的压力复测中，把人物大角度转出视野后，返回方向有过10秒超时并安全停车的情况；不能承诺任意位置都能找到人物。课堂展示建议先确认实际摄像头内看得到正面人脸，再演示视觉闭环与回应前朝向。

云端chroot复测另遇到Fast DDS大参数响应丢失导致控制器未启动；最终测试在独立ROS域31、仅本机UDP、16KiB最大消息和1MiB收发缓冲的测试专用配置下完成。该配置未写入用户工程，不改动原虚拟机已验证的启动环境。
