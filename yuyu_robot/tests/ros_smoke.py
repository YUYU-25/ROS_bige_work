#!/usr/bin/env python3
"""在已启动 demo_all 的 Humble 环境中验证真实节点与仿真通信。"""
import hashlib
import json
import math
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, LaserScan, Range
from std_msgs.msg import String
from gazebo_msgs.srv import GetEntityState


def main():
    rclpy.init()
    node = Node('yuyu_smoke_test')
    values = {}
    def save(name):
        return lambda msg: values.update({name: msg})
    node.create_subscription(Image,'/face_image',save('face'),2)
    node.create_subscription(LaserScan,'/scan',save('scan'),qos_profile_sensor_data)
    node.create_subscription(Image,'/camera/image_raw',save('camera'),qos_profile_sensor_data)
    node.create_subscription(Odometry,'/odom',save('odom'),10)
    node.create_subscription(String,'/safety_status',save('safety'),10)
    node.create_subscription(Twist,'/cmd_vel',save('velocity'),10)
    for name in ('front_left','front_right','rear_left','rear_right'):
        node.create_subscription(Range,'/cliff/'+name,save(name),qos_profile_sensor_data)
    face = node.create_publisher(String,'/face_expr',10)
    text = node.create_publisher(String,'/face_text',10)
    teleop = node.create_publisher(Twist,'/teleop_cmd_vel',10)
    command = node.create_publisher(String,'/command_text',10)
    ground_truth = node.create_client(GetEntityState,'/gazebo/get_entity_state')
    def pump(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            rclpy.spin_once(node,timeout_sec=.05)
    def real_pose():
        assert ground_truth.wait_for_service(timeout_sec=10)
        request=GetEntityState.Request();request.name='yuyu';request.reference_frame='world'
        future=ground_truth.call_async(request)
        while not future.done():
            rclpy.spin_once(node,timeout_sec=.1)
        assert future.result().success
        return future.result().state.pose
    try:
        for _ in range(60):
            pump(.5)
            if all(n in values for n in ('face','camera','scan','odom','safety','velocity')):
                break
        assert all(n in values for n in ('face','camera','scan','odom','safety','velocity')), list(values)
        safety=json.loads(values['safety'].data)
        assert safety['ready'] and not any(safety['edges'].values()),safety
        assert values['camera'].width==640 and values['camera'].height==480
        assert len(values['scan'].ranges)==360
        for name in ('front_left','front_right','rear_left','rear_right'):
            assert .025<values[name].range<.06,(name,values[name].range)
        hashes=[]
        for expr in ('happy','care','sleepy','curious','silent','dance'):
            face.publish(String(data=expr));pump(.4)
            img=values['face']
            assert (img.width,img.height,img.encoding)==(320,192,'rgb8')
            hashes.append(hashlib.sha256(bytes(img.data)).hexdigest())
        assert len(set(hashes))==6
        face.publish(String(data='happy'));pump(.3)
        original=bytes(values['face'].data)
        text.publish(String(data='你好呀，我是禹禹。'));pump(.4)
        assert bytes(values['face'].data)!=original
        pump(3.1)
        assert bytes(values['face'].data)==original
        p=values['odom'].pose.pose.position
        start=(p.x,p.y)
        start_stamp=values['odom'].header.stamp
        start_time=start_stamp.sec+start_stamp.nanosec*1e-9
        real_start=real_pose().position
        for _ in range(25):
            msg=Twist();msg.linear.x=.02
            teleop.publish(msg);pump(.1)
            output=values['velocity']
            assert abs(output.linear.x-output.angular.z*.06)<=.025001
            assert abs(output.linear.x+output.angular.z*.06)<=.025001
        pump(.8)
        assert abs(values['velocity'].linear.x)<1e-5
        p=values['odom'].pose.pose.position
        moved=math.hypot(p.x-start[0],p.y-start[1])
        assert moved>.01,('里程计没有前进',moved)
        assert p.x>start[0]+.005,('正向指令方向不对',start,(p.x,p.y))
        end_stamp=values['odom'].header.stamp
        sim_duration=end_stamp.sec+end_stamp.nanosec*1e-9-start_time
        assert moved<=.027*sim_duration+.004,(moved,sim_duration)
        actual=real_pose()
        real_moved=math.hypot(actual.position.x-real_start.x,actual.position.y-real_start.y)
        assert real_moved>.005,('Gazebo 刚体未实际移动',real_moved)
        assert actual.position.z>.72 and abs(actual.orientation.x)<.1 and abs(actual.orientation.y)<.1,actual
        command.publish(String(data='不想说'));pump(.5)
        publishers=node.get_publishers_info_by_topic('/cmd_vel')
        assert len(publishers)==1 and publishers[0].node_name=='velocity_mux',publishers
        print('PASS: 真实传感器、640×480 相机、六种脸、中文3秒清除、低速里程计与超时停车。')
        print('里程计 %.4f m，Gazebo 真值 %.4f m，仿真时长 %.2f s，/cmd_vel 发布者=%s' % (moved,real_moved,sim_duration,publishers[0].node_name))
    finally:
        teleop.publish(Twist())
        command.publish(String(data='停下'))
        pump(.2)
        node.destroy_node()
        rclpy.shutdown()


if __name__=='__main__':
    main()
