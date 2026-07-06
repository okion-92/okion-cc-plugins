# 参数化生成 HAP 架构图(树形图：请求主干 → K8s 枢纽(ns default/flink) → 扇出各后端 + Flink 数据集成流)。
# 用法: build_arch2.py <std|pro|lite> [A|B] <outdir>
import sys, fitz, os
ver=sys.argv[1]; scene=(sys.argv[2] if len(sys.argv)>2 and sys.argv[2] in ('A','B') else '')
outdir=sys.argv[-1] if len(sys.argv)>2 else '.'
if ver=='lite': scene=''
FONT="'Microsoft YaHei','PingFang SC',sans-serif"
C={'grey':('#F1EFE8','#5F5E5A','#2C2C2A'),'green':('#E1F5EE','#0F6E56','#085041'),
   'blue':('#E6F1FB','#185FA5','#0C447C'),'purple':('#EEEDFE','#534AB7','#3C3489'),
   'tan':('#FAEEDA','#854F0B','#633806'),'red':('#FAECE7','#993C1D','#712B13'),
   'pink':('#FBE7EE','#A11D58','#791541')}
def IPS(s, base='192.168.1'):   # ".31/.32/.33" -> 完整 IP 列表(便于按入参逐一替换)
    return [(base+x.strip() if x.strip().startswith('.') else x.strip()) for x in s.split('/')]

def spec_std(scene):
    sw = '同一 Swarm（Node01 编排·2377）' if scene=='B' else '独立 docker（单节点 swarm）'
    trunk=[('grey','外部用户 / 终端',['浏览器 / 移动端','https://hap.domain.com']),
           ('grey','上游 LB / 网关 · 192.168.1.10',['监听 80 / 443 · HTTPS 终止']),
           ('green','负载 · Nginx 双节点高可用',['VIP 192.168.1.20 · Keepalived VRRP · 80','Nginx01 192.168.1.11 · MASTER','Nginx02 192.168.1.12 · BACKUP'])]
    khub=('Kubernetes 集群 · 3 Master',
          ['K8s Master+Node · 192.168.1.21 · 192.168.1.22 · 192.168.1.23 · Istio 1.29.1','微服务 www · 8880（多副本）'],
          ['Flink 专属节点 · 192.168.1.61 · 192.168.1.62','JobManager UI 28081 / TaskManager'])
    leaves=[('tan','MySQL MGR',['MGR · 3306 / Router 6446','与 MongoDB 共置']+IPS('.31/.32/.33')),
            ('tan','MongoDB 副本集',['Primary/Sec · 27017','与 MySQL 共置']+IPS('.31/.32/.33')),
            ('red','Redis 哨兵',['6379 / Sentinel 26379']+IPS('.41/.42/.43')),
            ('pink','Kafka',['9092 / ZK 2181']+IPS('.52/.53/.54')),
            ('pink','Elasticsearch',['9200 / 9300']+IPS('.52/.53/.54')),
            ('pink','MinIO + File',['MinIO 9011-9014 / File 9001-9004',sw]+IPS('.51/.52/.53/.54'))]
    return '集群标准版部署架构','17 节点 · 部分共置',trunk,khub,leaves

def spec_pro(scene):
    sw = '同一 Swarm（Node01·2377）' if scene=='B' else '独立 docker（单节点 swarm）'
    trunk=[('grey','外部用户 / 终端',['浏览器 / 移动端','https://hap.domain.com']),
           ('grey','上游 LB / 网关 · 192.168.1.10',['监听 80 / 443 · HTTPS 终止']),
           ('green','负载 · Nginx 双节点高可用',['VIP 192.168.1.20 · Keepalived VRRP · 80','Nginx01 192.168.1.11 · Nginx02 192.168.1.12'])]
    khub=('Kubernetes 集群 · 3 Master + 2 Worker',
          ['K8s Master · 192.168.1.21 · 192.168.1.22 · 192.168.1.23 · Istio','K8s Worker · 192.168.1.24 · 192.168.1.25 · 微服务 www 8880'],
          ['Flink 独立节点 · 192.168.1.81 · 192.168.1.82 · 192.168.1.83','JobManager UI 28081 / TaskManager'])
    leaves=[('tan','MySQL MGR',['独立 · 3306 / Router 6446']+IPS('.31/.32/.33')),
            ('tan','MongoDB 副本集',['独立 · 27017']+IPS('.34/.35/.36')),
            ('red','Redis 哨兵',['6379 / Sentinel 26379']+IPS('.41/.42/.43')),
            ('pink','Kafka',['9092 / ZK 2181']+IPS('.51/.52/.53')),
            ('pink','Elasticsearch',['9200 / 9300']+IPS('.61/.62/.63')),
            ('pink','MinIO + File',['MinIO 9011-9014 / File 9001-9004',sw]+IPS('.71/.72/.73/.74'))]
    return '集群专业版部署架构','29 节点 · 各组件独立部署',trunk,khub,leaves

def spec_lite():
    trunk=[('grey','外部用户 / 终端',['浏览器 / 移动端','https://hap.domain.com']),
           ('green','负载 · Nginx 单节点（无 VIP）',['192.168.1.20 · 监听 80 · upstream→K8s 8880'])]
    khub=('Kubernetes 集群 · 1 主 1 从',
          ['K8s Master 192.168.1.21（已移除污点） · Worker 192.168.1.22 · Istio','微服务 www · 8880'],
          ['Flink · 192.168.1.30','JobManager + TaskManager'])
    leaves=[('tan','MySQL',['3306（直连）']+IPS('.31')),
            ('tan','MongoDB',['27017（无副本集）']+IPS('.31')),
            ('red','Redis',['6379（无哨兵）']+IPS('.31')),
            ('pink','Kafka',['9092 / ZK 2181']+IPS('.51')),
            ('pink','Elasticsearch',['9200']+IPS('.51')),
            ('pink','MinIO + File',['MinIO 9011 / File 9000']+IPS('.51'))]
    return '集群精简版部署架构','6 节点 · 单节点共置',trunk,khub,leaves

if ver=='std': title,sub,trunk,khub,leaves=spec_std(scene)
elif ver=='pro': title,sub,trunk,khub,leaves=spec_pro(scene)
else: title,sub,trunk,khub,leaves=spec_lite()
if scene: sub=sub+' · 场景 '+scene+('（开启 Swarm）' if scene=='B' else '（未开启 Swarm）')

# ---- 画布与基础绘制 ----
W=1040
svg=['<svg xmlns="http://www.w3.org/2000/svg" font-family="%s" width="%d" height="{H}" viewBox="0 0 %d {H}">'%(FONT,W,W)]
svg.append('<defs>'
  '<marker id="af" markerWidth="11" markerHeight="11" refX="6" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#5F5E5A"/></marker>'
  '<marker id="afc" markerWidth="11" markerHeight="11" refX="6" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#534AB7"/></marker>'
  '<marker id="afw" markerWidth="11" markerHeight="11" refX="6" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#C2410C"/></marker>'
  '</defs>')
def esc(t): return t.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def T(x,y,t,sz,col,anchor='middle',w='normal'):
    svg.append('<text x="%g" y="%g" font-size="%g" fill="%s" text-anchor="%s" font-weight="%s">%s</text>'%(x,y,sz,col,anchor,w,esc(t)))
def R(x,y,w,h,fill,stroke,rx=8,sw=1.3):
    svg.append('<rect x="%g" y="%g" width="%g" height="%g" rx="%g" fill="%s" stroke="%s" stroke-width="%g"/>'%(x,y,w,h,rx,fill,stroke,sw))
def LINE(x1,y1,x2,y2,color,mk='af',wid=2):
    svg.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="%g" marker-end="url(#%s)"/>'%(x1,y1,x2,y2,color,wid,mk))
def POLY(pts,color,mk,wid=2.2):
    d=' '.join('%g,%g'%(x,y) for x,y in pts)
    svg.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%g" marker-end="url(#%s)"/>'%(d,color,wid,mk))
def PILL(cx,cy,t,col='#5F5E5A'):
    w=len(t)*6.6+16; R(cx-w/2,cy-9,w,18,'#ffffff','#C9C7BF',9,1); T(cx,cy+3.5,t,9,col,'middle','bold')
def box(x,y,w,title,subs,ckey,tsz=11.5):
    bg,bd,tc=C[ckey]; h=24+len(subs)*13+8
    R(x,y,w,h,'#ffffff',bd,7,1.4); T(x+w/2,y+17,title,tsz,'#1f1f1f','middle','bold')
    yy=y+33
    for s in subs: T(x+w/2,yy,s,9,'#444441','middle'); yy+=13
    return h

cx=W/2; y=24
T(cx,y+16,'HAP '+title,22,'#1f1f1f','middle','bold'); y+=30
T(cx,y+14,sub,13,'#5F5E5A','middle'); y+=28

# ---- 1) 请求主干(树根→K8s) ----
TW=360; FLOW=['HTTPS 接入 · 80/443','转发 HTTP · 80','upstream → 微服务 www · 8880']
prevb=None
fi=0
for (ck,tt,subs) in trunk:
    h=box(cx-TW/2,y,TW,tt,subs,ck)
    if prevb is not None:
        LINE(cx,prevb,cx,y-1,'#5F5E5A'); PILL(cx,(prevb+y)/2,FLOW[min(fi,len(FLOW)-1)]); fi+=1
    prevb=y+h; y=y+h+34
# K8s 枢纽(同一集群两个 namespace)
ht,dft,flk=khub
KW=620; bgB=C['blue'][0]; bgP=C['purple'][0]
hp=24+8 + (24+len(dft)*13+6) + (24+len(flk)*13+6) + 6
R(cx-KW/2,y,KW,hp,'#FBFCFE',C['blue'][1],9,1.6)
T(cx,y+18,ht,13,C['blue'][2],'middle','bold')
py=y+26
# ns default 子带
dh=22+len(dft)*13+6; R(cx-KW/2+10,py,KW-20,dh,bgB,C['blue'][1],6,1)
T(cx-KW/2+22,py+15,'namespace: default · 微服务',9.5,C['blue'][2],'start','bold')
yy=py+30
for s in dft: T(cx,yy,s,9,'#33414f','middle'); yy+=13
py+=dh+6
# ns flink 子带
fh=22+len(flk)*13+6; R(cx-KW/2+10,py,KW-20,fh,bgP,C['purple'][1],6,1)
T(cx-KW/2+22,py+15,'namespace: flink · 数据集成',9.5,C['purple'][2],'start','bold')
yy=py+30
for s in flk: T(cx,yy,s,9,'#3b3560','middle'); yy+=13
flink_panel_bottom=py+fh; flink_panel_cx=cx
LINE(cx,prevb,cx,y-1,'#5F5E5A'); PILL(cx,(prevb+y)/2,FLOW[min(fi,len(FLOW)-1)])
hub_bottom=y+hp; y=hub_bottom

# ---- 2) 扇出：微服务(ns default) → 各后端叶子 ----
MGN=22; n=len(leaves); gap=12
lw=(W-2*MGN-(n-1)*gap)/n
bus_y=y+26; leaf_y=bus_y+26
lcx=[MGN+lw/2+i*(lw+gap) for i in range(n)]
LINE(cx,hub_bottom+1,cx,bus_y,'#185FA5')          # 枢纽 → 总线
svg.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#185FA5" stroke-width="2"/>'%(lcx[0],bus_y,lcx[-1],bus_y))
PILL(cx,(hub_bottom+bus_y)/2,'微服务调用 · ns:default 读写各后端','#0C447C')
leafh=0
for i,(ck,tt,subs) in enumerate(leaves):
    LINE(lcx[i],bus_y,lcx[i],leaf_y-1,'#185FA5')
    h=box(lcx[i]-lw/2,leaf_y,lw,tt,subs,ck,11)
    leafh=max(leafh,h)
y=leaf_y+leafh+40

# ---- 3) Flink 数据集成流(独立条带：Kafka → Flink → MinIO) ----
T(cx,y,'数据集成流 · namespace: flink（Flink 在同一 K8s 集群内运行）',11,C['purple'][2],'middle','bold'); y+=14
sbw=250; sgap=120; total=3*sbw+2*sgap; sx=(W-total)/2
ky=y+8
h1=box(sx,ky,sbw,'Kafka',['消息队列 · 9092','业务事件 / 数据变更'],'pink',11)
h2=box(sx+sbw+sgap,ky,sbw,'Flink（ns:flink）',['JobManager / TaskManager','实时聚合 / 数据集成'],'purple',11)
h3=box(sx+2*(sbw+sgap),ky,sbw,'MinIO 对象存储',['s3 endpoint · 9011','聚合结果落地'],'pink',11)
my=ky+max(h1,h2,h3)/2
LINE(sx+sbw+2,my,sx+sbw+sgap-2,my,'#534AB7','afc',2.4)      # Kafka →消费→ Flink
T((sx+sbw)+sgap/2,my-8,'① 消费 Kafka',9.5,C['purple'][2],'middle','bold')
LINE(sx+2*sbw+sgap+2,my,sx+2*sbw+2*sgap-2,my,'#C2410C','afw',2.4)  # Flink →写入→ MinIO
T(sx+2*sbw+sgap+sgap/2,my-8,'② 写入 MinIO（s3）',9.5,'#C2410C','middle','bold')
y=ky+max(h1,h2,h3)+30

# ---- 图例 ----
legt = '说明：灰/绿/蓝主干 = 用户请求路径（HTTPS→Nginx→K8s 微服务 www 8880）；蓝色扇出 = 微服务(ns:default)读写各后端；紫/橙 = Flink(ns:flink)消费 Kafka、写入 MinIO。'
R(MGN,y,W-2*MGN,46,'#F1EFE8','#C9C7BF',8,1)
T(MGN+12,y+18,legt,9.3,'#5F5E5A','start')
snote = ('场景 %s：'%scene)+('对象存储 4 节点同一 Swarm，Node01 统一编排，放通 2377/4789/7946。' if scene=='B' else '对象存储 4 节点各自独立单节点 Swarm，无需放通 2377。') if scene else '单节点架构，无副本集 / 哨兵 / MGR 冗余。'
T(MGN+12,y+36,snote,9.3,'#5F5E5A','start')
y+=46+18

svg.append('</svg>')
out='\n'.join(svg).replace('{H}',str(int(y)))
base='HAP集群%s版%s_架构图'%({'std':'标准','pro':'专业','lite':'精简'}[ver], ('_场景'+scene) if scene else '')
os.makedirs(outdir,exist_ok=True)
svgp=os.path.join(outdir,base+'.svg'); pngp=os.path.join(outdir,base+'.png')
open(svgp,'w',encoding='utf-8').write(out)
doc=fitz.open(svgp); pix=doc[0].get_pixmap(matrix=fitz.Matrix(2,2)); pix.save(pngp)
print('生成:',base,'| 叶子',len(leaves),'| H',int(y))
