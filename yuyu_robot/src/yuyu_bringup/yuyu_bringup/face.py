"""Pillow 表情画布；图像坐标与 Gazebo 屏幕宽高一致。"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

EXPRESSIONS = ('happy', 'care', 'sleepy', 'curious', 'silent', 'dance')


def find_font(requested=''):
    candidates = [requested, '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
                  '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                  '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc']
    for path in candidates:
        if path and Path(path).is_file():
            return path
    raise FileNotFoundError('缺少中文字体，请安装 fonts-noto-cjk 或设置 font_path 参数')


def render(expression='happy', text='', font_path='', phase=0.0):
    expression = expression if expression in EXPRESSIONS else 'happy'
    bg = dict(happy='#087eb0', care='#8d79ab', sleepy='#4a505b',
              curious='#b28b08', silent='#101c40', dance='#342460')[expression]
    img = Image.new('RGB', (320, 192), bg)
    d = ImageDraw.Draw(img)
    white = '#e5fcff'
    if expression == 'dance':
        for x in range(320):
            hue = [(math.sin(x/44+phase+k*2.094)+1)*65 for k in range(3)]
            d.line((x, 0, x, 192), fill=tuple(int(v) for v in hue))
    # 有文字时把表情上移，预留三行中文区域。
    cy = 55 if text else 82
    for cx in (106, 214):
        if expression == 'happy':
            d.rounded_rectangle((cx-19, cy-21, cx+19, cy+17), 9, fill=white)
        elif expression == 'care':
            d.ellipse((cx-9, cy-8, cx+9, cy+10), fill=white)
            tilt = -1 if cx < 160 else 1
            d.line((cx-15, cy-22+tilt*5, cx+15, cy-22-tilt*5), fill=white, width=4)
        elif expression == 'sleepy':
            d.line((cx-20, cy, cx+20, cy), fill=white, width=5)
        elif expression in ('curious', 'silent'):
            d.rounded_rectangle((cx-19, cy-22, cx+19, cy+20), 16,
                                outline=white, width=4)
        else:
            points = []
            for i in range(10):
                a = i*math.pi/5-math.pi/2
                r = 24 if i % 2 == 0 else 10
                points.append((cx+r*math.cos(a), cy+r*math.sin(a)))
            d.polygon(points, fill=white)
            for a in (0, math.pi/2, math.pi, 3*math.pi/2):
                d.line((cx+30*math.cos(a), cy+30*math.sin(a),
                        cx+37*math.cos(a), cy+37*math.sin(a)), fill=white, width=3)
    if expression in ('happy', 'care', 'dance'):
        d.arc((140, cy+12, 180, cy+39), 0, 180, fill=white, width=4)
    elif expression == 'curious':
        d.ellipse((152, cy+27, 168, cy+43), outline=white, width=3)
    elif expression == 'sleepy':
        d.text((148, cy+16), 'Zz', fill=white,
               font=ImageFont.truetype(find_font(font_path), 22))
    if text:
        # 一行最多 15 字；超长消息完整轮播到下一页，由节点负责分页。
        lines = [text[i:i+15] for i in range(0, len(text), 15)][:3]
        font = ImageFont.truetype(find_font(font_path), 19)
        for i, line in enumerate(lines):
            box = d.textbbox((0, 0), line, font=font)
            d.text(((320-(box[2]-box[0]))/2, 115+i*24), line,
                   fill='white', font=font, stroke_width=0)
    return img
