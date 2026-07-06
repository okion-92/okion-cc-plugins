import os
_HERE=os.path.dirname(os.path.abspath(__file__))
_SRC=os.path.join(_HERE,'deploy_src')
_OUT=os.environ.get('HAP_DEPLOY_WORK', os.path.join(_SRC,'_work'))
os.makedirs(_OUT, exist_ok=True)
# 标准版(17节点共置)部署文档：复用专业版完整配置，重构标题 -> 重映射正文IP(跳过标题/STD_TOP) -> Flink哨兵
import re, sys
scene = sys.argv[1].upper()
SUF = {"B":"，场景 B Swarm","A":"，场景 A 独立单节点 Swarm"}[scene]
SD = {"B":"VXLAN 正常开启，对象存储 4 节点组成同一 Docker Swarm 集群",
      "A":"VXLAN 未开启，对象存储 4 节点各自运行独立的单节点 Docker Swarm，不组集群"}[scene]
NET = ("- 所有节点内网二层互通；中间件 4 节点（192.168.1.51-54）之间放通 Swarm 端口 **TCP 2377、UDP/TCP 4789、TCP 7946**（场景 B）。" if scene=="B"
       else "- 所有节点内网二层互通；中间件 4 节点（192.168.1.51-54）各自运行独立单节点 Swarm，**无需放通 2377/4789/7946**（场景 A）。")

head = open(os.path.join(_SRC,'deploy_head.md'),encoding='utf-8').read()
tail = open(os.path.join(_SRC,'deploy_tail.md'),encoding='utf-8').read()
mf   = open(os.path.join(_OUT,'minio_file_%s.md'%scene),encoding='utf-8').read()

STD_TOP = '''# 文档说明

本文档为 HAP（明道云 超级应用平台）私有化部署 **集群标准版（并发 600+ · 部分共置）** 的部署实施手册，网络形态为 **场景 @S@（@SD@）**。

## 集群标准版架构

集群标准版采用「部分共置」架构：数据库节点共置 MongoDB + MySQL（3 台），中间件节点共置 Kafka / ES / MinIO / 文件服务（4 台），缓存、负载、数据同步各自独立成节点，适用于并发 600+ 的生产环境，具备基本高可用（节点冗余、自动容错）。核心组件全部高可用：MySQL 采用 **MGR + Router** 三节点组复制，MongoDB 采用三节点 **副本集**，Redis 采用三节点 **哨兵**，Kafka / Elasticsearch / MinIO 均为多节点集群，Kubernetes 为三 Master 高可用。

本套拓扑共 **17 个节点**（按官方《服务器资源推荐》标准版口径核定，含数据同步 Flink 节点）。

## 节点 IP 规划

| 角色 | 主机名 | IP | 部署组件 |
| --- | --- | --- | --- |
| 负载均衡 01 | hap-nginx-01 | 192.168.1.11 | Nginx + Keepalived |
| 负载均衡 02 | hap-nginx-02 | 192.168.1.12 | Nginx + Keepalived |
| **负载 VIP** | — | **192.168.1.20** | Keepalived 虚拟 IP（对外入口） |
| 微服务 / K8s Master 01 | hap-k8s-01 | 192.168.1.21 | K8s Master + Istio + 微服务 |
| 微服务 / K8s Master 02 | hap-k8s-02 | 192.168.1.22 | K8s Master + 微服务 |
| 微服务 / K8s Master 03 | hap-k8s-03 | 192.168.1.23 | K8s Master + 微服务 |
| 数据库 01 | hap-db-01 | 192.168.1.31 | MongoDB 副本集 + MySQL MGR + Router |
| 数据库 02 | hap-db-02 | 192.168.1.32 | MongoDB 副本集 + MySQL MGR + Router |
| 数据库 03 | hap-db-03 | 192.168.1.33 | MongoDB 副本集 + MySQL MGR + Router |
| Redis 01 (Master) | hap-redis-01 | 192.168.1.41 | Redis + Sentinel |
| Redis 02 | hap-redis-02 | 192.168.1.42 | Redis + Sentinel |
| Redis 03 | hap-redis-03 | 192.168.1.43 | Redis + Sentinel |
| 中间件 01 | hap-mw-01 | 192.168.1.51 | MinIO + File |
| 中间件 02 | hap-mw-02 | 192.168.1.52 | Kafka + ES + MinIO + File |
| 中间件 03 | hap-mw-03 | 192.168.1.53 | Kafka + ES + MinIO + File |
| 中间件 04 | hap-mw-04 | 192.168.1.54 | Kafka + ES + MinIO + File |
| 数据同步 01 | hap-flink-01 | 192.168.1.61 | Flink (HDP 超级数据平台) |
| 数据同步 02 | hap-flink-02 | 192.168.1.62 | Flink (HDP 超级数据平台) |

> 访问入口：https://hap.domain.com（端口 443，经 Nginx VIP 192.168.1.20 转发到 K8s 微服务 www 端口 8880）。示例 IP，交付时整体替换。
> 共置说明：数据库节点 3 台共置 MongoDB+MySQL；中间件节点 4 台，后 3 台（02/03/04）共置 Kafka 与 ES，全部 4 台共置 MinIO 与文件服务。

## 关键端口与版本

| 组件 | 版本 | 关键端口 |
| --- | --- | --- |
| MySQL | 8.0.45 | 3306 / Router 6446·6447 / 33061 |
| MongoDB | 4.4.30 | 27017 |
| Redis | 8.x | 6379 / Sentinel 26379 |
| Kafka | 3.9.1 (JDK 21) | 9092 / ZK 2181 / 2888 / 3888 |
| Elasticsearch | 8.19.8 | 9200 / 9300 |
| MinIO | RELEASE.2025-04-22 | 9011-9014（容器内 9000） |
| HAP File | 2.1.0 | 9001-9004（容器内 9000） |
| Kubernetes | 1.35.3 | 6443 / 8880 / 18880 / 38880 / 38881 |
| Istio | 1.29.1 | — |
| HAP 微服务 | 7.3.4 | 8880(www 主地址) / 18880(www 扩展地址，按需启用) / 38880(安装管理器 ENV_CAPTAIN_ENDPOINT) / 38881(管理入口) |
| Flink | 1.19.720 | JobManager 8081 |
| Docker / Nginx | 28.5.2 / 1.28.2 | 80 / 443 |

# 一、服务器资源清单

集群标准版生产环境最小拓扑（共 17 节点，HDP 节点即 Flink 节点）：

| 角色 | 配置 | 操作系统 | 部署服务 | 数量 |
| --- | --- | --- | --- | --- |
| 负载均衡 | 4C / 8G / 60G 系统盘 + 200G SSD | Debian 12 | Nginx + Keepalived | 2 |
| 微服务 | 16C / 64G / 60G 系统盘 + 200G SSD | Debian 12 | K8s + Istio + HAP 微服务 | 3 |
| 缓存 | 4C / 16G / 60G 系统盘 + 200G SSD | Debian 12 | Redis 哨兵 | 3 |
| 中间件 | 8C / 32G / 60G 系统盘 + 500G SSD | Debian 12 | Kafka + ES + MinIO + File | 4 |
| 数据库 | 8C / 32G / 60G 系统盘 + 300G SSD | Debian 12 | MongoDB + MySQL（共置） | 3 |
| 数据同步 | 8C / 32G / 60G 系统盘 + 200G SSD | Debian 12 | Flink (HDP) | 2 |
| **合计** | — | — | — | **17** |

> 注：标准版数据库节点（MongoDB+MySQL）3 台共置；中间件节点 4 台，后 3 台共置 Kafka 与 ES、全部 4 台共置 MinIO 与文件服务；HDP/Flink 2 台。

## 1.2 网络互通要求

@NET@
- K8s 节点（.21/.22/.23）放通 6443、10250、179(Calico)、VXLAN 4789(UDP)、NodePort 1024-32767。
- 微服务节点访问：MySQL Router 6446、MongoDB 27017、Redis 6379/26379、Kafka 9092、ES 9200、File 9001-9004。
- 仅 Nginx VIP 192.168.1.20 的 80/443 对外暴露。

'''.replace("@S@",scene).replace("@SD@",SD).replace("@NET@",NET)

# head: 用 STD_TOP 替换专业版「文档说明~一」
i2 = head.find("# 二、操作系统初始化")
head = STD_TOP + head[i2:]

# sec6
mf = mf.replace("# 九、中间件部署 — MinIO 集群（中间件节点 01/02/03/04）",
  "# 六、对象存储与文件服务\n\n## 6.1 MinIO 集群（中间件节点 01/02/03/04%s）"%SUF)
mf = mf.replace("# 十、中间件部署 — HAP 文件服务（中间件节点 01/02/03/04）",
  "## 6.2 HAP 文件服务（中间件节点 01/02/03/04）")
mf = re.sub(r'^## 9\.(\d+) ', lambda m:'### 6.1.%s '%m.group(1), mf, flags=re.M)
mf = re.sub(r'^## 10\.(\d+) ', lambda m:'### 6.2.%s '%m.group(1), mf, flags=re.M)

s = head + "\n\n" + mf + "\n\n" + tail

# ===== STEP 1: 重构(标题重命名+重编号), reps OLD 用专业版原标题(专业版IP) =====
reps = [
 ("# 四、数据库部署\n\n## 4.1 MongoDB 4.4 副本集（节点 192.168.1.34 / .35 / .36）",
  "# 四、数据库部署 — MongoDB 4.4 副本集（数据库节点 01/02/03 · 192.168.1.31/.32/.33）"),
 ("## 4.2 MySQL 8.0 MGR 集群（节点 192.168.1.31 / .32 / .33 + Router）",
  "# 五、数据库部署 — MySQL 8.0 MGR 集群（数据库节点 01/02/03 · 192.168.1.31/.32/.33 + Router）"),
 ("## 4.3 Redis 哨兵（节点 192.168.1.41 / .42 / .43）",
  "# 六、数据库部署 — Redis 哨兵（Redis 节点 01/02/03 · 192.168.1.41/.42/.43）"),
 ("# 五、消息与检索中间件\n\n## 5.1 Kafka 集群（节点 192.168.1.51 / .52 / .53）",
  "# 七、中间件部署 — Kafka 集群（中间件节点 02/03/04 · ⟦KE⟧）"),
 ("## 5.2 Elasticsearch 集群（节点 192.168.1.61 / .62 / .63）",
  "# 八、中间件部署 — Elasticsearch 集群（中间件节点 02/03/04 · ⟦KE⟧）"),
 ("# 六、对象存储与文件服务\n\n## 6.1 MinIO 集群（中间件节点 01/02/03/04%s）"%SUF,
  "# 九、中间件部署 — MinIO 集群（中间件节点 01/02/03/04 · ⟦MW⟧%s）"%SUF),
 ("## 6.2 HAP 文件服务（中间件节点 01/02/03/04）",
  "# 十、中间件部署 — HAP 文件服务（中间件节点 01/02/03/04 · ⟦MW⟧）"),
 ("# 七、Kubernetes 1.35.3 多 Master 集群（微服务节点 192.168.1.21-.25）",
  "# 十二、Kubernetes 1.35.3 三 Master 集群（微服务节点 01/02/03 · 192.168.1.21-.23）"),
 ("# 八、Istio 1.29.1 安装","# 十三、Istio 1.29.1 服务网格（K8s 集群）"),
 ("# 九、HAP 微服务部署（管理器在 K8s 01）","# 十四、HAP 微服务部署（K8s 集群）"),
 ("# 十、Flink 部署（数据同步节点 192.168.1.81 / .82 / .83）","# 十五、Flink 部署（HDP / Flink 节点 · ⟦FK⟧）"),
 ("# 十一、Nginx + Keepalived 高可用（192.168.1.11 / .12，VIP 192.168.1.20）","# 十六、Nginx 反向代理 + Keepalived（Nginx 节点 01/02 · VIP 192.168.1.20）"),
 ("# 十二、监控部署（Prometheus + Grafana）","# 十七、监控部署（Prometheus + Grafana）"),
 ("# 十三、上线验证与验收","# 十八、部署后验收"),
]
for a,b in reps:
    assert a in s, "NOT FOUND: "+repr(a[:46])
    s=s.replace(a,b)
sub3={'4.1':'@D1@','4.2':'@D2@','4.3':'@D3@','5.1':'@M1@','5.2':'@M2@','6.1':'@O1@','6.2':'@O2@'}
for k,v in sub3.items(): s=re.sub(r'### %s\.'%re.escape(k),'## %s.'%v,s)
for k,v in [('7','@K@'),('9','@SV@'),('10','@FL@'),('11','@NG@'),('12','@MO@'),('13','@VR@')]:
    s=re.sub(r'^## %s\.'%k,'## %s.'%v,s,flags=re.M)
final={'@D1@':'4','@D2@':'5','@D3@':'6','@M1@':'7','@M2@':'8','@O1@':'9','@O2@':'10',
       '@K@':'12','@SV@':'14','@FL@':'15','@NG@':'16','@MO@':'17','@VR@':'18'}
for k,v in final.items(): s=s.replace('## %s.'%k,'## %s.'%v)
s=s.replace('# 加入后重复 7.5 的后处理','# 加入后重复 12.5 的后处理')

# ===== STEP 2: 结构缩减(正文, 专业版IP) =====
# K8s 5->3: 删 Worker 段、改说明
s=s.replace("> 微服务层共 5 节点：3 Master（.21/.22/.23）+ 2 Worker（.24/.25）。",
            "> 微服务层共 3 节点：3 Master（.21/.22/.23）。")
s=s.replace('''
# Worker 01 / 02（192.168.1.24 / .25）：
kubeadm join k8s-master:6443 --token <TOKEN> \\
  --discovery-token-ca-cert-hash sha256:<HASH>
echo "maxPods: 300" >> /var/lib/kubelet/config.yaml
systemctl restart kubelet
''',"\n")
s=s.replace("    server 192.168.1.24:8880 max_fails=3 fail_timeout=15s;\n","")
s=s.replace("    server 192.168.1.25:8880 max_fails=3 fail_timeout=15s;\n","")
s=s.replace('"192.168.1.21:59100","192.168.1.22:59100","192.168.1.23:59100","192.168.1.24:59100","192.168.1.25:59100"',
            '"192.168.1.21:59100","192.168.1.22:59100","192.168.1.23:59100"')
# 监控去掉与他组重复的行(MongoDB=数据库节点 与 MySQL 同IP; ES 与 Kafka 同IP)
s=s.replace('      - targets: ["192.168.1.34:59100","192.168.1.35:59100","192.168.1.36:59100"]  # MongoDB\n','')
s=s.replace('      - targets: ["192.168.1.61:59100","192.168.1.62:59100","192.168.1.63:59100"]  # ES\n','')
s=s.replace("# node_exporter：所有 29 个节点部署，监听 :59100","# node_exporter：所有 17 个节点部署，监听 :59100")
s=s.replace("# cadvisor：仅对象存储 4 节点","# cadvisor：仅中间件 4 节点")
# Flink 3->2: 文本 + IP 哨兵(避免与 ES->.61/.62/.63 remap 冲突)
s=s.replace("对 192.168.1.81 / .82 / .83 三个 Flink 节点执行（替换 $flink_node_name 为各节点名）",
            "对 @F1@ / @F2@ 两个 Flink 节点执行（替换 $flink_node_name 为各节点名）")
s=s.replace("192.168.1.81","@F1@").replace("192.168.1.82","@F2@").replace("192.168.1.83","@F2@")

# ===== STEP 3: 正文IP重映射(STD_TOP 之后全部行; 标题里的标准IP已用 ⟦..⟧ 令牌保护) =====
# Docker 章标题 + cadvisor 注释里的缩写区间 -> 令牌(避免 .71-.74 被半remap)
s=s.replace("# 三、Docker 安装（对象存储节点 192.168.1.71-74）","# 三、Docker 安装（中间件节点 ⟦MW⟧）")
s=s.replace("（192.168.1.71-.74，跑 docker）","（⟦MW⟧，跑 docker）")
ipmap={'34':'31','35':'32','36':'33','51':'52','52':'53','53':'54','61':'52','62':'53','63':'54',
       '71':'51','72':'52','73':'53','74':'54'}
idx=s.find("# 二、操作系统初始化")
toppart, restpart = s[:idx], s[idx:]   # STD_TOP 不参与 remap
restpart=re.sub(r'192\.168\.1\.(\d+)', lambda m:'192.168.1.'+ipmap.get(m.group(1),m.group(1)), restpart)
s=toppart+restpart
# 还原令牌
s=s.replace("⟦KE⟧","192.168.1.52/.53/.54").replace("⟦MW⟧","192.168.1.51-.54").replace("⟦FK⟧","192.168.1.61/.62")
s=s.replace("@F1@","192.168.1.61").replace("@F2@","192.168.1.62")

# 监控 node_exporter: 专业版29节点(remap后有共置重复) -> 标准版17节点干净列表
std_groups=[("Nginx",[("11","hap-nginx-01"),("12","hap-nginx-02")]),
 ("微服务/K8s",[("21","hap-k8s-01"),("22","hap-k8s-02"),("23","hap-k8s-03")]),
 ("数据库(MongoDB+MySQL 共置)",[("31","hap-db-01"),("32","hap-db-02"),("33","hap-db-03")]),
 ("Redis",[("41","hap-redis-01"),("42","hap-redis-02"),("43","hap-redis-03")]),
 ("中间件(Kafka/ES/MinIO/File 共置)",[("51","hap-mw-01"),("52","hap-mw-02"),("53","hap-mw-03"),("54","hap-mw-04")]),
 ("Flink",[("61","hap-flink-01"),("62","hap-flink-02")])]
ne=[]
for label,nodes in std_groups:
    for suf,name in nodes:
        ne.append('      - targets: ["192.168.1.%s:59100"]'%suf)
        ne.append('        labels:'); ne.append('          nodename: %s'%name); ne.append('          origin_prometheus: node')
STD_NE="\n".join(ne)
s=re.sub(r'(  - job_name: "node_exporter"\n    static_configs:\n).*?(\n\n  # docker 监控)',
         lambda m: m.group(1)+STD_NE+m.group(2), s, count=1, flags=re.S)
s=s.replace("# node_exporter（所有 29 个节点均部署）","# node_exporter（所有 17 个节点均部署）")
s=s.replace("> 采集：每个节点 node_exporter（:59100）；跑 Docker 的节点（对象存储 4 节点）",
            "> 采集：每个节点 node_exporter（:59100）；跑 Docker 的节点（中间件 4 节点）")

# 插入 上传预置文件
preconf='''# 十一、上传预置文件到 MinIO

> 微服务首次启动前，需将 HAP 预置文件上传到 MinIO 业务桶；任选一个 MinIO 节点（如中间件节点 01 · 192.168.1.51）执行。
> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/file/v2/upload-preconf-files

```text
wget https://pdpublic.mingdao.com/private-deployment/source/7.3.0/file_init.tar.gz
mkdir file_init
tar xf file_init.tar.gz -C file_init
docker cp file_init/data "$(docker ps | grep mingdaoyun-minio | awk 'NR==1{print $1}')":/tmp
docker exec -it "$(docker ps | grep mingdaoyun-minio | awk 'NR==1{print $1}')" bash
mc alias set myminio http://127.0.0.1:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD
mc mb myminio/mdmedia
mc mb myminio/mdoc
mc mb myminio/mdpic
mc mb myminio/mdpub
mc cp -r /tmp/data/mdmedia/* myminio/mdmedia
mc cp -r /tmp/data/mdpic/*   myminio/mdpic
mc cp -r /tmp/data/mdpub/*   myminio/mdpub
```

'''
anchor="# 十二、Kubernetes 1.35.3 三 Master 集群（微服务节点 01/02/03"
s=s.replace(anchor, preconf+anchor)

out=os.path.join(_OUT,'deploy_std_%s_v2.md'%scene)
open(out,'w',encoding='utf-8').write(s)
leftover=sum(s.count(x) for x in ['192.168.1.34','192.168.1.71','192.168.1.81','192.168.1.24','192.168.1.63'])
print("standard",scene,"| chapters(应19):",len([l for l in s.split('\n') if re.match(r'^# (文档说明|[一二三四五六七八九十]+、)',l)]),
      "| createUser:",s.count('db.createUser'),"| 残留专业版IP(应0):",leftover)
