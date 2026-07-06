import os
_HERE=os.path.dirname(os.path.abspath(__file__))
_SRC=os.path.join(_HERE,'deploy_src')
_OUT=os.environ.get('HAP_DEPLOY_WORK', os.path.join(_SRC,'_work'))
os.makedirs(_OUT, exist_ok=True)
# 生成集群精简版部署实施文档 markdown(6节点·单节点·不分A/B·每组件H1)
HAP_DBS = ["MDLicense","ClientLicense","commonbase","MDAlert","mdapproles","mdapprove","mdapps",
"mdattachment","mdcalendar","mdcategory","MDChatTop","mdcheck","mddossier","mdemail","mdform",
"MDGroup","mdgroups","MDHistory","mdIdentification","mdinbox","mdkc","mdmap","mdmobileaddress",
"MDNotification","mdpost","mdreportdata","mdroles","mdsearch","mdservicedata","mdsms","MDSso",
"mdtag","mdtransfer","MDUser","mdworkflow","mdworksheet","mdworkweixin","mdwsrows","pushlog",
"taskcenter","mdintegration","mdactionlog","mdworksheetlog","mdworksheetsearch","mddatapipeline",
"mdwfplugin","mdpayment","mdwfai","mdopenauth","mdaisearch"]
mongo=['use admin','db.createUser({user:"root",pwd:"<强密码>",roles:[{role:"root",db:"admin"}]})']
for db in HAP_DBS:
    mongo.append('use %s'%db); mongo.append('db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"%s"}]})'%db)
MONGO="\n".join(mongo)

REDIS='''bind 0.0.0.0
protected-mode yes
port 6379
tcp-backlog 511
timeout 0
tcp-keepalive 300
daemonize no
supervised no
pidfile /usr/local/redis/redis.pid
loglevel notice
logfile /usr/local/redis/redis.log
databases 16
save 900 1
save 300 10
save 60 100000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /data/redis
slave-serve-stale-data yes
slave-read-only yes
repl-diskless-sync no
repl-diskless-sync-delay 5
repl-disable-tcp-nodelay no
slave-priority 100
lua-time-limit 5000
slowlog-log-slower-than 10000
slowlog-max-len 128
latency-monitor-threshold 0
notify-keyspace-events ""
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
list-compress-depth 0
set-max-intset-entries 512
zset-max-ziplist-entries 128
zset-max-ziplist-value 64
hll-sparse-max-bytes 3000
activerehashing yes
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit slave 256mb 64mb 60
client-output-buffer-limit pubsub 0 0 0
hz 10
requirepass <强密码>
masterauth <强密码>
maxmemory 6gb
maxmemory-policy allkeys-lru
maxclients 100000
rename-command KEYS ""'''

KAFKA_SP='''broker.id=0
listeners=PLAINTEXT://0.0.0.0:9092
advertised.listeners=PLAINTEXT://192.168.1.51:9092
num.network.threads=3
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600
log.dirs=/data/kafka/kafka-logs/
num.partitions=10
num.recovery.threads.per.data.dir=1
offsets.topic.replication.factor=1
transaction.state.log.replication.factor=1
transaction.state.log.min.isr=1
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000
zookeeper.connect=127.0.0.1:2181
zookeeper.connection.timeout.ms=6000
group.initial.rebalance.delay.ms=0
message.max.bytes=10485760
replica.fetch.max.bytes=10485760'''

ES_YML='''cluster.name: md-elasticsearch-private
node.name: elasticsearch-1
node.roles: [master,data]
network.host: 0.0.0.0
http.port: 9200
transport.port: 9300
path.data: /data/elasticsearch/data
path.logs: /data/elasticsearch/logs
ingest.geoip.downloader.enabled: false
xpack.security.enabled: true
xpack.security.http.ssl.enabled: false
xpack.security.transport.ssl.enabled: false
cluster.max_shards_per_node: 20000
discovery.type: single-node'''

D = '''# 文档说明

本文档为 HAP（明道云 超级应用平台）私有化部署 **集群精简版（6 节点 · 单节点共置）** 的部署实施手册。精简版适用于并发 300 以内的中小规模：所有存储组件均为**单节点**（MySQL 单实例直连 3306、MongoDB 无副本集、Redis 无哨兵、Kafka/ES/MinIO/文件服务各单实例），K8s 为 1 主 1 从（需移除 Master 污点让 Pod 调度到 Master）。**精简版不分场景 A/B。**

## 节点 IP 规划（共 6 节点）

| 角色 | 主机名 | IP | 部署组件 |
| --- | --- | --- | --- |
| 负载均衡 | hap-nginx | 192.168.1.20 | Nginx（单节点，无 VIP） |
| 微服务 / K8s Master | hap-k8s-01 | 192.168.1.21 | K8s Master+Node + Istio + 微服务 |
| 微服务 / K8s Worker | hap-k8s-02 | 192.168.1.22 | K8s Node + 微服务 |
| 中间件 | hap-middleware | 192.168.1.51 | Kafka + ZooKeeper + ES + MinIO + File（单机共置） |
| 数据库 | hap-db | 192.168.1.31 | MySQL + MongoDB + Redis（单机共置） |
| 数据同步 | hap-flink | 192.168.1.30 | Flink（HDP 超级数据平台） |

> 访问入口：https://hap.domain.com（端口 443，经 Nginx 192.168.1.20 转发到 K8s 微服务 www 端口 8880）。示例 IP，交付时整体替换。

## 关键端口与版本

| 组件 | 版本 | 关键端口 |
| --- | --- | --- |
| MySQL | 8.0.45 | 3306（单实例直连，无 Router/MGR） |
| MongoDB | 4.4.30 | 27017（单节点，无副本集） |
| Redis | 8.x | 6379（单节点，无哨兵） |
| Kafka | 3.9.1 (JDK 21) | 9092 / ZK 2181（单 broker，replication=1） |
| Elasticsearch | 8.19.8 | 9200 / 9300（discovery.type=single-node） |
| MinIO | RELEASE.2025-04-22 | 9011（容器内 9000，单节点 Swarm） |
| HAP File | 2.1.0 | 9000（容器内 9000，单实例） |
| Kubernetes | 1.35.3 | 6443 / 8880 / 18880 / 38880 / 38881（单 Master + 1 Worker） |
| Istio | 1.29.1 | — |
| HAP 微服务 | 7.3.4 | 8880(www 主地址) / 18880(www 扩展地址，按需启用) / 38880(安装管理器 ENV_CAPTAIN_ENDPOINT) / 38881(管理入口) |
| Flink | 1.19.720 | JobManager 8081 |
| Docker | 28.5.2 | — |
| Nginx | 1.28.2 | 80 / 443 |

# 一、服务器资源清单

集群精简版生产环境最小拓扑（共 6 节点，HDP 节点即 Flink 节点）：

| 角色 | 配置 | 操作系统 | 部署服务 | 数量 |
| --- | --- | --- | --- | --- |
| 负载均衡 | 4C / 8G / 60G 系统盘 + 200G SSD | Debian 12 | Nginx | 1 |
| 微服务 | 16C / 64G / 60G 系统盘 + 200G SSD | Debian 12 | K8s + Istio + HAP 微服务 | 2 |
| 中间件 | 8C / 32G / 60G 系统盘 + 500G SSD | Debian 12 | Kafka + ES + MinIO + File | 1 |
| 数据库 | 8C / 32G / 60G 系统盘 + 300G SSD | Debian 12 | MySQL + MongoDB + Redis | 1 |
| 数据同步 | 8C / 32G / 60G 系统盘 + 200G SSD | Debian 12 | Flink (HDP) | 1 |
| **合计** | — | — | — | **6** |

> 注：精简版数据库节点单机共置 MongoDB/MySQL/Redis，中间件节点单机共置 Kafka/ES/MinIO/文件服务；存储层为单点，无高可用，适合中小规模或测试环境。

## 1.2 网络互通要求

- 所有节点内网二层互通；中间件节点 192.168.1.51 运行单节点 Docker Swarm（MinIO/File），本机自洽，无需跨节点 Swarm 端口。
- K8s 节点（.21/.22）放通 6443、10250、179(Calico)、VXLAN 4789(UDP)、NodePort 1024-32767。
- 微服务节点访问：MySQL 192.168.1.31:3306、MongoDB 27017、Redis 6379、Kafka 192.168.1.51:9092、ES 9200、File 9000。
- 仅 Nginx 192.168.1.20 的 80/443 对外暴露。

# 二、操作系统初始化（所有节点）

> 以下初始化操作在全部节点执行，确保系统环境一致。

## 2.1 关闭防火墙与 SELinux

```bash
systemctl stop nftables firewalld 2>/dev/null
systemctl disable nftables firewalld 2>/dev/null
# CentOS/RHEL 另需：setenforce 0; sed -i 's/^SELINUX=.*/SELINUX=disabled/' /etc/selinux/config
```

## 2.2 关闭 swap

```bash
swapoff -a
sed -i '/ swap / s/^/#/' /etc/fstab
```

## 2.3 内核参数与文件句柄

```bash
cat >> /etc/sysctl.d/99-sysctl.conf <<'EOF'
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-iptables = 1
net.core.somaxconn = 32768
vm.max_map_count = 262144
vm.swappiness = 1
fs.file-max = 1000000
EOF
modprobe br_netfilter
sysctl -p /etc/sysctl.d/99-sysctl.conf
cat >> /etc/security/limits.conf <<'EOF'
* soft nofile 1000000
* hard nofile 1000000
EOF
```

## 2.4 时间同步

```bash
apt-get install -y chrony
systemctl enable --now chrony
ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
```

# 三、Docker 安装（中间件节点 + Nginx 节点）

> 中间件节点（Kafka/ES/MinIO/文件服务以 Swarm 运行）与 Nginx 节点需要 Docker；K8s 微服务节点用 containerd（见第十二章）。

## 3.1 下载并安装 Docker 二进制

```bash
wget https://pdpublic.mingdao.com/private-deployment/offline/common/docker-28.5.2.tgz
tar -zxvf docker-28.5.2.tgz
mv -f docker/* /usr/local/bin/
mkdir -p /etc/docker/
```

## 3.2 配置 daemon.json

```bash
cat > /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": ["https://uvlkeb6d.mirror.aliyuncs.com"],
  "data-root": "/data/docker",
  "max-concurrent-downloads": 10,
  "exec-opts": ["native.cgroupdriver=cgroupfs"],
  "storage-driver": "overlay2",
  "default-address-pools": [{"base": "172.80.0.0/16", "size": 24}],
  "log-driver": "json-file",
  "log-opts": {"max-size": "1g", "max-file": "5"}
}
EOF
```

## 3.3 配置 systemd 并启动

```bash
cat > /etc/systemd/system/docker.service <<'EOF'
[Unit]
Description=Docker
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
ExecStart=/usr/local/bin/dockerd
ExecReload=/bin/kill -s HUP $MAINPID
LimitNOFILE=102400
LimitNPROC=infinity
LimitCORE=0
TimeoutStartSec=0
Delegate=yes
KillMode=process
Restart=on-failure
StartLimitBurst=3
StartLimitInterval=60s

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now docker
docker version
```

# 四、数据库部署 — MongoDB 单节点（数据库节点 192.168.1.31）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/mongodb/4.4/standalone
> 单节点无 --replSet、无 keyFile，端口 27017，启用 --auth。

## 4.1 安装（数据库节点执行）

```bash
# Debian 11/12
wget https://pdpublic.mingdao.com/private-deployment/offline/common/libssl1.1_1.1.1w-0+deb11u1_amd64.deb
dpkg -i libssl1.1_1.1.1w-0+deb11u1_amd64.deb
wget https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-debian10-4.4.30.tgz
tar -zxvf mongodb-linux-x86_64-debian10-4.4.30.tgz
mv mongodb-linux-x86_64-debian10-4.4.30 /usr/local/mongodb
useradd -M -s /sbin/nologin mongodb
mkdir -p /data/mongodb/ /data/logs/mongodb
chown -R mongodb:mongodb /usr/local/mongodb/ /data/mongodb/ /data/logs/mongodb
```

## 4.2 关闭透明大页 THP

```bash
cat > /etc/systemd/system/disable-thp.service <<\\EOF
[Unit]
Description=Disable Transparent Huge Pages (THP)
DefaultDependencies=no
After=sysinit.target local-fs.target
Before=mongodb.service

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo never > /sys/kernel/mm/transparent_hugepage/enabled'
ExecStart=/bin/sh -c 'echo never > /sys/kernel/mm/transparent_hugepage/defrag'

[Install]
WantedBy=basic.target
EOF
systemctl daemon-reload
systemctl enable --now disable-thp
```

## 4.3 systemd 服务（单节点，无 --replSet/--keyFile）

```bash
cat > /etc/systemd/system/mongodb.service <<'EOF'
[Unit]
Description=MongoDB
After=network-online.target
Wants=network-online.target

[Service]
User=mongodb
Group=mongodb
LimitNOFILE=1000000
LimitNPROC=1000000
LimitMEMLOCK=infinity
ExecStart=/usr/local/mongodb/bin/mongod --logpath /data/logs/mongodb/mongodb.log --dbpath /data/mongodb --auth --port 27017 --bind_ip 0.0.0.0
ExecStop=/usr/bin/kill $MAINPID
Restart=on-failure
RestartSec=5
TimeoutStopSec=300

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable mongodb
```

## 4.4 创建业务库用户（数据库节点执行）

先以 `--noauth` 临时启动，创建 root 管理员与全部 HAP 业务库 hap 用户（共 root + @@NDB@@ 个业务库），完成后停止临时实例并正式启动：

```bash
su -c '/usr/local/mongodb/bin/mongod --fork --logpath /data/logs/mongodb/mongodb.log --dbpath /data/mongodb --noauth --port 27017' -s /bin/bash mongodb

/usr/local/mongodb/bin/mongo <<'JS'
@@MONGO@@
JS

kill $(pgrep -f 'mongod')
systemctl start mongodb
```

# 五、数据库部署 — MySQL 单节点（数据库节点 192.168.1.31）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/mysql/mysql-8.0/
> 单实例直连 3306，无 MGR、无 Router。

## 5.1 安装与初始化（数据库节点执行）

```bash
wget https://pdpublic.mingdao.com/private-deployment/offline/common/mysql-8.0.45-linux-glibc2.17-x86_64.tar.xz
tar -xvf mysql-8.0.45-linux-glibc2.17-x86_64.tar.xz
mv mysql-8.0.45-linux-glibc2.17-x86_64 /usr/local/mysql
useradd -U -M -s /sbin/nologin mysql
mkdir -p /data/mysql/ /data/logs/mysql
chown -R mysql:mysql /usr/local/mysql/ /data/mysql/ /data/logs/mysql/
/usr/local/mysql/bin/mysqld --initialize --datadir=/data/mysql/ --user=mysql --log-error=/data/logs/mysql/mysqld.log
```

## 5.2 systemd 服务（参数内联，单实例）

```ini
[Unit]
Description=MySQL Server
Documentation=man:mysqld(8)
After=network.target
After=syslog.target

[Service]
User=mysql
Group=mysql
Type=forking
PIDFile=/usr/local/mysql/mysqld.pid
ExecStart=/usr/local/mysql/bin/mysqld --daemonize --log-error=/data/logs/mysql/mysqld.log --datadir=/data/mysql --socket=/usr/local/mysql/mysql.sock --character-set-server=utf8mb4 --pid-file=/usr/local/mysql/mysqld.pid --server-id=1 --log-bin=mysql-bin --max_connections=2000 --slow_query_log=1 --slow_query_log_file=/data/logs/mysql/mysql-slow.log
LimitNOFILE=102400
Restart=on-failure
PrivateTmp=false

[Install]
WantedBy=multi-user.target
```

## 5.3 启动并设置 root 密码

```bash
systemctl daemon-reload
systemctl enable mysql
systemctl start mysql

/usr/local/mysql/bin/mysql -h127.0.0.1 -uroot -p$(grep 'temporary password' /data/logs/mysql/mysqld.log | awk '{print $NF}')
ALTER USER USER() IDENTIFIED BY '<强密码>';
update mysql.user set host='%' where user='root';
FLUSH PRIVILEGES;
grant all privileges on *.* to 'root'@'%' with grant option;
FLUSH PRIVILEGES;
quit;
```

# 六、数据库部署 — Redis 单节点（数据库节点 192.168.1.31）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/redis/
> 单节点，无哨兵。

## 6.1 安装与内核调优

```bash
wget https://pdpublic.mingdao.com/private-deployment/offline/common/redis-8.6.3-glibc2.17-amd64.tar.gz
tar -zxvf redis-8.6.3-glibc2.17-amd64.tar.gz
mv redis-8.6.3-glibc2.17-amd64 /usr/local/redis
echo 'net.core.somaxconn = 32768' >> /etc/sysctl.d/99-sysctl.conf
echo 'vm.overcommit_memory = 1' >> /etc/sysctl.d/99-sysctl.conf
sysctl -p
mkdir /data/redis
useradd -U -M -s /sbin/nologin redis
chown -R redis:redis /usr/local/redis/ /data/redis
```

## 6.2 redis.conf（官方完整，单节点）

```ini
@@REDIS@@
```

## 6.3 systemd 与启动

```bash
cat > /etc/systemd/system/redis.service <<'EOF'
[Unit]
Description=Redis

[Service]
User=redis
Group=redis
TasksMax=infinity
LimitNOFILE=102400
LimitNPROC=infinity
LimitCORE=0
ExecStart=/usr/local/redis/bin/redis-server /usr/local/redis/redis.conf
ExecStop=/usr/bin/kill $MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now redis
/usr/local/redis/bin/redis-cli -a '<强密码>' ping
```

# 七、中间件部署 — Kafka 单节点（中间件节点 192.168.1.51）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/kafka/
> 单 broker，replication=1，ZooKeeper 本机 127.0.0.1:2181。

## 7.1 安装 JDK 21 与 Kafka

```bash
wget https://pdpublic.mingdao.com/private-deployment/offline/common/OpenJDK21U-jdk_x64_linux_hotspot_21.0.8_9.tar.gz
tar -zxvf OpenJDK21U-jdk_x64_linux_hotspot_21.0.8_9.tar.gz
mv jdk-21.0.8+9 /usr/local/openjdk-21
ln -sf /usr/local/openjdk-21/bin/java /bin/java
wget https://pdpublic.mingdao.com/private-deployment/offline/common/kafka_2.13-3.9.1.tgz
tar -zxvf kafka_2.13-3.9.1.tgz -C /usr/local
mv /usr/local/kafka_2.13-3.9.1/ /usr/local/kafka/
mkdir -p /data/kafka/zookeeper/ /data/kafka/kafka-logs/
sed -i ':a;N;$!ba;s/Xm[xs]1G/Xmx4G/1' /usr/local/kafka/bin/kafka-server-start.sh
sed -i ':a;N;$!ba;s/Xm[xs]1G/Xms4G/1' /usr/local/kafka/bin/kafka-server-start.sh
useradd -M -s /sbin/nologin kafka
chown -R kafka:kafka /usr/local/kafka /data/kafka
```

## 7.2 zookeeper.properties

```properties
admin.enableServer=false
dataDir=/data/kafka/zookeeper/
clientPort=2181
maxClientCnxns=0
```

## 7.3 server.properties（单节点完整）

```properties
@@KAFKA@@
```

## 7.4 systemd 与启动

```bash
cat > /etc/systemd/system/zookeeper.service <<'EOF'
[Unit]
Description=Zookeeper
[Service]
User=kafka
Group=kafka
LimitNOFILE=102400
ExecStart=/usr/local/kafka/bin/zookeeper-server-start.sh /usr/local/kafka/config/zookeeper.properties
ExecStop=/usr/bin/kill $MAINPID
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/kafka.service <<'EOF'
[Unit]
Description=Kafka
After=zookeeper.service
Requires=zookeeper.service
[Service]
User=kafka
Group=kafka
LimitNOFILE=102400
ExecStart=/usr/local/kafka/bin/kafka-server-start.sh /usr/local/kafka/config/server.properties
ExecStop=/usr/bin/kill $MAINPID
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now zookeeper
systemctl enable --now kafka
```

# 八、中间件部署 — Elasticsearch 单节点（中间件节点 192.168.1.51）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/elasticsearch/
> discovery.type=single-node，传输层 SSL 关闭（单节点无需集群证书）。

## 8.1 安装、IK 分词与内核调优

```bash
wget https://pdpublic.mingdao.com/private-deployment/offline/common/elasticsearch-8.19.8-linux-x86_64.tar.gz
wget https://pdpublic.mingdao.com/private-deployment/offline/common/elasticsearch-analysis-ik-8.19.8.zip
tar xf elasticsearch-8.19.8-linux-x86_64.tar.gz
mv elasticsearch-8.19.8 /usr/local/elasticsearch
mkdir /usr/local/elasticsearch/plugins/elasticsearch-analysis-ik
unzip elasticsearch-analysis-ik-8.19.8.zip -d /usr/local/elasticsearch/plugins/elasticsearch-analysis-ik/
echo 'vm.max_map_count=262144' >> /etc/sysctl.d/99-sysctl.conf
sysctl -p
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf
mkdir -p /data/elasticsearch/{data,logs}
useradd -M -s /sbin/nologin elasticsearch
chown -R elasticsearch:elasticsearch /data/elasticsearch /usr/local/elasticsearch
sed -ri "s/##[, ]*(-Xm[s|x])[0-9]g/\\14g/g" /usr/local/elasticsearch/config/jvm.options
```

## 8.2 elasticsearch.yml（单节点完整）

```yaml
@@ESYML@@
```

## 8.3 systemd、启动与设置密码

```bash
cat > /etc/systemd/system/elasticsearch.service <<'EOF'
[Unit]
Description=Elasticsearch
[Service]
User=elasticsearch
Group=elasticsearch
LimitNOFILE=102400
ExecStart=/usr/local/elasticsearch/bin/elasticsearch
ExecStop=/usr/bin/kill $MAINPID
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now elasticsearch
# 设置 elastic 密码（仅字母数字，避免 @ ! # &）
/usr/local/elasticsearch/bin/elasticsearch-reset-password -u elastic -i
curl -u elastic:'<强密码>' 127.0.0.1:9200/_cat/health?v
```

# 九、中间件部署 — MinIO 单节点（中间件节点 192.168.1.51）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/minio/minio-single
> 单节点 Docker Swarm，对外端口 9011（容器内 9000）。

## 9.1 初始化单节点 Swarm、拉镜像、建目录

```bash
docker swarm init
docker pull registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-minio:RELEASE.2025-04-22T22-12-26Z
mkdir -p /usr/local/minio /data/minio/volume
```

## 9.2 minio.yaml

```text
cat > /usr/local/minio/minio.yaml <<'EOF'
version: '3'
services:
  minio:
    image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-minio:RELEASE.2025-04-22T22-12-26Z
    environment:
      MINIO_ROOT_USER: "mingdao"
      MINIO_ROOT_PASSWORD: "<强密码>"
    volumes:
      - /usr/share/zoneinfo/Etc/GMT-8:/etc/localtime
      - /data/minio/volume:/data/storage
    ports:
      - "9011:9000"
    command: minio server /data/storage/data --console-address ":9001"
EOF
```

## 9.3 启停脚本与启动

```text
cat > /usr/local/minio/start.sh <<'EOF'
docker stack deploy -c /usr/local/minio/minio.yaml minio --detach=false
EOF
cat > /usr/local/minio/stop.sh <<'EOF'
docker stack rm minio
EOF
chmod +x /usr/local/minio/start.sh /usr/local/minio/stop.sh
bash /usr/local/minio/start.sh
docker stack ps minio
```

# 十、中间件部署 — HAP 文件服务单节点（中间件节点 192.168.1.51）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/file/v2/single-node
> 单实例，端口 9000；s3-config 指向本机 MinIO 192.168.1.51:9011。

## 10.1 拉镜像、建目录、写 s3-config.json

```text
docker pull registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-file:2.1.0
mkdir -p /data/file/volume/{cache,data,fetchtmp,multitmp,tmp}
mkdir -p /usr/local/MDPrivateDeployment/clusterMode/config

cat > /usr/local/MDPrivateDeployment/clusterMode/config/s3-config.json << EOF
{
  "mode": 1,
  "accessKeyID": "<MinIO ROOT_USER>",
  "secretAccessKey": "<MinIO ROOT_PASSWORD>",
  "bucketEndPoint": "http://192.168.1.51:9011",
  "bucketName": {
    "mdmedia": "mdmedia",
    "mdpic": "mdpic",
    "mdpub": "mdpub",
    "mdoc": "mdoc"
  },
  "region": "1",
  "addressingModel": 1
}
EOF
```

## 10.2 file.yaml（单实例）

```text
cat > /usr/local/MDPrivateDeployment/clusterMode/file.yaml <<EOF
version: '3'
services:
  file:
    image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-file:2.1.0
    volumes:
      - /usr/share/zoneinfo/Etc/GMT-8:/etc/localtime
      - /data/file/volume:/data/storage
      - /usr/local/MDPrivateDeployment/clusterMode/config/s3-config.json:/usr/local/file/s3-config.json
    ports:
      - "9000:9000"
    environment:
      ENV_ACCESS_KEY_FILE: storage
      ENV_SECRET_KEY_FILE: <强密码>
      ENV_MINGDAO_PROTO: "http"
      ENV_MINGDAO_HOST: "hap.domain.com"
      ENV_MINGDAO_PORT: "80"
      ENV_FILE_CACHE: "redis://:<强密码>@192.168.1.31:6379"
      ENV_FILECACHE_EXPIRE: "false"
      ENV_FILE_ID: "file1"
      ENV_FILE_DOMAIN: "http://192.168.1.51:9000"
    command: ["./main", "server", "/data/storage/data"]
EOF
```

## 10.3 启停脚本与启动

```text
cat > /usr/local/MDPrivateDeployment/clusterMode/start.sh <<EOF
docker stack deploy -c /usr/local/MDPrivateDeployment/clusterMode/file.yaml file --detach=false
EOF
cat > /usr/local/MDPrivateDeployment/clusterMode/stop.sh <<EOF
docker stack rm file
EOF
chmod +x /usr/local/MDPrivateDeployment/clusterMode/start.sh /usr/local/MDPrivateDeployment/clusterMode/stop.sh
bash /usr/local/MDPrivateDeployment/clusterMode/start.sh
docker stack ps file
```

# 十一、上传预置文件到 MinIO

> 微服务首次启动前，将 HAP 预置文件上传到 MinIO 业务桶（中间件节点 192.168.1.51 执行）。
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

# 十二、Kubernetes 单 Master 集群（微服务节点 192.168.1.21/22）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/kubernetes/kubernetes-1.35.3/single-master-deployment
> 1 Master（.21）+ 1 Worker（.22）。**精简版节点少，必须移除 Master 污点**让微服务 Pod 调度到 Master。

## 12.1 安装包与 containerd（两节点均执行）

```bash
wget https://pdpublic.mingdao.com/private-deployment/offline/common/kubernetes-1.35.3/1.35-k8s-amd64-pkg.tar.gz
tar xzvf 1.35-k8s-amd64-pkg.tar.gz
cd 1.35-k8s-amd64-pkg
tar -zxvf containerd-static-2.2.2-linux-amd64.tar.gz
mv -f bin/* /usr/local/bin/
mkdir /etc/containerd
containerd config default > /etc/containerd/config.toml
sed -i \\
  -e 's|SystemdCgroup =.*|SystemdCgroup = true|g' \\
  -e 's|bin_dirs =.*|bin_dirs = ["/usr/local/kubernetes/cni/bin"]|' \\
  -e 's|sandbox =.*|sandbox = "127.0.0.1:5000/pause:3.10.1"|' \\
  -e 's|^root =.*|root = "/data/containerd"|' \\
  /etc/containerd/config.toml
systemctl daemon-reload && systemctl enable --now containerd
```

## 12.2 安装 kubeadm/kubelet/kubectl（两节点均执行）

```bash
mkdir -p /usr/local/kubernetes/bin
tar -zxvf crictl-v1.35.0-linux-amd64.tar.gz -C /usr/local/kubernetes/bin
cp ./{kubeadm,kubelet,kubectl} /usr/local/kubernetes/bin/
chmod +x /usr/local/kubernetes/bin/*
cat > /etc/profile.d/kubernetes.sh <<'EOF'
export PATH=/usr/local/kubernetes/bin/:$PATH
EOF
source /etc/profile.d/kubernetes.sh
crictl config runtime-endpoint unix:///run/containerd/containerd.sock
```

## 12.3 初始化 Master（192.168.1.21）

```bash
cd /usr/local/kubernetes/
kubeadm config print init-defaults > kubeadm-config.yaml
sed -ri 's|imageRepository.*|imageRepository: 127.0.0.1:5000|' kubeadm-config.yaml
sed -ri '/serviceSubnet/a \\ \\ podSubnet: 10.244.0.0\\/16' kubeadm-config.yaml
sed -ri 's|advertiseAddress.*|advertiseAddress: 192.168.1.21|' kubeadm-config.yaml
sed -ri 's|kubernetesVersion.*|kubernetesVersion: 1.35.3|' kubeadm-config.yaml
kubeadm init --config=kubeadm-config.yaml --upload-certs --v=6
echo 'export KUBECONFIG=/etc/kubernetes/admin.conf' >> /etc/profile.d/kubernetes.sh
source /etc/profile.d/kubernetes.sh
```

## 12.4 移除 Master 污点（精简版关键步骤）

```bash
# 精简版节点少，必须移除污点让业务 Pod 调度到 Master
kubectl taint node $(kubectl get node | grep control-plane | awk '{print $1}') node-role.kubernetes.io/control-plane:NoSchedule-
echo "maxPods: 300" >> /var/lib/kubelet/config.yaml
systemctl restart kubelet
```

## 12.5 安装 Calico 并加入 Worker（192.168.1.22）

```bash
mv calico.yaml /usr/local/kubernetes/
sed -ri 's|image: quay.io/calico|image: 127.0.0.1:5000|g' /usr/local/kubernetes/calico.yaml
kubectl apply -f /usr/local/kubernetes/calico.yaml
# Worker（.22）加入：用 kubeadm init 输出的 worker join 命令
kubeadm join 192.168.1.21:6443 --token <TOKEN> --discovery-token-ca-cert-hash sha256:<HASH>
echo "maxPods: 300" >> /var/lib/kubelet/config.yaml
systemctl restart kubelet
kubectl get node -o wide
```

# 十三、Istio 1.29.1 服务网格（K8s 集群）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/istio/istio-1.29.1/istio

```bash
sysctl -w fs.inotify.max_user_watches=10485760
sysctl -w fs.inotify.max_user_instances=10240
cat >> /etc/sysctl.d/99-sysctl.conf <<EOF
fs.inotify.max_user_watches=10485760
fs.inotify.max_user_instances=10240
EOF
cd 1.35-k8s-amd64-pkg
tar -zxvf istio-1.29.1-linux-amd64.tar.gz -C /usr/local/
mv /usr/local/istio-1.29.1 /usr/local/istio
cat > /etc/profile.d/istio.sh <<'EOF'
export PATH=/usr/local/istio/bin/:$PATH
EOF
source /etc/profile.d/istio.sh
istioctl install --set profile=default -y --set values.global.hub=127.0.0.1:5000
kubectl label namespace default istio-injection=enabled --overwrite
```

# 十四、HAP 微服务部署（K8s 集群）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/service

## 14.1 部署管理器（Captain，在 192.168.1.21）

```bash
wget https://pdpublic.mingdao.com/private-deployment/7.3.4/mingdaoyun_private_deployment_captain_linux_amd64.tar.gz
mkdir /usr/local/MDPrivateDeployment/
tar -zxvf mingdaoyun_private_deployment_captain_linux_amd64.tar.gz -C /usr/local/MDPrivateDeployment/
cat > /etc/systemd/system/hap-manager.service <<'EOF'
[Unit]
Description=HAP Manager
After=network-online.target
Wants=network-online.target
[Service]
Type=oneshot
WorkingDirectory=/usr/local/MDPrivateDeployment
ExecStart=/usr/bin/bash ./service.sh start
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now hap-manager
cd /usr/local/MDPrivateDeployment/
bash ./service.sh install https://hap.domain.com
echo -n 'StageStart' > installer.stage
```

## 14.2 创建 ConfigMap（单节点连接地址）

```yaml
cat > config.yaml <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: env-list
  namespace: default
data:
  ENV_APP_VERSION: "7.3.4"
  ENV_MYSQL_HOST: "192.168.1.31"
  ENV_MYSQL_PORT: "3306"
  ENV_MYSQL_USERNAME: "root"
  ENV_MYSQL_PASSWORD: "<强密码>"
  ENV_MONGODB_URI: "mongodb://hap:<强密码>@192.168.1.31:27017"
  ENV_MONGODB_OPTIONS: "?authSource=admin&maxIdleTimeMS=600000&maxLifeTimeMS=1800000"
  ENV_REDIS_HOST: "192.168.1.31"
  ENV_REDIS_PORT: "6379"
  ENV_REDIS_PASSWORD: "<强密码>"
  ENV_KAFKA_ENDPOINTS: "192.168.1.51:9092"
  ENV_ELASTICSEARCH_ENDPOINTS: "http://192.168.1.51:9200"
  ENV_ELASTICSEARCH_PASSWORD: "elastic:<强密码>"
  ENV_FILE_ENDPOINTS: "192.168.1.51:9000"
  ENV_FILE_ACCESSKEY: "storage"
  ENV_FILE_SECRETKEY: "<强密码>"
  ENV_ADDRESS_MAIN: "https://hap.domain.com"
  ENV_API_TOKEN: "<高熵随机字符串>"
  ENV_TIME_ZONE: "Asia/Shanghai"
EOF
kubectl apply -f config.yaml
```

## 14.3 设置副本数并启动微服务

```bash
wget https://pdpublic.mingdao.com/private-deployment/data/set_microservice_replicas.sh
chmod +x set_microservice_replicas.sh
bash set_microservice_replicas.sh lite
cd /data/mingdao/script/kubernetes/ && bash start.sh
kubectl get pod -o wide
```

# 十五、Flink 部署（HDP / Flink 节点 192.168.1.30）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/flink

```bash
gunzip -d mingdaoyun-flink-linux-amd64-1.19.720.tar.gz
ctr -n k8s.io image import mingdaoyun-flink-linux-amd64-1.19.720.tar
mkdir -p /data/mingdao/script/kubernetes/flink
cd /data/mingdao/script/kubernetes/flink
# 给 Flink 节点打污点/标签并建命名空间
kubectl taint nodes $flink_node_name hap=flink:NoSchedule
kubectl label nodes $flink_node_name hap=flink
kubectl create ns flink
sed -i 's/namespace: default/namespace: flink/g' flink.yaml
kubectl apply -f flink.yaml
```

flink-conf.yaml 关键项（对接单节点 MinIO）：

```yaml
s3.access-key: mingdao
s3.secret-key: <强密码>
s3.ssl.enabled: false
s3.path.style.access: true
s3.endpoint: 192.168.1.51:9011
state.checkpoints.dir: s3://mdoc/checkpoints
state.savepoints.dir: s3://mdoc/savepoints
high-availability.storageDir: s3://mdoc/recovery
jobmanager.memory.process.size: 3072m
taskmanager.memory.process.size: 12288m
```

# 十六、Nginx 反向代理（Nginx 节点 192.168.1.20）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/nginx/deploy-nginx
> 精简版单 Nginx，无 Keepalived/VIP。

```bash
mkdir -p /data/logs/weblogs
cat > /usr/local/nginx/conf/hap.conf <<'EOF'
upstream hap {
    least_conn;
    server 192.168.1.21:8880 max_fails=3 fail_timeout=15s;
    server 192.168.1.22:8880 max_fails=3 fail_timeout=15s;
    keepalive 32;
}
server {
    listen 80;
    server_name hap.domain.com;
    access_log /data/logs/weblogs/hap.log;
    client_max_body_size 2048m;
    location / {
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $http_host;
        proxy_pass http://hap;
    }
}
EOF
systemctl enable --now nginx
```

# 十七、监控部署（Prometheus + Grafana）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/monitor/prometheus 、 .../monitor/grafana
> 6 节点均部署 node_exporter（:59100）；中间件节点（跑 docker）部署 cadvisor（:59101）；Kafka 所在中间件节点部署 kafka_exporter（:59102）；K8s 内 kube-state-metrics（NodePort 30686，资源清单同集群版）。

## 17.1 node_exporter（所有 6 个节点均部署）

```bash
wget https://pdpublic.mingdao.com/private-deployment/offline/common/node_exporter-1.9.1.linux-amd64.tar.gz
tar xf node_exporter-1.9.1.linux-amd64.tar.gz -C /usr/local/
mv /usr/local/node_exporter-1.9.1.linux-amd64 /usr/local/node_exporter

cat > /etc/systemd/system/node_exporter.service <<'EOF'
[Unit]
Description=Node Exporter for Prometheus
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/node_exporter/node_exporter --web.listen-address=:59100
User=root
Group=root
Restart=always
RestartSec=10
LimitNOFILE=102400

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now node_exporter
```

## 17.2 cadvisor（中间件节点 192.168.1.51）与 kafka_exporter（中间件节点 192.168.1.51）

```bash
# cadvisor
wget https://pdpublic.mingdao.com/private-deployment/offline/common/cadvisor-v0.52.1-linux-amd64
mkdir /usr/local/cadvisor
mv cadvisor-v0.52.1-linux-amd64 /usr/local/cadvisor/cadvisor
chmod +x /usr/local/cadvisor/cadvisor
cat > /etc/systemd/system/cadvisor.service <<'EOF'
[Unit]
Description=cAdvisor Container Monitoring
After=network.target
[Service]
Type=simple
ExecStart=/usr/local/cadvisor/cadvisor -port=59101
User=root
Group=root
Restart=always
RestartSec=10
LimitNOFILE=102400
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now cadvisor

# kafka_exporter
wget https://pdpublic.mingdao.com/private-deployment/offline/common/kafka_exporter-1.9.0.linux-amd64.tar.gz
tar -zxvf kafka_exporter-1.9.0.linux-amd64.tar.gz -C /usr/local/
mv /usr/local/kafka_exporter-1.9.0.linux-amd64 /usr/local/kafka_exporter
cat > /etc/systemd/system/kafka_exporter.service <<'EOF'
[Unit]
Description=Kafka Exporter for Prometheus
After=network.target
[Service]
Type=simple
ExecStart=/usr/local/kafka_exporter/kafka_exporter --kafka.server=192.168.1.51:9092 --web.listen-address=:59102
User=root
Group=root
Restart=always
RestartSec=10
LimitNOFILE=102400
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now kafka_exporter
```

## 17.3 Prometheus 安装与 prometheus.yml（6 节点）

```bash
wget https://pdpublic.mingdao.com/private-deployment/offline/common/prometheus-3.5.0.linux-amd64.tar.gz
tar -zxvf prometheus-3.5.0.linux-amd64.tar.gz -C /usr/local/
mv /usr/local/prometheus-3.5.0.linux-amd64 /usr/local/prometheus
```

```yaml
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: "node_exporter"
    static_configs:
      - targets: ["192.168.1.20:59100"]
        labels: {nodename: hap-nginx, origin_prometheus: node}
      - targets: ["192.168.1.21:59100"]
        labels: {nodename: hap-k8s-01, origin_prometheus: node}
      - targets: ["192.168.1.22:59100"]
        labels: {nodename: hap-k8s-02, origin_prometheus: node}
      - targets: ["192.168.1.31:59100"]
        labels: {nodename: hap-db, origin_prometheus: node}
      - targets: ["192.168.1.51:59100"]
        labels: {nodename: hap-middleware, origin_prometheus: node}
      - targets: ["192.168.1.30:59100"]
        labels: {nodename: hap-flink, origin_prometheus: node}
  - job_name: "cadvisor"
    static_configs:
      - targets: ["192.168.1.51:59101"]
  - job_name: kafka_exporter
    static_configs:
      - targets: ["192.168.1.51:59102"]
  - job_name: privatedeploy_kubernetes_metrics
    static_configs:
      - targets: ["192.168.1.21:30686"]
        labels: {origin_prometheus: kubernetes}
```

```bash
cat > /etc/systemd/system/prometheus.service <<'EOF'
[Unit]
Description=Prometheus Monitoring System
After=network.target
[Service]
Type=simple
ExecStart=/usr/local/prometheus/prometheus \\
  --storage.tsdb.path=/data/prometheus/data \\
  --storage.tsdb.retention.time=30d \\
  --config.file=/usr/local/prometheus/prometheus.yml \\
  --web.enable-lifecycle
ExecReload=/usr/bin/curl -X POST http://127.0.0.1:9090/-/reload
User=root
Group=root
Restart=always
RestartSec=10
LimitNOFILE=102400
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now prometheus
```

## 17.4 Grafana 安装与配置

```bash
wget https://pdpublic.mingdao.com/private-deployment/offline/common/grafana_12.1.2_17957162798_linux_amd64.tar.gz
tar -xf grafana_12.1.2_17957162798_linux_amd64.tar.gz -C /usr/local/
mv /usr/local/grafana-12.1.2 /usr/local/grafana
sed -ri 's#^root_url = .*#root_url = %(protocol)s://%(domain)s:%(http_port)s/privatedeploy/mdy/monitor/grafana/#' /usr/local/grafana/conf/defaults.ini
sed -ri 's#^serve_from_sub_path = .*#serve_from_sub_path = true#' /usr/local/grafana/conf/defaults.ini
cat > /etc/systemd/system/grafana.service <<'EOF'
[Unit]
Description=Grafana Dashboard
After=network.target
[Service]
Type=simple
WorkingDirectory=/usr/local/grafana
ExecStart=/usr/local/grafana/bin/grafana-server web
User=root
Group=root
Restart=always
RestartSec=10
LimitNOFILE=102400
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now grafana
```

> Grafana 初始 admin/admin，首次登录强制改密；登录后 Connections → Data sources 添加 Prometheus（URL `http://127.0.0.1:9090`），导入官方 HAP 仪表盘 JSON（服务器资源 / Docker / Kafka / Kubernetes）。

# 十八、部署后验收

## 18.1 组件健康核验（单节点）

| 组件 | 核验命令 | 期望 |
| --- | --- | --- |
| MongoDB | `systemctl status mongodb` + `mongo -u root -p` | 单实例运行、可登录 |
| MySQL | `mysql -h127.0.0.1 -uroot -p` | 3306 直连成功 |
| Redis | `redis-cli -a '<强密码>' ping` | PONG |
| Kafka | `systemctl status kafka` + 收发测试 | 正常 |
| Elasticsearch | `curl -u elastic:* :9200/_cat/health?v` | green / yellow（单节点副本0为 yellow 正常） |
| MinIO | `docker stack ps minio` | 1 副本 Running |
| File | `docker stack ps file` | 1 副本 Running |
| K8s | `kubectl get node` / `kubectl get pod -A` | 2 节点 Ready、已移除 Master 污点、Pod 全 Running |
| 微服务 | `kubectl get pod -o wide` | 全部 Running |
| Flink | `kubectl get pod -n flink` | Running |
| 入口 | 浏览器访问 https://hap.domain.com | 进入初始化向导 |

## 18.2 平台初始化与验收

1. 访问 https://hap.domain.com 完成超级管理员初始化。
2. 新建测试应用 + 工作表，加记录、传附件并预览（验证 MinIO/File）。
3. 配置工作流并触发（验证 Kafka）。
4. 全文搜索（验证 ES）。
5. 建聚合表/数据集成（验证 Flink）。
6. 核对 Grafana 各节点指标正常上报。

> 精简版存储层为单点，无高可用；生产建议定期备份（mysqldump / mongodump / redis BGSAVE / mc mirror）。验收通过后按《凭据登记表》登记真实密码并交客户保管。
'''
D=D.replace('@@NDB@@',str(len(HAP_DBS))).replace('@@MONGO@@',MONGO).replace('@@REDIS@@',REDIS).replace('@@KAFKA@@',KAFKA_SP).replace('@@ESYML@@',ES_YML)

# 十七章监控：复用 fix_monitor 的逐字官方内容(6节点)
import re as _re, sys as _sys
_sys.path.insert(0,_HERE)
from fix_monitor import gen_ne, build_monitor
_ne = gen_ne([("",[("192.168.1.20","hap-nginx"),("192.168.1.21","hap-k8s-01"),("192.168.1.22","hap-k8s-02"),
                   ("192.168.1.31","hap-db"),("192.168.1.51","hap-middleware"),("192.168.1.30","hap-flink")])])
_mon = build_monitor(_ne,"所有 6 个节点均部署",["192.168.1.51"],"192.168.1.51","192.168.1.21","192.168.1.20")
_mon = _mon.replace("# 十二、监控部署","# 十七、监控部署").replace("## 12.","## 17.")
_mon = _mon.replace("（仅运行 Docker 的节点，即对象存储 4 节点，:59101）","（仅运行 Docker 的节点，即中间件节点 192.168.1.51，:59101）")
D = _re.sub(r'# 十七、监控部署（Prometheus \+ Grafana）.*?(?=\n# 十八、部署后验收)', _mon.rstrip()+"\n\n", D, flags=_re.S)

open(os.path.join(_OUT,'deploy_streamlined.md'),'w',encoding='utf-8').write(D)
import re
print("streamlined md chars:",len(D))
print("章节(应19):", len([l for l in D.split('\n') if re.match(r'^# (文档说明|[一二三四五六七八九十]+、)',l)]))
print("createUser(应51):", D.count('db.createUser'))
