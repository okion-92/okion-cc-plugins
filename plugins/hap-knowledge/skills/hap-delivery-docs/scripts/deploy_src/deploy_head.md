# 文档说明

本文档为 HAP（明道云 超级应用平台）私有化部署 **集群专业版（并发 1000+ · 各组件独立部署）** 的部署实施手册，网络形态为 **场景 B（VXLAN 正常开启，对象存储 4 节点组成同一 Docker Swarm 集群）**。

## 集群专业版架构

集群专业版采用「各组件独立部署」架构：负载、微服务、缓存、消息队列、全文检索、对象存储、关系库、文档库、数据同步各自独立成节点，避免组件互相争抢资源，适用于并发 1000+ 的生产场景。核心组件全部高可用：MySQL 采用 **MGR + Router** 三节点组复制，MongoDB 采用三节点 **副本集**，Redis 采用三节点 **哨兵**，Kafka / Elasticsearch / MinIO 均为多节点集群，Kubernetes 为三 Master 高可用。

本套拓扑共 **29 个节点**（按官方《服务器资源推荐》专业版口径核定，含数据同步 Flink 节点）。向量检索（Milvus）与向量服务（etcd）为按需可选组件，本文档默认不纳入核心拓扑，如启用 AI 检索能力再行扩展。

## 节点 IP 规划

| 角色 | 主机名 | IP | 部署组件 |
| --- | --- | --- | --- |
| 负载均衡 01 | hap-nginx-01 | 192.168.1.11 | Nginx + Keepalived |
| 负载均衡 02 | hap-nginx-02 | 192.168.1.12 | Nginx + Keepalived |
| **负载 VIP** | — | **192.168.1.20** | Keepalived 虚拟 IP（对外访问入口） |
| 微服务 / K8s Master 01 | hap-k8s-master-01 | 192.168.1.21 | K8s Master + Istio + 微服务 |
| 微服务 / K8s Master 02 | hap-k8s-master-02 | 192.168.1.22 | K8s Master + 微服务 |
| 微服务 / K8s Master 03 | hap-k8s-master-03 | 192.168.1.23 | K8s Master + 微服务 |
| 微服务 / K8s Worker 01 | hap-k8s-worker-01 | 192.168.1.24 | K8s Worker + 微服务 |
| 微服务 / K8s Worker 02 | hap-k8s-worker-02 | 192.168.1.25 | K8s Worker + 微服务 |
| MySQL 01 (Primary) | hap-mysql-01 | 192.168.1.31 | MySQL MGR + Router |
| MySQL 02 | hap-mysql-02 | 192.168.1.32 | MySQL MGR + Router |
| MySQL 03 | hap-mysql-03 | 192.168.1.33 | MySQL MGR + Router |
| MongoDB 01 (Primary) | hap-mongodb-01 | 192.168.1.34 | MongoDB 副本集 |
| MongoDB 02 | hap-mongodb-02 | 192.168.1.35 | MongoDB 副本集 |
| MongoDB 03 | hap-mongodb-03 | 192.168.1.36 | MongoDB 副本集 |
| Redis 01 (Master) | hap-redis-01 | 192.168.1.41 | Redis + Sentinel |
| Redis 02 | hap-redis-02 | 192.168.1.42 | Redis + Sentinel |
| Redis 03 | hap-redis-03 | 192.168.1.43 | Redis + Sentinel |
| Kafka 01 | hap-kafka-01 | 192.168.1.51 | Kafka + ZooKeeper |
| Kafka 02 | hap-kafka-02 | 192.168.1.52 | Kafka + ZooKeeper |
| Kafka 03 | hap-kafka-03 | 192.168.1.53 | Kafka + ZooKeeper |
| Elasticsearch 01 | hap-es-01 | 192.168.1.61 | Elasticsearch |
| Elasticsearch 02 | hap-es-02 | 192.168.1.62 | Elasticsearch |
| Elasticsearch 03 | hap-es-03 | 192.168.1.63 | Elasticsearch |
| 对象存储 01 | hap-storage-01 | 192.168.1.71 | MinIO + File（Swarm manager） |
| 对象存储 02 | hap-storage-02 | 192.168.1.72 | MinIO + File |
| 对象存储 03 | hap-storage-03 | 192.168.1.73 | MinIO + File |
| 对象存储 04 | hap-storage-04 | 192.168.1.74 | MinIO + File |
| 数据同步 01 | hap-flink-01 | 192.168.1.81 | Flink (HDP 超级数据平台) |
| 数据同步 02 | hap-flink-02 | 192.168.1.82 | Flink (HDP 超级数据平台) |
| 数据同步 03 | hap-flink-03 | 192.168.1.83 | Flink (HDP 超级数据平台) |

> 访问入口：https://hap.domain.com（端口 443，经 Nginx VIP 192.168.1.20 转发到 K8s 微服务 www 端口 8880）。上述 IP 为示例拓扑，交付时按客户实际网段整体替换。

## 关键端口与版本

| 组件 | 版本 | 关键端口 |
| --- | --- | --- |
| MySQL | 8.0.45 | 3306 / Router 6446(读写) 6447(只读) / 33061(MGR 内部) |
| MongoDB | 4.4.30 | 27017 |
| Redis | 8.x | 6379 / Sentinel 26379 |
| Kafka | 3.9.1 (JDK 21) | 9092 / ZK 2181 / 2888 / 3888 |
| Elasticsearch | 8.19.8 | 9200 / 9300 |
| MinIO | RELEASE.2025-04-22 | 9011-9014（容器内 9000）/ Swarm 2377 |
| HAP File | 2.1.0 | 9001-9004（容器内 9000） |
| Kubernetes | 1.35.3 | 6443 / 8880 / 18880 / 38880 / 38881 / NodePort 1024-32767 |
| Istio | 1.29.1 | — |
| HAP 微服务 | 7.3.4 | 8880(www 主地址) / 18880(www 扩展地址，按需启用) / 38880(安装管理器 ENV_CAPTAIN_ENDPOINT) / 38881(管理入口) |
| Flink | 1.19.720 | JobManager 8081 |
| Docker | 28.5.2 | — |
| Nginx | 1.28.2 | 80 / 443 |

# 一、服务器资源清单

按官方《服务器资源推荐 · 专业版（1000+ 并发）》核定，共 29 个节点。

| 角色 | 配置 | 操作系统 | 部署服务 | 数量 |
| --- | --- | --- | --- | --- |
| 负载均衡 | 4C / 8G / 60G 系统盘 + 200G SSD | Debian 12 | Nginx + Keepalived | 2 |
| 微服务 | 24C / 64G / 60G 系统盘 + 300G SSD | Debian 12 | K8s + Istio + HAP 微服务 | 5 |
| 缓存 | 8C / 32G / 60G 系统盘 + 200G SSD | Debian 12 | Redis 哨兵 | 3 |
| 消息队列 | 8C / 32G / 60G 系统盘 + 500G SSD | Debian 12 | Kafka + ZooKeeper | 3 |
| 全文检索 | 8C / 32G / 60G 系统盘 + 500G SSD | Debian 12 | Elasticsearch | 3 |
| 文件存储 | 8C / 32G / 60G 系统盘 + 500G SSD | Debian 12 | MinIO + HAP File | 4 |
| 关系库 | 8C / 16G / 60G 系统盘 + 200G SSD | Debian 12 | MySQL MGR + Router | 3 |
| 文档库 | 32C / 64G / 60G 系统盘 + 500G SSD | Debian 12 | MongoDB 副本集 | 3 |
| 数据同步 | 16C / 64G / 60G 系统盘 + 200G SSD | Debian 12 | Flink (HDP) | 3 |
| **合计** | — | — | — | **29** |

> 可选扩展（启用 AI/向量检索时再加）：向量检索 Milvus 16C/64G ×3、向量服务 etcd 4C/16G ×3。

## 1.2 网络互通要求

- 所有节点内网二层互通；对象存储 4 节点（192.168.1.71-74）之间需放通 Swarm 端口 **TCP 2377、UDP/TCP 4789、TCP 7946**（场景 B）。
- K8s 节点间放通 6443、10250、179(Calico BGP)、VXLAN 4789(UDP)、NodePort 1024-32767。
- 微服务节点需访问：MySQL Router 6446、MongoDB 27017、Redis 6379/26379、Kafka 9092、ES 9200、File 9001-9004。
- 仅 Nginx VIP 192.168.1.20 的 80/443 对外暴露，其余端口仅限内网。

# 二、操作系统初始化（所有节点）

所有节点统一执行以下初始化（Debian 12 为例）。

## 2.1 关闭防火墙与 SELinux

```bash
# Debian/Ubuntu
systemctl stop nftables firewalld 2>/dev/null
systemctl disable nftables firewalld 2>/dev/null
# 如为 CentOS/RHEL
# setenforce 0
# sed -i 's/^SELINUX=.*/SELINUX=disabled/' /etc/selinux/config
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
net.bridge.bridge-nf-call-ip6tables = 1
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
* soft nproc  65536
* hard nproc  65536
EOF
```

## 2.4 时间同步

```bash
# Debian
apt-get install -y chrony
systemctl enable --now chrony
chronyc sources
# 时区
ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
```

# 三、Docker 安装（对象存储节点 192.168.1.71-74）

对象存储 4 节点（MinIO + File）以 Docker Swarm 方式运行，需安装 Docker（离线二进制方式，适配各发行版）。

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

# 四、数据库部署

## 4.1 MongoDB 4.4 副本集（节点 192.168.1.34 / .35 / .36）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/mongodb/4.4/replica-set

### 4.1.1 安装（三节点均执行）

```bash
# Debian 11/12
wget https://pdpublic.mingdao.com/private-deployment/offline/common/libssl1.1_1.1.1w-0+deb11u1_amd64.deb
dpkg -i libssl1.1_1.1.1w-0+deb11u1_amd64.deb
wget https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-debian10-4.4.30.tgz
tar -zxvf mongodb-linux-x86_64-debian10-4.4.30.tgz
mv mongodb-linux-x86_64-debian10-4.4.30 /usr/local/mongodb
```

### 4.1.2 用户、目录与 keyFile（三节点均执行）

```bash
useradd -M -s /sbin/nologin mongodb
mkdir -p /data/mongodb/ /data/logs/mongodb
# keyFile 三节点必须一致（下方为示例，部署时自行生成）
echo '<副本集 keyFile 内容，三节点一致>' > /data/mongodb/keyfile
chmod 400 /data/mongodb/keyfile
chown -R mongodb:mongodb /usr/local/mongodb/ /data/mongodb/ /data/logs/mongodb
```

### 4.1.3 关闭透明大页 THP（三节点均执行）

```bash
cat > /etc/systemd/system/disable-thp.service <<\EOF
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

### 4.1.4 systemd 服务（三节点均执行）

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
ExecStart=/usr/local/mongodb/bin/mongod --logpath /data/logs/mongodb/mongodb.log --dbpath /data/mongodb --auth --keyFile /data/mongodb/keyfile --port 27017 --replSet local-mongodb-one --bind_ip 0.0.0.0
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

### 4.1.5 创建数据库用户（仅 192.168.1.34 执行）

先以 `--noauth` 临时启动，创建 root 管理员与全部 HAP 业务库 hap 用户（**以下为官方完整库清单，共 root + 50 个业务库，逐库 readWrite**），完成后停止临时实例：

```bash
su -c '/usr/local/mongodb/bin/mongod --fork --logpath /data/logs/mongodb/mongodb.log --dbpath /data/mongodb --noauth --port 27017' -s /bin/bash mongodb

/usr/local/mongodb/bin/mongo <<'JS'
use admin
db.createUser({user:"root",pwd:"<强密码>",roles:[{role:"root",db:"admin"}]})
use MDLicense
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"MDLicense"}]})
use ClientLicense
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"ClientLicense"}]})
use commonbase
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"commonbase"}]})
use MDAlert
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"MDAlert"}]})
use mdapproles
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdapproles"}]})
use mdapprove
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdapprove"}]})
use mdapps
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdapps"}]})
use mdattachment
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdattachment"}]})
use mdcalendar
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdcalendar"}]})
use mdcategory
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdcategory"}]})
use MDChatTop
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"MDChatTop"}]})
use mdcheck
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdcheck"}]})
use mddossier
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mddossier"}]})
use mdemail
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdemail"}]})
use mdform
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdform"}]})
use MDGroup
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"MDGroup"}]})
use mdgroups
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdgroups"}]})
use MDHistory
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"MDHistory"}]})
use mdIdentification
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdIdentification"}]})
use mdinbox
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdinbox"}]})
use mdkc
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdkc"}]})
use mdmap
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdmap"}]})
use mdmobileaddress
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdmobileaddress"}]})
use MDNotification
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"MDNotification"}]})
use mdpost
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdpost"}]})
use mdreportdata
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdreportdata"}]})
use mdroles
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdroles"}]})
use mdsearch
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdsearch"}]})
use mdservicedata
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdservicedata"}]})
use mdsms
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdsms"}]})
use MDSso
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"MDSso"}]})
use mdtag
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdtag"}]})
use mdtransfer
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdtransfer"}]})
use MDUser
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"MDUser"}]})
use mdworkflow
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdworkflow"}]})
use mdworksheet
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdworksheet"}]})
use mdworkweixin
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdworkweixin"}]})
use mdwsrows
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdwsrows"}]})
use pushlog
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"pushlog"}]})
use taskcenter
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"taskcenter"}]})
use mdintegration
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdintegration"}]})
use mdactionlog
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdactionlog"}]})
use mdworksheetlog
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdworksheetlog"}]})
use mdworksheetsearch
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdworksheetsearch"}]})
use mddatapipeline
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mddatapipeline"}]})
use mdwfplugin
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdwfplugin"}]})
use mdpayment
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdpayment"}]})
use mdwfai
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdwfai"}]})
use mdopenauth
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdopenauth"}]})
use mdaisearch
db.createUser({user:"hap",pwd:"<强密码>",roles:[{role:"readWrite",db:"mdaisearch"}]})
JS

kill $(pgrep -f 'mongod')
```
### 4.1.6 启动并初始化副本集

```bash
# 三节点均启动
systemctl start mongodb

# 仅 192.168.1.34 登录并初始化副本集
/usr/local/mongodb/bin/mongo -u root -p '<强密码>' --authenticationDatabase admin <<'JS'
rs.initiate({_id:"local-mongodb-one",members:[
  {_id:1, host:"192.168.1.34:27017"},
  {_id:2, host:"192.168.1.35:27017"},
  {_id:3, host:"192.168.1.36:27017"}
]})
rs.status()
JS
```

## 4.2 MySQL 8.0 MGR 集群（节点 192.168.1.31 / .32 / .33 + Router）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/mysql/mysql-8.0/mgr

### 4.2.1 安装（三节点均执行）

```bash
wget https://pdpublic.mingdao.com/private-deployment/offline/common/mysql-8.0.45-linux-glibc2.17-x86_64.tar.xz
wget https://pdpublic.mingdao.com/private-deployment/offline/common/mysql-router-8.0.45-linux-glibc2.17-x86_64.tar.xz
tar -xvf mysql-8.0.45-linux-glibc2.17-x86_64.tar.xz
mv mysql-8.0.45-linux-glibc2.17-x86_64 /usr/local/mysql
echo 'export PATH=/usr/local/mysql/bin:$PATH' > /etc/profile.d/mysql.sh
source /etc/profile.d/mysql.sh
useradd -U -r -s /sbin/nologin mysql
mkdir -p /data/mysql /data/logs/mysql
chown -R mysql:mysql /data/mysql /data/logs/mysql /usr/local/mysql/
mysqld --no-defaults --initialize --datadir=/data/mysql/ --user=mysql --log-error=/data/logs/mysql/mysqld.log
```

### 4.2.2 my.cnf（三节点各自完整配置，差异仅 server-id / report_host / group_replication_local_address）

三节点 `group_replication_group_name` 与 `group_replication_group_seeds` 必须完全一致；以下为官方完整 my.cnf（写入 `/etc/my.cnf`），逐节点给出。

**MySQL Node01（192.168.1.31，Primary）的 /etc/my.cnf：**

```ini
[mysqld]
user                         = mysql
basedir                      = /usr/local/mysql
datadir                      = /data/mysql
socket                       = /usr/local/mysql/mysqld.sock
pid-file                     = /usr/local/mysql/mysqld.pid
log-error                    = /data/logs/mysql/mysqld.log
server-id                    = 1
bind-address                 = 0.0.0.0
port                         = 3306
mysqlx_port                  = 33060
skip-name-resolve            = ON
max_connections              = 5000
default_storage_engine       = InnoDB
innodb_buffer_pool_size      = 2G
character_set_server         = utf8mb4
collation_server             = utf8mb4_0900_ai_ci
slow_query_log               = 1
slow_query_log_file          = /data/logs/mysql/mysql-slow.log
long_query_time              = 1
log_bin                      = /data/mysql/mysql-bin
binlog_format                = ROW
sync_binlog                  = 1
binlog_expire_logs_seconds   = 2592000
gtid_mode                    = ON
enforce_gtid_consistency     = ON
log_slave_updates            = ON
master_info_repository       = TABLE
relay_log_info_repository    = TABLE
transaction_write_set_extraction = XXHASH64
binlog_transaction_dependency_tracking = WRITESET
replica_parallel_type                  = LOGICAL_CLOCK
replica_parallel_workers               = 4
replica_preserve_commit_order          = ON
report_host                  = 192.168.1.31
report_port                  = 3306
plugin_load_add              = 'group_replication.so'
group_replication_group_name = "c9f6d3f2-7b21-4e5a-9c87-3a0e9f0a43d2"
group_replication_start_on_boot = OFF
group_replication_local_address = "192.168.1.31:33061"
group_replication_group_seeds   = "192.168.1.31:33061,192.168.1.32:33061,192.168.1.33:33061"
group_replication_single_primary_mode = ON
group_replication_enforce_update_everywhere_checks = OFF
group_replication_recovery_get_public_key = ON

[client]
port                 = 3306
socket               = /usr/local/mysql/mysqld.sock

[mysql]
default-character-set = utf8mb4
```

**MySQL Node02（192.168.1.32）的 /etc/my.cnf：**

```ini
[mysqld]
user                         = mysql
basedir                      = /usr/local/mysql
datadir                      = /data/mysql
socket                       = /usr/local/mysql/mysqld.sock
pid-file                     = /usr/local/mysql/mysqld.pid
log-error                    = /data/logs/mysql/mysqld.log
server-id                    = 2
bind-address                 = 0.0.0.0
port                         = 3306
mysqlx_port                  = 33060
skip-name-resolve            = ON
max_connections              = 5000
default_storage_engine       = InnoDB
innodb_buffer_pool_size      = 2G
character_set_server         = utf8mb4
collation_server             = utf8mb4_0900_ai_ci
slow_query_log               = 1
slow_query_log_file          = /data/logs/mysql/mysql-slow.log
long_query_time              = 1
log_bin                      = /data/mysql/mysql-bin
binlog_format                = ROW
sync_binlog                  = 1
binlog_expire_logs_seconds   = 2592000
gtid_mode                    = ON
enforce_gtid_consistency     = ON
log_slave_updates            = ON
master_info_repository       = TABLE
relay_log_info_repository    = TABLE
transaction_write_set_extraction = XXHASH64
binlog_transaction_dependency_tracking = WRITESET
replica_parallel_type                  = LOGICAL_CLOCK
replica_parallel_workers               = 4
replica_preserve_commit_order          = ON
report_host                  = 192.168.1.32
report_port                  = 3306
plugin_load_add              = 'group_replication.so'
group_replication_group_name = "c9f6d3f2-7b21-4e5a-9c87-3a0e9f0a43d2"
group_replication_start_on_boot = OFF
group_replication_local_address = "192.168.1.32:33061"
group_replication_group_seeds   = "192.168.1.31:33061,192.168.1.32:33061,192.168.1.33:33061"
group_replication_single_primary_mode = ON
group_replication_enforce_update_everywhere_checks = OFF
group_replication_recovery_get_public_key = ON

[client]
port                 = 3306
socket               = /usr/local/mysql/mysqld.sock

[mysql]
default-character-set = utf8mb4
```

**MySQL Node03（192.168.1.33）的 /etc/my.cnf：**

```ini
[mysqld]
user                         = mysql
basedir                      = /usr/local/mysql
datadir                      = /data/mysql
socket                       = /usr/local/mysql/mysqld.sock
pid-file                     = /usr/local/mysql/mysqld.pid
log-error                    = /data/logs/mysql/mysqld.log
server-id                    = 3
bind-address                 = 0.0.0.0
port                         = 3306
mysqlx_port                  = 33060
skip-name-resolve            = ON
max_connections              = 5000
default_storage_engine       = InnoDB
innodb_buffer_pool_size      = 2G
character_set_server         = utf8mb4
collation_server             = utf8mb4_0900_ai_ci
slow_query_log               = 1
slow_query_log_file          = /data/logs/mysql/mysql-slow.log
long_query_time              = 1
log_bin                      = /data/mysql/mysql-bin
binlog_format                = ROW
sync_binlog                  = 1
binlog_expire_logs_seconds   = 2592000
gtid_mode                    = ON
enforce_gtid_consistency     = ON
log_slave_updates            = ON
master_info_repository       = TABLE
relay_log_info_repository    = TABLE
transaction_write_set_extraction = XXHASH64
binlog_transaction_dependency_tracking = WRITESET
replica_parallel_type                  = LOGICAL_CLOCK
replica_parallel_workers               = 4
replica_preserve_commit_order          = ON
report_host                  = 192.168.1.33
report_port                  = 3306
plugin_load_add              = 'group_replication.so'
group_replication_group_name = "c9f6d3f2-7b21-4e5a-9c87-3a0e9f0a43d2"
group_replication_start_on_boot = OFF
group_replication_local_address = "192.168.1.33:33061"
group_replication_group_seeds   = "192.168.1.31:33061,192.168.1.32:33061,192.168.1.33:33061"
group_replication_single_primary_mode = ON
group_replication_enforce_update_everywhere_checks = OFF
group_replication_recovery_get_public_key = ON

[client]
port                 = 3306
socket               = /usr/local/mysql/mysqld.sock

[mysql]
default-character-set = utf8mb4
```
### 4.2.3 组复制引导（三节点建复制账号，仅 Primary 引导）

```sql
-- 三节点均执行
SET SQL_LOG_BIN=0;
CREATE USER 'repl'@'%' IDENTIFIED BY '<强密码>';
GRANT REPLICATION SLAVE, CONNECTION_ADMIN, BACKUP_ADMIN, GROUP_REPLICATION_STREAM ON *.* TO 'repl'@'%';
SET SQL_LOG_BIN=1;
CHANGE REPLICATION SOURCE TO SOURCE_USER='repl', SOURCE_PASSWORD='<强密码>' FOR CHANNEL 'group_replication_recovery';
```

```sql
-- 仅 Primary（192.168.1.31）引导集群
SET GLOBAL group_replication_bootstrap_group=ON;
START GROUP_REPLICATION;
SET GLOBAL group_replication_bootstrap_group=OFF;
```

```sql
-- 节点 02 / 03 加入
START GROUP_REPLICATION;
SELECT * FROM performance_schema.replication_group_members;
```

### 4.2.4 MySQL Router（三节点均部署，读写口 6446 / 只读口 6447）

```bash
mysqlrouter --bootstrap root:'<强密码>'@192.168.1.31:3306 --user=mysql --report-host=192.168.1.31
sed -i '/^\[DEFAULT\]$/a max_total_connections=5000' /usr/local/mysql-router/mysqlrouter.conf
chown -R mysql:mysql /usr/local/mysql-router
systemctl daemon-reload
systemctl enable --now mysqlrouter
# 验证
mysql -h 127.0.0.1 -P 6446 -u root -p
```

## 4.3 Redis 哨兵（节点 192.168.1.41 / .42 / .43）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/redis/sentinel

### 4.3.1 安装与内核调优（三节点均执行）

```bash
wget https://pdpublic.mingdao.com/private-deployment/offline/common/redis-8.6.3-glibc2.17-amd64.tar.gz
tar -zxvf redis-8.6.3-glibc2.17-amd64.tar.gz
mv redis-8.6.3-glibc2.17-amd64 /usr/local/redis
echo 'net.core.somaxconn = 32768' >> /etc/sysctl.d/99-sysctl.conf
echo 'vm.overcommit_memory = 1' >> /etc/sysctl.d/99-sysctl.conf
sysctl -p
mkdir -p /data/redis
```

### 4.3.2 redis.conf（Master 与从节点各自完整配置）

以下为官方完整 redis.conf（写入 `/usr/local/redis/redis.conf`）；三节点 requirepass / masterauth 必须一致，从节点末尾比 Master 多一行 `slaveof`。

**Redis Master（192.168.1.41）的 redis.conf：**

```ini
bind 0.0.0.0
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
maxmemory 16gb
maxmemory-policy allkeys-lru
maxclients 100000
rename-command KEYS ""
```

**Redis Slave-01（192.168.1.42）的 redis.conf：**

```ini
bind 0.0.0.0
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
maxmemory 16gb
maxmemory-policy allkeys-lru
maxclients 100000
rename-command KEYS ""
slaveof 192.168.1.41 6379
```

**Redis Slave-02（192.168.1.43）的 redis.conf：**

```ini
bind 0.0.0.0
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
maxmemory 16gb
maxmemory-policy allkeys-lru
maxclients 100000
rename-command KEYS ""
slaveof 192.168.1.41 6379
```
### 4.3.3 sentinel.conf（三节点均部署，端口 26379）

```ini
port 26379
daemonize yes
sentinel deny-scripts-reconfig yes
sentinel monitor mymaster 192.168.1.41 6379 2
sentinel auth-pass mymaster <强密码>
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 30000
dir "/data/redis/sentinel"
```

### 4.3.4 用户、systemd 与启动（三节点均执行）

```bash
useradd -U -M -s /sbin/nologin redis
mkdir -p /data/redis/sentinel
chown -R redis:redis /usr/local/redis/ /data/redis

cat > /etc/systemd/system/redis.service <<'EOF'
[Unit]
Description=Redis
[Service]
User=redis
Group=redis
LimitNOFILE=102400
ExecStart=/usr/local/redis/bin/redis-server /usr/local/redis/redis.conf
ExecStop=/usr/bin/kill $MAINPID
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/sentinel.service <<'EOF'
[Unit]
Description=Redis-sentinel
[Service]
User=redis
Group=redis
Type=forking
LimitNOFILE=102400
ExecStart=/usr/local/redis/bin/redis-sentinel /usr/local/redis/sentinel.conf
ExecStop=/usr/bin/kill $MAINPID
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now redis
systemctl enable --now sentinel
# 验证
/usr/local/redis/bin/redis-cli -a '<强密码>' -p 26379 SENTINEL get-master-addr-by-name mymaster
```

# 五、消息与检索中间件

## 5.1 Kafka 集群（节点 192.168.1.51 / .52 / .53）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/kafka/kafka-cluster

### 5.1.1 安装 JDK 21 与 Kafka（三节点均执行）

```bash
wget https://pdpublic.mingdao.com/private-deployment/offline/common/OpenJDK21U-jdk_x64_linux_hotspot_21.0.8_9.tar.gz
tar -zxvf OpenJDK21U-jdk_x64_linux_hotspot_21.0.8_9.tar.gz
mv jdk-21.0.8+9 /usr/local/openjdk-21
ln -sf /usr/local/openjdk-21/bin/java /bin/java

wget https://pdpublic.mingdao.com/private-deployment/offline/common/kafka_2.13-3.9.1.tgz
tar -zxvf kafka_2.13-3.9.1.tgz -C /usr/local
mv /usr/local/kafka_2.13-3.9.1/ /usr/local/kafka/
mkdir -p /data/kafka/zookeeper/ /data/kafka/kafka-logs/
```

### 5.1.2 ZooKeeper myid（逐节点）与 zookeeper.properties（三节点一致）

```bash
# 192.168.1.51 执行：
echo 1 > /data/kafka/zookeeper/myid
# 192.168.1.52 执行：echo 2 > /data/kafka/zookeeper/myid
# 192.168.1.53 执行：echo 3 > /data/kafka/zookeeper/myid

cat > /usr/local/kafka/config/zookeeper.properties <<'EOF'
admin.enableServer=false
dataDir=/data/kafka/zookeeper/
clientPort=2181
maxClientCnxns=0
initLimit=10
syncLimit=5
server.1=192.168.1.51:2888:3888
server.2=192.168.1.52:2888:3888
server.3=192.168.1.53:2888:3888
EOF
```

### 5.1.3 server.properties（三节点各自完整配置，差异仅 broker.id / advertised.listeners）

以下为官方完整 server.properties（写入 `/usr/local/kafka/config/server.properties`）；三节点 zookeeper.connect 一致。JVM 内存可用 `sed` 将 kafka-server-start.sh 的 1G 调到 4G。

**Kafka Node01（192.168.1.51）的 server.properties：**

```properties
broker.id=0
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
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000
zookeeper.connect=192.168.1.51:2181,192.168.1.52:2181,192.168.1.53:2181
zookeeper.connection.timeout.ms=6000
group.initial.rebalance.delay.ms=0
default.replication.factor=3
acks=all
min.insync.replicas=2
message.max.bytes=10485760
replica.fetch.max.bytes=10485760
```

**Kafka Node02（192.168.1.52）的 server.properties：**

```properties
broker.id=1
listeners=PLAINTEXT://0.0.0.0:9092
advertised.listeners=PLAINTEXT://192.168.1.52:9092
num.network.threads=3
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600
log.dirs=/data/kafka/kafka-logs/
num.partitions=10
num.recovery.threads.per.data.dir=1
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000
zookeeper.connect=192.168.1.51:2181,192.168.1.52:2181,192.168.1.53:2181
zookeeper.connection.timeout.ms=6000
group.initial.rebalance.delay.ms=0
default.replication.factor=3
acks=all
min.insync.replicas=2
message.max.bytes=10485760
replica.fetch.max.bytes=10485760
```

**Kafka Node03（192.168.1.53）的 server.properties：**

```properties
broker.id=2
listeners=PLAINTEXT://0.0.0.0:9092
advertised.listeners=PLAINTEXT://192.168.1.53:9092
num.network.threads=3
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600
log.dirs=/data/kafka/kafka-logs/
num.partitions=10
num.recovery.threads.per.data.dir=1
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000
zookeeper.connect=192.168.1.51:2181,192.168.1.52:2181,192.168.1.53:2181
zookeeper.connection.timeout.ms=6000
group.initial.rebalance.delay.ms=0
default.replication.factor=3
acks=all
min.insync.replicas=2
message.max.bytes=10485760
replica.fetch.max.bytes=10485760
```
### 5.1.4 systemd 与启动（三节点均执行）

```bash
useradd -M -s /sbin/nologin kafka
chown -R kafka:kafka /usr/local/kafka /data/kafka

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

## 5.2 Elasticsearch 集群（节点 192.168.1.61 / .62 / .63）

> 原文链接：https://docs-pdop.mingdao.com/deployment/cluster/installation/elasticsearch/elasticsearch-cluster

### 5.2.1 内核调优、安装与 IK 分词（三节点均执行）

```bash
echo 'vm.max_map_count=262144' >> /etc/sysctl.d/99-sysctl.conf
sysctl -p
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

tar xf elasticsearch-8.19.8-linux-x86_64.tar.gz
mv elasticsearch-8.19.8 /usr/local/elasticsearch
mkdir /usr/local/elasticsearch/plugins/elasticsearch-analysis-ik
unzip elasticsearch-analysis-ik-8.19.8.zip -d /usr/local/elasticsearch/plugins/elasticsearch-analysis-ik/
mkdir -p /data/elasticsearch/{data,logs}
mkdir /usr/local/elasticsearch/config/cert
useradd -M -s /sbin/nologin elasticsearch
chown -R elasticsearch:elasticsearch /data/elasticsearch /usr/local/elasticsearch
```

### 5.2.2 生成传输层证书（仅 192.168.1.61 执行，证书分发到三节点）

```bash
/usr/local/elasticsearch/bin/elasticsearch-certutil ca --out /usr/local/elasticsearch/config/cert/elastic-ca.p12 --days 36500 --pass ""
/usr/local/elasticsearch/bin/elasticsearch-certutil cert --ca /usr/local/elasticsearch/config/cert/elastic-ca.p12 --ca-pass "" --out /usr/local/elasticsearch/config/cert/elastic-node-certificate.p12 --days 36500 --pass ""
```

### 5.2.3 elasticsearch.yml（三节点各自完整配置，差异在 node.name / publish_host）

写入 `/usr/local/elasticsearch/config/elasticsearch.yml`；三节点 seed_hosts 与 initial_master_nodes 一致，证书 p12 由 5.2.2 生成后分发到三节点同一路径。

**ES Node01（192.168.1.61）的 elasticsearch.yml：**

```yaml
cluster.name: md-elasticsearch-private
node.name: elasticsearch-1
node.roles: [ master, data ]
network.host: 0.0.0.0
network.publish_host: 192.168.1.61
http.port: 9200
transport.port: 9300
path.data: /data/elasticsearch/data
path.logs: /data/elasticsearch/logs
discovery.seed_hosts: [ 192.168.1.61:9300, 192.168.1.62:9300, 192.168.1.63:9300 ]
cluster.initial_master_nodes: [ elasticsearch-1, elasticsearch-2, elasticsearch-3 ]
xpack.security.enabled: true
xpack.security.http.ssl.enabled: false
xpack.security.transport.ssl.enabled: true
xpack.security.transport.ssl.verification_mode: certificate
xpack.security.transport.ssl.keystore.path: cert/elastic-node-certificate.p12
xpack.security.transport.ssl.truststore.path: cert/elastic-node-certificate.p12
ingest.geoip.downloader.enabled: false
cluster.max_shards_per_node: 20000
```

**ES Node02（192.168.1.62）的 elasticsearch.yml：**

```yaml
cluster.name: md-elasticsearch-private
node.name: elasticsearch-2
node.roles: [ master, data ]
network.host: 0.0.0.0
network.publish_host: 192.168.1.62
http.port: 9200
transport.port: 9300
path.data: /data/elasticsearch/data
path.logs: /data/elasticsearch/logs
discovery.seed_hosts: [ 192.168.1.61:9300, 192.168.1.62:9300, 192.168.1.63:9300 ]
cluster.initial_master_nodes: [ elasticsearch-1, elasticsearch-2, elasticsearch-3 ]
xpack.security.enabled: true
xpack.security.http.ssl.enabled: false
xpack.security.transport.ssl.enabled: true
xpack.security.transport.ssl.verification_mode: certificate
xpack.security.transport.ssl.keystore.path: cert/elastic-node-certificate.p12
xpack.security.transport.ssl.truststore.path: cert/elastic-node-certificate.p12
ingest.geoip.downloader.enabled: false
cluster.max_shards_per_node: 20000
```

**ES Node03（192.168.1.63）的 elasticsearch.yml：**

```yaml
cluster.name: md-elasticsearch-private
node.name: elasticsearch-3
node.roles: [ master, data ]
network.host: 0.0.0.0
network.publish_host: 192.168.1.63
http.port: 9200
transport.port: 9300
path.data: /data/elasticsearch/data
path.logs: /data/elasticsearch/logs
discovery.seed_hosts: [ 192.168.1.61:9300, 192.168.1.62:9300, 192.168.1.63:9300 ]
cluster.initial_master_nodes: [ elasticsearch-1, elasticsearch-2, elasticsearch-3 ]
xpack.security.enabled: true
xpack.security.http.ssl.enabled: false
xpack.security.transport.ssl.enabled: true
xpack.security.transport.ssl.verification_mode: certificate
xpack.security.transport.ssl.keystore.path: cert/elastic-node-certificate.p12
xpack.security.transport.ssl.truststore.path: cert/elastic-node-certificate.p12
ingest.geoip.downloader.enabled: false
cluster.max_shards_per_node: 20000
```

### 5.2.4 systemd、启动与设置 elastic 密码

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

# 三节点起来后，仅在一台重置 elastic 密码（密码仅用字母数字，避免 @ ! # &）
/usr/local/elasticsearch/bin/elasticsearch-reset-password -u elastic -i
# 验证
curl -u elastic:'<强密码>' 127.0.0.1:9200/_cat/health?v
```
