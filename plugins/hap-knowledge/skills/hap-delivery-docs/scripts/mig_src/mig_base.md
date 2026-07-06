# 文档说明

本文档面向需要将 HAP（明道云超级应用平台）单机版本（Docker Compose 一体化部署）数据迁移至 HAP 集群标准版（场景 A · 未开启 Docker Swarm 集群）新环境的实施工程师与运维工程师。文档以官方推荐方案为基础，详细描述从老环境停服到新环境验证的完整迁移路径。本文档与《HAP 部署实施文档（集群标准版 · 场景 A）》配套使用，所有新环境节点 IP 均按该场景 A 17 节点拓扑给出。

本文档以 CentOS 7.9 / Debian 12 系统为示例进行迁移操作。命令中所有 IP / 路径 / 版本号 / 密码占位符需替换为实际环境参数。

## 迁移方案适用场景

单机版本因业务量增长，需平滑升级到集群版本以获取更高的可用性与可扩展性。

已有单机环境因主机老旧或机房搬迁，需将数据原样迁移到新建的 K8s 集群。

私有云资源池整合，需将分散的单机部署归并到统一的集群部署。

## 迁移核心思路

整体方案的核心是「在老环境停止微服务后，启动一个仅挂载明道云数据目录的临时存储容器，在该容器内对内置的 MySQL、MongoDB、MinIO 服务执行导出操作，再通过网络管道传输至新集群环境对应节点完成清空与还原，最后清理 Elasticsearch 索引、Redis 缓存并启动新集群微服务」。整个流程严格按照「停服 → 导出 → 传输 → 还原 → 清理 → 启动 → 验证」的顺序串行执行。

## 内容来源

迁移规范：https://docs-pdop.mingdao.com/migration/guide

私有部署迁移到私有部署：https://docs-pdop.mingdao.com/migration/p2p/

单机迁移集群：https://docs-pdop.mingdao.com/migration/p2p/migdoc

MongoDB Database Tools：https://www.mongodb.com/try/download/database-tools

```text
迁移前提示
请按文档章节顺序执行，前置阶段未完成不得提前进入后续阶段。
新集群环境的 MongoDB、MySQL、Redis、Elasticsearch、MinIO、Kafka、Nginx 与 Kubernetes 微服务均已按集群部署文档完成部署，且各组件健康状态正常。
老单机环境与新集群环境之间网络互通，至少保证迁移传输节点之间 TCP 9900 端口可达。
新集群环境的存储容量不小于老环境实际数据量的 1.5 倍，预留充足磁盘空间。
建议在业务低峰期（夜间或周末）执行迁移，迁移期间老环境微服务需停止，新环境完成迁移前不开放对外访问。
迁移开始前，老环境与新环境数据需双向备份留底，便于出现问题时回切。
命令中所有 IP / 密码 / 域名占位符需替换为实际环境参数。
```

# 一、迁移整体流程

整个迁移过程分为十个阶段，按顺序串行执行。每个阶段都有明确的输入条件、操作步骤与验收产物，避免阶段之间出现遗漏或返工。典型迁移流程如下：

| 阶段 | 操作 | 关键产物 | 约束 / 注意 |
| --- | --- | --- | --- |
| 1. 准备 | 确认新集群部署完成；获取老单机环境登录凭据；规划停服窗口 | 停服时间表、网络白名单 | 老环境需保留完整运行能力 |
| 2. 停服 | 检查 Kafka 队列堆积；停止单机微服务 | 工作流队列已清零 | Kafka 有堆积时不可立即停服 |
| 3. 临时容器 | 启动挂载数据目录的临时容器；启动内置 mysql / mongodb / file 服务 | 可访问的内置存储服务 | 镜像 ID、容器 ID 以实际为准 |
| 4. 文件存储 | mc mirror 将单机 MinIO 数据同步到集群 MinIO | mdmedia / mdoc / mdpic / mdpub | 区分 V1 / V2 版本 |
| 5. 数据库导出 | mysqldump 导出 MySQL；mongodump 导出 MongoDB | mysql_dump、mongodb_dump 目录 | 数据量大时使用 nohup |
| 6. 数据传输 | tar + nc 管道传输到新环境 | 新环境 /data/recover 目录 | 确保接收端先启动 |
| 7. 数据库还原 | 新环境清空旧库 → 字符集修正 → 还原导入 | 已导入的 MySQL、MongoDB 业务库 | 新环境如有数据请先备份 |
| 8. 索引与缓存清理 | ES 删除业务索引；Redis flushall | 空索引列表、空 Redis | 仅清理新环境 |
| 9. 启动微服务 | 校对 config.yaml / file.yaml；启动并重刷索引 | HAP 可访问，Pod 全 2/2 | 重刷 mongodb / es 索引 |
| 10. 业务验证 | 登录系统验证应用、文件、搜索、IM | 签字确认的验证报告 | 保留老环境作为回切预案 |

# 二、停止单机版本老环境

停服是迁移工作的第一个关键步骤。停服前需要先确认 Kafka 队列内没有未消费的工作流消息，否则停服后这部分消息会丢失，导致新环境出现「工作流持续显示排队、永不消费」的现象。

## 2.1 检查老环境 Kafka 队列堆积情况

第一步：进入单机版本中存储组件容器（mingdaoyun-sc）。

```text
docker exec -it $(docker ps | grep mingdaoyun-sc | awk '{print $1}') bash
```

第二步：在容器内确认当前文件存储服务的版本（V1 或 V2）。后续文件存储迁移步骤会因版本不同而存在差异。

```text
ps aux | grep [m]inio
```

| 输出情况 | 判定结论 | 后续动作 |
| --- | --- | --- |
| 有 minio 进程输出 | 文件存储服务为 V2 版本 | 按 V2 流程：在临时容器内启动 minio 后用 mc mirror 同步 |
| 无 minio 进程输出 | 文件存储服务为 V1 版本 | 按 V1 流程：直接在临时容器内启动 filev1Run 后用 mc mirror 同步 |

第三步：检查 Kafka 工作流队列是否有消息堆积。

```text
/usr/local/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server ${ENV_KAFKA_ENDPOINTS:=127.0.0.1:9092} \
  --describe --group md-workflow-consumer | awk '{count+=$6} END {print count}'
```

仅输出 0 ：表示队列内无堆积，可以立即停止微服务。

输出大于 0 ：当前队列中仍有工作流消息待消费，需要等待全部消费完毕后再停服。

```text
严重提醒
如果在 Kafka 队列内有未消费数据时强行停止微服务，迁移完成后新环境会出现某些工作流流程一直显示排队数字、永不消失的现象，且这些显示排队的流程也不会在新环境继续消费。
正确做法：等待 awk 输出值降为 0 后，再执行后续 service.sh stopall 命令。
```

## 2.2 停止单机微服务

在确认 Kafka 队列已清空后，进入老环境安装管理器所在目录（默认 /data/mingdao/script），执行停止全部微服务的命令。

```text
cd /data/mingdao/script
bash service.sh stopall
```

命令执行后，原本 docker ps 看到的全部明道云容器均会停止。请通过 docker ps -a | grep mingdaoyun 验证容器状态确实变为 Exited。

# 三、启动临时容器

微服务停止后，原 mingdaoyun-sc 容器中内置的 MySQL、MongoDB、MinIO 服务也会一同停止。为了能够导出这些内置存储中的数据，需要单独启动一个临时容器，仅挂载明道云数据目录、并在内部按需启动各个存储服务。

## 3.1 启动挂载数据目录的临时容器

```text
docker run -itd --entrypoint bash --rm \
  -v /data/mingdao/script/volume/data/:/data/ \
  788b6f437789
```

788b6f437789 为存储组件 mingdaoyun-sc 的镜像 ID，可通过 docker images | grep mingdaoyun-sc 查看实际值。

如果单机环境的明道云数据目录不是默认的 /data/mingdao/script/volume/data/ ，需替换为实际路径。

--rm 参数确保临时容器在退出后自动清理，避免残留。

## 3.2 进入临时容器

```text
docker exec -it 363625b14db6 bash
```

363625b14db6 为上一步启动的临时容器 ID，可通过 docker ps 查看实际值。

## 3.3 在临时容器内启动各存储服务

进入临时容器后，按以下命令依次启动 MySQL、MongoDB、文件存储 V1（filev1Run）。这些命令都使用 & 放入后台。

```text
source /entrypoint.sh && mysqlStartup &
source /entrypoint.sh && mongodbStartup &
source /entrypoint.sh && filev1Run &
```

如果在 2.1 节中确认文件存储为 V2 版本，则还需要额外启动 minio 服务。注意需先在 /etc/hosts 内追加 sc 主机映射，否则 minio 启动会失败。

```text
echo "127.0.0.1 sc" >> /etc/hosts
source /entrypoint.sh && minioStartup &
```

```text
提示
上述启动命令进入后台后，建议执行 ps -ef | grep -E 'mysql|mongo|minio' 确认各进程已正常启动。
若任何一项进程启动失败，请检查 /data 目录权限、端口占用以及容器内日志。
本步骤启动的服务仅供导出使用，导出完成后无需做任何关闭操作，临时容器退出时会一并清理。
```

# 四、文件存储迁移

文件存储迁移使用 mc mirror 命令直接将单机环境内置 MinIO 中的四个业务桶（mdmedia / mdoc / mdpic / mdpub）同步到新集群环境的 MinIO。该命令支持断点续传与多线程并发，是大数据量场景下的推荐方式。

| 业务桶 | 存储内容 | 影响功能 |
| --- | --- | --- |
| mdmedia | 工作表附件、聊天文件、流程附件等用户上传文件 | 附件下载、聊天图片、流程附件预览 |
| mdoc | 在线文档与知识中心相关文件 | 知识中心、在线文档预览 |
| mdpic | 用户头像、应用 logo、封面图等图片资源 | 头像加载、应用图标显示 |
| mdpub | 公开访问资源，如静态资源与公开链接文件 | 公开链接、外部链接预览 |

## 4.1 在临时容器内配置 mc 别名

以下命令在 3.2 节进入的临时容器内执行。配置两个 MinIO 别名：minio_old 指向单机老环境内置 MinIO，minio_new 指向新集群 MinIO。

```text
mc alias set minio_old http://127.0.0.1:9000 \
  <老环境内置 MinIO AccessKey> <老环境内置 MinIO SecretKey>
 
mc alias set minio_new http://192.168.1.51:9011 \
  mingdao <强密码>
```

minio_old 中的地址 127.0.0.1:9000 与认证信息（<内置 AccessKey> / <内置 SecretKey>）为单机内置 MinIO 默认值，无需修改。

minio_new 中的 IP（192.168.1.51）为场景 A 任一中间件节点（192.168.1.51 ~ 192.168.1.54 均可），端口为 9011-9014（.51→9011 / .52→9012 / .53→9013 / .54→9014）；AccessKey 默认为 mingdao，密码请替换为新集群 MinIO 实际密码。

配置完成后可执行 mc ls minio_new 验证连通性，应返回新集群中的桶列表。

## 4.2 同步业务桶数据到新集群

使用 mc mirror 将四个业务桶分别同步到新集群 MinIO。mirror 命令会在源端与目标端之间增量比对、缺失文件才会传输，支持中断后重新执行。

```text
mc mirror minio_old/mdmedia minio_new/mdmedia
mc mirror minio_old/mdoc    minio_new/mdoc
mc mirror minio_old/mdpic   minio_new/mdpic
mc mirror minio_old/mdpub   minio_new/mdpub
```

```text
数据量与磁盘空间提示
若文件存储数据量较大（百 GB 以上），建议为每个桶单独后台执行 mirror 命令以并行加速：nohup mc mirror minio_old/mdmedia minio_new/mdmedia > mdmedia.log 2>&1 &
mc mirror 直接源端到目标端流式传输，不需要在临时容器或宿主机落盘中转，因此对临时容器所在节点的磁盘空间几乎没有要求。
同步完成后，可在新集群任一节点执行 mc du minio_new/mdmedia 等命令，对比每个桶的总容量与文件数与老环境是否一致。
```

# 五、数据库迁移

数据库迁移分为「老环境导出 → 新环境传输 → 新环境还原」三个阶段。导出全部在 3.2 节启动的临时容器内执行，导出后的数据会通过容器挂载落盘到老环境宿主机的 /data/mingdao/script/volume/data/backup 目录中。

## 5.1 MySQL 数据导出

第一步：在临时容器内创建 MySQL 数据导出目录，并切换到 backup 目录。

```text
mkdir -p /data/backup/mysql_dump
cd /data/backup/
```

第二步：使用循环逐库执行 mysqldump 导出。对包含 emoji 等特殊字符的环境，统一使用 utf8mb4 字符集。

```text
for dbname in MDApplication MDCalendar MDLog MDProject MDStructure; do
  mysqldump --set-gtid-purged=off --default-character-set=utf8mb4 \
    -h127.0.0.1 -P3306 -uroot -p123456 $dbname \
    > mysql_dump/$dbname.sql
done
```

命令中的 -p123456 为单机内置 MySQL 默认密码，如有自定义请替换为实际密码。

--set-gtid-purged=off 参数避免导出文件中带入 GTID 信息，导致新环境导入时报错。

如老环境启用了 HDP（高级数据处理）功能，请将 MDHDP 数据库一并加入导出列表。

第三步：导出文件因为容器挂载关系，会自动持久化到老环境宿主机的以下路径：

```text
/data/mingdao/script/volume/data/backup/mysql_dump/
```

## 5.2 MongoDB 数据导出

第一步：在临时容器内创建 MongoDB 数据导出目录。

```text
mkdir -p /data/backup/mongodb_dump
cd /data/backup/
```

第二步：创建待导出的 MongoDB 库列表。明道云 HAP 默认会用到 40+ 个 MongoDB 数据库，需逐一导出。

```text
cat > mongodb.list <<EOF
MDAlert
MDChatTop
MDGroup
MDHistory
MDLicense
MDNotification
MDSso
MDUser
commonbase
mdIdentification
mdactionlog
mdapproles
mdapprove
mdapps
mdattachment
mdcalendar
mdcategory
mdcheck
mddossier
mdemail
mdform
mdgroups
mdinbox
mdkc
mdmap
mdmobileaddress
mdpost
mdreportdata
mdroles
mdsearch
mdservicedata
mdsms
mdtag
mdtransfer
mdworkflow
mdworksheet
mdworkweixin
mdwsrows
pushlog
taskcenter
mdintegration
mdworksheetlog
mdworksheetsearch
mddatapipeline
mdwfplugin
mdpayment
mdwfai
EOF
```

如果旧环境启用了聚合表功能，需要将 mdaggregationwsrows 数据库加入 MongoDB 导出列表。

如果旧环境启用了 HDP 功能，需要将 mdhdp 数据库加入 MongoDB 导出列表。

第三步：执行导出。使用 mongodump 命令开启 gzip 压缩与并行集合处理。

```text
for i in $(cat mongodb.list); do
  mongodump --uri mongodb://127.0.0.1:27017/$i \
    --numParallelCollections=6 --gzip \
    -o ./mongodb_dump/
done
```

--numParallelCollections 指定并行处理集合数，默认 4，文档示例 6。如服务器 CPU、磁盘 I/O 性能较高可调大；性能受限时建议保持默认。

--gzip 启用导出文件压缩，可显著减少落盘空间与后续传输流量。

数据量较大时，建议使用 nohup 放后台执行，避免 SSH 会话中断导致导出失败：

```text
nohup bash -c 'for i in $(cat mongodb.list); do
  mongodump --uri mongodb://127.0.0.1:27017/$i \
    --numParallelCollections=6 --gzip -o ./mongodb_dump/
done' > mongodump.log 2>&1 &
```

导出文件会持久化保存到老环境宿主机的以下路径：

```text
/data/mingdao/script/volume/data/backup/mongodb_dump/
```

# 六、数据传输

数据传输使用 tar 与 nc（netcat）管道方式，将打包流式传输到新环境，避免在中转节点上重复落盘。整个过程需要先启动「接收端」，再启动「发送端」，否则会因连接被拒绝而失败。

```text
传输前置检查
确认老环境宿主机与新环境对应节点之间网络互通，可通过 telnet 或 nc -zv 提前测试。
确认新环境节点上 9900 端口未被占用，且防火墙已放行该端口。
确认新环境对应节点的 /data 分区有足够剩余空间，至少能容纳老环境导出文件总和。
```

## 6.1 MySQL 数据传输

第一步：在新集群环境的 MySQL MGR Primary 节点（场景 A 默认 192.168.1.31）上启动接收端。

```text
mkdir -p /data/recover && cd /data/recover
nc -l 9900 | tar -zxvf -
```

接收端启动后会一直阻塞等待发送端连接，看到流式输出文件列表后表示传输已开始。

第二步：在老环境宿主机上进入导出文件所在目录，启动发送端。

```text
cd /data/mingdao/script/volume/data/backup
tar -zcvf - mysql_dump | nc 192.168.1.31 9900
```

命令中的 192.168.1.31 替换为新集群 MySQL master 节点的实际 IP。

发送端命令完成后，接收端的 nc 进程会自动退出，可在 /data/recover/ 下查看到 mysql_dump/ 目录。

## 6.2 MongoDB 数据传输

MongoDB 数据传输操作流程与 MySQL 相同，区别在于接收端是新集群的 MongoDB primary 节点。

第一步：在新集群 MongoDB Primary 节点（场景 A 默认 192.168.1.31）启动接收端。

```text
mkdir -p /data/recover && cd /data/recover
nc -l 9900 | tar -zxvf -
```

第二步：在老环境宿主机启动发送端。

```text
cd /data/mingdao/script/volume/data/backup
tar -zcvf - mongodb_dump | nc 192.168.1.31 9900
```

命令中的 192.168.1.31 替换为新集群 MongoDB primary 节点的实际 IP。如果 MySQL 与 MongoDB 复用同一台传输机器，可分别使用不同端口（如 9900、9901）以避免冲突。

# 七、数据库还原

```text
严重风险提示
MySQL 与 MongoDB 数据在新环境还原前，会先执行 drop database 清空新环境当前业务库！
如果新集群在迁移之前已经被使用过（哪怕只做过一次登录测试），相关的业务数据将被永久删除，无法找回。
执行还原前必须再次确认：(1) 新环境的现有数据可以放弃；(2) 新环境的微服务已停止；(3) 已为新环境做过快照或备份。
```

## 7.1 MySQL 数据还原

```text
通用说明
场景 A 下 MySQL 采用 MGR + Router 模式部署，下列 MySQL 还原命令应通过 Router 端口 6446 连接（写入会自动路由到当前 PRIMARY），不要直连 3306（直连 SECONDARY 会因只读而失败）。命令统一形式为：mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码>。
命令中的 -p<强密码> 请替换为新环境实际的 root 密码。
如果新环境启用了 HDP，请在每一步同时处理 MDHDP 数据库。
```

### 7.1.1 删除新环境的 HAP 业务库

```text
/usr/local/mysql/bin/mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码> <<< 'drop database MDApplication;'
/usr/local/mysql/bin/mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码> <<< 'drop database MDCalendar;'
/usr/local/mysql/bin/mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码> <<< 'drop database MDLog;'
/usr/local/mysql/bin/mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码> <<< 'drop database MDProject;'
/usr/local/mysql/bin/mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码> <<< 'drop database MDStructure;'
```

如启用 HDP，请补充：

```text
/usr/local/mysql/bin/mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码> <<< 'drop database MDHDP;'
```

### 7.1.2 重建空的 HAP 业务库

```text
/usr/local/mysql/bin/mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码> <<< 'create database MDApplication;'
/usr/local/mysql/bin/mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码> <<< 'create database MDCalendar;'
/usr/local/mysql/bin/mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码> <<< 'create database MDLog;'
/usr/local/mysql/bin/mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码> <<< 'create database MDProject;'
/usr/local/mysql/bin/mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码> <<< 'create database MDStructure;'
```

### 7.1.3 字符集修正

老单机环境部分老版本可能仍使用 utf8 字符集，新集群环境统一使用 utf8mb4。导入前需先对 SQL 文件执行字符集替换，否则会出现 4 字节 emoji 等字符无法存储的问题。

```text
for dbname in MDApplication MDCalendar MDLog MDProject MDStructure; do
  sed -ri 's/CHARSET=utf8(;| )/CHARSET=utf8mb4\1/g' \
    /data/recover/mysql_dump/$dbname.sql
done
 
# MDProject 库历史结构中存在 utf8_bin 排序规则，单独处理
sed -i 's/CHARACTER SET utf8 COLLATE utf8_bin //' \
  /data/recover/mysql_dump/MDProject.sql
```

如旧环境启用 HDP，对 MDHDP.sql 执行同样的字符集替换：

```text
sed -ri 's/CHARSET=utf8(;| )/CHARSET=utf8mb4\1/g' /data/recover/mysql_dump/MDHDP.sql
```

### 7.1.4 导入备份数据

```text
/usr/local/mysql/bin/mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码> --default-character-set utf8mb4 \
  -D MDApplication < /data/recover/mysql_dump/MDApplication.sql
/usr/local/mysql/bin/mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码> --default-character-set utf8mb4 \
  -D MDCalendar   < /data/recover/mysql_dump/MDCalendar.sql
/usr/local/mysql/bin/mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码> --default-character-set utf8mb4 \
  -D MDLog        < /data/recover/mysql_dump/MDLog.sql
/usr/local/mysql/bin/mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码> --default-character-set utf8mb4 \
  -D MDProject    < /data/recover/mysql_dump/MDProject.sql
/usr/local/mysql/bin/mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码> --default-character-set utf8mb4 \
  -D MDStructure  < /data/recover/mysql_dump/MDStructure.sql
```

如启用 HDP，请补充导入 MDHDP.sql：

```text
/usr/local/mysql/bin/mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码> --default-character-set utf8mb4 \
  -D MDHDP < /data/recover/mysql_dump/MDHDP.sql
```

## 7.2 MongoDB 数据还原

### 7.2.1 创建删除库脚本

将所有 HAP 用到的 MongoDB 业务库整理成 dropMongodb.list 文件，后续一次性执行 drop。

```text
cat > dropMongodb.list <<EOF
use MDAlert
db.dropDatabase()
use MDChatTop
db.dropDatabase()
use MDGroup
db.dropDatabase()
use MDHistory
db.dropDatabase()
use MDLicense
db.dropDatabase()
use MDNotification
db.dropDatabase()
use MDSso
db.dropDatabase()
use MDUser
db.dropDatabase()
use commonbase
db.dropDatabase()
use mdIdentification
db.dropDatabase()
use mdactionlog
db.dropDatabase()
use mdapproles
db.dropDatabase()
use mdapprove
db.dropDatabase()
use mdapps
db.dropDatabase()
use mdattachment
db.dropDatabase()
use mdcalendar
db.dropDatabase()
use mdcategory
db.dropDatabase()
use mdcheck
db.dropDatabase()
use mddossier
db.dropDatabase()
use mdemail
db.dropDatabase()
use mdform
db.dropDatabase()
use mdgroups
db.dropDatabase()
use mdinbox
db.dropDatabase()
use mdkc
db.dropDatabase()
use mdmap
db.dropDatabase()
use mdmobileaddress
db.dropDatabase()
use mdpost
db.dropDatabase()
use mdreportdata
db.dropDatabase()
use mdroles
db.dropDatabase()
use mdsearch
db.dropDatabase()
use mdservicedata
db.dropDatabase()
use mdsms
db.dropDatabase()
use mdtag
db.dropDatabase()
use mdtransfer
db.dropDatabase()
use mdworkflow
db.dropDatabase()
use mdworksheet
db.dropDatabase()
use mdworkweixin
db.dropDatabase()
use mdwsrows
db.dropDatabase()
use pushlog
db.dropDatabase()
use taskcenter
db.dropDatabase()
use mdintegration
db.dropDatabase()
use mdworksheetlog
db.dropDatabase()
use mdworksheetsearch
db.dropDatabase()
use mddatapipeline
db.dropDatabase()
use mdwfplugin
db.dropDatabase()
use mdpayment
db.dropDatabase()
use mdwfai
db.dropDatabase()
EOF
```

若新环境启用聚合表，请将 mdaggregationwsrows 加入 dropMongodb.list 列表。

若新环境启用 HDP，请将 mdhdp 加入 dropMongodb.list 列表。

### 7.2.2 删除新环境业务库

```text
/usr/local/mongodb/bin/mongo \
  mongodb://root:<强密码>@192.168.1.31:27017/admin?authSource=admin&replicaSet=local-mongodb-one < dropMongodb.list
```

### 7.2.3 安装 mongodb-database-tools 工具包

新集群环境通常默认未安装 mongorestore 命令，需要单独下载工具包。请根据新环境的操作系统选择对应版本，参考下表：

| 操作系统 | 下载链接 |
| --- | --- |
| RedHat / CentOS 8.0 x64 | https://fastdl.mongodb.org/tools/db/mongodb-database-tools-rhel80-x86_64-100.9.3.tgz |
| Debian 12.0 x64 | https://fastdl.mongodb.org/tools/db/mongodb-database-tools-debian12-x86_64-100.9.3.tgz |
| 麒麟 / 统信等国产 OS | 一般使用 RedHat 8.0 对应的版本即可 |

下载后上传到 MongoDB primary 节点并解压，记录下 mongorestore 二进制的实际路径，后续命令需替换。

### 7.2.4 还原 MongoDB 数据

```text
for dbname in $(ls /data/recover/mongodb_dump/); do
  /your_path/mongorestore --host 192.168.1.31 \
    -u root -p <强密码> --authenticationDatabase admin \
    --numParallelCollections=6 --numInsertionWorkersPerCollection=2 \
    -d $dbname --gzip \
    --dir /data/recover/mongodb_dump/$dbname/
done
```

/your_path/mongorestore 替换为上一步解压后的实际路径。

--numParallelCollections 默认 4，示例 6。

--numInsertionWorkersPerCollection 默认 1，示例 2。两个并行参数都可根据 MongoDB 服务器性能适当调整，但不建议超过 CPU 核心数。

数据量较大时，建议使用 nohup 后台执行，避免 SSH 中断：

```text
nohup bash -c '
for dbname in $(ls /data/recover/mongodb_dump/); do
    /your_path/mongorestore --host 192.168.1.31 \
      -u root -p <强密码> --authenticationDatabase admin \
      --numParallelCollections=6 --numInsertionWorkersPerCollection=2 \
      -d "$dbname" --gzip \
      --dir "/data/recover/mongodb_dump/$dbname/"
done' > mongorestore.log 2>&1 &
```

### 7.2.5 修正组织 ID 绑定

HAP License 与组织 ID 绑定，迁移后新环境的组织 ID 与老环境不一致。需要在 ClientLicense 库中将新环境的组织 ID 修正为老环境的组织 ID，否则会出现 License 校验失败、应用无法访问的现象。

```text
/usr/local/mongodb/bin/mongo -h 192.168.1.31 -u root -p <强密码> --authenticationDatabase admin
 
> use ClientLicense;
> db.projects.updateMany(
>   { "projectID": "新环境组织ID" },
>   { $set: { "projectID": "老环境组织ID" } }
> );
```

「老环境组织 ID」可在老环境管理后台 → 组织管理页面查询。

「新环境组织 ID」可在新环境部署完成后，未导入数据前的管理后台中查询。

# 八、Elasticsearch 索引清理

新环境微服务首次启动前，新集群 Elasticsearch 中不应残留任何 HAP 业务索引（部署调试期间会自动创建一些索引）。微服务启动后会自动重建符合当前数据特征的索引。场景 A 下 ES 共置中间件节点 02/03/04（192.168.1.52 / 192.168.1.53 / 192.168.1.54），下列命令在任一 ES 节点上执行即可，127.0.0.1:9200 表示本机 ES 服务。

## 8.1 查看新环境索引列表

```text
curl -u elastic:<强密码> 127.0.0.1:9200/_cat/indices
```

典型输出示例（输出中第三列为索引名称）：

```text
green open chatmessage_190329                            Ed7b0fAeT2C4MT7zdxykDQ 1 1   0 0    450b    225b
green open actionlogb304361c-84ea-4f17-8ce2-bd11111115d3 SQx-1XftQ6e2Q95QSfjXZw 5 1 141 0   1.5mb 790.4kb
green open usedata                                       59PEzs1uSsuHU-HWRy27jA 5 1  13 0 178.4kb  89.2kb
green open actionlog9                                    UClpsSWkS7q1fIL6z6LxfQ 5 1  12 0 277.7kb 138.8kb
green open kcnode_190329                                 2Zxqp0uyQKKRLq7xjtaC1w 1 1   0 0    450b    225b
green open post_190723                                   0Cnp7rQjQRWb8gw5fFv9Dg 1 1   3 0  32.2kb  16.1kb
green open task_190723                                   PT5sEOV_Sq6AI29vhUe1bQ 1 1   1 0  15.2kb   7.6kb
```

## 8.2 删除业务索引

方式 A：逐个删除（适合索引较少的场景，便于精确控制）。

```text
curl -XDELETE -u elastic:<强密码> 127.0.0.1:9200/chatmessage_190329
curl -XDELETE -u elastic:<强密码> 127.0.0.1:9200/actionlogb304361c-84ea-4f17-8ce2-bd11111115d3
curl -XDELETE -u elastic:<强密码> 127.0.0.1:9200/usedata
curl -XDELETE -u elastic:<强密码> 127.0.0.1:9200/actionlog9
curl -XDELETE -u elastic:<强密码> 127.0.0.1:9200/kcnode_190329
curl -XDELETE -u elastic:<强密码> 127.0.0.1:9200/post_190723
curl -XDELETE -u elastic:<强密码> 127.0.0.1:9200/task_190723
```

方式 B：脚本一键清理（适合索引较多的场景）。

```text
elastic_pwd=<强密码>
for i in $(curl -u elastic:$elastic_pwd 127.0.0.1:9200/_cat/indices | awk '{print $3}'); do
  curl -XDELETE -u elastic:$elastic_pwd 127.0.0.1:9200/$i
done
```

## 8.3 校验清理结果

```text
curl -u elastic:<强密码> 127.0.0.1:9200/_cat/indices
```

命令执行后如果没有任何索引返回，说明清理成功。

```text
注意
Elasticsearch 索引清理仅在新集群环境执行，老单机环境的 ES 索引保持不动。
若新集群中除 HAP 索引外还有其他业务的索引，请改用方式 A 精确删除，避免误清理。
本步骤必须在新环境微服务启动前完成；启动后再删除索引会导致正在写入的请求报错。
```

# 九、Redis 缓存清理

新环境微服务首次启动前，需要清空新集群 Redis 缓存，避免部署调试阶段的脏缓存数据混入生产数据。

## 9.1 执行清理命令

```text
/usr/local/redis/bin/redis-cli -a <强密码> "flushall"
```

命令中的 -a <强密码> 替换为新集群 Redis 实际密码。

flushall 会清空 Redis 中所有 db（db0 ~ db15）的数据，操作不可逆。

场景 A 新集群采用 Redis 哨兵模式部署（192.168.1.41 / 192.168.1.42 / 192.168.1.43）。执行 flushall 前请先在任一节点执行 redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster 查询当前 Master 的 IP，然后到该 Master 节点上执行 flushall。

```text
注意
Redis 清理仅在新集群环境执行，老单机环境的 Redis 保持不动。
如果新集群除 HAP 业务外还运行了其他业务并共享同一 Redis，必须协调好各业务方再执行；建议为 HAP 配置独立的 Redis 实例。
```

# 十、新环境微服务启动

## 10.1 校对配置文件

如果新集群环境的对外访问地址与老单机环境不同，需要先修改两份核心配置中的访问地址变量，否则启动后会出现地址错乱、回调失败等问题。

| 配置文件 | 需要校对的变量 | 说明 |
| --- | --- | --- |
| 微服务 config.yaml | ENV_ADDRESS_MAIN | HAP 主访问地址，本环境为 https://hap.domain.com |
| 微服务 config.yaml | ENV_ADDRESS_ALLOWLIST | 允许的访问域名白名单，多个用英文逗号分隔 |
| File 服务 file.yaml | ENV_MINGDAO_HOST | HAP 主域名（不含协议） |
| File 服务 file.yaml | ENV_MINGDAO_PROTO | 协议（http 或 https） |
| File 服务 file.yaml | ENV_MINGDAO_PORT | 端口号，默认 80 / 443 时可省略 |

## 10.2 启动微服务

使用集群部署提供的启动脚本拉起全部 HAP 微服务。场景 A 下控制节点默认为 K8s Master 01（192.168.1.21）。

```text
cd /data/mingdao/script/kubernetes/
bash ./restart.sh
```

## 10.3 检查 Pod 状态

启动后通过 kubectl get pod 命令观察所有 HAP 相关 Pod，确认全部进入 Running 且 READY 列为 2/2。

```text
kubectl get pod -o wide | grep -v Running
# 上述命令应无任何业务 Pod 输出
kubectl get pod
```

如有 Pod 处于 Pending、CrashLoopBackOff 或 0/2 状态，需要先用 kubectl describe pod <pod-name> 与 kubectl logs <pod-name> 排查启动异常，再执行后续重刷索引步骤。

## 10.4 重刷 MongoDB 索引

数据导入后，部分 MongoDB 集合的索引可能与新版本不一致，需要在 config 容器内重刷。

```text
# 进入 config 容器
kubectl exec -it $(kubectl get pod | grep config | awk 'NR==1{print $1}') -- bash
 
# 重刷 MongoDB 索引
source /entrypoint.sh && mongodbUpdateIndex
```

## 10.5 重刷 Elasticsearch 索引

MongoDB 索引重刷完成后，继续在 config 容器内执行 ES 索引重建。该过程会扫描业务数据并重新写入 Elasticsearch，耗时与数据量相关。

```text
source /entrypoint.sh && resetCollaborationIndex
```

```text
提示
重刷 Elasticsearch 索引期间，新环境登录系统后全局搜索、操作日志可能短暂为空，属于正常现象。
命令执行结束、回到 shell 提示符后，可在 Elasticsearch 中重新执行 _cat/indices ，确认 chatmessage、actionlog、kcnode、post、task 等索引已重新出现。
```

# 十一、迁移验证与回切预案

## 11.1 业务功能验证清单

按以下清单逐项验证，每完成一项在《HAP 私有部署交付清单》中勾选签字。

| 序号 | 验证项 | 验证方法 | 预期结果 |
| --- | --- | --- | --- |
| 1 | 登录验证 | 使用业务管理员账号登录新环境 | 登录成功，组织信息与老环境一致 |
| 2 | 应用列表完整性 | 进入工作台，查看应用列表 | 应用数量、图标、排序与老环境一致 |
| 3 | 工作表数据 | 随机抽查 5～10 个核心应用，进入工作表 | 数据行数、字段、视图均完整 |
| 4 | 工作流状态 | 查看工作流列表与运行实例 | 工作流定义完整，历史实例可查 |
| 5 | 自定义页面 | 进入自定义页面查看图表数据 | 图表可正常加载，数据准确 |
| 6 | 附件功能 | 下载附件、预览图片、查看文档 | 全部可正常加载 |
| 7 | 全局搜索 | 在搜索框输入关键词 | 返回结果（说明 ES 已重建） |
| 8 | 操作日志 | 进入应用操作日志页面 | 可查询历史操作记录 |
| 9 | 消息推送 | 触发一条聊天或工作流消息 | 对应用户可收到通知 |
| 10 | IM 聊天 | 用户之间互发消息 | 消息可送达、历史聊天记录完整 |
| 11 | License 校验 | 查看管理后台 License 信息 | License 状态正常、未过期 |
| 12 | 组织成员 | 查看部门、成员列表 | 成员数量、组织架构与老环境一致 |

## 11.2 回切预案

迁移过程中始终保留老单机环境的完整运行能力，不要立即销毁老环境，以便万一新环境验证失败时快速回切。

| 回切步骤 | 操作 | 目标 |
| --- | --- | --- |
| 1. 暂停切流 | DNS 或负载均衡 VIP 暂不指向新环境 | 用户访问仍走老环境 |
| 2. 启动老环境 | 在老单机宿主机执行 bash service.sh startall | 老环境微服务恢复运行 |
| 3. 验证老环境 | 通过老环境地址登录、随机抽查业务 | 确认老环境数据完整可用 |
| 4. 切回访问 | DNS 或 VIP 维持指向老环境 | 用户体感无感知 |
| 5. 处理新环境 | 在新集群删除已导入的业务库、重置 ES、清空 Redis | 新环境恢复到部署完成时的初始状态 |
| 6. 复盘分析 | 整理迁移失败原因，输出根因报告 | 为下一次迁移提供改进依据 |

```text
回切窗口期建议
建议老单机环境在迁移成功验证后保留 7～14 天，期间可作为只读历史查询使用。
保留期满、业务方书面确认数据无问题后，再正式释放老环境资源。
正式下线老环境前，建议对老环境数据再做一次完整冷备份，永久归档保存。
```

# 十二、附录

## 12.1 命令速查表

| 阶段 | 命令简述 | 执行位置 |
| --- | --- | --- |
| 停服检查 | kafka-consumer-groups.sh ... | awk '{count+=$6}' | 老 mingdaoyun-sc 容器内 |
| 停服 | bash service.sh stopall | 老环境宿主机 |
| 临时容器 | docker run -itd --entrypoint bash --rm -v /data/mingdao/script/volume/data/:/data/ <镜像ID> | 老环境宿主机 |
| 内置 mysql | source /entrypoint.sh && mysqlStartup & | 临时容器内 |
| 内置 mongo | source /entrypoint.sh && mongodbStartup & | 临时容器内 |
| 内置 file V1 | source /entrypoint.sh && filev1Run & | 临时容器内 |
| 内置 minio V2 | source /entrypoint.sh && minioStartup & | 临时容器内 |
| 文件迁移 | mc mirror minio_old/<bucket> minio_new/<bucket>  # minio_new 指向 192.168.1.51:9000 | 临时容器内 |
| MySQL 导出 | mysqldump --set-gtid-purged=off --default-character-set=utf8mb4 ... | 临时容器内 |
| MongoDB 导出 | mongodump --uri ... --numParallelCollections=6 --gzip | 临时容器内 |
| 数据传输 | tar -zcvf - <dir> | nc <new_ip> 9900 | 老环境宿主机 → 192.168.1.31（新环境数据库节点） |
| MySQL 还原 | mysql -h 192.168.1.31 -P 6446 -uroot -p<强密码> --default-character-set utf8mb4 -D <db> < <db>.sql | 新环境 192.168.1.31（MGR Router 端口 6446） |
| MongoDB 还原 | mongorestore --host 192.168.1.31 -u root -p <强密码> --authenticationDatabase admin --gzip --dir ... -d <db> | 新环境 192.168.1.31（MongoDB Primary） |
| ES 清理 | curl -XDELETE -u elastic:<强密码> 127.0.0.1:9200/<index> | 新环境 192.168.1.52-192.168.1.54 任一 ES 节点 |
| Redis 清理 | redis-cli -a <强密码> flushall | 新环境当前 Redis Master（参见 9.1 说明） |
| 微服务启动 | bash /data/mingdao/script/kubernetes/restart.sh | 新环境 K8s 控制节点 192.168.1.21 |
| 重刷索引 | source /entrypoint.sh && mongodbUpdateIndex | 新环境 K8s 中 config 容器内 |
| 重刷索引 | source /entrypoint.sh && resetCollaborationIndex | 新环境 K8s 中 config 容器内 |

## 12.2 常见问题排查

| 现象 | 可能原因 | 处理建议 |
| --- | --- | --- |
| nc 接收端报「Address already in use」 | 9900 端口被占用 | 更换其他端口（如 9901、9999）或释放占用进程 |
| mongorestore 报「authentication failed」 | 密码错误或 authenticationDatabase 不正确 | 确认 -u root -p <实际密码> --authenticationDatabase admin 三参数完整 |
| MySQL 导入后中文乱码 | 字符集未替换为 utf8mb4 或导入未指定 utf8mb4 | 重新执行 7.1.3 字符集替换 + 7.1.4 导入 |
| 新环境登录后提示 License 不匹配 | 组织 ID 未修正 | 执行 7.2.5 中的 db.projects.updateMany 修正组织 ID |
| 全局搜索无结果 | ES 索引未重刷 | 进入 config 容器执行 resetCollaborationIndex |
| 工作流持续显示排队不消费 | 停服时 Kafka 队列有未消费消息 | 重新评估迁移完整性，必要时回切或局部补偿 |
| mc mirror 中途中断 | 网络抖动或权限失效 | 重新执行同一条 mc mirror 命令，会自动续传 |
| Pod 持续 0/2 或 CrashLoopBackOff | config.yaml / file.yaml 配置错误 | kubectl logs 查看具体报错，校对 10.1 配置项 |

## 12.3 迁移交付确认

| 迁移开始时间 |  |
| --- | --- |
| 迁移完成时间 |  |
| 停服窗口时长 |  |
| 实施工程师 |  |
| 客户验收人 |  |
| 验收结论 | □ 通过    □ 不通过（附原因） |
| 签字日期 |  |

```text
迁移完成
至此完成全部数据迁移工作。
请在《HAP 私有部署交付清单》中勾选迁移项并签字归档。
祝业务在新集群环境中运行顺利。
```
