import os
_HERE=os.path.dirname(os.path.abspath(__file__))
_SRC=os.path.join(_HERE,'chk_src')
_OUT=os.environ.get('HAP_DEPLOY_WORK', os.path.join(_SRC,'_work'))
os.makedirs(_OUT, exist_ok=True)
import re, sys
base=open(os.path.join(_SRC,'chk_base.md'),encoding='utf-8').read()
base=re.sub(r'(?m)^[ \t]+$','',base)

# 规范化到本套命名 + MinIO 端口对齐部署口径(标准A 基线)
for a,b in [
 ('HAP部署实施文档_集群标准版_场景A_未开启Swarm_.docx','HAP部署实施文档_集群标准版_场景A.docx'),
 ('部署实施文档（集群标准版 · 场景 A · 未开启 Swarm）','部署实施文档（集群标准版 · 场景 A）'),
 ('集群标准版 · 场景 A · 未开启 Swarm','集群标准版 · 场景 A'),
 ('HAP数据迁移文档_单机迁移集群标准版_场景A_.docx','HAP数据迁移文档_单机迁移集群标准版.docx'),
 ('数据迁移文档（单机迁移集群标准版 · 场景 A）','数据迁移文档（单机迁移集群标准版）'),
 ('HAP运维文档_集群标准版_场景A_.docx','HAP运维文档_集群标准版_场景A.docx'),
 ('Sheet 1（凭据登记表）：34 条记录','Sheet 1（凭据登记表）：28 条记录'),
 ('统一 9000 端口','9011-9014 端口'),('统一 9000 端口可访问','9011-9014 端口可访问'),
 ('MinIO 4 节点（192.168.1.51/192.168.1.52/192.168.1.53/192.168.1.54）单节点 docker swarm 部署，4 节点 9011-9014 端口可访问',
  'MinIO 4 节点（192.168.1.51/192.168.1.52/192.168.1.53/192.168.1.54）单节点 docker swarm 部署，9011-9014 端口可访问'),
]:
    base=base.replace(a,b)

def remap_pro(s):
    out=[]
    for ln in s.split('\n'):
        def sub(mp): return re.sub(r'192\.168\.1\.(\d+)', lambda m:'192.168.1.'+mp.get(m.group(1),m.group(1)), ln)
        if any(k in ln for k in ['MinIO','minio','文件','File','对象存储']):
            out.append(sub({'51':'71','52':'72','53':'73','54':'74'}))
        elif any(k in ln for k in ['Kafka','kafka']) and 'ES' not in ln and 'Elasticsearch' not in ln:
            out.append(sub({'52':'51','53':'52','54':'53'}))
        elif any(k in ln for k in ['Elasticsearch','ES ','ES','检索']):
            out.append(sub({'52':'61','53':'62','54':'63'}))
        elif any(k in ln for k in ['MongoDB','mongo','副本集']) and 'MySQL' not in ln:
            out.append(sub({'31':'34','32':'35','33':'36'}))
        elif any(k in ln for k in ['Flink','flink']):
            out.append(sub({'61':'81','62':'82'}))
        else:
            out.append(ln)
    return '\n'.join(out)

def to_scene_B(s, vlabel):
    s=s.replace('HAP部署实施文档_%s_场景A.docx'%vlabel,'HAP部署实施文档_%s_场景B.docx'%vlabel)
    s=s.replace('HAP运维文档_%s_场景A.docx'%vlabel,'HAP运维文档_%s_场景B.docx'%vlabel)
    s=s.replace('%s_场景A_架构图'%vlabel,'%s_场景B_架构图'%vlabel)
    s=s.replace('%s_场景A_凭据登记表'%vlabel,'%s_场景B_凭据登记表'%vlabel)
    s=s.replace('未开启 Docker Swarm','开启 Docker Swarm').replace('未开启 Swarm','开启 Swarm')
    s=s.replace('单节点 docker swarm 部署','同一 Swarm 集群部署（Node01 统一编排）')
    s=s.replace('每节点单节点 docker swarm 部署','4 节点同一 Swarm 集群（Node01 统一编排）')
    s=s.replace('MinIO/File 单节点 swarm 启停','MinIO/File Swarm 集群 Node01 统一启停')
    s=s.replace('场景 A','场景 B')
    return s

tier=sys.argv[1]
if tier=='stdA':
    out=base
elif tier=='stdB':
    out=to_scene_B(base,'集群标准版')
elif tier=='proA':
    s=base.replace('集群标准版','集群专业版')
    s=s.replace('17 节点','29 节点')
    s=s.replace('3 台数据库共置节点（MongoDB 副本集 + MySQL MGR + Router）、3 台 Redis Master/Slave + Sentinel、4 台中间件共置节点（MinIO + File + Kafka + ES，每节点单节点 docker swarm 部署）、2 台 Flink 节点（K8s Worker · Flink 专属）',
                '3 台 MySQL MGR + Router、3 台 MongoDB 副本集、3 台 Redis + Sentinel、3 台 Kafka、3 台 Elasticsearch、4 台 MinIO + File（各组件独立部署，每节点单节点 docker swarm）、3 台 Flink 节点')
    s=s.replace('K8s 3 节点 → 数据库 3 节点 + Redis 3 节点 + 中间件 4 节点 + Flink 2 节点','K8s 5 节点 → MySQL 3 + MongoDB 3 + Redis 3 + Kafka 3 + ES 3 + 对象存储 4 + Flink 3 节点')
    s=s.replace('K8s 3 Master','K8s 3 Master + 2 Worker')
    s=remap_pro(s)
    out=s
elif tier=='proB':
    s=base.replace('集群标准版','集群专业版')
    s=s.replace('17 节点','29 节点')
    s=s.replace('3 台数据库共置节点（MongoDB 副本集 + MySQL MGR + Router）、3 台 Redis Master/Slave + Sentinel、4 台中间件共置节点（MinIO + File + Kafka + ES，每节点单节点 docker swarm 部署）、2 台 Flink 节点（K8s Worker · Flink 专属）',
                '3 台 MySQL MGR + Router、3 台 MongoDB 副本集、3 台 Redis + Sentinel、3 台 Kafka、3 台 Elasticsearch、4 台 MinIO + File（各组件独立部署，每节点单节点 docker swarm）、3 台 Flink 节点')
    s=s.replace('K8s 3 节点 → 数据库 3 节点 + Redis 3 节点 + 中间件 4 节点 + Flink 2 节点','K8s 5 节点 → MySQL 3 + MongoDB 3 + Redis 3 + Kafka 3 + ES 3 + 对象存储 4 + Flink 3 节点')
    s=s.replace('K8s 3 Master','K8s 3 Master + 2 Worker')
    s=remap_pro(s)
    out=to_scene_B(s,'集群专业版')
elif tier=='lite':
    s=base.replace('集群标准版','集群精简版')
    # 文件名去场景(精简版部署/运维无场景)
    s=s.replace('HAP部署实施文档_集群精简版_场景A.docx','HAP部署实施文档_集群精简版.docx')
    s=s.replace('HAP运维文档_集群精简版_场景A.docx','HAP运维文档_集群精简版.docx')
    s=s.replace('集群精简版_场景A_架构图','集群精简版_架构图').replace('集群精简版_场景A_凭据登记表','集群精简版_凭据登记表')
    s=s.replace('架构图（场景 A · 矢量版）','架构图（矢量版）').replace('架构图（场景 A · 位图版）','架构图（位图版）').replace('凭据登记表（场景 A · ','凭据登记表（')
    s=s.replace('Sheet 1（凭据登记表）：28 条记录','Sheet 1（凭据登记表）：23 条记录')
    s=s.replace('部署实施文档（集群精简版 · 场景 A）','部署实施文档（集群精简版）')
    s=s.replace('运维文档（集群精简版 · 场景 A）','运维文档（集群精简版）')
    s=s.replace('（集群精简版 · 场景 A）','（集群精简版）').replace(' · 场景 A','')
    s=s.replace('17 节点','6 节点')
    s=s.replace('（场景 A · 未开启 Docker Swarm 集群）','（单节点架构）').replace('场景 A · 未开启 Docker Swarm 集群','单节点架构').replace('场景 A','')
    s=s.replace('2 台 Nginx + Keepalived、3 台 K8s Master+Node、3 台数据库共置节点（MongoDB 副本集 + MySQL MGR + Router）、3 台 Redis Master/Slave + Sentinel、4 台中间件共置节点（MinIO + File + Kafka + ES，每节点单节点 docker swarm 部署）、2 台 Flink 节点（K8s Worker · Flink 专属）',
                '1 台 Nginx（无 VIP）、2 台 K8s（1 主 1 从）、1 台数据库节点（MySQL + MongoDB + Redis 单实例共置）、1 台中间件节点（Kafka + ES + MinIO + File 单实例共置）、1 台 Flink 节点')
    s=s.replace('上游 LB 192.168.1.10 → Keepalived VIP 192.168.1.20 → 2 台 Nginx → K8s 3 节点 → 数据库 3 节点 + Redis 3 节点 + 中间件 4 节点 + Flink 2 节点',
                'Nginx 192.168.1.20（单节点）→ K8s 2 节点 → 数据库节点 192.168.1.31（MySQL/MongoDB/Redis 单实例）+ 中间件节点 192.168.1.51（Kafka/ES/MinIO/File 单实例）+ Flink 192.168.1.30')
    out=s
else: sys.exit('tier 必须是 stdA|stdB|proA|proB|lite')
__op=os.path.join(_OUT,'chk_%s.md'%tier); open(__op,'w',encoding='utf-8').write(out); print('OUT:'+__op)
# 校验
import re as _r
leak=(['盘符路径'] if _r.search(r'[A-Za-z]:[\\/]私有',out) else [])
print('chk_%s.md'%tier,'| 泄露:',leak if leak else '无','| 字符',len(out))
