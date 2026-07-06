import os
_HERE=os.path.dirname(os.path.abspath(__file__))
_SRC=os.path.join(_HERE,'deploy_src')
_OUT=os.environ.get('HAP_DEPLOY_WORK', os.path.join(_SRC,'_work'))
os.makedirs(_OUT, exist_ok=True)
# 用法: build_scene.py <A|B>  -> 生成 deploy_<scene>_v2.md (专业版, 每组件H1结构)
import re, sys
scene = sys.argv[1].upper()
SUF = {"B":"，场景 B Swarm","A":"，场景 A 独立单节点 Swarm"}[scene]

head = open(os.path.join(_SRC,'deploy_head.md'),encoding='utf-8').read()
tail = open(os.path.join(_SRC,'deploy_tail.md'),encoding='utf-8').read()
mf   = open(os.path.join(_OUT,'minio_file_%s.md'%scene),encoding='utf-8').read()

# --- head 按场景调整(文档说明首段 + 1.2 网络要求) ---
head = head.replace(
 "网络形态为 **场景 B（VXLAN 正常开启，对象存储 4 节点组成同一 Docker Swarm 集群）**。",
 "网络形态为 **场景 %s（%s）**。"%(scene,
   "VXLAN 正常开启，对象存储 4 节点组成同一 Docker Swarm 集群" if scene=="B"
   else "VXLAN 未开启，对象存储 4 节点各自运行独立的单节点 Docker Swarm，不组集群"))
head = head.replace(
 "- 所有节点内网二层互通；对象存储 4 节点（192.168.1.71-74）之间需放通 Swarm 端口 **TCP 2377、UDP/TCP 4789、TCP 7946**（场景 B）。",
 "- 所有节点内网二层互通；对象存储 4 节点（192.168.1.71-74）之间需放通 Swarm 端口 **TCP 2377、UDP/TCP 4789、TCP 7946**（场景 B）。" if scene=="B"
 else "- 所有节点内网二层互通；对象存储 4 节点（192.168.1.71-74）各自运行独立单节点 Swarm，**无需放通 2377/4789/7946**（场景 A 不组 Swarm 集群）。")

# --- sec6: gen_minio_file 输出(# 九/十) -> 六 wrapper + 6.1/6.2 ---
mf = mf.replace("# 九、中间件部署 — MinIO 集群（中间件节点 01/02/03/04）",
  "# 六、对象存储与文件服务\n\n## 6.1 MinIO 集群（对象存储节点 192.168.1.71 / .72 / .73 / .74%s）"%SUF)
mf = mf.replace("# 十、中间件部署 — HAP 文件服务（中间件节点 01/02/03/04）",
  "## 6.2 HAP 文件服务（对象存储节点 192.168.1.71 / .72 / .73 / .74）")
mf = re.sub(r'^## 9\.(\d+) ', lambda m:'### 6.1.%s '%m.group(1), mf, flags=re.M)
mf = re.sub(r'^## 10\.(\d+) ', lambda m:'### 6.2.%s '%m.group(1), mf, flags=re.M)
mf = mf.replace("中间件节点","对象存储节点")

s = head + "\n\n" + mf + "\n\n" + tail

# --- 重构为每组件 H1（与 restructure_deploy.py 同逻辑）---
reps = [
 ("# 四、数据库部署\n\n## 4.1 MongoDB 4.4 副本集（节点 192.168.1.34 / .35 / .36）",
  "# 四、数据库部署 — MongoDB 4.4 副本集（MongoDB 节点 01/02/03 · 192.168.1.34/.35/.36）"),
 ("## 4.2 MySQL 8.0 MGR 集群（节点 192.168.1.31 / .32 / .33 + Router）",
  "# 五、数据库部署 — MySQL 8.0 MGR 集群（MySQL 节点 01/02/03 · 192.168.1.31/.32/.33 + Router）"),
 ("## 4.3 Redis 哨兵（节点 192.168.1.41 / .42 / .43）",
  "# 六、数据库部署 — Redis 哨兵（Redis 节点 01/02/03 · 192.168.1.41/.42/.43）"),
 ("# 五、消息与检索中间件\n\n## 5.1 Kafka 集群（节点 192.168.1.51 / .52 / .53）",
  "# 七、中间件部署 — Kafka 集群（Kafka 节点 01/02/03 · 192.168.1.51/.52/.53）"),
 ("## 5.2 Elasticsearch 集群（节点 192.168.1.61 / .62 / .63）",
  "# 八、中间件部署 — Elasticsearch 集群（ES 节点 01/02/03 · 192.168.1.61/.62/.63）"),
 ("# 六、对象存储与文件服务\n\n## 6.1 MinIO 集群（对象存储节点 192.168.1.71 / .72 / .73 / .74%s）"%SUF,
  "# 九、中间件部署 — MinIO 集群（对象存储节点 01-04 · 192.168.1.71-.74%s）"%SUF),
 ("## 6.2 HAP 文件服务（对象存储节点 192.168.1.71 / .72 / .73 / .74）",
  "# 十、中间件部署 — HAP 文件服务（对象存储节点 01-04 · 192.168.1.71-.74）"),
 ("# 七、Kubernetes 1.35.3 多 Master 集群（微服务节点 192.168.1.21-.25）",
  "# 十二、Kubernetes 1.35.3 三 Master 集群（微服务节点 01-05 · 192.168.1.21-.25）"),
 ("# 八、Istio 1.29.1 安装","# 十三、Istio 1.29.1 服务网格（K8s 集群）"),
 ("# 九、HAP 微服务部署（管理器在 K8s 01）","# 十四、HAP 微服务部署（K8s 集群）"),
 ("# 十、Flink 部署（数据同步节点 192.168.1.81 / .82 / .83）","# 十五、Flink 部署（HDP / Flink 节点 · 192.168.1.81-.83）"),
 ("# 十一、Nginx + Keepalived 高可用（192.168.1.11 / .12，VIP 192.168.1.20）","# 十六、Nginx 反向代理 + Keepalived（Nginx 节点 01/02 · VIP 192.168.1.20）"),
 ("# 十二、监控部署（Prometheus + Grafana）","# 十七、监控部署（Prometheus + Grafana）"),
 ("# 十三、上线验证与验收","# 十八、部署后验收"),
]
for a,b in reps:
    assert a in s, "NOT FOUND: "+a[:40]
    s=s.replace(a,b)
sub3={'4.1':'@D1@','4.2':'@D2@','4.3':'@D3@','5.1':'@M1@','5.2':'@M2@','6.1':'@O1@','6.2':'@O2@'}
for k,v in sub3.items(): s=re.sub(r'### %s\.'%re.escape(k),'## %s.'%v,s)
for k,v in [('7','@K@'),('9','@S@'),('10','@F@'),('11','@N@'),('12','@P@'),('13','@V@')]:
    s=re.sub(r'^## %s\.'%k,'## %s.'%v,s,flags=re.M)
final={'@D1@':'4','@D2@':'5','@D3@':'6','@M1@':'7','@M2@':'8','@O1@':'9','@O2@':'10',
       '@K@':'12','@S@':'14','@F@':'15','@N@':'16','@P@':'17','@V@':'18'}
for k,v in final.items(): s=s.replace('## %s.'%k,'## %s.'%v)

# 插入「十一、上传预置文件」
preconf='''# 十一、上传预置文件到 MinIO

> 微服务首次启动前，需将 HAP 预置文件（图标、模板等）上传到 MinIO 业务桶；任选一个 MinIO 节点（如对象存储节点 01 · 192.168.1.71）执行。
> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/file/v2/upload-preconf-files

```text
# 下载预置文件包并解压
wget https://pdpublic.mingdao.com/private-deployment/source/7.3.0/file_init.tar.gz
mkdir file_init
tar xf file_init.tar.gz -C file_init

# 拷贝 data 目录到任一 MinIO 容器
docker cp file_init/data "$(docker ps | grep mingdaoyun-minio | awk 'NR==1{print $1}')":/tmp

# 进入 MinIO 容器，配置 mc 别名并建桶
docker exec -it "$(docker ps | grep mingdaoyun-minio | awk 'NR==1{print $1}')" bash
mc alias set myminio http://127.0.0.1:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD
mc mb myminio/mdmedia
mc mb myminio/mdoc
mc mb myminio/mdpic
mc mb myminio/mdpub

# 上传预置数据到对应桶
mc cp -r /tmp/data/mdmedia/* myminio/mdmedia
mc cp -r /tmp/data/mdpic/*   myminio/mdpic
mc cp -r /tmp/data/mdpub/*   myminio/mdpub
```

'''
anchor="# 十二、Kubernetes 1.35.3 三 Master 集群"
assert anchor in s
s=s.replace(anchor, preconf+anchor)
s=s.replace('# 加入后重复 7.5 的后处理','# 加入后重复 12.5 的后处理')

out=os.path.join(_OUT,'deploy_%s_v2.md'%scene)
open(out,'w',encoding='utf-8').write(s)
h1=[l for l in s.split('\n') if re.match(r'^# ',l) and '、' in l or l=='# 文档说明']
print("scene",scene,"-> ",out," | 章节(应19):", len([l for l in s.split('\n') if re.match(r'^# (文档说明|[一二三四五六七八九十]+、)',l)]))
