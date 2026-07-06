#!/usr/bin/env python3
# HAP 数据迁移文档一键生成（确定性，跨机一致；不分场景）。
# 用法: python gen_mig.py <std|pro|lite> [outdir] [date]
import os, sys, subprocess
_HERE=os.path.dirname(os.path.abspath(__file__)); _SK=os.path.dirname(_HERE)
_WORK=os.path.join(_HERE,'mig_src','_work'); os.makedirs(_WORK,exist_ok=True)
ver=sys.argv[1].lower() if len(sys.argv)>1 else 'std'
assert ver in ('std','pro','lite'), "version 必须是 std|pro|lite"
outdir=sys.argv[2] if len(sys.argv)>2 else '.'
date=sys.argv[3] if len(sys.argv)>3 else os.environ.get('COVER_DATE','2026/06/23')
os.makedirs(outdir,exist_ok=True); PY=sys.executable
M={'std':('集群标准版','Standard'),'pro':('集群专业版','Professional'),'lite':('集群精简版','Streamlined')}
vlabel,en=M[ver]
env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',HAP_DEPLOY_WORK=_WORK)
r=subprocess.run([PY,os.path.join(_HERE,'mig_build.py'),ver],cwd=_HERE,env=env,capture_output=True,text=True,encoding='utf-8')
if r.returncode!=0: sys.exit("mig_build.py 失败:\n"+(r.stderr or r.stdout))
md=[l[4:] for l in r.stdout.splitlines() if l.startswith('OUT:')][-1]
title="数据迁移文档（单机迁移%s）"%vlabel
ensub="HAP Data Migration Guide (Standalone to %s Cluster)"%en
fname="HAP数据迁移文档_单机迁移%s.docx"%vlabel
outdoc=os.path.join(outdir,fname)
renv=dict(os.environ,COVER_TITLE=title,COVER_EN=ensub,COVER_DATE=date)
if subprocess.run(["node",os.path.join(_HERE,'render_deploy.js'),md,outdoc,title],cwd=_SK,env=renv).returncode!=0:
    sys.exit("render 失败（确认 skill 根目录已 npm install docx）")
subprocess.run([PY,os.path.join(_HERE,'inject_cover.py'),outdoc,title,ensub,date],env=env,check=True)
print("生成完成:",outdoc)
