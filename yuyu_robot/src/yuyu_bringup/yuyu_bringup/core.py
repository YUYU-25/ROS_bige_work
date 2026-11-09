"""不依赖 ROS 的规则、几何与防护逻辑，便于独立验证。"""
import math

CLIFF_NAMES = ('front_left', 'front_right', 'rear_left', 'rear_right')


def interpret(text):
    """先判断否定指令，避免把“别过来”识别成“过来”。"""
    command = None
    if any(s in text for s in ('别过来', '后退')):
        command = 'back'
    elif any(s in text for s in ('停止', '停下')):
        command = 'stop'
    elif any(s in text for s in ('回去', '待命')):
        command = 'return'
    elif '跳' in text:
        command = 'dance'
    elif '过来' in text:
        command = 'come'
    emotion = None
    if any(s in text for s in ('不想说', '安静', '嘘')):
        emotion = 'silent'
        command = 'stop'
    elif any(s in text for s in ('恢复说话', '可以说话')):
        emotion = 'none'
    elif any(s in text for s in ('烦', '难过')):
        emotion = 'annoyed'
    elif '累' in text:
        emotion = 'tired'
    elif any(s in text for s in ('开心', '高兴')):
        emotion = 'happy'
    return command, emotion


def wrap_angle(a):
    return math.atan2(math.sin(a), math.cos(a))


def wheel_limit(v, w, radius=0.025, separation=0.12, max_rad_s=1.0):
    """等比限幅，直行与转弯组合时也不突破任一轮子的转速。"""
    peak = max(abs(v - w * separation / 2), abs(v + w * separation / 2))
    factor = min(1.0, radius * max_rad_s / peak) if peak else 1.0
    return v * factor, w * factor


def cliff_state(samples, now, timeout=0.7, drop_distance=0.075):
    ready = all(name in samples and now - samples[name][1] <= timeout
                for name in CLIFF_NAMES)
    edges = {}
    for name in CLIFF_NAMES:
        value = samples.get(name, (math.inf, 0.0))[0]
        edges[name] = not math.isfinite(value) or value > drop_distance or value < 0.005
    return ready, edges


def safe_velocity(v, w, status, age, front=math.inf, rear=math.inf):
    """所有速度源经过同一出口；数据失效、禁行方向或越界时输出零。"""
    if (not math.isfinite(v) or not math.isfinite(w) or math.isnan(front)
            or math.isnan(rear) or age > 0.7 or not status.get('ready', False)):
        return 0.0, 0.0
    edges = status['edges']
    front_edge = edges['front_left'] or edges['front_right']
    rear_edge = edges['rear_left'] or edges['rear_right']
    if v > 0 and (front_edge or front < 0.045):
        return 0.0, 0.0
    if v < 0 and (rear_edge or rear < 0.045):
        return 0.0, 0.0
    if abs(w) > 0.01 and (front_edge or rear_edge):
        return 0.0, 0.0
    # 桌面已知边界作为第二层保护；越界后仅允许向内移动。
    x, y, yaw = status.get('pose', (0.0, 0.0, 0.0))
    dx, dy = v * math.cos(yaw), v * math.sin(yaw)
    if (x > 0.375 and dx > 0) or (x < -0.375 and dx < 0):
        return 0.0, 0.0
    if (y > 0.175 and dy > 0) or (y < -0.175 and dy < 0):
        return 0.0, 0.0
    # 已知物品也保护键盘/行为；若已经过近，仍可向增加间距的方向退开。
    clearance = map_clearance(x, y)
    next_clearance = map_clearance(x+dx*0.3, y+dy*0.3)
    if next_clearance < 0 and next_clearance < clearance-1e-8:
        return 0.0, 0.0
    return wheel_limit(v, w)


def map_clearance(x, y, margin=0.115):
    """按包含耳机的包络圆检查桌沿和三个桌上物品。"""
    # 笔盒矩形与包络圆的最近距离。
    px = max(abs(x + 0.2) - 0.075, 0)
    py = max(abs(y + 0.15) - 0.025, 0)
    return min(0.5-abs(x)-margin, 0.3-abs(y)-margin,
               math.hypot(x-.2,y-.1)-.04-margin,
               math.hypot(px,py)-margin,
               math.hypot(x-.35,y+.2)-.045-margin)


def point_clear(x, y, margin=0.115):
    return map_clearance(x, y, margin) > 0


def heart_path(width=0.4, height=0.3, count=60):
    pts = []
    for i in range(count):
        t = 2 * math.pi * i / count
        pts.append((16 * math.sin(t)**3,
                    13 * math.cos(t) - 5 * math.cos(2*t)
                    - 2 * math.cos(3*t) - math.cos(4*t)))
    xmin, xmax = min(p[0] for p in pts), max(p[0] for p in pts)
    ymin, ymax = min(p[1] for p in pts), max(p[1] for p in pts)
    return [((x-(xmin+xmax)/2)*width/(xmax-xmin),
             (y-(ymin+ymax)/2)*height/(ymax-ymin)) for x, y in pts]


def fit_heart(pose, width=0.4, height=0.3):
    """从当前位置开始闭合心形；逐级缩小，放不下则拒绝启动。"""
    x, y, yaw = pose
    for scale in (1.0, 0.75, 0.5, 0.35):
        raw = heart_path(width*scale, height*scale)
        start = raw[0]
        for angle in (yaw, yaw+math.pi/2, yaw+math.pi, yaw-math.pi/2):
            points = []
            for px, py in raw + raw[:1]:
                a, b = px-start[0], py-start[1]
                points.append((x+a*math.cos(angle)-b*math.sin(angle),
                               y+a*math.sin(angle)+b*math.cos(angle)))
            # 采样每条线段，防止航点安全但连线穿过障碍物。
            if all(point_clear(a[0]+(b[0]-a[0])*t/5,
                               a[1]+(b[1]-a[1])*t/5)
                   for a, b in zip(points, points[1:]) for t in range(6)):
                return points, scale
    return [], 0.0


def chase(pose, goal, speed=0.02):
    x, y, yaw = pose
    distance = math.hypot(goal[0]-x, goal[1]-y)
    error = wrap_angle(math.atan2(goal[1]-y, goal[0]-x)-yaw)
    w = max(-0.30, min(0.30, 1.3*error))
    v = min(speed, 0.8*distance) if abs(error) < 0.35 else 0.0
    return wheel_limit(v, w), distance
