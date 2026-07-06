import sys,re,zipfile,shutil,os
_HERE=os.path.dirname(os.path.abspath(__file__))
_ASSETS=os.path.normpath(os.path.join(_HERE,'..','assets'))
# 用法: inject_cover.py <docx> <标题(不带场景)> <英文(不带Scenario)> <日期> [keep_scene]
docx, title, en, date = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
keep_scene = len(sys.argv)>5 and sys.argv[5]=='keep'

# XML 转义注入文本，避免标题/副标题/日期中的 & < > 破坏 document.xml
def _xesc(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
title, en, date = _xesc(title), _xesc(en), _xesc(date)

SAMPLE=_ASSETS
cover=open(os.path.join(_ASSETS,'cover_block_template.xml'),encoding='utf-8').read()

if not keep_scene:
    # 仅替换标题文字(段[3])："部署实施文档（集群标准版 · 场景 A）" -> title
    cover=re.sub(r'(<w:t xml:space="preserve">)部署实施文档（[^<]*）(</w:t>)', r'\g<1>'+title+r'\g<2>', cover)
    # 英文副标题(段[4])：整段 HAP ... Scenario ... -> en
    cover=re.sub(r'(<w:t xml:space="preserve">)HAP[^<]*?(?:Scenario|Swarm)[^<]*(</w:t>)', r'\g<1>'+en+r'\g<2>', cover)
# 日期(段[9])
cover=re.sub(r'(<w:t xml:space="preserve">)2026/05/14(</w:t>)', r'\g<1>'+date+r'\g<2>', cover)

# 解包目标 docx
import tempfile; work=os.path.join(tempfile.gettempdir(),'_hap_inject_tmp')
if os.path.exists(work): shutil.rmtree(work)
os.makedirs(work)
with zipfile.ZipFile(docx) as z: z.extractall(work)

# document.xml: 用 cover 替换"占位段 + 紧随分页段"
docp=os.path.join(work,'word','document.xml')
doc=open(docp,encoding='utf-8').read()
pat=r'<w:p>(?:(?!</w:p>).)*__COVER_PLACEHOLDER__.*?</w:p>\s*<w:p>(?:(?!</w:p>).)*<w:br[^>]*w:type="page"[^>]*/>.*?</w:p>'
m=re.search(pat,doc,re.S)
if not m:
    pat=r'<w:p>(?:(?!</w:p>).)*__COVER_PLACEHOLDER__.*?</w:p>'
    m=re.search(pat,doc,re.S)
assert m,"未找到占位段"
doc=doc[:m.start()]+cover+doc[m.end():]
open(docp,'w',encoding='utf-8').write(doc)

# 页眉页脚: 直接用新附件原文件,仅替换其中文档名(去场景A)
for fn in ['header1.xml','footer1.xml']:
    tmpl={'header1.xml':'header_template.xml','footer1.xml':'footer_template.xml'}[fn]
    src=os.path.join(_ASSETS,tmpl)
    x=open(src,encoding='utf-8').read()
    if not keep_scene:
        x=re.sub(r'部署实施文档（[^<）]*）', title, x)
    open(os.path.join(work,'word',fn),'w',encoding='utf-8').write(x)

out=docx
if os.path.exists(out): os.remove(out)
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for root,_,files in os.walk(work):
        for f in files:
            fp=os.path.join(root,f); arc=os.path.relpath(fp,work)
            z.write(fp,arc)
print("封面整段照搬注入完成(keep_scene=%s):"%keep_scene,out)
