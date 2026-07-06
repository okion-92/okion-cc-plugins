# 文档说明

本文档面向 HAP 私有部署集群精简版（6 节点 · 单节点共置）生产/测试环境的日常运维工程师与系统管理员，覆盖单节点架构下的常用命令、组件维护、数据备份与还原、数据清理、版本升级、资源监控、安全管理与故障排查。集群精简版所有存储组件均为**单节点**（MongoDB 无副本集、MySQL 单实例直连 3306、Redis 无哨兵、Kafka / ES / MinIO / File 各单实例），K8s 为 1 主 1 从。**精简版不区分场景 A / B。**

> **⚠️ 高危操作提示**：本文档涉及**数据删除、数据还原、版本升级**等高危操作。执行任何删除 / 还原类操作前，强烈建议先咨询 HAP 官方技术支持，或先在**完整组件集群层面做好快照备份**（虚拟机 / 存储快照 + 各组件数据备份，参见第四章），确认可回滚后再执行；生产变更须在变更窗口内进行。**精简版存储层为单点，无副本 / 主从 / 哨兵冗余，任一组件故障即不可用，备份尤为关键。**

## 适用架构

本文档对应集群精简版，最小拓扑 6 节点：1 台 Nginx（192.168.1.20，单节点无 VIP）、2 台 K8s（192.168.1.21 Master+Node / 192.168.1.22 Worker，已移除 Master 污点）+ Istio、1 台数据库节点（192.168.1.31，单机共置 MySQL + MongoDB + Redis）、1 台中间件节点（192.168.1.51，单机共置 Kafka + ZooKeeper + Elasticsearch + MinIO + File）、1 台 Flink 节点（192.168.1.30）。详细部署步骤请参阅《HAP部署实施文档（集群精简版）》。

```text
运维原则
所有操作必须先备份配置 → 灰度执行 → 校验影响 → 留档说明。
生产变更必须在变更窗口内执行；紧急变更需事后补登。
组件版本不可越级升级；如涉及多版本跨度，请按发版顺序逐版升级。
精简版存储层为单节点（无副本集 / 主从 / 哨兵）：任何变更前必须完整备份，必要时停服窗口内操作；单节点故障会导致对应组件不可用。
数据库节点单机共置 MySQL + MongoDB + Redis，中间件节点单机共置 Kafka + ES + MinIO + File；同一节点上的组件会相互影响，变更需评估整机影响。
```

# 一、组件维护信息

## 1.1 数据库节点（192.168.1.31，单机共置）

| 组件 | 节点（IP） | 端口 | 安装路径 | 数据目录 | 日志目录 |
| --- | --- | --- | --- | --- | --- |
| MySQL（单实例） | 192.168.1.31 | 3306 | /usr/local/mysql | /data/mysql | /data/logs/mysql |
| MongoDB（单实例） | 192.168.1.31 | 27017 | /usr/local/mongodb | /data/mongodb | /data/logs/mongodb |
| Redis（单实例） | 192.168.1.31 | 6379 | /usr/local/redis | /data/redis | /usr/local/redis/redis.log |

注：MySQL 单实例直连 3306（无 Router / MGR）；MongoDB 单实例无副本集、无 keyFile；Redis 单实例无哨兵。MySQL 配置 /etc/my.cnf；MongoDB systemd /etc/systemd/system/mongodb.service；Redis 配置 /usr/local/redis/redis.conf。

## 1.2 中间件节点（192.168.1.51，单机共置）

| 组件 | 节点（IP） | 端口 | 安装路径 | 数据目录 |
| --- | --- | --- | --- | --- |
| Kafka + ZooKeeper（单实例） | 192.168.1.51 | 9092 / 2181 | /usr/local/kafka | /data/kafka |
| Elasticsearch（单节点） | 192.168.1.51 | 9200 / 9300 | /usr/local/elasticsearch | /data/elasticsearch |
| MinIO（单实例） | 192.168.1.51 | 9011 | 单节点 docker swarm | /data/minio/volume |
| File（单实例） | 192.168.1.51 | 9000 | 单节点 docker swarm | /data/file/volume |

注：Kafka 单 broker（replication.factor=1）；ES 单节点（discovery.type=single-node，传输层 SSL 关闭）；MinIO 单实例对外 9011（容器内 9000）；File 单实例对外 9000。Kafka 配置 /usr/local/kafka/config/server.properties + zookeeper.properties；ES 配置 /usr/local/elasticsearch/config/elasticsearch.yml；MinIO + File 配置 /usr/local/minio/minio.yaml + /usr/local/MDPrivateDeployment/clusterMode/file.yaml。

## 1.3 微服务节点（K8s）

| 组件 | 节点（IP） | 角色 | 说明 |
| --- | --- | --- | --- |
| K8s Master 01 | 192.168.1.21 | Master + Worker | kubeadm 引导节点；**已移除 Master 污点**让 Pod 调度到 Master；管理器入口 38881 |
| K8s Worker 02 | 192.168.1.22 | Worker | 通过 kubeadm join 加入 |
| Istio | 由 K8s 2 节点承载 | istio-system 命名空间 | 版本 1.29.1，sidecar 自动注入 default 命名空间 |
| HAP 微服务 | 由 K8s 2 节点承载 | default 命名空间 | mingdaoyun-hap 镜像，副本数按 lite 档位 |
| Flink | 192.168.1.30 | Flink 专属节点 | JobManager × 1 + TaskManager，flink 命名空间 |

> 注：精简版 K8s 为单 Master，Master 宕机时 kubectl 暂不可用，但已运行的业务容器不受影响；恢复 Master 后 kubectl 即恢复。

## 1.4 Nginx 节点

| 组件 | 节点（IP） | 端口 | 安装路径 | 说明 |
| --- | --- | --- | --- | --- |
| Nginx（单节点） | 192.168.1.20 | 80 | /usr/local/nginx | 单节点，无 Keepalived / VIP；upstream 指向 K8s 2 节点 www 8880 |

注：精简版 Nginx 为单节点，无 VIP 漂移；Nginx 故障即入口不可用，建议配合外部健康检查/重启守护。

# 二、常用命令

## 2.1 K8s 集群管理（K8s Master 192.168.1.21）

```text
# 节点状态
kubectl get node -o wide
kubectl get pod -A -o wide

# 资源使用情况
kubectl top node
kubectl top pod -A

# 查看 Pod 详细
kubectl describe pod <pod-name> -n default
kubectl logs <pod-name> -n default --tail 200 -f

# 进入容器
kubectl exec -it <pod-name> -n default -- /bin/bash

# 重启某 Deployment
kubectl rollout restart deployment <deployment-name> -n default
kubectl rollout status deployment <deployment-name> -n default

# 扩缩容
kubectl scale deployment <deployment-name> -n default --replicas=<n>
```

## 2.2 HAP 微服务启停（K8s Master）

```text
cd /data/mingdao/script/kubernetes/

# 启动 / 停止 / 重启
bash start.sh
bash stop.sh
bash restart.sh

# 查看 Pod 状态
kubectl get pod -o wide -w

# 一键查看微服务版本
kubectl get cm env-list -o jsonpath='{.data.ENV_APP_VERSION}'
```

## 2.3 MinIO + File 容器管理（中间件节点 192.168.1.51 · 单节点 docker swarm）

```text
# 精简版 MinIO / File 以单节点 docker swarm 方式运行在中间件节点（192.168.1.51）

# 查看 stack 与服务状态
docker stack ls
docker stack ps minio
docker stack ps file

# 启动
docker stack deploy -c /usr/local/minio/minio.yaml minio --detach=false
docker stack deploy -c /usr/local/MDPrivateDeployment/clusterMode/file.yaml file --detach=false
# 或直接调用部署脚本
bash /usr/local/minio/start.sh
bash /usr/local/MDPrivateDeployment/clusterMode/start.sh

# 停止
docker stack rm minio
docker stack rm file

# 查看容器日志
docker ps -a | grep -E 'minio|file'
docker logs -f --tail 200 <container-id>
```

## 2.4 数据库连接（数据库节点 192.168.1.31）

```text
# MySQL（单实例直连 3306，无 Router）
mysql -h 192.168.1.31 -P 3306 -u root -p<强密码>

# MongoDB（单实例，无副本集；URI 不带 replicaSet 参数）
/usr/local/mongodb/bin/mongo -u root -p <强密码> --authenticationDatabase admin --port 27017
# 连接具体库示例
/usr/local/mongodb/bin/mongo mongodb://root:<强密码>@192.168.1.31:27017/mdservicedata?authSource=admin

# Redis（单实例，无哨兵）
/usr/local/redis/bin/redis-cli -h 192.168.1.31 -a <强密码> -p 6379
/usr/local/redis/bin/redis-cli -a <强密码> info replication
```

## 2.5 ES / Kafka / MinIO 健康检查（中间件节点 192.168.1.51）

```text
# ES 单节点健康（单节点副本为 0，status 为 yellow 属正常）
curl -u elastic:<强密码> 127.0.0.1:9200/_cat/health?v
curl -u elastic:<强密码> 127.0.0.1:9200/_cat/indices?v

# Kafka topic 列表
/usr/local/kafka/bin/kafka-topics.sh --bootstrap-server 127.0.0.1:9092 --list
/usr/local/kafka/bin/kafka-topics.sh --bootstrap-server 127.0.0.1:9092 --describe --topic <topic>

# MinIO 信息（进入容器执行 mc）
docker exec -it $(docker ps | grep minio | awk 'NR==1{print $1}') mc admin info local
```

## 2.6 数据库启停命令（数据库节点 192.168.1.31）

```text
# === MySQL（单实例）===
systemctl status mysql
systemctl start mysql
systemctl stop mysql
systemctl restart mysql

# === MongoDB（单实例）===
systemctl status mongodb
systemctl start mongodb
systemctl stop mongodb
systemctl restart mongodb

# === Redis（单实例）===
systemctl status redis
systemctl start redis
systemctl stop redis
systemctl restart redis
```

## 2.7 中间件启停命令（中间件节点 192.168.1.51）

```text
# === Kafka + ZooKeeper（启动顺序：先 ZooKeeper 后 Kafka；停止相反）===
systemctl status zookeeper
systemctl start zookeeper
systemctl status kafka
systemctl start kafka
systemctl stop kafka
systemctl stop zookeeper

# === Elasticsearch（单节点）===
systemctl status elasticsearch
systemctl start elasticsearch
systemctl stop elasticsearch
systemctl restart elasticsearch

# === MinIO + File ===
# 参见 2.3 节，使用 docker stack deploy / docker stack rm
```

# 三、数据存储介绍

集群精简版数据集中在数据库节点与中间件节点：

| 数据类型 | 存储节点 | 物理路径 | 说明 |
| --- | --- | --- | --- |
| MongoDB 数据 | 192.168.1.31 | /data/mongodb | 业务库（mdwsrows / mdworksheet / mdservicedata 等数十个库）；单实例 |
| MongoDB 日志 | 192.168.1.31 | /data/logs/mongodb/mongodb.log | 组件运行日志 |
| MySQL 数据 | 192.168.1.31 | /data/mysql | binlog + ibdata；单实例直连 3306 |
| MySQL binlog | 192.168.1.31 | /data/mysql/mysql-bin.* | binlog_expire_logs_seconds 控制保留期 |
| Redis 数据 | 192.168.1.31 | /data/redis/dump.rdb | 快照 RDB；单实例 |
| Kafka topic 数据 | 192.168.1.51 | /data/kafka/kafka-logs | replication.factor=1（单 broker），retention 168 小时 |
| Zookeeper 数据 | 192.168.1.51 | /data/kafka/zookeeper | Kafka 元数据 + myid |
| Elasticsearch 索引 | 192.168.1.51 | /data/elasticsearch/data | 单节点；discovery.type=single-node |
| MinIO 对象数据 | 192.168.1.51 | /data/minio/volume | 单实例；桶 mdmedia / mdpic / mdpub / mdoc |
| File 缓存与临时 | 192.168.1.51 | /data/file/volume/{cache,fetchtmp,multitmp,tmp} | 附件缩略图 / 转码临时数据 |
| HAP 微服务配置 | K8s 01（192.168.1.21） | /data/mingdao/script/kubernetes/ | service.yaml / config.yaml / start/stop 脚本 |
| etcd 数据（K8s） | 192.168.1.21 | /data/etcd | K8s 元数据（单 Master） |
| containerd 镜像 | 192.168.1.21 / 192.168.1.22 | /data/containerd | 镜像缓存 |
| Nginx 配置 + 日志 | 192.168.1.20 | /usr/local/nginx + /data/logs/weblogs | 配置文件、access/error 日志 |

# 四、数据备份

```text
备份原则
精简版为单节点，无 SECONDARY / Slave 可用于分流备份，备份直接在数据库 / 中间件节点本机执行，建议安排在业务低峰期（每天 03:00–05:00）。
备份产物建议加密上传到独立的备份服务器或对象存储，至少保留 30 天。
单点架构强烈建议在变更/升级前额外做一次完整组件级快照（VM/存储快照）。
```

## 4.1 MongoDB 备份（数据库节点 192.168.1.31）

```text
mkdir -p /data/backup/mongo/$(date +%F)
# 单库备份
/usr/local/mongodb/bin/mongodump \
  --uri "mongodb://root:<强密码>@192.168.1.31:27017/?authSource=admin" \
  --gzip --out /data/backup/mongo/$(date +%F)/
# 全量备份（所有库归档）
/usr/local/mongodb/bin/mongodump \
  --uri "mongodb://root:<强密码>@192.168.1.31:27017/?authSource=admin" \
  --gzip --archive=/data/backup/mongo/full-$(date +%F).gz
```

## 4.2 MySQL 备份（数据库节点 192.168.1.31）

```text
mkdir -p /data/backup/mysql/$(date +%F)
mysqldump -h 192.168.1.31 -P 3306 -u root -p<强密码> \
  --all-databases --routines --triggers --events --single-transaction \
  --set-gtid-purged=OFF \
  | gzip > /data/backup/mysql/$(date +%F)/full-$(date +%F).sql.gz
```

## 4.3 Redis 备份（数据库节点 192.168.1.31）

```text
mkdir -p /data/backup/redis/$(date +%F)
# 触发存盘
/usr/local/redis/bin/redis-cli -a <强密码> -p 6379 BGSAVE
# 复制 RDB
cp /data/redis/dump.rdb /data/backup/redis/$(date +%F)/dump-$(date +%F).rdb
```

## 4.4 MinIO 文件备份（中间件节点 192.168.1.51）

```text
# 配置 mc alias 指向本机 MinIO（9011）
mc alias set hap-minio http://192.168.1.51:9011 mingdao <强密码>
# 镜像备份到独立备份位置（建议异地）
mc mirror --overwrite hap-minio/mdmedia  /data/backup/minio/$(date +%F)/mdmedia/
mc mirror --overwrite hap-minio/mdpic    /data/backup/minio/$(date +%F)/mdpic/
mc mirror --overwrite hap-minio/mdpub    /data/backup/minio/$(date +%F)/mdpub/
mc mirror --overwrite hap-minio/mdoc     /data/backup/minio/$(date +%F)/mdoc/
```

## 4.5 ES 快照备份（可选，建议）

```text
# 1. elasticsearch.yml 增加 path.repo: ["/data/elasticsearch/snapshots"] 并重启
# 2. 注册仓库
curl -u elastic:<强密码> -XPUT "http://127.0.0.1:9200/_snapshot/hap-backup" -H 'Content-Type: application/json' -d '
{ "type": "fs", "settings": { "location": "/data/elasticsearch/snapshots" } }'
# 3. 创建快照
curl -u elastic:<强密码> -XPUT "http://127.0.0.1:9200/_snapshot/hap-backup/snapshot_$(date +%F)?wait_for_completion=true"
```

## 4.6 K8s ConfigMap 与微服务配置备份（K8s 01）

```text
mkdir -p /data/backup/k8s/$(date +%F)
cp -r /data/mingdao/script/kubernetes/ /data/backup/k8s/$(date +%F)/
kubectl get cm -A -o yaml > /data/backup/k8s/$(date +%F)/configmaps.yaml
kubectl get secret -A -o yaml > /data/backup/k8s/$(date +%F)/secrets.yaml
cp /etc/kubernetes/admin.conf /data/backup/k8s/$(date +%F)/admin.conf
# etcd 快照（单 Master）
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /data/backup/k8s/$(date +%F)/etcd-$(date +%F).db
```

# 五、数据还原

```text
还原顺序
1. 先停止微服务（kubectl scale deployment --all -n default --replicas=0），避免数据双写。
2. 单节点直接还原对应组件数据。
3. MinIO 还原后须验证桶可读写。
4. 启动微服务并校验功能。
```

## 5.1 MongoDB 还原（单实例）

```text
# 1. 停止微服务后，在数据库节点还原
/usr/local/mongodb/bin/mongorestore \
  --uri "mongodb://root:<强密码>@192.168.1.31:27017/?authSource=admin" \
  --gzip --archive=/data/backup/mongo/full-<日期>.gz --drop
# 2. 验证
/usr/local/mongodb/bin/mongo -u root -p <强密码> --authenticationDatabase admin --eval "db.adminCommand('listDatabases')"
```

## 5.2 MySQL 还原（单实例）

```text
# 在数据库节点导入备份
gunzip < /data/backup/mysql/<日期>/full-<日期>.sql.gz | mysql -h 192.168.1.31 -P 3306 -u root -p<强密码>
# 验证
mysql -h 192.168.1.31 -P 3306 -u root -p<强密码> -e "SHOW DATABASES;"
```

## 5.3 Redis 还原（单实例）

```text
# 1. 停止 redis
systemctl stop redis
# 2. 覆盖 RDB
cp /data/backup/redis/<日期>/dump-<日期>.rdb /data/redis/dump.rdb
chown redis:redis /data/redis/dump.rdb
# 3. 启动并验证
systemctl start redis
/usr/local/redis/bin/redis-cli -a <强密码> -p 6379 DBSIZE
```

## 5.4 MinIO 文件还原（中间件节点 192.168.1.51）

```text
mc alias set hap-minio http://192.168.1.51:9011 mingdao <强密码>
mc mirror --overwrite /data/backup/minio/<日期>/mdmedia/  hap-minio/mdmedia
mc mirror --overwrite /data/backup/minio/<日期>/mdpic/    hap-minio/mdpic
mc mirror --overwrite /data/backup/minio/<日期>/mdpub/    hap-minio/mdpub
mc mirror --overwrite /data/backup/minio/<日期>/mdoc/     hap-minio/mdoc
mc ls --recursive hap-minio/mdmedia | head -10
```

## 5.5 ES 快照还原

```text
# 1. 停 HAP 微服务
kubectl scale deployment --all -n default --replicas=0
# 2. 删除当前索引（慎用）
curl -u elastic:<强密码> -XDELETE "http://127.0.0.1:9200/<index-name>"
# 3. 还原快照
curl -u elastic:<强密码> -XPOST "http://127.0.0.1:9200/_snapshot/hap-backup/<snapshot-name>/_restore"
# 4. 验证
curl -u elastic:<强密码> 127.0.0.1:9200/_cat/health?v
```

## 5.6 还原后启动

```text
cd /data/mingdao/script/kubernetes/
bash start.sh
kubectl get pod -o wide -w
# 通过 Nginx 访问验证
curl -I http://192.168.1.20/
```

# 六、数据清理

## 6.1 Nginx 日志清理（Nginx 节点 192.168.1.20）

```text
cat > /usr/local/logrotate-config/nginx <<'EOF'
/data/logs/weblogs/*.log {
    daily
    rotate 180
    missingok
    compress
    delaycompress
    olddir /data/logs/weblogs/oldlogs/
    sharedscripts
    postrotate
        if [ -f /usr/local/nginx/logs/nginx.pid ]; then
            /usr/local/nginx/sbin/nginx -s reopen
        fi
    endscript
}
EOF
logrotate -f /usr/local/logrotate-config/nginx
find /data/logs/weblogs/oldlogs -name "*.gz" -mtime +30 -delete
```

## 6.2 MongoDB 历史数据归档（数据库节点 192.168.1.31）

原文链接：

数据管理总览：https://docs-pd.mingdao.com/deployment/docker-compose/standalone/data/

应用行为日志归档：https://docs-pd.mingdao.com/optimize/mongodb/archive/actionlog/

工作表行记录日志归档：https://docs-pd.mingdao.com/optimize/mongodb/archive/worksheetlog/

工作流执行历史归档：https://docs-pd.mingdao.com/optimize/mongodb/archive/workflowlog/

MongoDB 中的"日志类"数据会随业务运行长期累积，可用归档工具 mingdaoyun-archivetools 迁移到独立的归档库。精简版 MongoDB 为单实例，src 连接串为单节点地址（不含 replicaSet 参数）。

```text
注意事项
归档工具会对来源库、目标库及程序所在机器产生资源占用，建议在业务空闲期执行。
精简版 MongoDB 为单实例，src 连接字符串为单节点地址，无 replicaSet 参数。
归档完成后会删除源库已归档数据，但磁盘空间不会立即释放（可参考官方 compact 文档回收）。
工作流执行历史归档涉及业务连续性 — 进行中的流程被归档后将无法继续。
```

config.json 示例（单节点 src，应用行为日志）：

```text
[
  {
    "id": "1",
    "text": "描述",
    "start": "2022-12-31 16:00:00",
    "end": "2023-12-31 16:00:00",
    "src": "mongodb://root:<强密码>@192.168.1.31:27017/mdservicedata?authSource=admin",
    "archive": "mongodb://root:<强密码>@<归档库IP>:27017/mdservicedata_archive_2023?authSource=admin",
    "table": "al_actionlog*",
    "delete": true,
    "batchSize": 500,
    "retentionDays": 0
  }
]
```

启动归档（应用行为日志用 1.0.4，工作表/工作流用 1.0.3）：

```text
docker run -d -it \
  -v $(pwd)/config.json:/usr/local/MDArchiveTools/config.json \
  -v /usr/share/zoneinfo/Etc/GMT-8:/etc/localtime \
  registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-archivetools:1.0.4
```

> 字段说明（id/text/start/end/src/archive/table/delete/batchSize/retentionDays）与时间为 UTC 等细节同集群版，详见上方原文链接。归档后如需立即回收磁盘，单实例可在停服窗口对相应集合执行 compact。

## 6.3 Kafka 数据清理（中间件节点 192.168.1.51）

```text
# 查看 topic retention
/usr/local/kafka/bin/kafka-configs.sh --bootstrap-server 127.0.0.1:9092 --describe --entity-type topics --entity-name <topic>
# 临时调短后再恢复
/usr/local/kafka/bin/kafka-configs.sh --bootstrap-server 127.0.0.1:9092 --alter --entity-type topics --entity-name <topic> --add-config retention.ms=3600000
/usr/local/kafka/bin/kafka-configs.sh --bootstrap-server 127.0.0.1:9092 --alter --entity-type topics --entity-name <topic> --add-config retention.ms=604800000
```

## 6.4 历史镜像清理

```text
# K8s 2 节点（192.168.1.21 / 192.168.1.22）
crictl images
crictl rmi registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hap:<旧版本>
crictl rmi --prune
# 中间件节点（192.168.1.51 · docker）
docker images
docker image prune -af
```

## 6.5 MinIO / File 临时文件清理（中间件节点 192.168.1.51）

```text
find /data/file/volume/cache    -type f -mtime +7  -delete
find /data/file/volume/fetchtmp -type f -mtime +7  -delete
find /data/file/volume/multitmp -type f -mtime +7  -delete
find /data/file/volume/tmp      -type f -mtime +1  -delete
```

# 七、版本升级

```text
升级前必读
升级前请到「版本发布历史」https://docs-pdop.mingdao.com/version 查看当前版本到目标版本之间是否有「含升级附加操作」的版本。
升级前请注意授权密钥中升级服务是否已到期；超期升级会导致密钥失效。
升级前务必完成数据备份（参见第四章）并在测试环境验证通过；单节点架构建议额外做整机快照。
组件版本不可越级升级；多版本跨度按发版顺序逐版升级。
```

## 7.1 HAP 微服务升级

原文链接：https://docs-pd.mingdao.com/deployment/kubernetes/upgrade/hap

```text
# 1. 拉取目标版本镜像（K8s 两节点都执行；离线则导入 tar）
crictl pull registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hap:<目标版本号>
# 2. 在控制节点执行更新
cd /data/mingdao/script/kubernetes/
bash update.sh update hap <目标版本号>
# 3. 等待 3~5 分钟，确认 Pod 正常
kubectl get pod -o wide
```

> 精简版微服务节点内存有限，若不足以滚动更新，可先 `bash stop.sh` 停服再 `bash update.sh update hap <目标版本号>`。

## 7.2 中间件升级

```text
# MinIO / File（中间件节点单节点 swarm）
docker pull registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-minio:<新版本>
docker pull registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-file:<新版本>
sed -ri 's|mingdaoyun-minio:.*|mingdaoyun-minio:<新版本>|g' /usr/local/minio/minio.yaml
sed -ri 's|mingdaoyun-file:.*|mingdaoyun-file:<新版本>|g' /usr/local/MDPrivateDeployment/clusterMode/file.yaml
docker stack deploy -c /usr/local/minio/minio.yaml minio --detach=false
docker stack deploy -c /usr/local/MDPrivateDeployment/clusterMode/file.yaml file --detach=false

# Kafka / ES 单实例升级：stop → 备份数据目录 → 替换二进制 → 保留配置 → start，升级前务必备份
```

## 7.3 数据库升级（单实例）

数据库升级风险高，必须先在测试环境验证；单实例升级期间服务会中断，须在停服窗口执行：

MongoDB / MySQL / Redis 单实例升级通用步骤：stop 服务 → 备份数据目录 → 替换二进制 → 保留配置（my.cnf / mongodb.service / redis.conf）→ start → 验证。MongoDB 大版本升级（如 4.4 → 5.0）须按官方 FCV 流程，建议联系明道云团队评估。

## 7.4 升级回滚

如升级后服务异常：立即停止服务 → 恢复升级前备份（第五章）→ 回滚到升级前镜像 / 二进制 → 启动并验证。ES 跨大版本回滚不被支持，必须从快照恢复；MongoDB FCV 切换后需先还原 FCV 再降级二进制。

# 八、资源监控

## 8.1 关键监控指标

| 节点类型 | 关键指标 | 告警阈值 |
| --- | --- | --- |
| Nginx（1 台） | CPU / 内存 / 5xx 错误率 / 进程存活 | CPU > 70% / 内存 > 80% / 5xx > 1% / nginx 进程异常 |
| K8s（2 台） | CPU / 内存 / Pod Pending / etcd 延迟 | Pod Pending > 5 min / 单 Master 不可用 |
| 数据库节点（1 台，MySQL+MongoDB+Redis） | CPU / 内存 / 磁盘 / 各组件连接数 / 慢查询 | 内存 > 80% / 磁盘 > 80% / 慢查询激增 |
| 中间件节点（1 台，Kafka+ES+MinIO+File） | CPU / 内存 / 磁盘 / ES heap / Kafka 堆积 | 磁盘 > 80% / ES heap > 75% / 消费堆积 |
| Flink（1 台） | JobManager 存活 / job 失败次数 / checkpoint 失败 | job 重启异常 / checkpoint 持续失败 |

## 8.2 Grafana 仪表盘建议

Node Exporter Full（dashboard ID: 1860）— 主机层全部 6 节点。

Kubernetes Cluster Monitoring（dashboard ID: 7249）— K8s 2 节点 + 微服务 Pod。

MySQL（dashboard ID: 7362）/ MongoDB（dashboard ID: 2583）/ Redis（dashboard ID: 763）/ Kafka（dashboard ID: 7589）/ Elasticsearch（dashboard ID: 14191）— 单实例对应面板。

## 8.3 日常巡检清单（每日 08:30）

K8s：kubectl get node 全部 Ready；kubectl get pod -A 全部 Running 且 RESTARTS 无新增。

Nginx：192.168.1.20 上 nginx 进程存活；http://192.168.1.20/ 可访问。

MySQL：mysql 可连接、SHOW DATABASES 正常；慢查询日志无异常激增。

MongoDB：可连接、listDatabases 正常；/data/mongodb 磁盘 < 80%。

Redis：redis-cli ping 返回 PONG；info replication 正常。

Kafka：zookeeper-shell.sh ls /brokers/ids 显示 [0]；无异常堆积。

Elasticsearch：_cat/health 显示 status=green 或 yellow（单节点副本 0 为 yellow 正常）。

MinIO + File：docker stack ps 显示 minio/file 容器 Running；mc admin info 正常。

微服务：HAP 控制台首页可正常访问。

备份：/data/backup 当日目录已生成且大小符合预期。

磁盘：所有节点根分区 < 70%；数据盘 < 80%；超阈值参考第六章清理。

# 九、安全管理

## 9.1 网络访问控制

生产环境必须通过堡垒机统一接入；禁止开放 22 端口到公网。

Nginx 节点（192.168.1.20）开放 80/443；其他所有节点不对公网暴露。

K8s API（6443）、etcd（2379/2380）只在节点之间互通。

数据库节点（MongoDB 27017、MySQL 3306、Redis 6379）仅对微服务子网可达。

Kafka 9092、ES 9200/9300、MinIO 9011、File 9000 仅对微服务子网可达。

精简版 MinIO / File 为单节点 docker swarm（本机自洽），无需在节点间放通 2377/7946/4789。

## 9.2 凭证与密钥管理

数据库 root / hap 用户、Redis requirepass、MinIO MINIO_ROOT_PASSWORD、ES elastic、File ENV_SECRET_KEY_FILE 全部使用强口令；密码字符仅允许 - 或 _ 类特殊字符。

K8s admin.conf 严禁留在非 Master 节点；管理器入口 38881 不对公网暴露，管理员密码定期轮换。

## 9.3 产品与组件漏洞修复

关注 https://docs-pdop.mingdao.com 与 https://docs-pd.mingdao.com 的安全公告。

每季度对底层 OS 与依赖（OpenSSL、glibc、kernel）执行漏扫并按计划升级。

对暴露给互联网的 Nginx 入口启用 WAF。

# 十、故障排查

## 10.1 微服务 Pod 持续 CrashLoopBackOff

```text
kubectl describe pod <pod-name> -n default
kubectl logs <pod-name> -n default --previous --tail 200

# 常见原因（精简版连接口径）：
# 1. ConfigMap env-list 中 MySQL 连接应为 192.168.1.31:3306（单实例直连，无 Router 6446）
# 2. MongoDB 连接串为单节点地址，不含 ?replicaSet=（精简版无副本集）
# 3. Redis 为单实例（ENV_REDIS_HOST/PORT/PASSWORD），非哨兵参数
```

## 10.2 MongoDB 无法启动 / 数据异常（单实例）

```text
# 查看日志
tail -n 200 /data/logs/mongodb/mongodb.log
systemctl status mongodb

# 1. 端口被占 / 配置错误：检查 27017、mongodb.service 的 --dbpath/--port
# 2. 数据损坏：停服 → 用第五章备份还原（单实例无副本可自愈，依赖备份）
# 3. 磁盘满：df -h /data/mongodb，清理或扩容
```

## 10.3 MySQL 无法启动 / 连接失败（单实例）

```text
tail -n 200 /data/logs/mysql/mysqld.log
systemctl status mysql

# 1. 连接失败：确认 3306 端口、root 密码、host='%' 授权
# 2. 数据损坏：停服 → 第五章备份还原
# 3. 磁盘/ibdata 异常：df -h /data/mysql；必要时 innodb_force_recovery 谨慎拉起后导出
```

## 10.4 Redis 连接报错（单实例）

```text
/usr/local/redis/bin/redis-cli -a <强密码> -p 6379 ping
# 1. 鉴权失败：核对 requirepass 与微服务 ENV_REDIS_PASSWORD 一致
# 2. 内存超限：info memory，maxmemory / maxmemory-policy（默认 allkeys-lru）
# 3. 持久化失败：检查 /data/redis 磁盘空间与 dump.rdb 权限
```

## 10.5 Kafka 异常（单 broker）

```text
systemctl status kafka zookeeper
/usr/local/kafka/bin/zookeeper-shell.sh 127.0.0.1:2181 ls /brokers/ids   # 应显示 [0]
# 1. 元数据损坏：备份后重命名 /data/kafka/kafka-logs 与 zookeeper 目录再重启
# 2. 磁盘满：df -h /data/kafka，清理 retention 或扩容
```

## 10.6 Elasticsearch 异常（单节点）

```text
curl -u elastic:<强密码> 127.0.0.1:9200/_cat/health?v
# 单节点副本为 0，status=yellow 属正常；status=red 表示主分片不可用
# 1. 磁盘超 watermark（默认 90%）：清理或扩容 /data/elasticsearch
# 2. heap 不足：调整 jvm.options
# 3. 数据损坏：停服 → 第五章快照还原
```

## 10.7 MinIO / File 服务异常（中间件节点 192.168.1.51）

```text
systemctl status docker
docker stack ps minio
docker stack ps file
# 重启服务
bash /usr/local/minio/start.sh
bash /usr/local/MDPrivateDeployment/clusterMode/start.sh
# MinIO 自动愈合
docker exec -it $(docker ps | grep minio | awk 'NR==1{print $1}') mc admin heal -r local
# 注意：单实例 MinIO 无纠删码冗余，磁盘损坏依赖备份恢复（参见 5.4）
```

## 10.8 K8s 控制平面异常（单 Master）

```text
systemctl status kubelet
journalctl -u kubelet -f
crictl ps -a | grep apiserver
# 单 Master 宕机时 kubectl 暂不可用，但已运行业务容器不受影响；
# 恢复 Master（重启 kubelet / 修复 etcd）后 kubectl 即恢复。
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key endpoint status -w table
```

## 10.9 Nginx 入口不可访问（单节点）

```text
systemctl status nginx
/usr/local/nginx/sbin/nginx -t       # 配置语法检查
# 1. nginx 进程异常：systemctl restart nginx
# 2. upstream（K8s www 8880）不通：kubectl get pod 确认微服务 Running
# 精简版无 VIP / 备机，Nginx 故障即入口中断，建议外部健康检查 + 自动拉起守护。
```
