import os
_HERE=os.path.dirname(os.path.abspath(__file__))
_SRC=os.path.join(_HERE,'mig_src')
_OUT=os.environ.get('HAP_DEPLOY_WORK', os.path.join(_SRC,'_work'))
os.makedirs(_OUT, exist_ok=True)
import re, sys
base=open(os.path.join(_SRC,'mig_base.md'),encoding='utf-8').read()
base=re.sub(r'(?m)^[ \t]+$','',base)

def strip_scene(s):
    for a,b in [('集群标准版（场景 A · 未开启 Docker Swarm 集群）新环境','集群标准版新环境'),
                ('（场景 A · 未开启 Docker Swarm 集群）',''),
                ('场景 A 任一','任一'),('场景 A 默认 ','默认 '),('场景 A 下 ',''),
                ('场景 A 新集群','新集群'),('按场景 A ','按'),('场景 A 拓扑','拓扑'),
                ('场景 A ',''),('场景 A','')]:
        s=s.replace(a,b)
    return s

def remap_pro(s):
    out=[]
    for ln in s.split('\n'):
        def sub(mp): return re.sub(r'192\.168\.1\.(\d+)', lambda m:'192.168.1.'+mp.get(m.group(1),m.group(1)), ln)
        if any(k in ln for k in ['minio','MinIO','mdmedia','mdpic','mdpub','mdoc']):
            out.append(sub({'51':'71','52':'72','53':'73','54':'74'}))
        elif any(k in ln for k in ['Elasticsearch','elasticsearch','9200','ES ','ES清理','ES 清理']):
            out.append(sub({'52':'61','53':'62','54':'63'}))
        elif any(k in ln for k in ['MongoDB','mongo','27017','副本集','primary','PRIMARY']) and 'MySQL' not in ln and '6446' not in ln:
            out.append(sub({'31':'34','32':'35','33':'36'}))
        else:
            out.append(ln)
    return '\n'.join(out)

tier=sys.argv[1]
if tier=='std':
    out=strip_scene(base)
elif tier=='pro':
    s=strip_scene(base).replace('集群标准版','集群专业版')
    s=remap_pro(s)
    out=s
elif tier=='lite':
    s=strip_scene(base).replace('集群标准版','集群精简版')
    # 单节点目标：MySQL 6446->3306 直连；MinIO 单节点 .51；MongoDB 单节点；Redis 收敛到 .31；ES 收敛到 .51
    s=s.replace('-P 6446','-P 3306')
    s=re.sub(r'MySQL 采用 MGR[^。]*。','MySQL 为单实例，下列 MySQL 还原命令直连 3306。', s)
    s=s.replace('（MGR Router 端口 6446）','（单实例直连 3306）').replace('MGR Router 端口 6446','单实例直连 3306')
    s=s.replace('MySQL MGR Primary 节点（默认 192.168.1.31）','MySQL 单实例节点（默认 192.168.1.31）')
    s=s.replace('MongoDB Primary 节点（默认 192.168.1.31）','MongoDB 单实例节点（默认 192.168.1.31）')
    s=s.replace('MongoDB primary 节点','MongoDB 单实例节点').replace('MongoDB Primary 节点','MongoDB 单实例节点')
    # MinIO 单节点
    s=s.replace('任一中间件节点（192.168.1.51 ~ 192.168.1.54 均可），端口为 9011-9014（.51→9011 / .52→9012 / .53→9013 / .54→9014）',
                '中间件单节点（192.168.1.51），端口 9011')
    s=s.replace('192.168.1.51 ~ 192.168.1.54','192.168.1.51')
    # Redis 哨兵 -> 单实例(收敛到数据库节点 .31)
    s=s.replace('采用 Redis 哨兵模式部署（192.168.1.41 / 192.168.1.42 / 192.168.1.43）','采用 Redis 单实例部署（192.168.1.31）')
    s=s.replace('192.168.1.41 / 192.168.1.42 / 192.168.1.43','192.168.1.31')
    # ES 单节点(收敛到 .51)
    s=s.replace('192.168.1.52-192.168.1.54 任一','192.168.1.51')
    s=s.replace('192.168.1.52-192.168.1.54','192.168.1.51')
    out=s
__op=os.path.join(_OUT,'mig_%s.md'%tier); open(__op,'w',encoding='utf-8').write(out); print('OUT:'+__op)
bad=sorted(set(re.findall(r'10\.8\.\d+',out)))
print('mig_%s.md'%tier,'| 场景残留:', '场景 A' in out,'| 示例外IP:',bad if bad else '无')
if tier=='pro': print('  MinIO .71:', '192.168.1.71' in out, '| MongoDB主 .34:', '192.168.1.34' in out, '| MySQL 6446 .31保留:', '6446' in out and '192.168.1.31' in out)
if tier=='lite': print('  MySQL 3306:', '-P 3306' in out, '| 无6446:', '6446' not in out, '| MinIO单节点 .51:', '192.168.1.51' in out)
