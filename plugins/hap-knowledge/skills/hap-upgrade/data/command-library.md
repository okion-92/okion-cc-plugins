---
title: HAP 升级命令库（集群 AMD64 为主，含具体版本/YAML/命令）
source_url: https://docs-pd.mingdao.com/deployment/kubernetes/upgrade/hap
last_verified: 2026-06-18   # 命令/YAML/版本均逐页实时核验；实时详情页更具体时以其为准
hap_version: any
tags: [upgrade, commands, cluster, yaml]
feeds: [hap-upgrade]
---

命令骨架库。版本号一律用应用版本（不带 `v`）。单机/集群、联网/离线、架构选择与禁混用规则见 [[crossver-rules]]。集群默认命名空间 `default`。

> **镜像名按目标版本选择**：目标 >=7.1.0 用 `mingdaoyun-hap`；<7.1.0 用 `mingdaoyun-community`；跨 7.1.0 分段用名。详见 [[threshold-actions]] §五。

## 组件目标版本（官方 `/deployment/component` 实时核验 2026-06-18）
| 组件 | 单机 | 集群 | 最低支持 |
|---|---|---|---|
| MySQL | 5.7.44 | **8.0.45** | 5.7.x / 8.x |
| MongoDB | 4.4.30 | **4.4.30** | 4.4.30+ |
| Redis | 8.6.3 | **8.6.3** | 3.2.13+ |
| Kafka | 3.9.1 | **3.9.1** | 1.1.1+ |
| Elasticsearch | 8.19.6 | **8.19.8** | 8.x |
| Flink | 1.19 | 1.19 | |
| Nginx | 1.30.2 | 1.30.2 | 1.16+ |

## HAP 微服务镜像（集群 AMD64）
- 联网：`crictl pull registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hap:{目标版本}`
- 离线包：`https://pdpublic.mingdao.com/private-deployment/offline/mingdaoyun-hap-linux-amd64-{目标版本}.tar.gz`
- 离线导入：
```bash
gunzip -d xxx.tar.gz
ctr -n k8s.io image import xxx.tar
crictl images
```

## 文档预览：doc 与 ldoc 是两个独立服务（别混）
- **doc（默认预览）**：镜像 `mingdaoyun-doc`，最终版本 **2.0.0**。
- **ldoc（文档预览扩展，LibreOffice）**：镜像 `mingdaoyun-ldoc:2.0.2`。**只有启用 LibreOffice 才需要**，与 doc 并存。
- 离线包：`mingdaoyun-doc-linux-amd64-2.0.0.tar.gz` / `mingdaoyun-ldoc-linux-amd64-2.0.2.tar.gz`

### ldoc 集群部署（启用 LibreOffice 时）
在 `service.yaml` 加 ldoc（namespace 默认 `default`）：
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ldoc
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ldoc
  template:
    metadata:
      labels:
        app: ldoc
    spec:
      containers:
      - name: ldoc
        image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-ldoc:2.0.2
        resources:
          limits: { cpu: "4", memory: 4096Mi }
          requests: { cpu: "0.01", memory: 64Mi }
        readinessProbe:
          tcpSocket: { port: 8000 }
          initialDelaySeconds: 10
          periodSeconds: 10
        livenessProbe:
          tcpSocket: { port: 8000 }
          initialDelaySeconds: 180
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: ldoc
  namespace: default
spec:
  selector:
    app: ldoc
  ports:
    - name: internal
      port: 8001
      targetPort: 8000
```
再在微服务配置（`config.yaml`）设环境变量：`ENV_DOCPREVIRE_EXT_ENDPOINTS: "ldoc:8001"`，并设 `ENV_PDF_CONVERT_TYPE: "libreoffice"`。

## 新增微服务的 service.yaml 配置（同一镜像，靠 ENV_SERVERID 区分）
所有这些服务用**同一个目标镜像** `mingdaoyun-hap:{目标版本}`，只是 name / ENV_SERVERID / port / resources 不同。
配置文件路径：`/data/mingdao/script/kubernetes/service.yaml`。

> 生成跨版本升级文档时，**优先按 [[per-version-ledger]] 逐版本铺真实 YAML/命令（低→高）**；下面的模板只作结构参考，不要把变量化模板直接当成品交付。

**通用模板**（把 `{NAME}`/`{SERVERID}`/`{PORT}`/`{CPU}`/`{MEM}` 按下表替换）：
```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {NAME}
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {NAME}
  template:
    metadata:
      labels:
        app: {NAME}
    spec:
      containers:
      - name: {NAME}
        image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hap:{目标版本}
        env:
        - name: ENV_SERVERID
          value: "{SERVERID}"
        resources:
          limits: { cpu: "{CPU}", memory: {MEM} }
          requests: { cpu: "0.01", memory: 64Mi }
        readinessProbe:
          tcpSocket: { port: {PORT} }
          initialDelaySeconds: 10
          periodSeconds: 10
        livenessProbe:
          tcpSocket: { port: {PORT} }
          initialDelaySeconds: 180
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: {NAME}
  namespace: default
spec:
  selector:
    app: {NAME}
  ports:
    - name: {端口名}
      port: {PORT}
      targetPort: {PORT}
```

**各服务参数表**（requests 统一 cpu 0.01 / mem 64Mi）：
| 服务 NAME | 引入版本 | ENV_SERVERID | PORT | CPU limit | MEM limit |
|---|---|---|---|---|---|
| computingschedule | 5.1.0 | single:computingschedule | 9158(http)+9159(grpc) | 24 | 2048Mi |
| templatemessage | 4.4.0 | single:templatemessage | 3259(grpc) | 24 | 2048Mi |
| wps | 4.5.0 | single:wps | 9017(http) | 24 | 20480Mi |
| reportconsumer | 5.0.0 | single:reportconsumer | 无(消费者,仅 Deployment,无 Service/端口探针) | 24 | 20480Mi |
| commandpuppeteer | 5.3.0 | single:commandpuppeteer | 9198 | 24 | 20480Mi |
| datamanager | 5.4.0 | single:datamanager | 8322 | 24 | 20480Mi |
| workflowplugin | 5.8.0 | single:workflowplugin | 8087(http)+9087(grpc) | 24 | 20480Mi |
| payment | 6.2.0 | single:payment | 9161(grpc) | 4 | 8096Mi |
| ai | 7.0.0 | single:ai | 8066(http) | 4 | 8096Mi |
| mcp | 7.0.0 | single:mcp | 8165(http) | 4 | 8096Mi |
| platformapi | 7.3.0 | single:platformapi | 1317 | 4 | 8096Mi |
| openauthorization | 7.3.0 | single:openauthorization | 5322 | 4 | 8096Mi |

**push 服务加 gRPC 端口（5.8.0）**：在 push 的 Service `spec.ports` 加一项：
```yaml
- name: grpc-push
  port: 3009
  targetPort: 3009
```
**删除 pushserver（7.3.0）**：从 service.yaml 删除 pushserver 的整段 Deployment 与 Service。

## MongoDB 预置数据更新
- 集群联网：`bash -c "$(curl -fsSL https://pdpublic.mingdao.com/private-deployment/data/preset_mongodb_k8s.sh)" -s {版本} default`
- 集群离线：下 `preset_mongodb_k8s.sh` + `preset_mongodb_{版本}.tar.gz`，执行
  `bash ./preset_mongodb_k8s.sh {版本} default ./preset_mongodb_{版本}.tar.gz`

## HAP 微服务升级
```bash
bash update.sh update hap {目标版本}
```
内存不足：`bash stop.sh` → `kubectl get pod -n default` → 再 `update.sh`。

## MongoDB 建库（开认证时；每库独立用户模式）
```bash
mongo -u 用户名 -p 密码 --authenticationDatabase admin
use {库名}
db.createUser({ user: "与其他库一致的用户名", pwd: "与其他库一致的密码", roles: [{ role: "readWrite", db: "{库名}" }] })
```
> 全局统一用户模式则改为给该用户授权新库，而非建新用户。

## MongoDB 升级 3.4→4.4（5.5.0 硬要求；供 5.6.0 聚合表还需副本集）
**通用规则**：必须逐级 3.4 → 3.6 → 4.0 → 4.2 → 4.4，不能跳级；每级升完设 `setFeatureCompatibilityVersion`。**单机与集群做法不同**：

### 单机（内置 MongoDB，用 sc-upgrade 镜像）
```bash
bash ./service.sh stopall                       # 1) 停服
mkdir -p /backup && tar -zcvf /backup/mongodb3.4_$(date +%Y%m%d%H%M%S).tar.gz /data/mingdao/script/volume/data/mongodb   # 2) 备份
docker pull registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-sc-upgrade:1.0.0               # 3) 拉镜像
# 4) 逐级（挂单机 MongoDB 数据目录）
docker run -i --rm -v /data/mingdao/script/volume/data/mongodb:/data/mongodb registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-sc-upgrade:1.0.0 <<< 'upgradeMongodb.sh 3.4 3.6'
docker run -i --rm -v /data/mingdao/script/volume/data/mongodb:/data/mongodb registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-sc-upgrade:1.0.0 <<< 'upgradeMongodb.sh 3.6 4.0'
docker run -i --rm -v /data/mingdao/script/volume/data/mongodb:/data/mongodb registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-sc-upgrade:1.0.0 <<< 'upgradeMongodb.sh 4.0 4.2'
docker run -i --rm -v /data/mingdao/script/volume/data/mongodb:/data/mongodb registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-sc-upgrade:1.0.0 <<< 'upgradeMongodb.sh 4.2 4.4'
# 成功标志：newRunVersion: 4.4
```

### 集群（独立部署，**副本集滚动升级**——不用 sc-upgrade/docker run）
MongoDB 在集群下是副本集。逐级 3.4→3.6→4.0→4.2→4.4，每一级对**每个节点**：停实例 → 替换为该级二进制 → 重启 → 验证连通；顺序 **SECONDARY 先、一次一个、PRIMARY 最后**，升 PRIMARY 前先 `rs.stepDown()` 触发故障转移。每级全部节点升完后，在 PRIMARY 执行：
```js
db.adminCommand({ setFeatureCompatibilityVersion: "3.6" })   // 升到 3.6 后；依次 "4.0" / "4.2" / "4.4"
db.adminCommand({ getParameter: 1, featureCompatibilityVersion: 1 })   // 验证
```
### 单节点转副本集（5.6.0 聚合表依赖；`/deployment/components/mongodb/replset`）
副本集名统一 `sc-mongodb`。四种场景：
- **内置·无认证**：docker-compose.yaml 设 `ENV_MONGODB_DAEMON_ARGS: "--replSet sc-mongodb"` → `bash ./service.sh restartall`。
- **内置·认证**：建 keyfile → `ENV_MONGODB_DAEMON_ARGS: "--auth --keyFile /data/mongodb/keyfile --replSet sc-mongodb"` → 进容器 `rs.initiate(...)` → `service.sh restartall`。
- **外置·无认证（集群常见）**：
```bash
mongod --bind_ip 0.0.0.0 --dbpath /data/mongodb --logpath /data/logs/mongodb.log --replSet sc-mongodb
mongo mongodb://sc:27017/admin
rs.initiate({_id:"sc-mongodb",members:[{_id:1,host:"服务名或IP:27017"}]})
```
- **外置·认证（集群常见）**：
```bash
echo $(openssl rand -base64 32) > /data/mongodb/keyfile && chmod 400 /data/mongodb/keyfile
mongod --bind_ip 0.0.0.0 --dbpath /data/mongodb --logpath /data/logs/mongodb.log --auth --keyFile /data/mongodb/keyfile --replSet sc-mongodb
mongo mongodb://root:******@sc:27017/admin
rs.initiate({_id:"sc-mongodb",members:[{_id:1,host:"服务名或IP:27017"}]})
```
keyfile 内容须各节点一致；客户端需能解析 `sc` 服务名。验证 `rs.status()`。
来源：集群 `/deployment/kubernetes/upgrade/mongodb/3.4_4.4`、单机 `/deployment/docker-compose/standalone/upgrade/mongodb/3.4_4.4`、副本集 `/deployment/components/mongodb/replset`、聚合表 `/faq/integrate/worksheet/aggtable`。

## MongoDB 重建 mdwsrows 索引（5.5.0 升 4.4 后必做）
进容器（单机）：`docker exec -it $(docker ps | grep mingdaoyun-sc | awk '{print $1}') bash`，集群在能连 MongoDB 的节点执行。
- 单机用 `reIndex.js`，集群用 `reIndexWithCmd.js`：
```bash
# 集群·有认证
nohup mongo mongodb://root:password@127.0.0.1:27017/admin --quiet reIndexWithCmd.js >> reIndexWithCmd_output.log 2>&1 &
# 集群·无认证：去掉 root:password@
# 单机：把 reIndexWithCmd.js 换成 reIndex.js
```
等脚本跑完，看 log 末尾完成提示。

## 升级后文件初始化
- 常规：`source /entrypoint-cluster.sh && fileInit`
- 外部 S3：`source /entrypoint-cluster.sh && s3fileInit`

## 镜像命名变更（v7.1.0 起：mingdaoyun-community → mingdaoyun-hap）
跨过 v7.1.0 必做替换（历史镜像名不变）。

单机：
```bash
sed -i -e 's/mingdaoyun-community/mingdaoyun-hap/g' /data/mingdao/script/docker-compose.yaml
sed -i -e 's/Community/Hap/g' -e 's/community/hap/g' /usr/local/MDPrivateDeployment/service.sh
if [ -f /data/mingdao/script/run.sh ]; then
  sed -i -e 's/mingdaoyun-community/mingdaoyun-hap/g' /data/mingdao/script/run.sh
fi
```
集群：
```bash
sed -i -e 's/mingdaoyun-community/mingdaoyun-hap/g' /data/mingdao/script/kubernetes/*.yaml
sed -i -e 's/Community/Hap/g' -e 's/community/hap/g' /data/mingdao/script/kubernetes/update.sh
```
详情：`/imagenamehistory#710`
