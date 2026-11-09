"""ROS 2 节点：文本、屏幕、语音、传感器防护、速度仲裁与行为。"""
import json
import math
import random
import shutil
import subprocess
import struct
import time
from functools import partial
from pathlib import Path

import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import Odometry, Path as NavPath
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.serialization import deserialize_message
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener, TransformException
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import Image, LaserScan, Range
from std_msgs.msg import Bool, Float64, String

from .core import (CLIFF_NAMES, chase, cliff_state, fit_heart, interpret,
                   safe_velocity, wrap_angle)
from .face import EXPRESSIONS, find_font, render

LATCH = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)


def string(value):
    return String(data=str(value))


def twist(v=0.0, w=0.0):
    msg = Twist()
    msg.linear.x, msg.angular.z = float(v), float(w)
    return msg


def pose_of(msg):
    p, q = msg.pose.pose.position, msg.pose.pose.orientation
    yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
    return p.x, p.y, yaw


def pose_in_map(buffer, now):
    """已知桌沿/物品位于 map，不能把会打滑漂移的原始 odom 直接当 map。"""
    transform = buffer.lookup_transform('map', 'base_footprint', Time())
    stamp = transform.header.stamp
    if now.nanoseconds-(stamp.sec*1000000000+stamp.nanosec)>700000000:
        raise TransformException('map 位姿已过期')
    t, q = transform.transform.translation, transform.transform.rotation
    return (t.x, t.y, math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z)))


def quotes():
    path = Path(get_package_share_directory('yuyu_bringup')) / 'config/quotes.yaml'
    return yaml.safe_load(path.read_text(encoding='utf-8'))


class VoiceEmotion(Node):
    def __init__(self):
        super().__init__('voice_emotion')
        self.library = quotes()
        self.behavior = self.create_publisher(String, '/behavior_cmd', 10)
        self.emotion = self.create_publisher(String, '/emotion_tag', LATCH)
        self.speak = self.create_publisher(String, '/speak_text', 10)
        self.text = self.create_publisher(String, '/face_text', 10)
        self.create_subscription(String, '/command_text', self.on_text, 10)

    def on_text(self, msg):
        command, emotion = interpret(msg.data)
        if emotion:
            self.emotion.publish(string(emotion))
            quote = random.choice(self.library.get(emotion, self.library['none']))
            if emotion == 'silent':
                self.text.publish(string(quote))
            else:
                self.speak.publish(string(quote))
        if command:
            self.behavior.publish(string(command))
        self.get_logger().info('文本：%s → 指令=%s，情绪=%s' % (msg.data, command, emotion))


class FaceDisplay(Node):
    def __init__(self):
        super().__init__('face_display')
        self.declare_parameter('font_path', '')
        self.font = find_font(self.get_parameter('font_path').value)
        self.expr, self.text, self.text_at = 'happy', '', 0.0
        self.pub = self.create_publisher(Image, '/face_image', 2)
        self.create_subscription(String, '/face_expr', self.on_expr, 10)
        self.create_subscription(String, '/face_text', self.on_text, 10)
        self.create_timer(0.1, self.tick)

    def on_expr(self, msg):
        if msg.data in EXPRESSIONS:
            self.expr = msg.data

    def on_text(self, msg):
        self.text, self.text_at = msg.data.replace('\n', ' '), time.monotonic()

    def tick(self):
        elapsed = time.monotonic()-self.text_at
        text = ''
        if elapsed < 3 and self.text:
            pages = math.ceil(len(self.text)/45)
            page = min(pages-1, int(elapsed/3*pages))
            text = self.text[page*45:(page+1)*45]
        img = render(self.expr, text, self.font, time.monotonic())
        msg = Image()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'face_screen_link'
        msg.width, msg.height = img.size
        msg.encoding, msg.step = 'rgb8', img.width*3
        msg.data = img.tobytes()
        self.pub.publish(msg)


class TTS(Node):
    def __init__(self):
        super().__init__('tts')
        self.declare_parameter('audio', True)
        self.audio = self.get_parameter('audio').value
        self.text = self.create_publisher(String, '/face_text', 10)
        self.done = self.create_publisher(Bool, '/speak_done', 10)
        self.silent, self.proc, self.queue = False, None, []
        self.deadline = 0.0
        self.create_subscription(String, '/speak_text', self.on_speak, 10)
        self.create_subscription(String, '/emotion_tag', self.on_emotion, LATCH)
        self.create_timer(0.1, self.tick)

    def on_emotion(self, msg):
        if msg.data == 'none':
            self.silent = False
        if msg.data == 'silent':
            self.silent = True
            self.queue.clear()
            if self.proc:
                self.proc.terminate()
            self.done.publish(Bool(data=True))

    def on_speak(self, msg):
        if not msg.data.strip():
            return
        if self.silent:
            self.text.publish(msg)
            self.done.publish(Bool(data=True))
        else:
            # 限制排队长度，避免测试时积攒很久以前的语音。
            self.queue = (self.queue+[msg.data])[-4:]

    def tick(self):
        if self.proc:
            if self.proc.poll() is None:
                return
            if self.proc.returncode > 0:
                self.get_logger().warning('语音进程退出；文字仍正常显示，请检查系统音频。')
            self.proc.wait()
            self.proc = None
            self.done.publish(Bool(data=True))
        if self.deadline:
            if time.monotonic() < self.deadline:
                return
            self.deadline = 0
            self.done.publish(Bool(data=True))
        if not self.queue or self.silent:
            return
        text = self.queue.pop(0)
        self.text.publish(string(text))
        self.done.publish(Bool(data=False))
        # 列表参数调用，不把用户输入交给 shell 执行。
        executable = shutil.which('espeak-ng') or shutil.which('espeak')
        if self.audio and executable:
            self.proc = subprocess.Popen([executable, '-v', 'cmn' if executable.endswith('espeak-ng') else 'zh',
                                          '-s', '145', '--', text],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            self.deadline = time.monotonic()+3
            self.get_logger().info('文字播报：'+text)

    def destroy_node(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        return super().destroy_node()


class RangeAdapter(Node):
    """修正 Gazebo 无回波的 FLT_MAX，绕开 Humble Python float32 边界断言。

    Range CDR 的最后一个字段为 float32 range。先归一化这 4 字节，再交给
    ROS 标准反序列化器处理头部和其余字段；正常有限距离完全保留。
    """
    def __init__(self):
        super().__init__('range_adapter')
        self.outputs = {}
        topics = ['/cliff/'+n for n in CLIFF_NAMES]+['/proximity/front','/proximity/rear']
        for topic in topics:
            self.outputs[topic] = self.create_publisher(Range, topic, qos_profile_sensor_data)
            self.create_subscription(Range, '/raw'+topic, partial(self.convert, topic),
                                     qos_profile_sensor_data, raw=True)

    def convert(self, topic, payload):
        if len(payload) < 8:
            return
        data = bytearray(payload)
        endian = '<' if data[1] & 1 else '>'
        value = struct.unpack(endian+'f', data[-4:])[0]
        if value > 1e30:
            data[-4:] = struct.pack(endian+'f', math.inf)
        try:
            msg = deserialize_message(bytes(data), Range)
        except (RuntimeError, ValueError, AssertionError):
            return  # 没有新数据时，下游看门狗会禁止运动。
        self.outputs[topic].publish(msg)


class EdgeGuard(Node):
    def __init__(self):
        super().__init__('edge_guard')
        self.samples, self.pose, self.odom_at, self.scan_at = {}, (0, 0, 0), 0., 0.
        self.declare_parameter('safety_frame','odom')
        self.use_map = self.get_parameter('safety_frame').value == 'map'
        self.tf = Buffer()
        self.tf_listener = TransformListener(self.tf,self)
        self.pub = self.create_publisher(Bool, '/edge_detected', LATCH)
        self.status = self.create_publisher(String, '/safety_status', 5)
        self.create_subscription(Odometry, '/odom', self.on_odom, 10)
        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        for name in CLIFF_NAMES:
            self.create_subscription(Range, '/cliff/'+name,
                                     partial(self.on_range, name),
                                     qos_profile_sensor_data)
        self.create_timer(0.05, self.tick)

    def on_range(self, name, msg):
        self.samples[name] = (msg.range, time.monotonic())

    def on_odom(self, msg):
        self.odom_at = time.monotonic()
        if not self.use_map:
            self.pose = pose_of(msg)

    def on_scan(self, msg):
        self.scan_at = time.monotonic()

    def tick(self):
        now = time.monotonic()
        ready, edges = cliff_state(self.samples, now)
        ready = ready and now-self.odom_at < 0.7 and now-self.scan_at < 0.7
        if self.use_map:
            try:
                self.pose = pose_in_map(self.tf,self.get_clock().now())
            except TransformException:
                ready = False
        ready = ready and all(math.isfinite(v) for v in self.pose)
        self.pub.publish(Bool(data=not ready or any(edges.values())))
        self.status.publish(string(json.dumps(dict(ready=ready, edges=edges, pose=self.pose))))


class VelocityMux(Node):
    def __init__(self):
        super().__init__('velocity_mux')
        self.mode, self.commands = 'idle', {}
        self.manual_at = 0.
        self.status, self.status_at = {}, 0.
        self.near = {'front': (0., 0.), 'rear': (0., 0.)}
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.report = self.create_publisher(String, '/motion_status', 10)
        self.manual = self.create_publisher(Bool, '/manual_override', 10)
        self.create_subscription(String, '/motion_mode', self.on_mode, LATCH)
        self.create_subscription(String, '/safety_status', self.on_status, 5)
        for source in ('teleop', 'nav', 'behavior', 'dance'):
            self.create_subscription(Twist, '/'+source+'_cmd_vel',
                                     partial(self.on_cmd, source), 10)
        for side in ('front', 'rear'):
            self.create_subscription(Range, '/proximity/'+side,
                                     partial(self.on_near, side),
                                     qos_profile_sensor_data)
        self.create_timer(0.05, self.tick)

    def on_mode(self, msg):
        self.mode = msg.data

    def on_status(self, msg):
        self.status, self.status_at = json.loads(msg.data), time.monotonic()

    def on_cmd(self, source, msg):
        self.commands[source] = (msg, time.monotonic())
        if source == 'teleop' and (abs(msg.linear.x)>1e-5 or abs(msg.angular.z)>1e-5):
            self.manual_at = time.monotonic()
            self.manual.publish(Bool(data=True))

    def on_near(self, side, msg):
        self.near[side] = (msg.range, time.monotonic())

    def tick(self):
        now = time.monotonic()
        source = self.mode
        # 键盘人为接管优先；必须持续刷新，旧命令不能长时间驱动。
        if now-self.manual_at < 0.35:
            source = 'teleop'
        msg, stamp = self.commands.get(source, (Twist(), 0.))
        v, w = (msg.linear.x, msg.angular.z) if now-stamp < 0.35 else (0., 0.)
        ranges = {}
        for side, (distance, received) in self.near.items():
            ranges[side] = distance if now-received < 0.7 else 0.
        v, w = safe_velocity(v, w, self.status, now-self.status_at,
                             ranges['front'], ranges['rear'])
        self.pub.publish(twist(v, w))
        self.report.publish(string('%s v=%.3f w=%.3f' % (source, v, w)))


class BehaviorManager(Node):
    def __init__(self):
        super().__init__('behavior_manager')
        self.state, self.emotion = 'IDLE', 'happy'
        self.pose, self.odom_at, self.safety = (0., 0., 0.), 0., {}
        self.entered, self.start_pose = time.monotonic(), self.pose
        self.goal_handle, self.goal_pending, self.generation = None, False, 0
        self.stage, self.direction, self.target_distance = 'retreat', -1., 0.2
        self.pub_vel = self.create_publisher(Twist, '/behavior_cmd_vel', 10)
        self.face = self.create_publisher(String, '/face_expr', 10)
        self.speak = self.create_publisher(String, '/speak_text', 10)
        self.mode = self.create_publisher(String, '/motion_mode', LATCH)
        self.state_pub = self.create_publisher(String, '/behavior_state', LATCH)
        self.dance = self.create_publisher(Bool, '/dance_start', 10)
        self.goal_pub = self.create_publisher(PoseStamped, '/nav_goal', 10)
        self.client = ActionClient(self, NavigateToPose, '/navigate_to_pose')
        self.create_subscription(String, '/behavior_cmd', self.on_command, 10)
        self.create_subscription(String, '/emotion_tag', self.on_emotion, LATCH)
        self.create_subscription(Bool, '/edge_detected', self.on_edge, LATCH)
        self.create_subscription(String, '/safety_status', self.on_safety, 5)
        self.create_subscription(Odometry, '/odom', self.on_odom, 10)
        self.create_subscription(Bool, '/dance_done', self.on_dance_done, 10)
        self.create_subscription(Bool, '/dance_active', self.on_dance_active, LATCH)
        self.create_subscription(Bool, '/speak_done', self.on_speak_done, 10)
        self.create_subscription(Bool, '/manual_override', self.on_manual, 10)
        self.last_spoken = True
        self.create_timer(0.05, self.tick)
        self.set_state('IDLE')

    def set_state(self, state):
        self.state, self.entered = state, time.monotonic()
        self.idle_sleep_sent = False
        mode = {'NAVIGATING': 'nav', 'DANCING': 'dance', 'FLEEING': 'behavior'}.get(state, 'idle')
        self.mode.publish(string(mode))
        self.state_pub.publish(string(state))
        self.pub_vel.publish(Twist())
        self.get_logger().info('状态：'+state)

    def stop(self):
        self.generation += 1
        if self.goal_handle:
            self.goal_handle.cancel_goal_async()
        self.goal_handle, self.goal_pending = None, False
        self.dance.publish(Bool(data=False))
        self.set_state('IDLE')

    def on_odom(self, msg):
        self.pose, self.odom_at = pose_of(msg), time.monotonic()

    def on_safety(self, msg):
        self.safety = json.loads(msg.data)

    def on_speak_done(self, msg):
        self.last_spoken = msg.data

    def on_manual(self, msg):
        if msg.data and self.state in ('NAVIGATING','DANCING','INTERACTING'):
            self.stop()

    def on_emotion(self, msg):
        self.emotion = msg.data
        expression = dict(annoyed='care', tired='sleepy', happy='happy',
                          silent='silent', none='sleepy').get(msg.data, 'happy')
        self.face.publish(string(expression))
        if msg.data == 'silent':
            self.stop()

    def on_edge(self, msg):
        if not msg.data or self.state == 'FLEEING':
            return
        self.stop()
        if not self.safety.get('ready'):
            return
        edges = self.safety['edges']
        f = edges['front_left'] or edges['front_right']
        r = edges['rear_left'] or edges['rear_right']
        if f != r:
            self.direction = -1. if f else 1.
            self.target_distance, self.stage = 0.06, 'retreat_edge'
            self.start_pose = self.pose
            self.set_state('FLEEING')

    def on_command(self, msg):
        if msg.data == 'dance' and self.state == 'DANCING':
            return
        self.stop()
        command = msg.data
        if command == 'stop':
            return
        if not self.safety.get('ready') or any(self.safety.get('edges', {}).values()):
            self.speak.publish(string('传感器尚未就绪，或距离桌沿太近，先停一下。'))
            return
        if command in ('come', 'return'):
            # 暂用桌面中心作目标；这不是人脸定位，文档中明确说明。
            if not self.client.server_is_ready():
                self.speak.publish(string('导航还在准备，请稍后再试。'))
                return
            goal = NavigateToPose.Goal()
            goal.pose.header.frame_id = 'map'
            goal.pose.header.stamp = self.get_clock().now().to_msg()
            goal.pose.pose.orientation.w = 1.
            # 中心与待命点不同，便于演示“回去”。
            goal.pose.pose.position.x = 0. if command == 'come' else -0.18
            goal.pose.pose.position.y = 0. if command == 'come' else 0.08
            self.goal_pub.publish(goal.pose)
            self.set_state('NAVIGATING')
            generation = self.generation
            self.goal_pending = True
            future = self.client.send_goal_async(goal)
            future.add_done_callback(lambda f: self.on_goal(f, generation))
        elif command == 'dance':
            self.set_state('DANCING')
            self.face.publish(string('dance'))
            self.dance.publish(Bool(data=True))
        elif command == 'back':
            self.direction, self.target_distance = -1., 0.2
            self.stage, self.start_pose = 'retreat', self.pose
            self.set_state('FLEEING')

    def on_goal(self, future, generation):
        handle = future.result()
        if generation != self.generation:
            if handle.accepted:
                handle.cancel_goal_async()
            return
        self.goal_pending = False
        if not handle.accepted:
            self.stop()
            return
        self.goal_handle = handle
        result = handle.get_result_async()
        result.add_done_callback(lambda f: self.on_nav_done(f, generation))

    def on_nav_done(self, future, generation):
        if generation != self.generation:
            return
        self.goal_handle = None
        if future.result().status == 4:
            self.set_state('INTERACTING')
            self.face.publish(string('curious'))
            self.speak.publish(string('我过来啦，陪你待一会儿。'))
        else:
            self.stop()
            self.speak.publish(string('这条路暂时走不过去，我先停在这里。'))

    def on_dance_done(self, msg):
        if msg.data and self.state == 'DANCING':
            self.set_state('IDLE')
            self.face.publish(string('happy'))

    def on_dance_active(self, msg):
        # 兼容直接发布 /dance_start 的独立测试，不绕开速度仲裁。
        if msg.data and self.state == 'IDLE':
            self.set_state('DANCING')
            self.face.publish(string('dance'))

    def tick(self):
        elapsed = time.monotonic()-self.entered
        if self.state == 'FLEEING':
            if time.monotonic()-self.odom_at > 0.7 or elapsed > 45:
                self.stop()
                return
            moved = math.hypot(self.pose[0]-self.start_pose[0], self.pose[1]-self.start_pose[1])
            if self.stage in ('retreat', 'retreat_edge'):
                if moved < self.target_distance:
                    self.pub_vel.publish(twist(self.direction*0.02))
                elif self.stage == 'retreat_edge':
                    self.stage, self.start_pose = 'turn', self.pose
                else:
                    self.stop()
            elif abs(wrap_angle(self.pose[2]-self.start_pose[2])) < math.pi/2-0.04:
                self.pub_vel.publish(twist(0, 0.28))
            else:
                self.stop()
        elif self.state == 'INTERACTING' and elapsed > 5 and self.last_spoken:
            self.set_state('IDLE')
        elif (self.state == 'IDLE' and elapsed > 60 and self.emotion != 'silent'
              and not self.idle_sleep_sent):
            self.face.publish(string('sleepy'))
            self.idle_sleep_sent = True
        # 周期重发模式，晚启动的仲裁器也能获得状态。
        self.mode.publish(string({'NAVIGATING': 'nav', 'DANCING': 'dance',
                                  'FLEEING': 'behavior'}.get(self.state, 'idle')))


class Dance(Node):
    def __init__(self):
        super().__init__('dance')
        self.pose, self.odom_at, self.points, self.index = (0., 0., 0.), 0., [], 0
        self.started = 0.
        self.tf = Buffer()
        self.tf_listener = TransformListener(self.tf,self)
        self.pub = self.create_publisher(Twist, '/dance_cmd_vel', 10)
        self.error = self.create_publisher(Float64, '/dance_error', 10)
        self.path = self.create_publisher(NavPath, '/dance_path', LATCH)
        self.done = self.create_publisher(Bool, '/dance_done', 10)
        self.active = self.create_publisher(Bool, '/dance_active', LATCH)
        self.note = self.create_publisher(String, '/face_text', 10)
        self.create_subscription(Odometry, '/odom', self.on_odom, 10)
        self.create_subscription(Bool, '/dance_start', self.on_start, 10)
        self.create_subscription(Bool, '/edge_detected', self.on_edge, LATCH)
        self.create_timer(0.05, self.tick)

    def on_odom(self, msg):
        self.odom_at = time.monotonic()

    def finish(self):
        was_active = bool(self.points)
        self.points = []
        self.pub.publish(Twist())
        self.active.publish(Bool(data=False))
        if was_active:
            self.done.publish(Bool(data=True))

    def on_edge(self, msg):
        if msg.data and self.points:
            self.finish()

    def on_start(self, msg):
        if not msg.data:
            self.finish()
            return
        if time.monotonic()-self.odom_at > 0.7:
            self.finish()
            self.done.publish(Bool(data=True))
            return
        try:
            self.pose = pose_in_map(self.tf,self.get_clock().now())
        except TransformException:
            self.done.publish(Bool(data=True))
            return
        self.points, scale = fit_heart(self.pose)
        self.index, self.started = 1, time.monotonic()
        if not self.points:
            self.note.publish(string('这里太挤啦，换个空一点的位置再跳。'))
            self.finish()
            self.done.publish(Bool(data=True))
            return
        self.note.publish(string('开始心形舞，尺寸为原计划的 %.0f%%。' % (scale*100)))
        self.active.publish(Bool(data=True))
        path = NavPath()
        path.header.frame_id = 'map'
        path.header.stamp = self.get_clock().now().to_msg()
        for x, y in self.points:
            p = PoseStamped()
            p.header = path.header
            p.pose.position.x, p.pose.position.y, p.pose.orientation.w = x, y, 1.
            path.poses.append(p)
        self.path.publish(path)

    def tick(self):
        if not self.points:
            return
        if time.monotonic()-self.odom_at > 0.7 or time.monotonic()-self.started > 300:
            self.finish()
            return
        try:
            self.pose = pose_in_map(self.tf,self.get_clock().now())
        except TransformException:
            self.finish()
            return
        (v, w), error = chase(self.pose, self.points[self.index])
        self.error.publish(Float64(data=error))
        if error < 0.006:
            self.index += 1
            if self.index >= len(self.points):
                self.finish()
                return
        self.pub.publish(twist(v, w))


def run(cls):
    """统一管理退出，避免 Ctrl+C 后遗留播报子进程。"""
    rclpy.init()
    node = cls()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def voice_main():
    run(VoiceEmotion)


def face_main():
    run(FaceDisplay)


def tts_main():
    run(TTS)


def edge_main():
    run(EdgeGuard)


def range_main():
    run(RangeAdapter)


def mux_main():
    run(VelocityMux)


def behavior_main():
    run(BehaviorManager)


def dance_main():
    run(Dance)
