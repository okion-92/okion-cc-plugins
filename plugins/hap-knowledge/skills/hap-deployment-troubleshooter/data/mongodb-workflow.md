# MongoDB / 工作流数据

> 由 sources/faq/ 生成，勿手改。每条 `## <slug>` 对应一个 source 文件，可在 ROUTING.md 反查。

## clear-process-normal-messages — 清理流程消息和普通消息（按人 / 按工作表 / 全部）


> ⚠️ **高危（数据删除操作）**：执行前请与 HAP 运维实施确认，并务必先做好快照 / 数据备份。操作不可逆。

### 场景
要清理流程消息 / 普通消息（按人、按工作表，或全部清空）。

进入容器并连 mongodb：
```bash
docker exec -it $(docker ps | grep community | awk '{print $1}') bash
/init/mongodb/mongo
```

### 一、按条件清理
普通消息 inbox（按人删，aid 换成目标账号Id）：
```javascript
use mdinbox
db.inboxrelation.remove({"aid":{$in:["190c724a-b817-45e9-9365-b1c0a64d0e22"]}});
db.inboxrelationnewly.remove({"aid":{$in:["190c724a-b817-45e9-9365-b1c0a64d0e22"]}});
```
```bash
redis-cli -a 123456 KEYS "*md.a.i*" | xargs redis-cli -a 123456 DEL
```
工作流消息（按工作表删，appId 换成目标工作表Id）：
```javascript
use mdworkflow
db.wf_instance.remove({processId:{$in:db.wf_process.find({"flowNodes.type":0,"flowNodes.appId":{$in:["622eb05dda42387cd94d67bc"]},deleted:false}).map(function(p){return p._id.valueOf()})}});
```
```bash
redis-cli -a 123456 KEYS "*h:wf:*" | xargs redis-cli -a 123456 DEL
```

### 二、清理全部消息（单机模式）
```javascript
use mdinbox
db.inboxrelation.remove({});
db.inboxrelationnewly.remove({});
use mdworkflow
db.wf_instance.remove({});
```
```bash
redis-cli -a 123456 KEYS "*md.a.i*" | xargs redis-cli -a 123456 DEL
redis-cli -a 123456 KEYS "*h:wf:*" | xargs redis-cli -a 123456 DEL
```
> 红点计数不消失见 [[message-red-dot-not-clear]]。

### 核验
- 按人删：`db.inboxrelation.count({"aid":{$in:["<目标账号Id>"]}})` 应为 0，其余 aid 的记录数不变。
- 按工作表删：对应 appId 的 wf_instance 已清空，其它工作表流程消息保留。
- 全部清空（单机）：`db.inboxrelation.count({})` 与 `db.wf_instance.count({})` 均为 0；Redis `redis-cli -a 123456 KEYS "*md.a.i*"` 无输出，前端刷新后消息列表为空。

## clear-serial-workflow-block — 清除串行工作流堵塞


> ⚠️ **高危（数据删除操作）**：执行前请与 HAP 运维实施确认，并务必先做好快照 / 数据备份。操作不可逆。

现象：串行工作流被触发后不自动执行，手动执行/复制后正常 → 通常是流程堵塞。

方法一：工作流后台拿到工作流 ID 后清除。
方法二：数据库清除（工作流 ID 示例 `5f12855302740ff3c82f`）：
```js
use mdworkflow
// 1. 查 storeId
db.app_consumerSequence.find({_id: ObjectId("<工作流ID>")})
// 2. 按 storeId 清堵塞（storeId 示例 32e8d0fdsa32948d449）
db.app_consumerSequence.remove({storeId: "<storeId>"})
db.app_consumerActivity.remove({processId: "<工作流ID>", storeId: "<storeId>"})
```

### 核验
- `db.app_consumerSequence.find({storeId: "<storeId>"})` 与 `db.app_consumerActivity.find({processId: "<工作流ID>", storeId: "<storeId>"})` 均返回空。
- 再次触发该串行工作流，应自动执行不再堵塞；其它 storeId 的队列不受影响。

## delete-dedicated-compute-instance — 删除专属算力实例（pod + mongo + kafka topic/消费组）


> ⚠️ **高危（数据删除操作）**：执行前请与 HAP 运维实施确认，并务必先做好快照 / 数据备份。操作不可逆。

### 场景
要彻底删除一个专属算力实例（页面删不掉 / 残留）。

```bash
# 1. 删 pod（删后页面提示实例异常）
kubectl delete pod workflowcompute-<实例ID>-xxxx

# 2. 删 mongodb 中对应数据（删后页面实例消失）
use mdIdentification
db.computingInstance.remove({ "ResourceId": "<实例ID>" })

# 3. 删对应 topic 与消费组
/usr/local/kafka/bin/kafka-consumer-groups.sh --bootstrap-server 127.0.0.1:9092 --delete --group md-workflow-consumer-<实例ID>
/usr/local/kafka/bin/kafka-topics.sh --bootstrap-server 127.0.0.1:9092 --delete --topic WorkFlow-<实例ID>
/usr/local/kafka/bin/kafka-topics.sh --bootstrap-server 127.0.0.1:9092 --delete --topic WorkSheet-<实例ID>
```

### 核验
- 页面实例已消失；`db.computingInstance.find({ "ResourceId": "<实例ID>" })` 返回空。
- `kubectl get pod | grep <实例ID>` 无残留 pod；`kafka-topics.sh --bootstrap-server 127.0.0.1:9092 --list | grep <实例ID>` 与 `kafka-consumer-groups.sh --bootstrap-server 127.0.0.1:9092 --list | grep <实例ID>` 均无输出，确认仅该实例被删、其余实例不受影响。

## delete-workflow-history-logs — 删除指定工作流的历史日志（物理删除，先备份）


> ⚠️ **高危（数据删除操作）**：执行前请与 HAP 运维实施确认，并务必先做好快照 / 数据备份。操作不可逆。

> ⚠️ 物理删除、不可恢复，操作前务必备份。

### 场景
要物理删除指定工作流的历史执行日志（瘦身 / 清理）。

### 第一步：取要删的所有历史流程 ID
- 方法一：工作流历史页 F12，看 `getHistory?processId=xxx` 请求，预览数据取所有历史流程 ID。
- 方法二：进入历史流程页面，URL 结尾的 ID 即该历史流程 ID，逐个取。

### 第二步：MongoDB 删除（替换 processId 为实际 ID；涉及 5 张关联表）
```js
use mdworkflow
db.getCollection("wf_instance")
 .find({ "processId": { $in: ["<流程ID1>", "<流程ID2>"] } })
 .noCursorTimeout()
 .forEach(function(ref) {
   db.getCollection("wf_instance").remove({ "_id": ref._id });
   db.getCollection("wf_subInstanceActivity").remove({ "instanceId": ref._id.valueOf() });
   db.getCollection("wf_subInstanceCallback").remove({ "instanceId": ref._id });
   db.getCollection("app_multiple_catch").remove({ "instanceId": ref._id.valueOf() });
   db.getCollection("custom_apipackageapi_catch").remove({ "instanceId": ref._id.valueOf() });
 });
```

### 大数据量：nohup 后台跑 delete_instances.js
```bash
nohup /usr/local/mongodb/bin/mongo -u root -p <密码> --authenticationDatabase admin --host <MongoDB host:port> mdworkflow delete_instances.js > delete_instances.log 2>&1 &
```
（脚本内容同上 forEach 逻辑，建议加 try/catch 打印进度。）

### 核验
- `db.getCollection("wf_instance").count({ "processId": { $in: ["<流程ID1>","<流程ID2>"] } })` 应为 0，关联表 `wf_subInstanceActivity`/`wf_subInstanceCallback` 按 instanceId 也查不到记录。
- 删前先记下目标 processId 的 count，删后只有这些 processId 归零、其余流程 ID 的 wf_instance 数量不变。

## hdp-start-fail-storehouse-disabled — HDP(hdpapi) 启动失败 —— 中间库功能未开启（聚合表中间库 mdaggregationwsrows 未启用）


### 现象
新部署启用 HDP 后 hdpapi 服务起不来，日志：
```
INFO  ... GrpcServerLifecycle - gRPC Server started, listening on ... port: 8366
ERROR com.mingdao.hdp.HdpApplication - 中间库功能未开启，系统禁止启动... 在配置中开启 storehouse.enable 后重试。
INFO  ... GrpcServerLifecycle - Completed gRPC server shutdown   # hdpapi 自杀退出
```
旁路：Kafka `KafkaListenerEndpointContainer` 对 `flink_metrics_counter-hdp-*` 触发 `partitions revoked`（rebalance）。

### 原因
HDP 把「中间库(storehouse)可用」当硬启动条件，**MongoDB 上没启用聚合表中间库 `mdaggregationwsrows`** 就直接退出。前置条件必须 5 项全满足，缺一项在不同位置报不同错——本案例报错只暴露第 5 项。

### 处理
按 HDP 启用前置条件逐项核对（5 层），重点是第 5 项：
1. **MySQL 库 MDHDP 是否创建**：进 sc 容器 `mysql -h sc -P 3306 -uroot -p<MYSQL_PASSWORD>`，`SHOW DATABASES LIKE 'MDHDP';`
2. **MongoDB 库 mdhdp 是否创建**（启用 Mongo 认证时强制）：`mongosh ... --eval "show dbs"` 看有无 `mdhdp`
3. **Flink 是否升到 1.19.720**：`docker images | grep flink` 或 K8s `kubectl get deploy flink -o jsonpath='{.spec.template.spec.containers[*].image}'`，须为 `mingdaoyun-flink:1.19.720`（或 arm64 变体）
4. **MongoDB 是否副本集**：`mongosh --eval "rs.status().ok"` 须返回 1（HDP/Flink CDC 依赖 oplog 与多文档事务）
5. **聚合表中间库 mdaggregationwsrows 是否开启**（**本次根因**）：在 MongoDB 端启用聚合表中间库（即开启聚合表功能；已购聚合表许可的按文档把 mdaggregationwsrows 库准备好）

修复后重启：
```bash
# 单机
bash /usr/local/MDPrivateDeployment/service.sh restartall
# 集群
kubectl rollout restart deployment/hdpapi -n <ns>
```

> 公开文档无 `storehouse.enable` 专门页；该开关由「聚合表功能 + mdaggregationwsrows 中间库」组合决定，新部署/迁移最容易漏。改完第 5 项也要顺手确认前 4 项，避免接着因副本集没开报别的错。

### 核验
hdpapi 日志不再出现 `中间库功能未开启`，gRPC server `listening on port: 8366` 后不再立即 shutdown，pod 稳定 Running 即恢复。

### 官方依据
- HDP 启用主文档（MDHDP/mdhdp/Flink 1.19.720/`ENV_HDP_ENABLE: "true"`）：https://docs-pd.mingdao.com/faq/integrate/hdp/enable-hdp
- 行记录多集群存储（mdaggregationwsrows 含义）：https://docs-pd.mingdao.com/optimize/mongodb/storage/mulitWSRows/
- 迁移文档旁证（启用聚合表需把 mdaggregationwsrows 加入库列表）：https://docs-pdop.mingdao.com/migration/p2p/migdoc/

## mongodb-4.0-to-4.2-upgrade-fail — MongoDB 4.0→4.2 升级失败（oplogDeleteFromPoint 未知字段）


### 场景
MongoDB 逐级升级 4.0→4.2 失败，报 oplogDeleteFromPoint unknown field。

环境：MongoDB v3.4.24 单节点副本集，逐级升级时 4.0→4.2 阶段失败，日志：
```
STORAGE [initandlisten] exception in initAndListen: Location40415: BSON field 'MinValidDocument.oplogDeleteFromPoint' is an unknown field., terminating
```

原因：MongoDB 4.2 移除了 `oplogDeleteFromPoint` 字段；低版本单节点副本集会有此字段，需在升到 **4.0** 时移除再继续（**不可在 3.4 时删**，否则升级后进入 STARTUP2 状态）。

处理：用 4.0 的 mongod 启动 mongodb，登录后移除该字段：
```js
use local
// 查看
db.replset.minvalid.find({}).pretty();
// 按其 _id 删除 oplogDeleteFromPoint 字段
db.replset.minvalid.update(
  { "_id": ObjectId("<上面查到的 _id>") },
  { $unset: { oplogDeleteFromPoint: "" } }
);
```
处理后重新执行 4.0→4.2 升级。

## mongodb-4.2.29-init-count-fix — 5.2.2 以前版本用 4.2.29 MongoDB 初始化报 count 弃用错误


现象：`mongodbInit` 初始化报 `bash: [[: DeprecationWarning: Collection.count() is deprecated...`，因 4.2.29 的 `count()` 返回带告警，导致脚本 `[[ ... -eq 0 ]]` 语法错。

解决：把初始化脚本里的 `count()` 改成 `countDocuments()`：
```bash
# 函数 mongodbInit() 内
# 旧：... --eval 'db.citys.count()'
# 新：
$ENV_BIN_MONGO $ENV_MONGODB_PRIMARY_URI/commonbase${ENV_MONGODB_SHELL_OPTIONS} --quiet --ipv6 --eval 'db.citys.countDocuments()'
```

## mongodb-4.4-index-build-tuning — MongoDB 4.4 临时调整建索引最大内存量/并发数


### 场景
建索引太慢、报内存或并发不足，需临时调 MongoDB 4.4 建索引参数。

重启 mongodb 后失效（临时参数）。

```js
// 索引构建允许的最大内存量（默认 200MB）
db.adminCommand({ setParameter: 1, maxIndexBuildMemoryUsageMegabytes: 2048 })
db.adminCommand({ getParameter: 1, maxIndexBuildMemoryUsageMegabytes: 1 })

// 日志报 "Too many index builds running simultaneously, waiting until"
// 同时进行的用户索引构建最大数量（默认 3），注意观察服务器资源
db.adminCommand({ setParameter: 1, maxNumActiveUserIndexBuilds: 6 })
db.adminCommand({ getParameter: 1, maxNumActiveUserIndexBuilds: 1 })
```

## mongodb-add-index-from-slowlog — MongoDB 慢查询后台索引添加（从慢日志推导 createIndex 并在容器内执行）


### 适用场景
MongoDB 慢查询/全表扫描（COLLSCAN）拖慢系统，从慢日志定位高频慢表，推导出索引字段，后台（background）方式添加索引。配合 mongodb-slow-query-analysis（日志分析命令）使用。

### 一、索引添加基本语法（mdwsrows 库）
进入容器并连库：
```bash
docker exec -it $(docker ps | grep mingdaoyun-community | awk '{print $1}') bash
/init/mongodb/mongo
use mdwsrows;
```
- 唯一索引：
```js
db.ws+表ID.createIndex({"controlid":1},{unique:true,background: true})
```
- 普通索引：
```js
db.ws+表ID.createIndex({"controlid":1,"controlid":1},{background: true})
```
- 表 ID 换为实际表 ID，`controlid` 换为实际控件 ID。例：
```js
use mdwsrows
db.ws61b1983082615619a9cf2d76.createIndex({"61c96c748c2e872727b629fc":1, "status":1}, {background: true})
```

### 二、从慢日志推导索引（集群专业版完整流程）

#### 第一步：找出慢查询 Top10 表名
```bash
# 最新 50w 行日志中 >1s 慢查询（前10）的表名
tail -n 500000 /usr/local/mongodb/mongodb.log | grep -v regex | grep COMMAND | awk '/protocol:op_query/ && match($0, / ([0-9]+)ms$/, a) && a[1] > 1000' | awk '{print $6}' | sort | uniq -c | sort -n | tail -n10

# 指定时间段（例 2022-12-27 10~13 时）>1s 慢查询（前10）的表名
cat /usr/local/mongodb/mongodb.log | grep -E '2022-12-27T1{0,1,2}' | grep -v regex | grep COMMAND | awk '/protocol:op_query/ && match($0, / ([0-9]+)ms$/, a) && a[1] > 1000' | awk '{print $6}' | sort | uniq -c | sort -n | tail -n10
```
输出格式形如 `2322 mdwsrows.ws63083d1b9400551460042a73`（库 mdwsrows，表 ws63083d1b9400551460042a73）。

#### 第二步：按表名过滤慢查询日志，取出 filter 条件
```bash
cat /usr/local/mongodb/mongodb.log | grep -E '2022-12-27T1{0,1,2}' | grep -v regex | grep COMMAND | grep 'mdwsrows.ws63083d1b9400551460042a73' | more
```
日志里 `filter:{...}` 的字段即为待加索引字段。三类常见命令对应三种索引：
```js
// 语法：db.表名.createIndex({"条件1":1,"条件2":1},{background: true})
db.ws63083d1b9400551460042a73.createIndex({"61ee413ace02610479cd026f":1,"61ee413ace02610479cd0270":1},{background: true})
db.ws63083d1b9400551460042a73.createIndex({"63e0bab0d71862a19751ee00":1},{background: true})
db.ws63083d1b9400551460042a73.createIndex({"62f21b781a5d53d016417ad5":1},{background: true})
```

#### 第三步：进微服务容器、连主库、执行 createIndex
```bash
# 1、判断 config 所在节点并进入对应服务器的 config 容器
docker stack ps mdcluster | grep config
docker exec -it $(docker ps | grep config | awk '{print $1}') bash
# 2、获取 mongodb 连接串（含密码，脱敏）
export | grep -i mongodb
# 输出形如 ENV_MONGODB_URI="mongodb://mingdao:<密码>@<MongoIP1>:27017,<MongoIP2>:27017,<MongoIP3>:27017"
# 找到 PRIMARY 节点后连对应库（此处库为 mdwsrows）：
mongo mongodb://mingdao:<密码>@<PRIMARY节点IP>:27017/mdwsrows
# 3、执行第二步组装好的 createIndex 命令
```

### 核验
`db.表名.getIndexes()` 能看到新建索引；重新跑第一步的慢日志统计，对应表的慢查询计数下降，`planSummary` 由 COLLSCAN 转为 IXSCAN。

## mongodb-aggregation-replset-config — MongoDB 改造副本集（聚合表需要）环境配置


### 场景
聚合表需要 MongoDB 副本集，要把内置 / 独立 MongoDB 改造成副本集。

### 前置条件
1. Flink 版本：1.17（参考 `/deployment/docker-compose/standalone/upgrade/flink/default/split`）
2. MongoDB 4.4（`mingdaoyun-sc:3.x` 内置）
3. MongoDB 副本集模式

### 一、内置 MongoDB（未开认证）
docker-compose.yaml 的 app 环境变量加：
```yaml
      ENV_FLINK_URL: "http://flink:8081"
      ENV_MONGODB_DAEMON_ARGS: "--replSet sc-mongodb"   # 开启副本集
```
重启：`./service.sh restartall`
检查副本集（输出 PRIMARY 即成功）与版本（4.4.x）：
```bash
docker exec -i $(docker ps | grep mingdaoyun-sc | awk '{print $1}') mongo --quiet <<< 'rs.status().members[0].stateStr'
docker exec -i $(docker ps | grep mingdaoyun-sc | awk '{print $1}') mongo --quiet <<< 'db.version()'
```

### 二、其他情况（内置开认证 / 外部单节点 / 外部多节点）
1. 登录 mongo shell，确认是副本集（`rs.status()` 有 PRIMARY）、版本 4.4.x。
2. 创建角色与用户（仅密码可改）：
```js
use admin;
db.createRole({
  role: "flinkrole",
  privileges: [{ resource: { db: "", collection: "" },
    actions: ["splitVector","listDatabases","listCollections","collStats","find","changeStream"] }],
  roles: [{ role: 'read', db: 'config' }]
});
db.createUser({
  user: 'flinkuser', pwd: '<flink 用户密码>',
  roles: [{ role: 'flinkrole', db: 'admin' }, { role: 'readWrite', db: 'mdaggregationwsrows' }]
});
```
3. 创建 keyfile（数据目录以 /data/mingdao 为例）：
```bash
echo '<keyfile 随机串>' > /data/mingdao/script/volume/data/mongodb/keyfile
chmod 400 /data/mingdao/script/volume/data/mongodb/keyfile
```
4. 配置环境变量（单机示例，集群同样这几个），重启微服务后进 sc 容器初始化副本集：
```yaml
      ENV_FLINK_URL: "http://flink:8081"
      ENV_MONGODB_DAEMON_ARGS: "--auth --replSet sc-mongodb --keyFile /data/mongodb/keyfile"
      ENV_MONGODB_URI: "mongodb://hap:<hap 密码>@sc:27017"
      ENV_MONGODB_URI_AGGREGATIONWSROWS: "mongodb://flinkuser:<flink 用户密码>@sc:27017/mdaggregationwsrows?authSource=admin"
```
```bash
bash ./service.sh restartall
docker exec -it script_sc_1 bash
mongo mongodb://root:<root 密码>@sc:27017/admin
rs.initiate({_id: "sc-mongodb", members:[ {_id : 1, host : "sc:27017"} ]})
```
5. 再次重启服务。

## mongodb-backup-restore-script — MongoDB 集群数据备份与恢复参考脚本（HAP 全业务库）


### 现象 / 场景
HAP 部署需定期备份 MongoDB 全部业务库，或迁移/恢复时需还原。脚本用 `mongodump --gzip` 逐库备份、`mongorestore` 逐库恢复，并清理 N 天前旧备份。

> 提醒：恢复段会先对每个库 `db.dropDatabase()` 再导入，属高危操作。务必先确认备份完整、目标可覆盖；正式恢复前建议把脚本中“恢复备份”整段单独执行并核对 `mongodb_restore_path`。

涵盖库列表（按部署版本可能增减，新版本新增库需自行加进 `dbList`）：
`MDLicense ClientLicense commonbase MDAlert mdapproles mdapprove mdapps mdattachment mdcalendar mdcategory MDChatTop mdcheck mddossier mdemail mdform MDGroup mdgroups MDHistory mdIdentification mdinbox mdkc mdmap mdmobileaddress MDNotification mdpost mdreportdata mdroles mdsearch mdservicedata mdsms MDSso mdtag mdtransfer MDUser mdworkflow mdworksheet mdworkweixin mdwsrows pushlog taskcenter mdintegration mdworksheetlog mdworksheetsearch mddatapipeline`

### 处理

#### mongodb_restore.sh（含备份段 + 恢复段）
```bash
#!/bin/bash
maxBackupFileAge=3
mongodbHost=127.0.0.1
mongodbPort=27017
mongodbUser=<MONGODB_USER>
mongodbPassword=<MONGODB_PASSWORD>
mongodbBackupDir=/test/mongodb_back
mongodbDumpCommandPath=mongodump
mongodbBackupLogFile=/test/mongodb_backup.log
mongodbDumpPath=$mongodbBackupDir/md_mongodb.bak$(date +%Y%m%d%H%M%S)
dbList='MDLicense ClientLicense commonbase MDAlert mdapproles mdapprove mdapps mdattachment mdcalendar mdcategory MDChatTop mdcheck mddossier mdemail mdform MDGroup mdgroups MDHistory mdIdentification mdinbox mdkc mdmap mdmobileaddress MDNotification mdpost mdreportdata mdroles mdsearch mdservicedata mdsms MDSso mdtag mdtransfer MDUser mdworkflow mdworksheet mdworkweixin mdwsrows pushlog taskcenter mdintegration mdworksheetlog mdworksheetsearch mddatapipeline '

echo "$(date +"%Y-%m-%d %H:%M:%S") INFO: starting backup" >> $mongodbBackupLogFile
mkdir -p "$mongodbDumpPath"
echo "$(date +"%Y-%m-%d %H:%M:%S") INFO: create backup directory $mongodbDumpPath" >> $mongodbBackupLogFile
for dbName in ${dbList[*]}
do
    if $mongodbDumpCommandPath --uri mongodb://$mongodbHost:$mongodbPort/$dbName --gzip -o $mongodbDumpPath; then
        echo "$(date +"%Y-%m-%d %H:%M:%S") INFO: $dbName backup finish" >> $mongodbBackupLogFile
    else
        echo "$(date +"%Y-%m-%d %H:%M:%S") INFO: $dbName backup error" >> $mongodbBackupLogFile
    fi
done
echo "$(date +"%Y-%m-%d %H:%M:%S") INFO: backup finish" >> $mongodbBackupLogFile

find $mongodbBackupDir -type d -name "md_mongodb.bak*" -mtime +$maxBackupFileAge -exec rm -r {} \;

#恢复备份
mongodbCommandPath=mongo
mongodbRestoreCommandPath=mongorestore
###这个值取决于恢复备份的具体日期，比如 md_mongodb.bak20231124141722，实际恢复中需要进行修改。
mongodb_restore_path=$mongodbBackupDir/md_mongodb.bak20231124141722
##删除现有库
for dbName in ${dbList[*]}
do
    if $mongodbCommandPath mongodb://$mongodbUser:$mongodbPassword@$mongodbHost:$mongodbPort/admin <<< "use $dbName
db.dropDatabase()"; then
        echo "$(date +"%Y-%m-%d %H:%M:%S") INFO: $dbName delete finish" >> $mongodbBackupLogFile
    else
        echo "$(date +"%Y-%m-%d %H:%M:%S") ERROR: $dbName delete error" >> $mongodbBackupLogFile
    fi
done
##备份数据导入
for dbName in ${dbList[*]}
do
    if $mongodbRestoreCommandPath --host $mongodbHost -u $mongodbUser -p $mongodbPassword --authenticationDatabase admin  --numParallelCollections=6 --numInsertionWorkersPerCollection=6 -d $dbName --gzip --dir $mongodb_restore_path/$dbName/;then
        echo "$(date +"%Y-%m-%d %H:%M:%S") INFO: $dbName restore finish" >> $mongodbBackupLogFile
    else
        echo "$(date +"%Y-%m-%d %H:%M:%S") ERROR: $dbName restore error" >> $mongodbBackupLogFile
    fi
done
```

说明：
- 仅备份时，把脚本中 `#恢复备份` 起的整段删除/注释；仅恢复时把上半备份段删除/注释并核对 `mongodb_restore_path`。
- `mongodbBackupDir=/test/mongodb_back` 为示例路径，生产请改到磁盘充足目录。
- `--numParallelCollections=6 --numInsertionWorkersPerCollection=6` 为并行度，按机器资源调整。

### 核验
- 备份：`mongodbBackupDir` 下生成 `md_mongodb.bak<时间戳>/` 目录，`mongodb_backup.log` 各库 “backup finish”。
- 恢复：日志各库 “restore finish”；登录平台核对各模块数据完整。

## mongodb-collection-size-stats — 统计 MongoDB 表大小（按集合）


### 场景
MongoDB 磁盘占用过高 / 数据目录膨胀时，先定位哪个集合最大，再决定清理或 compact。找到大表后：工作流缓存/日志类接 [[delete-workflow-history-logs]] 与 [[mongodb-loop-compact]]；wslog* 接 [[wslog-index-rebuild]]。

### 全库按集合大小排序
```js
use <库名>;
function hr(b){var i=-1,u=[' kB',' MB',' GB',' TB','PB','EB','ZB','YB'];do{b=b/1024;i++;}while(b>1024);return Math.max(b,0.1).toFixed(1)+u[i];}
var stats=[]; db.getCollectionNames().forEach(function(n){stats.push(db[n].stats());});
stats.sort(function(a,b){return b.count-a.count;});
for(var c in stats){print(stats[c].ns+" , "+stats[c].count+" ,"+hr(stats[c].storageSize));}
```

### 只看工作流缓存/日志类集合（mdworkflow）
把上面的 `db.getCollectionNames().forEach` 内加过滤：
```js
var specified=['code_catch','hooks_catch','webhooks_catch','app_multiple_catch','wf_instance','wf_subInstanceActivity','wf_subInstanceCallback','custom_apipackageapi_catch'];
// forEach 内：if(specified.includes(n)){ stats.push(db[n].stats()); }
```

### 只看 wslog* 表（mdworksheetlog）
```js
// forEach 内：if(/^wslog/.test(n)){ stats.push(db[n].stats()); }
```

## mongodb-log-rotate — MongoDB 日志切割（logrotate 脚本 + cron）


### 场景
MongoDB 日志文件过大，要做定时切割。

使用附件 `mongodb_logrotate.sh` 脚本，加入 crontab 定时执行：
```bash
echo "0 0 * * * /usr/local/bin/mongodb_logrotate.sh" | crontab -
```
（脚本本体在原记录附件。）

## mongodb-loop-compact — MongoDB 循环 compact 集合脚本（回收磁盘）


### 场景
MongoDB 删数据后磁盘没释放，要循环 compact 集合回收空间。

脚本 `mongo_compact.sh` 兼容 `mongo` 与 `mongosh`（另有 `mongo_compact.sh.bak-mongosh` 仅针对 mongosh）。

执行方法：
1. 修改 `mongo_compact.sh` 中的 MongoDB 连接地址为实际**从库**地址（compact 在从库执行，避免影响主库）。
2. 后台执行：
```bash
nohup bash ./mongo_compact.sh > compact.log 2>&1 &
```
3. 查看运行日志：`cat compact.log`

> compact 后磁盘空间才会真正回收；4.4.30+ 可在线执行。脚本本体在原记录附件。

### 核验
- `cat compact.log` 末尾显示各集合 compact 完成、无报错（`ok:1`）。
- 对比执行前后从库数据目录占用（`df -h` 或目录 `du -sh`）应明显下降；确认是在从库执行、主库未受影响。

## mongodb-mdwsrows-add-ctime-utime-index — 补 mdwsrows 库下集合缺失的 ctime / utime 索引


### 现象 / 场景
mdwsrows 库（工作表行数据）下部分集合缺少 `idx_ctime`（创建时间）/`idx_utime`（更新时间）索引，导致按时间排序/筛选的查询变慢。需排查并补齐文档数较大集合的这两个索引。

### 处理

#### 1. 查找文档数较大且缺少 idx_ctime / idx_utime 的集合
```javascript
use mdwsrows;

// 定义黑名单集合（跳过不处理）
var blacklist = [
    "discussion",
    "rowrelations",
    "workSheetRowTopic",
    "workSheetTopic",
    "wslogs"
];

// 获取所有集合并检查文档数和索引
db.getCollectionNames().forEach(function(collectionName) {
    // 跳过黑名单中的集合
    if(blacklist.indexOf(collectionName) !== -1) {
        return;
    }

    // 检查集合的文档数
    var count = db[collectionName].count();

    // 只处理文档数超过 5000 的集合
    if(count > 1) {
        var indexes = db[collectionName].getIndexes();
        var hasCTimeIndex = false;
        var hasUTimeIndex = false;

        // 检查每个索引
        indexes.forEach(function(index) {
            if(index.name === "idx_ctime") hasCTimeIndex = true;
            if(index.name === "idx_utime") hasUTimeIndex = true;
        });

        // 只输出缺少索引的集合
        if(!hasCTimeIndex || !hasUTimeIndex) {
            print("集合: " + collectionName);
            print("文档数: " + count);
            if(!hasCTimeIndex) print("缺少: idx_ctime");
            if(!hasUTimeIndex) print("缺少: idx_utime");
            print("----------------");
        }
    }
});
```

#### 2. 给文档数超过 5000 且缺索引的集合创建 idx_ctime / idx_utime
```javascript
use mdwsrows;

// 定义黑名单集合
var blacklist = [
    "discussion",
    "rowrelations",
    "workSheetRowTopic",
    "workSheetTopic",
    "wslogs"
];

// 获取所有集合并检查文档数和索引
db.getCollectionNames().forEach(function(collectionName) {
    // 跳过黑名单中的集合
    if(blacklist.indexOf(collectionName) !== -1) {
        return;
    }

    // 检查集合的文档数
    var count = db[collectionName].count();

    // 只处理文档数超过 5000 的集合
    if(count > 5000) {
        var indexes = db[collectionName].getIndexes();
        var hasCTimeIndex = false;
        var hasUTimeIndex = false;

        // 检查每个索引
        indexes.forEach(function(index) {
            if(index.name === "idx_ctime") hasCTimeIndex = true;
            if(index.name === "idx_utime") hasUTimeIndex = true;
        });

        // 只在缺少索引时输出信息并创建索引
        if(!hasCTimeIndex || !hasUTimeIndex) {
            print("集合 " + collectionName + " (文档数: " + count + ") 开始创建缺失的索引:");

            if(!hasCTimeIndex) {
                print("- 正在创建 idx_ctime 索引...");
                db[collectionName].createIndex(
                    { "ctime": 1 },
                    {
                        "v": 2,
                        "name": "idx_ctime",
                        "background": true
                    }
                );
                print("  idx_ctime 索引创建完成");
            }

            if(!hasUTimeIndex) {
                print("- 正在创建 idx_utime 索引...");
                db[collectionName].createIndex(
                    { "utime": 1 },
                    {
                        "v": 2,
                        "name": "idx_utime",
                        "background": true
                    }
                );
                print("  idx_utime 索引创建完成");
            }
        }
    }
});
```

注意：第 1 步用 `count > 1` 仅做巡检列出全部缺失集合；第 2 步用 `count > 5000` 实际建索引，避免给小集合无谓建索引。`background: true` 后台建索引，减少阻塞。

### 核验
重跑第 1 步巡检脚本，确认文档数 > 5000 的集合不再输出“缺少 idx_ctime/idx_utime”；对应集合 `db.<coll>.getIndexes()` 可见 idx_ctime、idx_utime。

## mongodb-oplog-delay-alert — 检查 MongoDB 副本集 oplog 延迟并 webhook 告警


### 现象 / 场景
监控 MongoDB 副本集从节点的 oplog 同步延迟，超阈值（默认 60 秒）时通过工作流 webhook 推送告警。脚本里把 webhook 接收到的告警消息写入工作表，可在工作流里继续加发短信/邮件节点提醒接收人。

### 处理
修改脚本中的 mongodb 连接信息（`mongodbHost`/`mongodbPassword` 等）以及工作流 webhook 地址（`webhookUrl`），密码与内网地址按实际填写，定时任务（crontab）周期执行：

```bash
#!/bin/bash

# mongodb 副本集的主机名和端口
mongodbHost="<MONGODB_HOST>"
mongodbPort="27017"
mongodbUser="root"
mongodbPassword="<MONGODB_PASSWORD>"
mongodbAuthDb="admin"
mongoPath="/usr/local/mongodb/bin/mongo"

# Webhook URL（HAP 工作流 webhook 触发地址）
webhookUrl="<WORKFLOW_WEBHOOK_URL>"

# 发送告警通知的函数
sendAlert() {
    local level=$1
    local message=$2
    local currentTime=$(TZ="Asia/Shanghai" date '+%Y-%m-%d %H:%M:%S')
    curl -X POST -H "Content-Type: application/json" -d '{
    "level": "'"$level"'",
    "message": "'"$message"'",
    "time": "'"$currentTime"'"
    }' $webhookUrl
}

# 检测 MongoDB 是否可达的函数
checkMongoDB() {
    if ! $mongoPath --host $mongodbHost:$mongodbPort -u $mongodbUser -p $mongodbPassword --authenticationDatabase $mongodbAuthDb --eval "db.stats().ok"; then
        message="无法连接到 MongoDB 主机 $mongodbHost 的端口 $mongodbPort"
        sendAlert "error" "$message" "$currentTime"
        exit 1
    fi
}

# 查询 oplog 延迟的函数
getOplogDelay() {
    local member=$1
    local oplogTime
    oplogTime=$( $mongoPath --host $mongodbHost:$mongodbPort -u $mongodbUser -p $mongodbPassword --authenticationDatabase $mongodbAuthDb --quiet --eval "rs.printSlaveReplicationInfo()" | grep -C 2 "$member" | tail -n 1 | awk '{print $1}')
    echo "$oplogTime"
}

# 主要逻辑
main() {
    # 检测 MongoDB 是否可达
    checkMongoDB

    # 获取副本集的非 PRIMARY 成员
    members=$( $mongoPath --host $mongodbHost:$mongodbPort -u $mongodbUser -p $mongodbPassword --authenticationDatabase $mongodbAuthDb --eval 'rs.status().members.forEach(function(member) { if (member.stateStr !== "PRIMARY") print(member.name) })' --quiet)

    # 循环检查每个成员的 oplog 延迟
    for member in $members; do
        oplogDelay=$(getOplogDelay $member)
        if [[ "$oplogDelay" == "null" ]]; then
            message="无法获取 oplog 延迟：$member"
            sendAlert "warning" "$message" "$currentTime"
        elif (( $(echo "$oplogDelay > 60" | bc -l) )); then
            message="$member 的 Oplog 延迟超出阈值：$oplogDelay seconds"
            sendAlert "warning" "$message"
        else
            echo "$member 的 Oplog 延迟在阈值内：$oplogDelay seconds"
        fi
    done
}

# 执行主要逻辑
main
```

依赖：节点需有 `bc`（浮点比较）；`mongoPath` 指向容器外 mongo 客户端，容器内运行需进 mongodb 容器执行。

### 核验
手动运行脚本：MongoDB 不可达会推 error 告警并 `exit 1`；从节点延迟 >60s 推 warning 告警；正常则打印「Oplog 延迟在阈值内」。确认工作表收到 webhook 写入的告警记录即生效。

## mongodb-recalc-rownum — MongoDB 手动校准工作表行数（大量删除后总数/页码不更新）


> ⚠️ **高危（数据删除操作）**：执行前请与 HAP 运维实施确认，并务必先做好快照 / 数据备份。操作不可逆。

现象：大量删除数据后总行数/页码没更新，翻后面页都是空。（`63fc8696e11fc2d4d285ddb2` 为示例工作表 ID）

1. 检查回收站，确认能否清空（物理删除）。
2. 先备份对应表：
```bash
mongodump --uri mongodb://mingdao:<密码>@127.0.0.1:27017/mdwsrows --collection ws63fc8696e11fc2d4d285ddb2 --out ./ --gzip
```
3. 清空回收站（remove status:9）：
```js
db.ws63fc8696e11fc2d4d285ddb2.remove({status: 9})
// 注：5.8.2 修复了回收站清理大数据量失败（无法清空）
```
4. 校准：取在用行数（status:1），写回 worksheet.rownum：
```js
use mdwsrows;
db.ws63fc8696e11fc2d4d285ddb2.count({status: 1});   // 例 1695903

use mdworksheet;
db.worksheet.update({ _id: ObjectId("63fc8696e11fc2d4d285ddb2") }, {
   $set: { "rownum": NumberLong("1695903") }   // 改为上一步查出的值
})
// 操作后立刻点该表回收站的【立即清空】按钮
```
5. 新增一条行记录，刷新浏览器。

### 核验
- `db.ws63fc8696e11fc2d4d285ddb2.count({status: 9})`（mdwsrows）应为 0（回收站已清空）。
- `db.worksheet.findOne({_id: ObjectId("63fc8696e11fc2d4d285ddb2")}).rownum` 等于 `count({status: 1})` 的值；前端该表总数/页码已与实际在用行数一致，翻到末页不再是空页。

## mongodb-reindex-database-whitelist — MongoDB 重建指定库下所有索引（支持白名单跳过，两种方式）


### 现象 / 场景
MongoDB 索引膨胀/碎片化、磁盘占用偏高，或需要重建指定库下所有集合的索引以释放空间、修复索引。提供两种脚本：

- 方式一 `reIndexWithCmd.js`：用 `reIndex()` 命令原地重建（脚本内置集合白名单，跳过指定集合）。
- 方式二 `reIndexWithDropCreate.js`：先删除索引再重建（脚本内置集合白名单与索引白名单）。

### 原因 / 注意
`reIndex` 会获取集合上的**独占 (W) 锁**，重建期间阻塞该集合的其它操作，直至完成。

- MongoDB v5.0 及以上：`reIndex` **只支持单节点实例执行**。
- MongoDB v6.0 及以上：才重新启用 `reIndex` 命令。
- 副本集/数据量大时优先用方式二（drop + create，可后台 background 建索引），避免 W 锁长时间阻塞。

官方文档：https://www.mongodb.com/zh-cn/docs/manual/reference/command/reIndex/

### 处理

#### 重建前可先调大相关参数（两种方式通用）
```javascript
// 1. 调大索引构建过程中允许使用的最大内存量，默认 200MB。例如调整到 2048MB
db.adminCommand({ setParameter: 1, maxIndexBuildMemoryUsageMegabytes: 2048 })
// 查看
db.adminCommand({ getParameter: 1, maxIndexBuildMemoryUsageMegabytes: 1 })

// 2. 调大同时构建索引的最大数量，默认 3 个。例如调整为 6 个
db.adminCommand({ setParameter: 1, maxNumActiveUserIndexBuilds: 6 })
// 查看
db.adminCommand({ getParameter: 1, maxNumActiveUserIndexBuilds: 1 })
```

#### 方式一：reIndexWithCmd.js（reIndex 命令原地重建）
脚本头部配置目标库与白名单集合，格式 `"数据库名": ["要跳过的集合1", ...]`，空数组 `[]` 表示该库所有集合都重建：

```javascript
// ====================================================================
//                          CONFIGURATION
// 格式: "数据库名": ["要跳过的集合1", "要跳过的集合2..."]
// 如果某个库下所有集合都需要重建索引，请使用空数组 []
var targetDatabases = {
    "mdpost": [],
    "MDHistory": []
};
// ====================================================================
// 脚本随后遍历每个库的非 system. 集合，逐个执行 collection.reIndex()，
// 打印集合统计、当前索引、reIndex 前后索引数与耗时（北京时间 +08:00）。
```

后台执行（脚本完整内容见原始附件 reIndexWithCmd.js）：
```bash
nohup /usr/local/mongodb/bin/mongo mongodb://root:<密码>@127.0.0.1:27017/admin --quiet reIndexWithCmd.js >> reIndex_output.log 2>&1 &
```

#### 方式二：reIndexWithDropCreate.js（先删除索引再创建）
脚本内置**集合白名单**与**索引白名单**，重建时跳过这些集合和索引名。日志额外含：删除索引语句/耗时、创建索引语句/耗时。

后台执行（脚本完整内容见原始附件 reIndexWithDropCreate.js）：
```bash
nohup /usr/local/mongodb/bin/mongo mongodb://root:<密码>@127.0.0.1:27017/admin --quiet reIndexWithDropCreate.js >> reIndex_output.log 2>&1 &
```

执行日志（两种方式）均输出到 `reIndex_output.log`，包含：开始时间、总计需重建集合数、顺序进度、集合数量/大小、重建索引详情与耗时。

### 核验
`tail -f reIndex_output.log` 跟踪进度，看到 “Process Completed / Overall End Time” 即完成；对每个集合 `db.<coll>.getIndexes()` 确认索引齐全、`db.<coll>.stats()` 看 totalIndexSize 是否回落。

## mongodb-slow-query-analysis — MongoDB 慢日志分析帮助命令


### 场景
要从 MongoDB 慢日志里捞出慢查询 / 全表扫描(COLLSCAN)的表。

### 处理

#### 旧格式（4.4 以前，文本日志）
```bash
# 耗时 >1000ms 的慢日志
tail -n 100000 mongodb.log | grep COMMAND | awk '/protocol:op_query/ && match($0, / ([0-9]+)ms$/, a) && a[1] > 1000'

# >1000ms 且 COLLSCAN，按表名出现次数排序
tail -n 100000 mongodb.log | grep -v regex | grep COMMAND | awk '/protocol:op_query/ && match($0, / ([0-9]+)ms$/, a) && a[1] > 1000' | grep COLLSCAN | grep -v regex | grep -P '[[:digit:]]{3,7}ms' | awk '{print $6}' | sort | uniq -c | sort -n | tail -n10

# 排除常见噪声，统计慢命令表名 Top10
tail -n 1000000 mongodb.log | awk -F'ms' '{print $1}' | grep -vE 'open\)|NETWORK|INDEX|wf_instance' | awk '{if($NF>1000)print $0}' | grep 'command: ' | awk '{print $6}' | sort | uniq -c | sort -n | tail -n10
```

#### 4.4+（JSON 日志，durationMillis）
```bash
# awk 取 >1000ms
tail -n 100000 mongodb.log | awk '/"c":"COMMAND"/ && /"attr":{/ {match($0, /"durationMillis":[^0-9]*([0-9]+)/, a);if (a[1]+0 > 1000) {print $0;}}'

# jq 取 >1000ms（需 jq 1.7）
tail -100000 mongodb.log | jq -c 'select(.c == "COMMAND" and .attr.durationMillis > 1000)'
# jq 下载：
# amd64 https://github.com/jqlang/jq/releases/download/jq-1.7/jq-linux-amd64
# arm64 https://github.com/jqlang/jq/releases/download/jq-1.7/jq-linux-arm64
```

#### 按命名空间统计 max/min/count（>1000ms）
```bash
tail -n 100000 mongodb.log | awk '/"c":"COMMAND"/ && /"attr":{/ {match($0, /"durationMillis":[^0-9]*([0-9]+)/, a);if (a[1]+0 > 1000) {match($0, /"ns":"([^"]+)"/, b);print b[1], a[1];}}' | awk '{
    ns[$1]["max"] = (ns[$1]["max"] == "" ? $2 : (ns[$1]["max"] > $2 ? ns[$1]["max"] : $2));
    ns[$1]["min"] = (ns[$1]["min"] == "" ? $2 : (ns[$1]["min"] < $2 ? ns[$1]["min"] : $2));
    if (!ns[$1]["count"]) ns[$1]["count"] = 0;
    ns[$1]["count"]++;
} END { for (i in ns) print i, ns[i]["max"], ns[i]["min"], ns[i]["count"]; }' | sort -k4,4n
```

#### Debian（GNU awk 无 match 三参，用 split 兜底，>1000ms 统计）
```bash
tail -n 100000 mongodb.log | grep 'Slow query' | awk '/"c":"COMMAND"/ && /"attr":/ {
    split($0, arr, "\"durationMillis\":")
    if (length(arr) > 1) {
        split(arr[2], dur, ","); gsub(/[^0-9]/, "", dur[1]); duration = dur[1] + 0
        if (duration > 1000) {
            split($0, nsarr, "\"ns\":\""); 
            if (length(nsarr) > 1) {
                split(nsarr[2], ns, "\""); nsname = ns[1]
                if (!(nsname in ns_max)) { ns_max[nsname]=duration; ns_min[nsname]=duration; ns_count[nsname]=1 }
                else { if (ns_max[nsname]<duration) ns_max[nsname]=duration; if (ns_min[nsname]>duration) ns_min[nsname]=duration; ns_count[nsname]++ }
            }
        }
    }
} END { for (i in ns_max) print i, ns_max[i], ns_min[i], ns_count[i] }' | sort -k4,4nr
```

#### 按时间段筛日志
```bash
awk -v start="2025-01-03T10:00" -v end="2025-01-03T10:07" '
{ if (match($0, /"t":\{"\$date":"([^"]+)"\}/, m)) { timestamp = substr(m[1], 1, 16); in_range = (timestamp >= start && timestamp <= end); } if (in_range) print; }' mongodb.log | less
```

#### Top30 命名空间总耗时报表（≥200ms）
```bash
tail -n 50000 mongodb.log | grep 'Slow query' | awk '
{
    match($0, /"durationMillis":[[:space:]]*[0-9]+/)
    if (RSTART > 0) { tmp = substr($0, RSTART, RLENGTH); gsub(/[^0-9]/, "", tmp); duration = tmp + 0 } else next
    if (duration < 200) next
    match($0, /"ns":[[:space:]]*"[^"]+"/)
    if (RSTART > 0) { tmp_ns = substr($0, RSTART, RLENGTH); gsub(/"ns":[[:space:]]*"/, "", tmp_ns); gsub(/"$/, "", tmp_ns); ns = tmp_ns } else ns = "unknown"
    count[ns]++; sum[ns] += duration
    if (duration > max[ns]) max[ns] = duration
    if (min[ns] == 0 || duration < min[ns]) min[ns] = duration
}
END { for (ns in count) { avg = int(sum[ns]/count[ns]); printf "%-60s %-10d %-10d %-10d %-10d %-12d\n", ns, count[ns], max[ns], min[ns], avg, sum[ns] } }' | sort -k6,6n | tail -n 30 | awk 'BEGIN {
    printf "%-60s %-10s %-10s %-10s %-10s %-12s\n", "NAMESPACE","COUNT","MAX(ms)","MIN(ms)","AVG(ms)","TOTAL(ms)"
    print "----------------------------------------------------------------------------------------------------------------------------"
} { print }'
```

## query-workflow-by-timerange — 查询指定时间段执行的工作流（按次数排序）


### 场景
要查某时间段执行了哪些工作流、按执行次数排序（定位刷流程）。

`companyId`：组织管理-工作流页面 URL 尾部 ID。时间为 UTC（东八区减 8 小时）。
```js
use mdworkflow
db.wf_instance.aggregate([
  {"$match": {"companyId":"<companyId>", "createDate": {"$gt": ISODate("2023-05-06T06:10:00.000Z"), "$lt": ISODate("2023-05-06T06:20:00.000Z")}}},
  {"$group": {"_id": "$processId", "count": {"$sum": 1}}},
  {"$sort": {"count": -1}}
])
```
`_id` 是工作流 ID，`count` 是执行次数。浏览器开 `系统地址/workflowedit/<工作流ID>` 进入；无权限则查名称：
```js
db.wf_process.find({"_id": ObjectId("<工作流ID>")})   // name 字段即工作流名，再到组织管理-工作流搜
```

## workflow-admin-backend-login — 工作流后台登录方式（v4.0.1+ 默认 404，需临时放通）


### 现象 / 场景
需要进入工作流后台（清堵塞、查实例等）。访问入口：
```
访问地址：系统地址/api/workflow/admin/user/login
账号：联系运维实施团队远程输入
密码：联系运维实施团队远程输入
```

> 账号 / 密码不外泄，需向运维实施团队申请远程输入，本文不记录。

### 处理
入口由微服务容器内的 nginx 配置控制，配置文件路径（按部署形态进对应容器）：
- k8s 环境：`www` 容器 pod
- 单机：`app` 服务的容器
- docker swarm：`cluster_www` 容器
- 专业版集群：进 `www` 容器

容器内路径：`/usr/local/nginx/conf/conf.d/private.conf`

v4.0.1 及以上版本，该入口默认已被置 404。需临时放通时，进微服务容器，编辑 `private.conf` 注释掉相关路径的 404 配置，然后校验并 reload nginx：
```bash
/usr/local/nginx/sbin/nginx -t
/usr/local/nginx/sbin/nginx -s reload
```

### 核验
浏览器访问 `系统地址/api/workflow/admin/user/login` 能正常打开登录页（不再 404）。维护完成后应恢复 404 注释并重新 reload，避免长期暴露后台入口。

## workflow-email-content-query — 根据工作流执行 ID 查邮件节点发送内容


### 场景
要按工作流执行 ID 查邮件节点实际发送的内容。

1. 工作流执行历史打开 F12，点历史记录看 `instanceId`。
2. 按 instanceId 查邮件节点内容：
```js
use mdworkflow
db.app_task.find({ instanceId: "<instanceId>" }).pretty()
```

## workflow-webhook-config-query — 根据工作流流程 ID 查 webhook 触发器配置


### 场景
要按工作流流程 ID 查它的 webhook 触发器配置。

```js
use mdworkflow
db.hooks_config.find({ "_id": ObjectId("<流程ID>") }).limit(1).pretty()
```

## wslog-index-rebuild — wslog 月度日志集合索引重建（mdworksheetlog）


### 场景
mdworksheetlog 月度日志集合索引缺失 / 异常，要重建索引。

### 1. 先查索引数量 <5 的集合
```js
use mdworksheetlog;
var collections = db.getCollectionNames().filter(function(c){
    return c.indexOf("system") !== 0 && c !== "rowdrafts";
});
collections.forEach(function(c){
    var idx = db.getCollection(c).getIndexes();
    if (idx.length < 5) {
        print("Collection: " + c + ", Number of indexes: " + idx.length);
    }
});
```

### 2. 针对查出的集合（如 wslog202412）创建索引（数据量大时较慢）
```js
use mdworksheetlog;
db.wslog202412.createIndex({oid:1, wsid:1, attrs:1}, {background:true, name:"oid_1_wsid_1_attrs_1"});
db.wslog202412.createIndex({uid:1}, {background:true, name:"uid_1"});
db.wslog202412.createIndex({oid:1, wsid:1, ctime:1, caid:1, attrs:1}, {background:true, name:"oid_1_wsid_1_ctime_1_caid_1_attrs_1"});
db.wslog202412.createIndex({oid:1, wsid:1, caid:1}, {background:true, name:"oid_1_wsid_1_caid_1"});
```

### 核验
- `db.wslog202412.getIndexes().length` 应 ≥5，且包含上面四个命名索引（`oid_1_wsid_1_attrs_1`、`uid_1` 等）。
- 重跑第 1 步扫描脚本，目标集合不再出现在「索引数量 <5」的输出里。

