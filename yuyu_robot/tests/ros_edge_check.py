#!/usr/bin/env python3
"""仅仿真验收：把机器人放到前桌沿，检查停车、后退与转向。

测试会改变 Gazebo 真值而不重置轮式里程计，完成后必须重启场景再做导航。
"""
import json
import math
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from std_msgs.msg import String, Bool
from geometry_msgs.msg import Twist
from gazebo_msgs.srv import SetEntityState, GetEntityState


def main():
    rclpy.init();n=Node('yuyu_edge_check')
    states=[];outputs=[];edges=[]
    latch=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL)
    n.create_subscription(String,'/behavior_state',lambda m:states.append(m.data),latch)
    n.create_subscription(Bool,'/edge_detected',lambda m:edges.append(m.data),latch)
    n.create_subscription(Twist,'/cmd_vel',lambda m:outputs.append((m.linear.x,m.angular.z)),10)
    pub=n.create_publisher(String,'/command_text',10)
    place=n.create_client(SetEntityState,'/gazebo/set_entity_state')
    inspect=n.create_client(GetEntityState,'/gazebo/get_entity_state')
    def pump(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            rclpy.spin_once(n,timeout_sec=.05)
    def call(client,request):
        assert client.wait_for_service(timeout_sec=10)
        f=client.call_async(request);deadline=time.monotonic()+10
        while not f.done() and time.monotonic()<deadline:
            rclpy.spin_once(n,timeout_sec=.05)
        assert f.done() and f.result().success
        return f.result()
    try:
        pump(2);pub.publish(String(data='停下'));pump(1)
        states.clear();edges.clear();outputs.clear()
        req=SetEntityState.Request();req.state.name='yuyu';req.state.reference_frame='world'
        req.state.pose.position.x=.455;req.state.pose.position.z=.751
        req.state.pose.orientation.w=1.
        call(place,req)
        deadline=time.monotonic()+40
        while time.monotonic()<deadline:
            pump(.1)
            if 'FLEEING' in states and states[-1]=='IDLE':
                break
        assert any(edges),'未检测到真实桌面落差'
        assert 'FLEEING' in states and states[-1]=='IDLE',states
        assert any(v<-.005 for v,w in outputs),'没有向安全方向后退'
        assert any(w>.1 for v,w in outputs),'没有在退回桌面后转向'
        req=GetEntityState.Request();req.name='yuyu';req.reference_frame='world'
        actual=call(inspect,req).state.pose
        assert actual.position.x<.43 and actual.position.z>.72,actual
        q=actual.orientation
        yaw=math.atan2(2*q.w*q.z,1-2*q.z*q.z)
        assert abs(yaw-math.pi/2)<.25,('转向角度异常',yaw)
        print('PASS: 真实前桌沿落差检测→后退→约90°转向→停车。')
        print('实际 x=%.4f m，yaw=%.1f°。测试后请重启场景。' % (actual.position.x,math.degrees(yaw)))
    finally:
        pub.publish(String(data='停下'));pump(.5)
        n.destroy_node();rclpy.shutdown()


if __name__=='__main__':
    main()
