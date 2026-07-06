#!/usr/bin/env python3
# HAP 部署实施文档一键生成（确定性，跨机一致）。
# 用法: python gen_deploy.py <pro|std|lite> [A|B] [outdir] [date]
#   pro = 集群专业版(29节点)  std = 集群标准版(17节点)  lite = 集群精简版(6节点,不分场景)
#   场景 A/B 仅 pro/std 需要(默认 B)；outdir 默认当前目录；date 默认 2026/06/22(交付日期,按需传)
# 前置: skill 根目录 `npm install docx`; `pip install openpyxl pymupdf python-docx`; 系统有微软雅黑/Consolas。
import os, sys, subprocess, shutil

_HERE = os.path.dirname(os.path.abspath(__file__))
_SK   = os.path.dirname(_HERE)
_WORK = os.path.join(_HERE, 'deploy_src', '_work')
os.makedirs(_WORK, exist_ok=True)

ver = sys.argv[1].lower() if len(sys.argv) > 1 else 'pro'
assert ver in ('pro','std','lite'), "version 必须是 pro|std|lite"
DEF_DATE = os.environ.get('COVER_DATE', '2026/06/22')
if ver == 'lite':                       # 精简版无场景: gen_deploy.py lite [outdir] [date]
    scene  = ''
    outdir = sys.argv[2] if len(sys.argv) > 2 else '.'
    date   = sys.argv[3] if len(sys.argv) > 3 else DEF_DATE
else:                                    # gen_deploy.py pro|std <A|B> [outdir] [date]
    scene  = (sys.argv[2].upper() if len(sys.argv) > 2 else 'B')
    outdir = sys.argv[3] if len(sys.argv) > 3 else '.'
    date   = sys.argv[4] if len(sys.argv) > 4 else DEF_DATE
    assert scene in ('A','B'), "scene 必须是 A|B"
os.makedirs(outdir, exist_ok=True)

PY = sys.executable
def run(cmd, **kw):
    env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8', HAP_DEPLOY_WORK=_WORK)
    r = subprocess.run(cmd, cwd=_HERE, env=env, **kw)
    if r.returncode != 0: sys.exit("命令失败: %r" % (cmd,))

# 1) MinIO/File 章（pro/std 用对象存储 .71-.74；std builder 再 remap 到 .51-.54）
if ver in ('pro','std'):
    mf = os.path.join(_WORK, 'minio_file_%s.md' % scene)
    run([PY, os.path.join(_HERE,'gen_minio_file.py'), scene,
         "192.168.1.71,192.168.1.72,192.168.1.73,192.168.1.74",
         "192.168.1.41,192.168.1.42,192.168.1.43", mf])

# 2) 组装 markdown
if ver == 'pro':
    run([PY, os.path.join(_HERE,'build_scene.py'), scene])
    md = os.path.join(_WORK, 'deploy_%s_v2.md' % scene)
    title = "部署实施文档（集群专业版 · 场景 %s）" % scene
    en = "HAP Professional Cluster Deployment Guide — Scenario %s (%s)" % (scene, "With Swarm" if scene=='B' else "Without Swarm")
    fname = "HAP部署实施文档_集群专业版_场景%s.docx" % scene
elif ver == 'std':
    run([PY, os.path.join(_HERE,'build_standard.py'), scene])
    md = os.path.join(_WORK, 'deploy_std_%s_v2.md' % scene)
    title = "部署实施文档（集群标准版 · 场景 %s）" % scene
    en = "HAP Standard Cluster Deployment Guide — Scenario %s (%s)" % (scene, "With Swarm" if scene=='B' else "Without Swarm")
    fname = "HAP部署实施文档_集群标准版_场景%s.docx" % scene
else:
    run([PY, os.path.join(_HERE,'build_streamlined.py')])
    md = os.path.join(_WORK, 'deploy_streamlined.md')
    title = "部署实施文档（集群精简版）"
    en = "HAP Streamlined Cluster Deployment Guide"
    fname = "HAP部署实施文档_集群精简版.docx"

# 3) 渲染 docx + 注入封面
outdoc = os.path.join(outdir, fname)
env = dict(os.environ, COVER_TITLE=title, COVER_EN=en, COVER_DATE=date)
r = subprocess.run(["node", os.path.join(_HERE,'render_deploy.js'), md, outdoc, title], cwd=_SK, env=env)
if r.returncode != 0: sys.exit("render_deploy.js 失败（确认 skill 根目录已 npm install docx）")
run([PY, os.path.join(_HERE,'inject_cover.py'), outdoc, title, en, date])
print("生成完成:", outdoc)
