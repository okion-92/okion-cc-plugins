#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HAP 交付文档 skill 环境自检。新机器拷过来后跑一次：
   py -3 doctor.py     （或 python doctor.py）
全部 [OK] 即可 python scripts/gen_from_input.py <入参.xlsx> <outdir>。"""
import os, sys, glob, subprocess, importlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # 避免 GBK 终端乱码
ROOT = os.path.dirname(os.path.abspath(__file__))
SC = os.path.join(ROOT, "scripts")
ok = lambda b: "[OK]" if b else "[缺]"
fail = []

print("HAP 交付文档 skill 环境自检")
print("skill 根:", ROOT)
print("-"*56)

# 1) Node
try:
    v = subprocess.run(["node","-v"], capture_output=True, text=True)
    node = v.returncode == 0
    print("%s Node.js        %s" % (ok(node), v.stdout.strip() if node else "未找到 node（装 Node.js）"))
except Exception:
    node=False; print("%s Node.js        未找到 node（装 Node.js）" % ok(False))
if not node: fail.append("Node.js")

# 2) docx 依赖
docxmod = os.path.isdir(os.path.join(ROOT,"node_modules","docx"))
print("%s node docx 包   %s" % (ok(docxmod), "node_modules/docx 在" if docxmod else "在 skill 根执行：npm install docx"))
if not docxmod: fail.append("npm install docx")

# 3) Python 包
for m,pip in [("fitz","pymupdf"),("docx","python-docx"),("openpyxl","openpyxl")]:
    try: importlib.import_module(m); print("%s py:%-9s 可导入" % (ok(True), m))
    except Exception: print("%s py:%-9s pip install %s" % (ok(False), m, pip)); fail.append("pip install "+pip)

# 4) 中文字体（Windows）
fonts = os.path.join(os.environ.get("WINDIR","C:\\Windows"),"Fonts")
ya = bool(glob.glob(os.path.join(fonts,"msyh*")))
co = bool(glob.glob(os.path.join(fonts,"consola*")))
print("%s 微软雅黑       %s" % (ok(ya), "msyh 在" if ya else "缺（docx/PNG 中文会回退字体）"))
print("%s Consolas       %s" % (ok(co), "consola 在" if co else "缺（代码块字体回退）"))
if not ya: fail.append("微软雅黑 msyh")

# 5) 关键脚本与基线
need = ["gen_from_input.py","make_input_template.py","gen_deploy.py","gen_ops.py","gen_mig.py",
        "gen_chk.py","gen_ref.py","gen_arch.py","gen_cred.py","render_deploy.js","inject_cover.py"]
miss = [n for n in need if not os.path.isfile(os.path.join(SC,n))]
print("%s 驱动/支撑脚本 %s" % (ok(not miss), "齐（%d 个）"%len(need) if not miss else "缺: "+", ".join(miss)))
if miss: fail.append("脚本缺失")
srcs = ["deploy_src/deploy_head.md","ops_src/ops_base.md","mig_src/mig_base.md",
        "chk_src/chk_base.md","ref_src/faq_body.md"]
msrc = [s for s in srcs if not os.path.isfile(os.path.join(SC,s))]
print("%s 固化基线源   %s" % (ok(not msrc), "齐" if not msrc else "缺: "+", ".join(msrc)))
if msrc: fail.append("基线缺失")

print("-"*56)
if fail:
    print("结果：未就绪，待解决 %d 项：" % len(fail))
    for f in fail: print("   - "+f)
    sys.exit(1)
print("结果：环境就绪 ✓  可执行")
print("   python scripts/make_input_template.py 入参模板.xlsx   # 生成入参模板")
print("   python scripts/gen_from_input.py 已填入参.xlsx 输出目录  # 一键出全套交付件")
