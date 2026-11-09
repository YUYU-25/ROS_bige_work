"""这些测试验证否定指令、防摔失效保护、双轮限速和轨迹几何。"""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src/yuyu_bringup'))
from yuyu_bringup.core import (CLIFF_NAMES, cliff_state, fit_heart, interpret,
                              point_clear, safe_velocity, wheel_limit)
from yuyu_bringup.face import EXPRESSIONS, find_font, render


class RobotTests(unittest.TestCase):
    def test_negative_command_and_quiet_priority(self):
        self.assertEqual(interpret('禹禹，别过来')[0], 'back')
        self.assertEqual(interpret('禹禹，过来')[0], 'come')
        self.assertEqual(interpret('今天不想说话，也别跳了'), ('stop','silent'))
        self.assertEqual(interpret('恢复说话'), (None,'none'))

    def test_wheel_speed_for_combined_motion(self):
        for v in [-1,-.02,0,.02,1]:
            for w in [-3,-.3,0,.3,3]:
                a,b = wheel_limit(v,w)
                self.assertLessEqual(abs((a-b*.06)/.025), 1+1e-12)
                self.assertLessEqual(abs((a+b*.06)/.025), 1+1e-12)

    def test_cliff_and_missing_sensor(self):
        data = {n:(.038,10.) for n in CLIFF_NAMES}
        ready, edges = cliff_state(data,10.1)
        self.assertTrue(ready)
        self.assertFalse(any(edges.values()))
        data['front_left']=(math.inf,10.)
        self.assertTrue(cliff_state(data,10.1)[1]['front_left'])
        self.assertFalse(cliff_state(data,11.)[0])
        del data['rear_left']
        self.assertFalse(cliff_state(data,10.1)[0])

    def test_no_forward_or_rotation_at_front_edge(self):
        status = {'ready':True,'edges':dict.fromkeys(CLIFF_NAMES,False),'pose':(0,0,0)}
        status['edges']['front_left']=True
        self.assertEqual(safe_velocity(.02,0,status,0), (0,0))
        self.assertEqual(safe_velocity(0,.2,status,0), (0,0))
        self.assertLess(safe_velocity(-.02,0,status,0)[0],0)
        self.assertEqual(safe_velocity(-.02,0,status,1), (0,0))
        self.assertEqual(safe_velocity(-.02,0,status,0,rear=.02),(0,0))

    def test_boundary_retreat_direction(self):
        s={'ready':True,'edges':dict.fromkeys(CLIFF_NAMES,False),'pose':(.38,0,0)}
        self.assertEqual(safe_velocity(.02,0,s,0),(0,0))
        self.assertLess(safe_velocity(-.02,0,s,0)[0],0)

    def test_invalid_numbers_never_reach_wheels(self):
        s={'ready':True,'edges':dict.fromkeys(CLIFF_NAMES,False),'pose':(0,0,0)}
        for v,w in [(math.nan,0),(0,math.inf)]:
            self.assertEqual(safe_velocity(v,w,s,0),(0,0))
        self.assertEqual(safe_velocity(.02,0,s,0,front=math.nan),(0,0))

    def test_fit_heart_and_reject_unsafe_location(self):
        points,scale=fit_heart((0,0,0))
        self.assertEqual(len(points),61)
        self.assertGreater(scale,0)
        self.assertEqual(points[0],points[-1])
        self.assertTrue(all(point_clear(*p) for p in points))
        self.assertEqual(fit_heart((.48,0,0))[0],[])

    def test_faces_have_distinct_rgb_images_with_chinese(self):
        font=find_font()
        images=[render(e,'你好呀，我是禹禹。',font) for e in EXPRESSIONS]
        self.assertEqual(len({i.tobytes() for i in images}),6)
        self.assertTrue(all(i.size==(320,192) and i.mode=='RGB' for i in images))


if __name__=='__main__':
    unittest.main(verbosity=2)
