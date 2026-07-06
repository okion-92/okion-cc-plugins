#!/usr/bin/env python3
# HAP 运维文档一键生成（确定性，跨机一致）。
# 用法: python gen_ops.py <std|pro|lite> [A|B] [outdir] [date]
#   std = 集群标准版(17节点)  pro = 集群专业版(29节点)  lite = 集群精简版(6节点,不分场景)
#   场景 A/B 仅 std/pro 需要(默认 A)；outdir 默认当前目录；date 默认 2026/06/23(交付日期,按需传)
# 前置: skill 根目录 `npm install docx`; `pip install pymupdf python-docx openpyxl`; 系统有微软雅黑/Consolas。
import os, sys, subprocess
_HERE = os.path.dirname(os.path.abspath(__file__))
_SK   = os.path.dirname(_HERE)
_WORK = os.path.join(_HERE, 'ops_src', '_work')
os.makedirs(_WORK, exist_ok=True)

ver = sys.argv[1].lower() if len(sys.argv) > 1 else 'std'
assert ver in ('std','pro','lite'), "version 必须是 std|pro|lite"
DEF_DATE = os.environ.get('COVER_DATE', '2026/06/23')
if ver == 'lite':
    scene=''; outdir = sys.argv[2] if len(sys.argv)>2 else '.'; date = sys.argv[3] if len(sys.argv)>3 else DEF_DATE
else:
    scene = (sys.argv[2].upper() if len(sys.argv)>2 else 'A')
    outdir = sys.argv[3] if len(sys.argv)>3 else '.'
    date = sys.argv[4] if len(sys.argv)>4 else DEF_DATE
    assert scene in ('A','B'), "scene 必须是 A|B"
os.makedirs(outdir, exist_ok=True)
PY = sys.executable

VLABEL={'std':'集群标准版','pro':'集群专业版','lite':'集群精简版'}[ver]
ENVER={'std':'Standard','pro':'Professional','lite':'Streamlined'}[ver]
key = 'lite' if ver=='lite' else ver+scene   # stdA/stdB/proA/proB/lite

# 1) 生成 markdown
env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8', HAP_DEPLOY_WORK=_WORK)
r = subprocess.run([PY, os.path.join(_HERE,'ops_build.py'), key], cwd=_HERE, env=env,
                   capture_output=True, text=True, encoding='utf-8')
if r.returncode != 0: sys.exit("ops_build.py 失败:\n"+(r.stderr or r.stdout))
md = r.stdout.strip().splitlines()[-1].strip()

# 2) 标题/文件名
if ver=='lite':
    title="运维文档（集群精简版）"; en="HAP Streamlined Cluster Operations and Maintenance"
    fname="HAP运维文档_集群精简版.docx"
else:
    sc_en = "Scenario %s"%scene
    title="运维文档（%s · 场景 %s）"%(VLABEL,scene)
    en="HAP %s Cluster Operations and Maintenance — %s"%(ENVER,sc_en)
    fname="HAP运维文档_%s_场景%s.docx"%(VLABEL,scene)

# 3) 渲染 + 封面
outdoc=os.path.join(outdir,fname)
renv=dict(os.environ, COVER_TITLE=title, COVER_EN=en, COVER_DATE=date)
r=subprocess.run(["node", os.path.join(_HERE,'render_deploy.js'), md, outdoc, title], cwd=_SK, env=renv)
if r.returncode!=0: sys.exit("render_deploy.js 失败（确认 skill 根目录已 npm install docx）")
subprocess.run([PY, os.path.join(_HERE,'inject_cover.py'), outdoc, title, en, date], env=env, check=True)
print("生成完成:", outdoc)
