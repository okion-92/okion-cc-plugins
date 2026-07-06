# 由 ops_src/ops_base.md(标准版场景A·含高危提示) 派生运维文档各形态 markdown 到 _OUT。
# 用法: python ops_build.py <stdA|stdB|proA|proB|lite>
import re, sys, os, shutil
_HERE=os.path.dirname(os.path.abspath(__file__))
_SRC=os.path.join(_HERE,'ops_src')
_OUT=os.environ.get('HAP_DEPLOY_WORK', os.path.join(_SRC,'_work'))
os.makedirs(_OUT, exist_ok=True)
base=open(os.path.join(_SRC,'ops_base.md'),encoding='utf-8').read()
base=re.sub(r'(?m)^[ \t]+$','',base)   # 把仅含空格的"空行"规范化为真空行，便于整块匹配

def scene_B(s, ver_label):
    # 文档说明
    s=s.replace('（场景 A · 未开启 Docker Swarm 集群）','（场景 B · 开启 Docker Swarm 集群）')
    s=s.replace('另一场景（场景 B · 开启 Docker Swarm）运维请参阅《HAP运维文档（%s · 场景 B）》。'%ver_label,
                '另一场景（场景 A · 未开启 Docker Swarm）运维请参阅《HAP运维文档（%s · 场景 A）》。'%ver_label)
    # 适用架构
    s=s.replace('场景 A（未开启 Docker Swarm 集群），','场景 B（开启 Docker Swarm 集群），')
    s=s.replace('每节点单节点 docker swarm','4 节点组成同一 Docker Swarm 集群（Node01 统一编排）')
    s=s.replace('《HAP部署实施文档（%s · 场景 A）》'%ver_label,'《HAP部署实施文档（%s · 场景 B）》'%ver_label)
    # 1.2 表 MinIO 安装路径列
    s=s.replace('| 单节点 docker swarm | /data/minio + /data/file |','| Swarm 集群（Node01 编排） | /data/minio + /data/file |')
    # 2.3 标题与正文
    s=s.replace('## 2.3 MinIO + File 容器管理（中间件 4 节点 · 单节点 docker swarm）',
                '## 2.3 MinIO + File 容器管理（中间件 4 节点 · 同一 Swarm 集群 · Node01 统一编排）')
    s=s.replace('''# 场景 A 下每个中间件节点各自维护一个单节点 docker swarm，
# 使用 docker stack deploy 部署 MinIO / File；每个节点独立操作。

# 在某中间件节点上查看本机 Swarm 节点状态
docker node ls

# 查看本节点 stack 列表与服务状态
docker stack ls
docker stack ps minio
docker stack ps file

# 启动（每个节点都执行；部署使用 docker stack deploy）
docker stack deploy -c /usr/local/minio/minio.yaml minio --detach=false
docker stack deploy -c /usr/local/MDPrivateDeployment/clusterMode/file.yaml file --detach=false
# 或者直接调用部署脚本
bash /usr/local/minio/start.sh
bash /usr/local/MDPrivateDeployment/clusterMode/start.sh

# 停止（每个节点都执行）
docker stack rm minio
docker stack rm file
# 或者直接调用部署脚本
bash /usr/local/minio/stop.sh
bash /usr/local/MDPrivateDeployment/clusterMode/stop.sh

# 查看容器日志
docker ps -a | grep -E 'minio|file'
docker logs -f --tail 200 <container-id>''',
'''# 场景 B 下 4 个中间件节点组成同一 Docker Swarm 集群，Node01 为 manager 统一编排；
# 以下 docker stack / service 命令仅在 Node01（192.168.1.51）执行，Swarm 自动调度到 4 节点。

# 查看 Swarm 集群节点状态（Node01）
docker node ls

# 查看 stack 列表与服务在各节点的分布
docker stack ls
docker stack ps minio
docker stack ps file
docker service ls

# 启动（仅 Node01 执行；Swarm 调度到 4 节点）
docker stack deploy -c /usr/local/minio/minio.yaml minio --detach=false
docker stack deploy -c /usr/local/MDPrivateDeployment/clusterMode/file.yaml file --detach=false
# 或直接调用部署脚本（仅 Node01）
bash /usr/local/minio/start.sh
bash /usr/local/MDPrivateDeployment/clusterMode/start.sh

# 停止（仅 Node01）
docker stack rm minio
docker stack rm file

# 强制某服务重新调度 / 滚动更新（Node01）
docker service update --force minio_minio1

# 查看容器日志（在容器实际所在节点）
docker ps -a | grep -E 'minio|file'
docker logs -f --tail 200 <container-id>''')
    # 7.2.1
    s=s.replace('### 7.2.1 MinIO / File 升级（4 节点 · 单节点 docker swarm）',
                '### 7.2.1 MinIO / File 升级（4 节点 · 同一 Swarm 集群 · Node01 编排）')
    s=s.replace('''# 1. 在 4 个 MinIO + File 节点都拉取新镜像
docker pull registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-minio:<新版本>
docker pull registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-file:<新版本>

# 2. 在 4 个节点上分别修改本机的 minio.yaml / file.yaml 镜像版本
sed -ri 's|mingdaoyun-minio:.*|mingdaoyun-minio:<新版本>|g' /usr/local/minio/minio.yaml
sed -ri 's|mingdaoyun-file:.*|mingdaoyun-file:<新版本>|g' /usr/local/MDPrivateDeployment/clusterMode/file.yaml

# 3. 滚动重启：建议逐节点执行，避免 4 节点同时停服
bash /usr/local/minio/stop.sh && bash /usr/local/minio/start.sh
bash /usr/local/MDPrivateDeployment/clusterMode/stop.sh && bash /usr/local/MDPrivateDeployment/clusterMode/start.sh

# 4. 验证
docker stack ps minio
docker stack ps file''',
'''# 1. 在 4 个 MinIO + File 节点都拉取新镜像（镜像需各节点本地具备）
docker pull registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-minio:<新版本>
docker pull registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-file:<新版本>

# 2. 仅在 Node01 修改同一份 minio.yaml / file.yaml 的镜像版本
sed -ri 's|mingdaoyun-minio:.*|mingdaoyun-minio:<新版本>|g' /usr/local/minio/minio.yaml
sed -ri 's|mingdaoyun-file:.*|mingdaoyun-file:<新版本>|g' /usr/local/MDPrivateDeployment/clusterMode/file.yaml

# 3. 仅在 Node01 执行 docker stack deploy，Swarm 滚动更新到 4 节点
docker stack deploy -c /usr/local/minio/minio.yaml minio --detach=false
docker stack deploy -c /usr/local/MDPrivateDeployment/clusterMode/file.yaml file --detach=false

# 4. 验证
docker stack ps minio
docker stack ps file''')
    # 9.1 网络
    s=s.replace('场景 A 未启用 Docker Swarm，无需开放 2377/7946/4789 端口；若切换至场景 B，请按场景 B 文档放通这些端口。',
                '场景 B 已启用 Docker Swarm，中间件 4 节点之间须放通 **2377（集群管理）、7946（节点发现）、4789（overlay 数据面）** 端口；这些端口仅在中间件 4 节点之间互通，不对其他网段暴露。')
    # 10.7
    s=s.replace('# 场景 A 下每个 MinIO + File 节点独立 docker compose 运行\n# 在该离线节点上排查：',
                '# 场景 B 下 4 节点为同一 Swarm 集群，在 Node01 统一排查：')
    s=s.replace('''# 查看本节点容器状态
docker stack ps minio
docker stack ps file

# 重新启动本节点的服务
bash /usr/local/minio/start.sh
bash /usr/local/MDPrivateDeployment/clusterMode/start.sh''',
'''# 在 Node01 查看 Swarm 节点与服务分布
docker node ls
docker service ps minio_minio1
docker stack ps minio
docker stack ps file

# 节点恢复后强制服务重新调度（Node01）
docker service update --force minio_minio1
docker service update --force file_file1''')
    return s

def pro(s):
    s=s.replace('集群标准版','集群专业版')
    # —— 哨兵保护要整体改写的散文块 ——
    P={}
    P['@ARCH@']=('本文档对应集群专业版场景 A（未开启 Docker Swarm 集群），最小拓扑 29 节点（各组件独立部署）：'
      '2 台 Nginx + Keepalived（VIP 192.168.1.20）、5 台 K8s（3 Master + 2 Worker）+ Istio、'
      '3 台 MySQL MGR + Router、3 台 MongoDB 副本集、3 台 Redis Master/Slave + Sentinel、'
      '3 台 Kafka + Zookeeper、3 台 Elasticsearch、4 台 MinIO + File（每节点单节点 docker swarm）、'
      '3 台 Flink 节点（K8s Worker · Flink 专属）。详细部署步骤请参阅《HAP部署实施文档（集群专业版 · 场景 A）》。')
    s=s.replace('本文档对应集群专业版场景 A（未开启 Docker Swarm 集群），最小拓扑 17 节点：2 台 Nginx + Keepalived（VIP 192.168.1.20）、3 台 K8s Master+Node + Istio、3 台数据库共置节点（MongoDB 副本集 + MySQL MGR + Router）、3 台 Redis Master/Slave + Sentinel、4 台中间件共置节点（MinIO + File + Kafka + Zookeeper + Elasticsearch，每节点单节点 docker swarm）、2 台 Flink 节点（K8s Worker · Flink 专属）。详细部署步骤请参阅《HAP部署实施文档（集群专业版 · 场景 A）》。','@ARCH@')
    P['@OPSP@']='MySQL、MongoDB 各自独立 3 节点部署（不共置）；同时操作两台或以上同一组件的数据库节点会影响该组件可用性 — 不要在变更窗口内同时操作。'
    s=s.replace('数据库节点与 MySQL/MongoDB 共置部署，3 台数据库节点同时故障会导致整个数据库层不可用 — 不要在变更窗口内同时操作两台或以上数据库节点。','@OPSP@')
    P['@DB27@']='MySQL MGR + Router 独立部署在 192.168.1.31 / 192.168.1.32 / 192.168.1.33；MongoDB 副本集独立部署在 192.168.1.34 / 192.168.1.35 / 192.168.1.36；Redis 独立在 192.168.1.41 / 192.168.1.42 / 192.168.1.43。本节列出三类组件的启停命令。建议变更窗口内逐节点操作。'
    s=s.replace('数据库节点（192.168.1.31 / 192.168.1.32 / 192.168.1.33）共置部署 MongoDB 副本集 + MySQL MGR + Router；Redis 独立在 192.168.1.41/192.168.1.42/192.168.1.43。本节列出三类组件的启停命令。建议变更窗口内逐节点操作。','@DB27@')
    P['@MW28@']='Kafka + ZooKeeper 独立部署在 192.168.1.51 / 192.168.1.52 / 192.168.1.53；Elasticsearch 独立部署在 192.168.1.61 / 192.168.1.62 / 192.168.1.63；MinIO + File 独立部署在 192.168.1.71 / 192.168.1.72 / 192.168.1.73 / 192.168.1.74。'
    s=s.replace('中间件节点（192.168.1.51 / 192.168.1.52 / 192.168.1.53 / 192.168.1.54）共置部署 Kafka + ZooKeeper、Elasticsearch、MinIO + File。Kafka 与 Elasticsearch 位于中间件 02-04（192.168.1.52-192.168.1.54）；MinIO + File 4 节点全部承载。','@MW28@')
    # 1.3 表整体替换(K8s 5 + Flink 3)
    P['@T13@']='''| 组件 | 节点（IP） | 角色 | 说明 |
| --- | --- | --- | --- |
| K8s Master 01 | 192.168.1.21 | Master | kubeadm 引导节点；存储 admin.conf；管理器入口 38881 |
| K8s Master 02 | 192.168.1.22 | Master | 通过 kubeadm join --control-plane 加入 |
| K8s Master 03 | 192.168.1.23 | Master | 通过 kubeadm join --control-plane 加入 |
| K8s Worker 01 | 192.168.1.24 | Worker | 承载微服务 Pod |
| K8s Worker 02 | 192.168.1.25 | Worker | 承载微服务 Pod |
| Istio | 由 K8s 全部 5 节点承载 | istio-system 命名空间 | 版本 1.29.1，sidecar 自动注入 default 命名空间 |
| HAP 微服务 | 由 K8s 全部 5 节点承载 | default 命名空间 | mingdaoyun-hap 镜像，多副本部署 |
| Flink | 192.168.1.81 / 192.168.1.82 / 192.168.1.83 | Worker（污点 hap=flink） | JobManager × 1 + TaskManager × N，flink 命名空间 |'''
    s=s.replace('''| 组件 | 节点（IP） | 角色 | 说明 |
| --- | --- | --- | --- |
| K8s Master+Node 01 | 192.168.1.21 | Master + Worker | kubeadm 引导节点；存储 admin.conf；管理器入口 38881 |
| K8s Master+Node 02 | 192.168.1.22 | Master + Worker | 通过 kubeadm join --control-plane 加入 |
| K8s Master+Node 03 | 192.168.1.23 | Master + Worker | 通过 kubeadm join --control-plane 加入 |
| Istio | 由 K8s 全部 3 节点承载 | istio-system 命名空间 | 版本 1.29.1，sidecar 自动注入 default 命名空间 |
| HAP 微服务 | 由 K8s 全部 3 节点承载 | default 命名空间 | mingdaoyun-hap 镜像，多副本部署 |
| Flink | 192.168.1.61 / 192.168.1.62 | Worker（污点 hap=flink） | JobManager × 1 + TaskManager × 2，flink 命名空间 |''','@T13@')
    # 8.x 计数
    s=s.replace('主机层全部 18 节点','主机层全部 29 节点')
    s=s.replace('| Flink（2 台） |','| Flink（3 台） |')
    s=s.replace('| MongoDB 副本集（3 台） |','| MongoDB 副本集（独立 3 台） |').replace('| MySQL MGR（3 台） |','| MySQL MGR（独立 3 台） |')
    s=s.replace('Kafka（3 台）','Kafka（独立 3 台）').replace('Elasticsearch（3 台）','Elasticsearch（独立 3 台）')
    # —— 上下文级 IP 重映射(按行判定组件) ——
    def remap(s):
        out=[]
        for ln in s.split('\n'):
            def sub(mp): return re.sub(r'192\.168\.1\.(\d+)', lambda m:'192.168.1.'+mp.get(m.group(1),m.group(1)), ln)
            if any(k in ln for k in ['minio','MinIO','/data/minio','/data/file','mdmedia','mdpic','mdpub','mdoc','file.yaml','minio.yaml','hap-minio','/data/file/volume','clusterMode']):
                out.append(sub({'51':'71','52':'72','53':'73','54':'74'}))
            elif any(k in ln for k in ['Kafka','kafka','zookeeper','ZooKeeper','broker','/data/kafka','9092','2181','2888','3888']):
                out.append(sub({'52':'51','53':'52','54':'53'}))
            elif any(k in ln for k in ['Elasticsearch','elasticsearch','9200','9300','/data/elasticsearch','elastic:','x-pack',' ES ','ES ','ES索引','ES 索引']):
                out.append(sub({'52':'61','53':'62','54':'63'}))
            elif any(k in ln for k in ['MongoDB','mongo','27017','副本集','replicaSet','local-mongodb-one','keyfile','keyFile','rs.','mongod']):
                out.append(sub({'31':'34','32':'35','33':'36'}))
            elif any(k in ln for k in ['Flink','flink','JobManager','TaskManager','8081','hap=flink']):
                out.append(sub({'61':'81','62':'82'}))
            else:
                out.append(ln)
        return '\n'.join(out)
    s=remap(s)
    for k,v in P.items(): s=s.replace(k,v)
    return s

key=sys.argv[1]
if key=='stdA':   out=base
elif key=='stdB': out=scene_B(base,'集群标准版')
elif key=='proA': out=pro(base)
elif key=='proB': out=scene_B(pro(base),'集群专业版')
elif key=='lite': out=open(os.path.join(_SRC,'ops_lite.md'),encoding='utf-8').read()
else: sys.exit('key 必须是 stdA|stdB|proA|proB|lite')
outpath=os.path.join(_OUT,'ops_%s.md'%key)
open(outpath,'w',encoding='utf-8').write(out)
print(outpath)
