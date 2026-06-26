# Elasticsearch / 搜索

> 由 sources/faq/ 生成，勿手改。每条 `## <slug>` 对应一个 source 文件，可在 ROUTING.md 反查。

## collab-suite-es-search-init — 协作套件 ES 搜索数据初始化（聊天 / 动态 / 任务索引重建）


### 场景
协作套件（聊天/动态/任务/知识）搜索结果异常，重建 ES 搜索索引。先清 mongodb `mdsearch` 库 `idindex` 表，再跑脚本。

### 通用
```bash
cd /usr/local/MDPrivateDeployment/searchindex/script/
# 容器内执行
node chatgroup.js
node chatuser.js
node kcnode_control.js
node post.js
node task.js
```

### 3.9+ 版本（用内置 node 路径，脚本有精简）
```bash
cd /usr/local/MDPrivateDeployment/searchindex/script/
/usr/local/node-12.16.1/bin/node kcnode_control.js
/usr/local/node-12.16.1/bin/node post.js
/usr/local/node-12.16.1/bin/node task.js
```

### 核验
- 各 `node *.js` 脚本运行结束无报错、打印完成/已索引条数。
- mongodb `mdsearch` 库 `idindex` 表已重新写入（`use mdsearch; db.idindex.count()` >0）。
- 前端在聊天/动态/任务/知识中搜索此前缺失的关键词，能正常命中结果，确认索引重建生效。

## elasticsearch-6.6.2-fix-log4j-cve — Elasticsearch v6.6.2 修复 Log4J 漏洞（替换 log4j jar 到 2.18.0）


### 适用场景
私有部署 Elasticsearch 6.6.2 修复 Log4J 漏洞，替换 lib 与 x-pack-security 模块下的 log4j jar 为 2.18.0。

### 步骤

#### 备份程序目录
```bash
cp -r /usr/local/elasticsearch/ /usr/local/elasticsearch.backup-$(date +%Y%m%d%H%M%S)
```

#### 一、处理 lib 目录
```bash
cd /usr/local/elasticsearch/lib/
# 查看
ls -l log4j-1.2-api-*.jar  log4j-api-*.jar  log4j-core-*.jar
# 删除旧版
rm -f log4j-1.2-api-*.jar  log4j-api-*.jar  log4j-core-*.jar
# 下载最新
curl -O https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-core/2.18.0/log4j-core-2.18.0.jar
curl -O https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-api/2.18.0/log4j-api-2.18.0.jar
curl -O https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-1.2-api/2.18.0/log4j-1.2-api-2.18.0.jar
# 确认
ls -l log4j-1.2-api-*.jar  log4j-api-*.jar  log4j-core-*.jar
# 改权限（默认 elasticsearch.elasticsearch）
chmod elasticsearch.elasticsearch log4j-1.2-api-*.jar  log4j-api-*.jar  log4j-core-*.jar
```

#### 二、处理 x-pack-security 模块目录
```bash
cd /usr/local/elasticsearch/modules/x-pack-security/
# 查看
ls -l log4j-slf4j-impl-*.jar
# 删除旧版
rm -f log4j-slf4j-impl-*.jar
# 下载最新
curl -O https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-slf4j-impl/2.18.0/log4j-slf4j-impl-2.18.0.jar
# 确认
ls -l log4j-slf4j-impl-*.jar
# 改权限
chmod elasticsearch.elasticsearch log4j-slf4j-impl-*.jar
```

#### 三、重启服务
```bash
systemctl restart elasticsearch
```

### 核验
```bash
ss -tnlp | grep '9200'
```
9200 端口已监听，ES 正常启动。

## elasticsearch-8.5.3-deploy — Elasticsearch v8.5.3 部署（集群 / 单节点）微服务连接配置


### 场景
微服务 yaml 配置 ES v8.5.3 的地址、账号、密码。

### 集群（多节点）
```yaml
ENV_ELASTICSEARCH_ENDPOINTS: "http://192.168.130.11:9200,http://192.168.130.12:9200,http://192.168.130.13:9200"
ENV_ELASTICSEARCH_PASSWORD: "elastic:密码"
```

### 单节点
```yaml
ENV_ELASTICSEARCH_ENDPOINTS: "http://192.168.130.11:9200"
ENV_ELASTICSEARCH_PASSWORD: "elastic:密码"
```

### 注意事项
- `ENV_ELASTICSEARCH_ENDPOINTS` 地址前必须带 `http://` 协议。
- `ENV_ELASTICSEARCH_PASSWORD` 用户名为 `elastic`，密码以部署后实际修改的为准。
- 若配置文件中有 `ENV_ELASTICSEARCH_VERSION` 指定版本则注释掉；没有此变量可忽略。

## elasticsearch-log4j-fix-2.17.1 — Elasticsearch log4j 漏洞修复（替换为 log4j 2.17.1）


### 现象 / 场景
私有部署 Elasticsearch 自带的 log4j 版本存在 Log4Shell 等漏洞，需将 log4j 相关 jar 升级到 2.17.1。适用于 `/usr/local/elasticsearch` 源码包部署的 ES。

### 处理
#### 下载新的 jar 包上传至 ~/mdtemp/
```
mkdir -p ~/mdtemp/ && cd ~/mdtemp/
wget https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-core/2.17.1/log4j-core-2.17.1.jar
wget https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-api/2.17.1/log4j-api-2.17.1.jar
wget https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-1.2-api/2.17.1/log4j-1.2-api-2.17.1.jar
wget https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-slf4j-impl/2.17.1/log4j-slf4j-impl-2.17.1.jar
```

#### 备份旧包（漏洞版本）
```
cd ~/mdtemp/ && mkdir -p ~/mdtemp/old/
mv /usr/local/elasticsearch/lib/log4j-* ./old/
mv /usr/local/elasticsearch/modules/x-pack-security/log4j-slf4j-* ./old/
```

#### 更新新包（修复版本）
```
cp ./log4j-core-2.17.1.jar /usr/local/elasticsearch/lib/
cp ./log4j-1.2-api-2.17.1.jar /usr/local/elasticsearch/lib/
cp ./log4j-api-2.17.1.jar /usr/local/elasticsearch/lib/
cp ./log4j-slf4j-impl-2.17.1.jar /usr/local/elasticsearch/modules/x-pack-security/
```

#### 修改权限
```
chown -R elasticsearch.elasticsearch /usr/local/elasticsearch/
```

#### 重启 elasticsearch
```
systemctl restart elasticsearch
```

### 核验
重启后 `systemctl status elasticsearch` 为 active；`ls /usr/local/elasticsearch/lib/log4j-*` 显示均为 2.17.1 版本；ES 日志无 log4j 相关报错、`_cat/health` 仍为 green。

## elasticsearch-write-blocked-read-only — Elasticsearch 数据无法写入（read_only_allow_delete 锁定）解锁与重置


> ⚠️ **高危（数据删除操作）**：执行前请与 HAP 运维实施确认，并务必先做好快照 / 数据备份。操作不可逆。

### 场景
ES 索引被置为 `read_only_allow_delete=true`（多因磁盘水位触发），只读只删、不能增改，导致数据无法写入。账号 `md`、密码按实际（示例 `ESPassWD1234`）。

### 一、解除写入锁定（保留数据）
```bash
# 1. 进入存储容器
docker exec -it $(docker ps | grep mingdaoyun-sc | awk '{print $1}') bash

# 2. 查 read_only_allow_delete，值为 true 即被锁
curl -u md:ESPassWD1234 127.0.0.1:9200/_all/_settings

# 3. 解除锁定
curl -u md:ESPassWD1234 -XPUT -H "Content-Type: application/json" \
  http://127.0.0.1:9200/_all/_settings \
  -d '{"index.blocks.read_only_allow_delete": null}'
```
> 锁定常因磁盘空间不足触发，解锁前/后应先清理磁盘，否则会再次锁定。

### 二、重置 ES 数据（索引损坏时）
```bash
docker exec -it $(docker ps | grep mingdaoyun-sc | awk '{print $1}') bash

# 删除所有索引
for i in $(curl -u md:ESPassWD1234 127.0.0.1:9200/_cat/indices | awk '{print $3}'); do
    curl -XDELETE -u md:ESPassWD1234 127.0.0.1:9200/$i
done

# 检查，输出应为空
curl -u md:ESPassWD1234 127.0.0.1:9200/_cat/indices
```
在管理器目录执行重启：`bash service.sh restartall`（ES 索引会自动重建）。

### 核验
- 解锁后：`curl -u md:ESPassWD1234 127.0.0.1:9200/_all/_settings` 中已无 `read_only_allow_delete: true`；前端新增/编辑数据可正常写入（含搜索）。
- 重置后：`curl -u md:ESPassWD1234 127.0.0.1:9200/_cat/indices` 初始为空，restartall 后索引自动重建并出现（status 为 green/yellow），搜索功能恢复。先确认磁盘已腾出空间，否则会再次被锁。

## es-endpoints-multinode-url-prefix — searchapi / searchindex CrashLoop —— ENV_ELASTICSEARCH_ENDPOINTS 多节点写法错（缺 http:// 前缀）


### 现象
集群 `searchapi` `CrashLoopBackOff`（短时反复重启 RESTARTS 6/12），`searchindex` 同步反复重启，其余 pod 正常。日志栈：
```
TypeError: Invalid URL
  at new URL (node:internal/url:806:29)
  at getUsernameAndPassword (.../searchapi/node_modules/es8/lib/client.js:347:44)
code: 'ERR_INVALID_URL', input: '10.10.185.163:9200'   # 第二个 ES 节点，无协议前缀
```
Housekeeper 侧：`Wait for 120000 milliseconds after connecting to MongoDB.`（Mongo 已通，是后续 ES 客户端初始化失败 → exit 1 → 重启）。

### 原因
`ENV_ELASTICSEARCH_ENDPOINTS` 多节点写法错——只有第一个 endpoint 带 `http://`，后续节点是裸 `host:port`，被 ES 客户端 `new URL()` 解析时把 IP 当 scheme，抛 `ERR_INVALID_URL`。
```
错：ENV_ELASTICSEARCH_ENDPOINTS: "http://10.10.185.162:9200,10.10.185.163:9200,10.10.185.164:9200"
对：ENV_ELASTICSEARCH_ENDPOINTS: "http://10.10.185.162:9200,http://10.10.185.163:9200,http://10.10.185.164:9200"
```

### 处理
1. 改 ConfigMap/Deployment 里的 `ENV_ELASTICSEARCH_ENDPOINTS`，**每个节点都加 `http://` 前缀**（启用 TLS 时是 `https://`），逗号分隔无空格。
2. 重启：`kubectl rollout restart deployment/searchapi -n <ns>` 和 `deployment/searchindex -n <ns>`。

> 与 Kafka 写法对比（高发口子）：`ENV_KAFKA_ENDPOINTS` 是裸 `host:port` 逗号分隔（**不**带协议）；`ENV_ELASTICSEARCH_ENDPOINTS` 是 URL 列表（**每个**都要带 `http://`）。别把 Kafka 写法套到 ES。

### 核验
```bash
# 部署前/复盘自检：揪出裸 host:port
echo "$ENV_ELASTICSEARCH_ENDPOINTS" | tr ',' '\n' | grep -vE '^https?://' && echo "存在裸 host:port 写法，需要修复"
```
`kubectl get pods -w` 观察 searchapi/searchindex 起来停在 Running、RESTARTS 不再增长即恢复。

## umask-es-start-fail — umask 非 0022 导致 ES 启动失败（重建数据目录恢复）


现象：umask 不是 022 时，ES 报无法创建相关文件。

```bash
# 1. 改 umask 永久生效并重启
umask 022
# 在 /etc/profile 或 ~/.bashrc 加 umask 022 后 source，再重启服务器

# 2. 备份数据目录、重装脚本目录
mv /data/mingdao /data/mingdao-bak
# 管理器目录：
bash ./service.sh install http://127.0.0.1:8880
\cp -rfp /data/mingdao-bak/script/docker-compose.yaml /data/mingdao/script/

# 3. 还原数据
bash service.sh startall
bash service.sh stopall
mv /data/mingdao/script/volume/data/mysql   /data/mingdao/script/volume/data/mysql-bak
mv /data/mingdao/script/volume/data/mongodb /data/mingdao/script/volume/data/mongodb-bak
mv /data/mingdao/script/volume/data/storage /data/mingdao/script/volume/data/storage-bak
\cp -rfp /data/mingdao-bak/script/volume/data/storage /data/mingdao/script/volume/data/
\cp -rfp /data/mingdao-bak/script/volume/data/mongodb /data/mingdao/script/volume/data/
\cp -rfp /data/mingdao-bak/script/volume/data/mysql   /data/mingdao/script/volume/data/
bash service.sh startall   # 启动检查、浏览器访问
```

