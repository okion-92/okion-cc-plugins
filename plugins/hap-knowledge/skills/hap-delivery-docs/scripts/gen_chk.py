#!/usr/bin/env python3
# HAP 交付清单一键生成（确定性，跨机一致）。客户名为占位「某示例客户」，交付时改。
# 用法: python gen_chk.py <std|pro|lite> [A|B] [outdir] [date]
import os, sys, subprocess
_HERE=os.path.dirname(os.path.abspath(__file__)); _SK=os.path.dirname(_HERE)
_WORK=os.path.join(_HERE,'chk_src','_work'); os.makedirs(_WORK,exist_ok=True)
ver=sys.argv[1].lower() if len(sys.argv)>1 else 'std'
assert ver in ('std','pro','lite'), "version 必须是 std|pro|lite"
DEF_DATE=os.environ.get('COVER_DATE','2026/06/23')
if ver=='lite':
    scene=''; outdir=sys.argv[2] if len(sys.argv)>2 else '.'; date=sys.argv[3] if len(sys.argv)>3 else DEF_DATE
else:
    scene=(sys.argv[2].upper() if len(sys.argv)>2 else 'A'); outdir=sys.argv[3] if len(sys.argv)>3 else '.'
    date=sys.argv[4] if len(sys.argv)>4 else DEF_DATE
    assert scene in ('A','B'), "scene 必须是 A|B"
os.makedirs(outdir,exist_ok=True); PY=sys.executable
key='lite' if ver=='lite' else ver+scene   # stdA/stdB/proA/proB/lite
M={'std':('集群标准版','Standard'),'pro':('集群专业版','Professional'),'lite':('集群精简版','Streamlined')}
vlabel,en=M[ver]
env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',HAP_DEPLOY_WORK=_WORK)
r=subprocess.run([PY,os.path.join(_HERE,'chk_build.py'),key],cwd=_HERE,env=env,capture_output=True,text=True,encoding='utf-8')
if r.returncode!=0: sys.exit("chk_build.py 失败:\n"+(r.stderr or r.stdout))
md=[l[4:] for l in r.stdout.splitlines() if l.startswith('OUT:')][-1]
if ver=='lite':
    title="交付清单（集群精简版）"; ensub="HAP Delivery Checklist (Streamlined Cluster)"; fname="HAP交付清单_集群精简版.docx"
else:
    title="交付清单（%s · 场景 %s）"%(vlabel,scene)
    ensub="HAP Delivery Checklist (%s Cluster · Scenario %s)"%(en,scene)
    fname="HAP交付清单_%s_场景%s.docx"%(vlabel,scene)
outdoc=os.path.join(outdir,fname)
renv=dict(os.environ,COVER_TITLE=title,COVER_EN=ensub,COVER_DATE=date)
if subprocess.run(["node",os.path.join(_HERE,'render_deploy.js'),md,outdoc,title],cwd=_SK,env=renv).returncode!=0:
    sys.exit("render 失败（确认 skill 根目录已 npm install docx）")
subprocess.run([PY,os.path.join(_HERE,'inject_cover.py'),outdoc,title,ensub,date],env=env,check=True)
print("生成完成:",outdoc)
