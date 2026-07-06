#!/usr/bin/env python3
# HAP 常见故障处理 / 服务器资源要求 文档（docx，版本/场景无关，全集群通用）。
# 内容来自官方链接（FAQ 5 页 / 资源 4 页），格式同其他交付文档（render_deploy.js + 封面）。
# 用法: python gen_ref.py <faq|resource> [outdir] [date]
import os, sys, subprocess
_HERE=os.path.dirname(os.path.abspath(__file__)); _SK=os.path.dirname(_HERE); _SRC=os.path.join(_HERE,'ref_src')
kind=sys.argv[1].lower() if len(sys.argv)>1 else 'faq'
assert kind in ('faq','resource'), "类型必须是 faq|resource"
outdir=sys.argv[2] if len(sys.argv)>2 else '.'
date=sys.argv[3] if len(sys.argv)>3 else os.environ.get('COVER_DATE','2026/06/23')
os.makedirs(outdir,exist_ok=True)
M={'faq':('faq_body.md','常见故障处理','HAP Troubleshooting Guide','HAP常见故障处理.docx'),
   'resource':('resource_body.md','服务器资源要求','HAP Server Resource Requirements','HAP服务器资源要求.docx')}
body,title,en,fname=M[kind]
md=os.path.join(_SRC,body); outdoc=os.path.join(outdir,fname)
renv=dict(os.environ,COVER_TITLE=title,COVER_EN=en,COVER_DATE=date,PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
if subprocess.run(["node",os.path.join(_HERE,'render_deploy.js'),md,outdoc,title],cwd=_SK,env=renv).returncode!=0:
    sys.exit("render 失败（确认 skill 根目录已 npm install docx）")
subprocess.run([sys.executable,os.path.join(_HERE,'inject_cover.py'),outdoc,title,en,date],env=renv,check=True)
print("生成完成:",outdoc)
