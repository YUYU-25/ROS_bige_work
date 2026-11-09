#!/usr/bin/env python3
"""完整动作验收：回待命点、过来、跳完一圈心形；需已启动 demo_all。"""
import math
import json
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from std_msgs.msg import String, Float64
from nav_msgs.msg import Odometry, Path
from tf2_ros import Buffer, TransformListener
from rclpy.time import Time


def main():
    rclpy.init()
    node=Node('yuyu_behavior_test')
    tf=Buffer();listener=TransformListener(tf,node)
    values={};states=[];errors=[]
    latch=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL)
    def state(msg):
        values['state']=msg.data
        if not states or states[-1]!=msg.data:
            states.append(msg.data)
            print('STATE:',msg.data,flush=True)
    node.create_subscription(String,'/behavior_state',state,latch)
    node.create_subscription(Odometry,'/odom',lambda m:values.update(odom=m),10)
    node.create_subscription(Path,'/dance_path',lambda m:values.update(path=m),latch)
    node.create_subscription(String,'/safety_status',lambda m:values.update(safety=json.loads(m.data)),10)
    node.create_subscription(Float64,'/dance_error',lambda m:errors.append(m.data),10)
    pub=node.create_publisher(String,'/command_text',10)
    def pump(duration):
        until=time.monotonic()+duration
        while time.monotonic()<until:
            rclpy.spin_once(node,timeout_sec=.05)
    def command(text):
        pub.publish(String(data=text));pump(.4)
    def navigate(text,goal):
        states.clear();command(text)
        until=time.monotonic()+200
        while time.monotonic()<until:
            pump(.1)
            if 'NAVIGATING' in states and 'INTERACTING' in states:
                p=tf.lookup_transform('map','base_footprint',Time()).transform.translation
                assert math.hypot(p.x-goal[0],p.y-goal[1])<.05,(p,goal)
                print('PASS:',text,'position=',p.x,p.y,flush=True)
                return
            if 'NAVIGATING' in states and values.get('state')=='IDLE':
                raise AssertionError('导航失败或被取消：'+text)
        raise AssertionError('导航超时：'+text)
    try:
        ready_until=time.monotonic()+60
        while not values.get('safety',{}).get('ready',False) and time.monotonic()<ready_until:
            pump(.2)
        assert values.get('safety',{}).get('ready',False),'传感器或 map 位姿未就绪'
        pump(2);command('恢复说话')
        navigate('禹禹，回去',(-.18,.08))
        navigate('禹禹，过来',(0,0))
        states.clear();command('禹禹，跳个舞')
        until=time.monotonic()+305
        while time.monotonic()<until:
            pump(.1)
            if 'DANCING' in states and values.get('state')=='IDLE':
                assert errors and 'path' in values
                p=tf.lookup_transform('map','base_footprint',Time()).transform.translation
                start=values['path'].poses[0].pose.position
                error=math.hypot(p.x-start.x,p.y-start.y)
                assert error<.025,('心形未闭合',error)
                print('PASS: 完整心形舞，航点=%d，闭合误差=%.4f m' % (len(values['path'].poses),error),flush=True)
                break
        else:
            raise AssertionError('心形舞超时')
    finally:
        pub.publish(String(data='停下'));pump(.5)
        node.destroy_node();rclpy.shutdown()


if __name__=='__main__':
    main()
