#!/usr/bin/env python3
"""检查命令方向、真实轮速及里程计反馈，避免只看到图像以为移动正常。"""
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState

rclpy.init()
n=Node('yuyu_motion_check')
data={}
n.create_subscription(Odometry,'/odom',lambda m:data.update(odom=m),10)
n.create_subscription(Twist,'/cmd_vel',lambda m:data.update(cmd=m),10)
n.create_subscription(JointState,'/joint_states',lambda m:data.update(joints=m),10)
p=n.create_publisher(Twist,'/teleop_cmd_vel',10)
ready_until=time.monotonic()+45
while not all(k in data for k in ('odom','cmd','joints')) and time.monotonic()<ready_until:
 rclpy.spin_once(n,timeout_sec=.1)
assert 'odom' in data,'控制器或里程计尚未就绪'
start=time.monotonic();next_pub=start;next_print=start;samples=[]
try:
 while time.monotonic()-start<10:
  now=time.monotonic()
  if now>=next_pub:
   m=Twist();m.linear.x=.01 if 1<now-start<3 else 0.
   m.angular.z=.30 if 4<now-start<7 else 0.
   p.publish(m);next_pub=now+.1
  rclpy.spin_once(n,timeout_sec=.02)
  if now>=next_print and 'odom' in data and 'joints' in data and 'cmd' in data:
   o=data['odom'];c=data['cmd'];j=data['joints']
   samples.append((c.linear.x,c.angular.z,o.twist.twist.linear.x,o.twist.twist.angular.z,list(j.velocity)))
   print('wall=%.1f sim=%d x=%.4f vx=%.4f wz=%.3f cmd=(%.3f,%.3f) wheels=%s' % (now-start,o.header.stamp.sec,o.pose.pose.position.x,o.twist.twist.linear.x,o.twist.twist.angular.z,c.linear.x,c.angular.z,j.velocity),flush=True)
   next_print=now+.5
 assert any(v>.005 and actual>.005 for v,w,actual,aw,j in samples),samples
 assert any(w>.2 and aw>.2 for v,w,actual,aw,j in samples),samples
 assert all(max(abs(s) for s in j)<1.1 for v,w,actual,aw,j in samples),samples
 print('PASS: 正向移动、转向反馈和轮速上限。',flush=True)
finally:
 p.publish(Twist());n.destroy_node();rclpy.shutdown()
