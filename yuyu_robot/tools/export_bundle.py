#!/usr/bin/env python3
"""打包源码，并按“结构树→完整代码→运行说明”生成阅读版。"""
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent


def included(p):
    rel = p.relative_to(ROOT)
    return (p.is_file() and not any(s in ('build','install','log','__pycache__') for s in rel.parts)
            and p.suffix != '.pyc' and not p.name.startswith('cloud-'))


def main():
    def order(p):
        rel=p.relative_to(ROOT)
        return ({'src':0,'tests':1,'tools':2}.get(rel.parts[0],3),str(rel))
    files = sorted((p for p in ROOT.rglob('*') if included(p)),key=order)
    archive = OUT/'yuyu_robot_humble.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p,'yuyu_robot/'+str(p.relative_to(ROOT)))
    reading = OUT/'yuyu_robot_complete_source.md'
    with reading.open('w',encoding='utf-8') as f:
        f.write('# 禹禹 Humble 项目：结构与完整代码\n\n')
        f.write('所有源文件均完整列出。二进制网格、地图和预览图随 ZIP 提供；'
                '模型/地图可通过 tools/generate_resources.py 重新生成。\n\n')
        f.write('## 1. 包结构树\n\n```text\n')
        tree={}
        for p in files:
            parts=p.relative_to(ROOT).parts;current=tree
            for part in parts[:-1]:
                current=current.setdefault(part,{})
            current[parts[-1]]=None
        def draw(branch,prefix=''):
            keys=sorted(branch,key=lambda name:(branch[name] is None,name))
            for index,name in enumerate(keys):
                last=index==len(keys)-1;folder=branch[name] is not None
                f.write(prefix+('└── ' if last else '├── ')+name+('/' if folder else '')+'\n')
                if folder:
                    draw(branch[name],prefix+('    ' if last else '│   '))
        f.write(ROOT.name+'/\n');draw(tree)
        f.write('```\n\n')
        f.write('## 2. 逐个文件完整代码\n\n')
        for p in files:
            if p.suffix in ('.stl','.pgm','.png'):
                f.write('### '+str(p.relative_to(ROOT))+'\n\n二进制资源，随 ZIP 提供。SHA-256: `'
                        +hashlib.sha256(p.read_bytes()).hexdigest()+'`\n\n')
                continue
            lang={'.py':'python','.xml':'xml','.xacro':'xml','.world':'xml',
                  '.yaml':'yaml','.rviz':'yaml','.sh':'bash','.md':'markdown'}.get(p.suffix,'text')
            # 文档中本身有代码块，外层用四个反引号保持完整。
            f.write('### '+str(p.relative_to(ROOT))+'\n\n````'+lang+'\n')
            f.write(p.read_text(encoding='utf-8').rstrip()+'\n````\n\n')
        f.write('## 3. 安装和运行步骤\n\n')
        instructions=(ROOT/'README.md').read_text(encoding='utf-8')
        for folder in ('docs','tools'):
            instructions=instructions.replace(']('+folder+'/',']('+ROOT.name+'/'+folder+'/')
        f.write(instructions)
    print(archive, archive.stat().st_size)
    print(reading, reading.stat().st_size)


if __name__=='__main__':
    main()
