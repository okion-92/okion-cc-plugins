# Kafka / 队列 / ZooKeeper

> 由 sources/faq/ 生成，勿手改。每条 `## <slug>` 对应一个 source 文件，可在 ROUTING.md 反查。

## arm64-zookeeper-systemd-g1gc — arm64 zookeeper systemd 启动失败（UseG1GC 实验选项）


现象：systemd 启动 zookeeper 报 `VM option 'UseG1GC' is experimental and must be enabled via -XX:+UnlockExperimentalVMOptions`，单命令能启但 systemd 起不来。

解决：在 `-XX:+UseG1GC` 前补 `-XX:+UnlockExperimentalVMOptions`：
```bash
sed -ri 's/(-XX:\+UseG1GC)/-XX:\+UnlockExperimentalVMOptions\ \1/g' /usr/local/kafka/bin/kafka-run-class.sh
grep UseG1GC /usr/local/kafka/bin/kafka-run-class.sh
systemctl restart zookeeper.service
```
（zookeeper-server-start.sh 或 kafka-run-class.sh 里找 UseG1GC。）

## kafka-1.1.1-fix-log4j-cve — Kafka v1.1.1 修复 Log4J 漏洞（替换 log4j/slf4j jar 到 2.18.0）


### 适用场景
私有部署 Kafka 1.1.1 修复 Log4J 漏洞，把 libs 下旧 log4j/slf4j jar 替换为 2.18.0。

### 步骤

#### 备份程序目录
```bash
cp -r /usr/local/kafka/ /usr/local/kafka.backup-$(date +%Y%m%d%H%M%S)
```

#### 进入程序目录
```bash
cd /usr/local/kafka/libs/
```

#### 查看当前 jar 包版本
```bash
ls -l log4j-core-*.jar log4j-api-*.jar log4j-1.2-api-*.jar log4j-slf4j-impl-*.jar slf4j-api-*.jar
ls -l slf4j-api-1.7.25.jar slf4j-log4j12-1.7.25.jar log4j-1.2.17.jar
```

#### 删除旧版本 jar 包
```bash
rm -f log4j-core-*.jar log4j-api-*.jar log4j-1.2-api-*.jar log4j-slf4j-impl-*.jar slf4j-api-*.jar
rm -f slf4j-api-1.7.25.jar slf4j-log4j12-1.7.25.jar log4j-1.2.17.jar
```

#### 下载最新 jar 包
```bash
curl -O https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-core/2.18.0/log4j-core-2.18.0.jar
curl -O https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-api/2.18.0/log4j-api-2.18.0.jar
curl -O https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-1.2-api/2.18.0/log4j-1.2-api-2.18.0.jar
curl -O https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-slf4j-impl/2.18.0/log4j-slf4j-impl-2.18.0.jar
curl -O https://repo1.maven.org/maven2/org/slf4j/slf4j-api/1.7.36/slf4j-api-1.7.36.jar
```

#### 确认 jar 版本已最新
```bash
ls -l log4j-core-*.jar log4j-api-*.jar log4j-1.2-api-*.jar log4j-slf4j-impl-*.jar slf4j-api-*.jar
```

#### 修改文件权限（默认用 kafka.kafka）
```bash
chmod kafka.kafka log4j-core-*.jar log4j-api-*.jar log4j-1.2-api-*.jar log4j-slf4j-impl-*.jar slf4j-api-*.jar
```

#### zookeeper 启动失败时关闭 jmx
先 `vim /usr/local/kafka/bin/zookeeper-server-start.sh` 查看是否已有 `-Dzookeeper.jmx.log4j.disable=true`，没有则执行：
```bash
sed -i 's/org.apache.zookeeper.server.quorum.QuorumPeerMain/-Dzookeeper.jmx.log4j.disable=true org.apache.zookeeper.server.quorum.QuorumPeerMain/' /usr/local/kafka/bin/zookeeper-server-start.sh
```

#### 重启服务
```bash
systemctl restart zookeeper kafka
```

### 核验
```bash
ss -tnlp | grep '2181\|9092'
```
2181（zookeeper）与 9092（kafka）端口均已监听。

## kafka-backlog-count-by-group — Kafka 各消费组堆积数量查看（工作流 / 汇总关联 / 字段编辑）


### 场景
快速看某个消费组当前总堆积（lag = $6 列汇总）。先进任意一台微服务容器：
```bash
docker exec -it $(docker ps | grep community | awk '{print $1}') bash
```

### 各消费组堆积
```bash
# 工作流队列
/usr/local/kafka/bin/kafka-consumer-groups.sh --bootstrap-server ${ENV_KAFKA_ENDPOINTS:=127.0.0.1:9092} \
  --describe --group md-workflow-consumer | awk '{count+=$6}END{print count}'

# 汇总、关联字段队列
... --group worksheet-passiverelation | awk '{count+=$6}END{print count}'

# 表单字段编辑队列
... --group worksheet-editcontrols | awk '{count+=$6}END{print count}'
```

### 实时盯（watch，注意转义 \$6）
```bash
watch -n1 -d "/usr/local/kafka/bin/kafka-consumer-groups.sh --bootstrap-server ${ENV_KAFKA_ENDPOINTS:=127.0.0.1:9092} --describe --group md-workflow-consumer | awk '{count+=\$6}END{print count}'"
```

> 自动告警脚本见 [[kafka-lag-alert-script]]，重平衡自恢复见 [[kafka-rebalance-watch]]。

## kafka-consume-message-content — Kafka 查询队列中的消息内容（消费速度 / processId 统计）


### 场景
要查 Kafka 队列里的消息内容、观察消费速度 / 定位刷队列的工作流。

### 观察短时间内的消费速度
多次执行，看间隔内消费量变化（$4/$5/$6 = current/log-end/lag 汇总）：
```bash
/usr/local/kafka/bin/kafka-consumer-groups.sh --bootstrap-server ${ENV_KAFKA_ENDPOINTS:=127.0.0.1:9092} \
  --describe --group md-workflow-consumer | awk '{c1+=$4;c2+=$5;c3+=$6}END{print c1,c2,c3}'

# 按具体 Topic 过滤
... | grep WorkFlow         | awk '{c1+=$4;c2+=$5;c3+=$6}END{print c1,c2,c3}'
... | grep WorkFlow-Process | awk '{c1+=$4;c2+=$5;c3+=$6}END{print c1,c2,c3}'
```

### 用 kafkactl 查看消息内容
```bash
# 各 Topic 实时消息
kafkactl consume WorkFlow         -o yaml -t
kafkactl consume WorkFlow-Batch   -o yaml -t
kafkactl consume WorkFlow-Button  -o yaml -t
kafkactl consume WorkFlow-Process -o yaml -t
kafkactl consume WorkFlow-Router  -o yaml -t

# 最后 1000 条里的 processId 去重统计排序（定位刷队列的工作流）
kafkactl consume WorkFlow --tail=1000 -o yaml | grep value | grep -oP 'processId":".*?"' | sort | uniq -c | sort -n
kafkactl consume WorkFlow-Process --tail=1000 -o yaml | grep value | grep -oP 'processId":".*?"' | sort | uniq -c | sort -n
kafkactl consume WorkFlow-Router  --tail=1000 -o yaml | grep value | grep -oP 'processId":".*?"' | sort | uniq -c | sort -n
```

### 用原生 kafka 命令查指定分区历史流程
```bash
/usr/local/kafka/bin/kafka-console-consumer.sh --bootstrap-server $ENV_KAFKA_ENDPOINTS \
  --topic WorkFlow-Process --partition 0 --offset 65015 | head -n1000 \
  | grep -oP 'processId":".*?"' | sort | uniq -c
```
> 按时间点查偏移量见 [[kafka-view-topic-messages-by-time]]。

## kafka-lag-alert-script — Kafka 消息堆积告警监控脚本


### 场景
要给 Kafka 消息堆积配自动告警监控（超阈值 / 持续增加）。

告警规则（每 5 分钟判断）：Topic 堆积达阈值告警；下次仍超阈值且大于上次→"持续增加"；小于上次但仍超阈值→"有减少但仍高"。WorkFlow/WorkSheet 阈值 3000，慢队列(WorkFlow-Router/WorkSheet-Router) 6000。

`/usr/local/sbin/kafkaCheckConsumerGroup.sh`（改 API_URL、kafka 路径、连接地址）：
```bash
#!/bin/bash
KAFKA_CONSUMER_GROUP=$1; TOPIC=$2; ALERT_COUNT=$3
API_URL=http://<告警API>
TEMP_FILE=/tmp/checkLAG-$TOPIC.temp
TEMP_NUM=/tmp/checkNUM-$TOPIC.temp
countLAG=$(/usr/local/kafka/bin/kafka-consumer-groups.sh --bootstrap-server <kafka>:9092 --describe --group $KAFKA_CONSUMER_GROUP | grep -P "$TOPIC " | awk 'BEGIN{c=0}{c=c+$6}END{print c}')
if [[ ${countLAG} -gt ${ALERT_COUNT} ]]; then
  if [[ $(cat $TEMP_NUM) -eq 0 ]]; then
    curl -d "{...达到阈值，堆积:${countLAG}...}" ${API_URL}; echo 1 > $TEMP_NUM
  else
    if [[ ${countLAG} -gt $(cat $TEMP_FILE) ]]; then curl -d "{...持续增加...}" ${API_URL}
    else curl -d "{...有减少但仍超阈值...}" ${API_URL}; fi
  fi
else echo 0 > $TEMP_NUM; fi
echo ${countLAG} > $TEMP_FILE
```
crontab（每 5 分钟，按 topic）：
```cron
*/5 * * * * /bin/bash /usr/local/sbin/kafkaCheckConsumerGroup.sh md-workflow-consumer WorkFlow 3000 >/dev/null 2>&1
*/5 * * * * /bin/bash /usr/local/sbin/kafkaCheckConsumerGroup.sh md-workflow-consumer WorkFlow-Batch 3000 >/dev/null 2>&1
*/5 * * * * /bin/bash /usr/local/sbin/kafkaCheckConsumerGroup.sh md-workflow-consumer WorkSheet 3000 >/dev/null 2>&1
*/5 * * * * /bin/bash /usr/local/sbin/kafkaCheckConsumerGroup.sh md-workflow-consumer WorkSheet-Router 6000 >/dev/null 2>&1
*/5 * * * * /bin/bash /usr/local/sbin/kafkaCheckConsumerGroup.sh md-workflow-consumer WorkFlow-Router 6000 >/dev/null 2>&1
# 其余 topic：WorkFlow-Button/WorkFlow-Process/WorkSheet-Batch 同 3000
```

## kafka-rebalance-watch — Kafka 消费组重平衡检测与自恢复脚本


### 场景
要自动检测 Kafka 消费组重平衡并自恢复（rollout restart）。

巡检脚本逻辑（`kafka-rebalance-watch.sh`）：
1. 检测消费组状态（基于 `--describe` 输出/错误）：匹配 `rebalanc(e|ing)`/`PreparingRebalance`/`CompletingRebalance` → 重平衡；`has no active members` → Empty。
2. 检测失败：等待 `ERROR_RECHECK_WAIT` 秒后重试，仍失败则发通知。
3. 重平衡：等待 `REBALANCE_INITIAL_WAIT` 秒后复检，仍重平衡则 `kubectl rollout restart <KUBE_RESOURCE>`，再等 `RECHECK_WAIT` 秒复检，仍异常则通知。
4. `Empty` 且 `TREAT_EMPTY_AS_ALERT=1` 时按异常处理。

cron（内部 flock 加锁避免并发）：
```cron
# 每分钟
* * * * * /bin/bash kafka-rebalance-watch.sh 2>&1
# 每 5 分钟
*/5 * * * * /bin/bash kafka-rebalance-watch.sh 2>&1
```

> v1.1（`kafka-rebalance-watch-v1.1.sh`）支持钉钉通知配置。脚本本体在原记录附件。

## kafka-view-topic-messages-by-time — Kafka 查看 Topic 指定时间生产的消息


### 场景
要按指定时间点查 Kafka Topic 偏移量并消费查看消息。

```bash
# 1. 查指定时间点的偏移量（--time 为毫秒时间戳）
/usr/local/kafka/bin/kafka-run-class.sh kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 --topic WorkFlow-Batch --time 1724057310000

# 2. 从指定偏移量消费查看（分区0、偏移1234起、最多10条）
/usr/local/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic WorkFlow-Batch \
  --offset 1234 --partition 0 --max-messages 10
```

## kafka-ws-etl-three-replicas — 数据集成同步任务/聚合表不可用 — ws-etl Topic 改为三副本


### 现象 / 场景
Kafka 为集群状态下，微服务启动后默认只为 ws-etl 创建了 **1 个副本**。

现象：datapipeline 服务启动正常，但**同步任务和聚合表无法正常使用**。可从 kafka 日志查看到 ws-etl 副本相关异常。

### 原因
集群 Kafka 下 ws-etl topic 副本数为 1，单 broker 故障/不可用即影响 datapipeline 消费，同步任务与聚合表无法工作。需将 ws-etl 调整为 3 副本。

### 处理

#### 方式一：已存在 ws-etl，重分配为三副本
```bash
cat > reassignment.json << 'EOF'
{
  "version": 1,
  "partitions": [
    {"topic": "ws-etl", "partition": 0, "replicas": [0, 1, 2], "log_dirs": ["any", "any", "any"]},
    {"topic": "ws-etl", "partition": 1, "replicas": [2, 0, 1], "log_dirs": ["any", "any", "any"]},
    {"topic": "ws-etl", "partition": 2, "replicas": [1, 2, 0], "log_dirs": ["any", "any", "any"]},
    {"topic": "ws-etl", "partition": 3, "replicas": [0, 1, 2], "log_dirs": ["any", "any", "any"]},
    {"topic": "ws-etl", "partition": 4, "replicas": [2, 0, 1], "log_dirs": ["any", "any", "any"]}
  ]
}
EOF

# 执行重分配
/usr/local/kafka/bin/kafka-reassign-partitions.sh --bootstrap-server localhost:9092 --reassignment-json-file reassignment.json --execute

# 查询当前 topic 副本分布
/usr/local/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic ws-etl
```

#### 方式二：初次部署未启动微服务，或删除 ws-etl 后手动创建
```bash
# 手动创建 ws-etl 三个副本（5 分区 / 3 副本）
/usr/local/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic ws-etl --partitions 5 --replication-factor 3
```

说明：`replicas` 中的 0/1/2 为 broker.id，按实际集群 broker id 调整；`--bootstrap-server` 按实际 Kafka 地址端口调整。

### 核验
执行 `kafka-topics.sh --describe --topic ws-etl`，确认每个分区的 Replicas 为 3 个且 Isr（同步副本）也为 3 个；回到平台测试数据集成同步任务与聚合表恢复正常。

## kafkactl-alter-topic-replicas — 用 kafkactl 调整 Kafka topic 副本数


### 场景
要用 kafkactl 调整 Kafka topic 副本数（单个 / 批量）。

```bash
# 查 broker / topic（含分区、副本信息）
kafkactl get brokers
kafkactl get topics

# 单个 topic 副本数调整为 3
kafkactl alter topic my-topic -r 3

# 批量把所有 topic 副本数调到 3
for i in $(kafkactl get topics | awk 'NR!=1{print $1}'); do kafkactl alter topic $i -r 3; done

# 消费组
kafkactl get consumer-groups
kafkactl describe consumer-group md-workflow-consumer
kafkactl describe consumer-group md-workflow-consumer --only-with-lag   # 只看有延迟的分区
```
> 扩容副本数需保证 broker 数 ≥ 目标副本数。

## zookeeper-unauth-iptables — iptables 临时解决 ZooKeeper 2181 未授权漏洞


### 场景
安全扫描报 ZooKeeper 2181 未授权访问漏洞，要用 iptables 限制来源。

仅允许指定 IP 访问 2181（zookeeper 各节点）。**顺序：先停 kafka 再停 zookeeper → 加 iptables → 先起 zookeeper 再起 kafka。**
```bash
iptables -I INPUT -p tcp --dport 2181 -j DROP -m comment --comment "Denied access to port 2181"
iptables -I INPUT -s 127.0.0.1 -p tcp --dport 2181 -j ACCEPT
iptables -I INPUT -s <节点1IP> -p tcp --dport 2181 -j ACCEPT
iptables -I INPUT -s <节点2IP> -p tcp --dport 2181 -j ACCEPT
iptables -I INPUT -s <节点3IP> -p tcp --dport 2181 -j ACCEPT
```
开机自加：把上述规则 `echo ... >> /etc/rc.d/rc.local && chmod +x /etc/rc.d/rc.local`。

