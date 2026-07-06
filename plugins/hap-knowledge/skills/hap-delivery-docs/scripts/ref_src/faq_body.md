# 文档说明

本文档汇总 HAP 私有部署在交付与日常运行过程中常见的故障现象、配置问题与处理方法，内容与明道云官方 FAQ 文档保持一致，章节顺序与标题与原文一致以便对照查阅。

内容来源：

- 部署问题：https://docs-pd.mingdao.com/faq/deployment
- 服务运行状况检查：https://docs-pd.mingdao.com/faq/troubleshooting/service-status-check
- 工作流持续排队：https://docs-pd.mingdao.com/faq/troubleshooting/workflow-keeps-queuing
- 图标不显示：https://docs-pd.mingdao.com/faq/troubleshooting/icon-not-showing
- 页面无法访问：https://docs-pd.mingdao.com/faq/troubleshooting/page-not-accessible

> 使用提示：从 v7.1.0 开始，mingdaoyun-community 镜像命名已调整为 mingdaoyun-hap，历史镜像名保持不变。执行任何修改前请先备份配置文件（如 /data/mingdao/script/docker-compose.yaml）；生产环境修改后请先在单节点重启观察，确认无影响后再批量执行。

# 第一部分：部署问题

> 原文链接：https://docs-pd.mingdao.com/faq/deployment

## 如何重新安装

```text
# 1. 停止已运行的 HAP 服务（管理器根目录执行，正常输出 stoped）
bash ./service.sh stopall
rm -f ./installer.stage

# 2. 备份 HAP 服务文件（首次部署可直接 rm -rf /data/mingdao/）
mv /data/mingdao/ /home/hapbak/

# 3. 确认已清理干净（以下命令输出应为空，不为空则 kill 对应进程）
docker ps | grep mingdaoyun
netstat -ntpl | grep 38881
ps -ef | grep 'mingdaoyun\|service.sh' | grep -v grep

# 4. 重启管理器，启动成功后访问 http://{服务器IP}:38881 再次安装
bash ./service.sh start
```

## 初始化失败

首次部署提示初始化失败时，执行以下命令观察输出，根据异常信息判断问题：

```text
bash ./service.sh restartall
```

若出现 `iptables failed` 关键字，通常是关闭 firewalld 时清空了 iptables 规则，需重启 Docker 重新生成默认 iptables 规则，然后再重新安装。

## 初始化完成后提示"账号已退出，请重新登录"

基本原因：服务器硬盘 IOPS 性能较低，服务启动过程中硬盘 IO 占满，导致存储组件启动缓慢。解决方法：在 docker-compose.yaml 的 app 服务中添加环境变量延迟微服务启动，添加后 `bash service.sh restartall` 重启：

```text
services:
  app:
    environment:
      ENV_ROLE_MODE_WAITMS: "90000"
```

ENV_ROLE_MODE_WAITMS 单位毫秒，默认 30 秒；示例调大到 90 秒，让存储组件先于微服务启动完成；仍无法解决可继续增大（如 180 秒）。治本方案是部署于高性能硬盘（SSD/NVMe）。

## 服务启动完成遇到响应码错误（Service response code error）

磁盘 I/O 性能较低导致启动较慢，启动 5 分钟后健康检查超时未响应即抛错。检查方法：

```text
# 1. 尝试访问 HAP 页面，能正常访问即核心服务已启动完成
# 2. 检查微服务容器日志（应主要为 INFO 级别）
docker logs $(docker ps | grep -E 'mingdaoyun-community|mingdaoyun-hap' | awk '{print $1}')
```

## 如何配置开机自启动

以管理器路径 /usr/local/MDPrivateDeployment/ 为例，推荐 systemd 方式：

```text
cat > /etc/systemd/system/hap-manager.service <<'EOF'
[Unit]
Description=HAP Manager
After=docker.service
Wants=docker.service
[Service]
Type=oneshot
WorkingDirectory=/usr/local/MDPrivateDeployment
ExecStart=/bin/bash service.sh restartall
RemainAfterExit=yes
StandardOutput=append:/usr/local/MDPrivateDeployment/hap-manager.log
StandardError=append:/usr/local/MDPrivateDeployment/hap-manager.log
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable hap-manager
```

## 服务器重启后 HAP 服务无法正常启动

```text
bash ./service.sh stopall
rm -f service.pid
bash ./service.sh startall
```

## 密钥丢失 / 服务器 Id 不显示

```text
bash ./service.sh stopall
# kill 残留进程（有输出则全部 kill）
ps -ef | grep 'mingdaoyun\|service.sh' | grep -v grep
bash ./service.sh startall
```

可能原因：服务器资源饱和导致管理器进程被强制终止；服务器时间不准确导致密钥有效期判断错误；重启后管理器未设开机自启；启停命令操作不规范。

## Kafka 启动失败

单机模式下 Kafka 为内置组件，非正常关闭（断电、OOM）可能损坏 Kafka/ZooKeeper 元数据，单机无副本只能清空异常数据重新初始化：

```text
bash ./service.sh stopall
mv /data/mingdao/script/volume/data/kafka{,_bak_$(date +%Y%m%d%H%M)}
mv /data/mingdao/script/volume/data/zookeeper{,_bak_$(date +%Y%m%d%H%M)}
bash ./service.sh startall
```

## 文档无法在线预览

内网与外部访问地址不通会导致预览失败，在 doc 服务中添加内网访问地址：

```text
services:
  doc:
    environment:
      ENV_FILE_INNER_URI: "app:8880"
```

如配置无误，可在预览界面按 F12 重新触发报错，查看 console 报错进一步分析（如跨域、http/https 协议头不一致）。

## 升级后页面左下角版本号不正确

```text
services:
  app:
    environment:
      ENV_APP_VERSION: "7.3.2"
```

## 工作表导出 Excel 失败（504 Gateway Time-out）

多为代理层超时与体积限制所致（Nginx 为例）：

```text
location ~ /excelapi {
  proxy_set_header Host $http_host;
  proxy_read_timeout 1800s;
  client_max_body_size 256m;
  proxy_pass http://hap;
}
```

## 上传附件接口超时

大于 4MB 文件默认分片上传，网络原因可能导致分片超时（Nginx 为例）：

```text
location ~ /file {
  proxy_set_header Host $http_host;
  proxy_read_timeout 1800s;
  client_max_body_size 20480m;
  proxy_pass http://hap;
}
```

## 如何开启子路径方式部署

```text
services:
  app:
    environment:
      ENV_MINGDAO_SUBPATH: "/hap"
```

## 如何开启双访问地址

添加 ENV_EXT_MINGDAO_PROTO/HOST/PORT，暴露端口 18880，再将外部域名解析到主机 18880 端口：

```text
services:
  app:
    environment:
      ENV_EXT_MINGDAO_PROTO: "http"
      ENV_EXT_MINGDAO_HOST: "hap1.domain.com"
      ENV_EXT_MINGDAO_PORT: "18880"
    ports:
      - 8880:8880
      - 18880:18880
```

详见多地址配置说明：https://docs-pd.mingdao.com/deployment/proxy/multipleurl

## 如何修改默认存储路径

`tail -n 3 service.sh` 查看管理器版本号。新安装：管理器 ≥ 3.6.0 启动前改 service.sh 的 installDir；< 3.6.0 启动前创建 /etc/pdcaptain.json 指定 dataDir。迁移：≥ 3.6.0 改 installDir，停服后将 /data/mingdao 全部移到 installDir 下再重启。

## 常用环境变量速查（app 服务，添加后重启生效）

| 场景 | 变量 | 示例 |
| --- | --- | --- |
| MongoDB 缓存上限 | ENV_MONGODB_CACHEGB | 6（默认 (内存-18)/2） |
| Redis 内存上限 | ENV_REDIS_MAXMEMORY | 5gb |
| 登录会话超时 | ENV_SESSION_TIMEOUT_MINUTES | 30（默认 10080） |
| 取消每次验证码 | ENV_LOGIN_CAPTCHA_LIMIT_COUNT | 0 |
| 登录失败锁定 | ENV_LOGIN_LOCK_LIMIT_COUNT / _MINUTES | 4 / 30 |
| 按 IP 锁定 | ENV_LOGIN_IP_LOCK_LIMIT_COUNT / _MINUTES | 10 / 30（需代理传 X-Real-IP） |
| 文件类型黑/白名单 | ENV_FILEEXT_BLOCKLIST / _ALLOWLIST | .exe,.sh / .docx,.txt |
| iframe 嵌入 | ENV_FRAME_OPTIONS | ALLOWALL |
| Webhook 超时 | ENV_WORKFLOW_WEBHOOK_TIMEOUT | 30（秒，默认 10） |
| 代码块超时/内存 | ENV_WORKFLOW_COMMAND_TIMEOUT / _MAXMEMORY | 30 / 128 |
| 工作流消费线程 | ENV_WORKFLOW_CONSUMER_THREADS | 与 topic 分区数匹配 |

# 第二部分：服务运行状况检查

> 原文链接：https://docs-pd.mingdao.com/faq/troubleshooting/service-status-check

## 容器/服务日志

```text
# 单机：微服务应用
docker logs $(docker ps -a | grep -E 'mingdaoyun-community|mingdaoyun-hap' | awk '{print $1}')
# 单机：存储组件
docker logs $(docker ps -a | grep mingdaoyun-sc | awk '{print $1}')
# 集群：
kubectl get pod -o wide
kubectl logs <pod-name>
```

日志以 INFO 为主、滚动平稳为正常；持续 ERROR / 堆栈需进一步分析。

## 物理资源检查

| 资源 | 命令 | 说明 |
| --- | --- | --- |
| CPU | `top -c` | 持续打满需扩容或排查热点进程 |
| 内存 | `free -h` | 接近占满有系统异常风险 |
| 磁盘 | `df -Th` | 分区写满将导致不可用 |
| 进程内存排序 | `top -co %MEM` | 定位异常进程 |

重启服务：单机 `bash service.sh restartall`；集群 `kubectl rollout restart deploy <name>`。重点关注历史资源趋势，从根因（MongoDB 慢查询、磁盘 I/O、空间耗尽）入手。

# 第三部分：工作流持续排队

> 原文链接：https://docs-pd.mingdao.com/faq/troubleshooting/workflow-keeps-queuing

## 有消费但堆积量大

触发器配置不当或工作流死循环产生海量事件。非必要工作流可临时停用，队列会快速消化；`top` 看 CPU/内存；按官方优化文档处理 MongoDB 慢查询；K8s 有余量时扩容。

## 完全不消费（队列阻塞）

```text
df -Th                       # 查磁盘
systemctl status kafka       # 查 Kafka（独立部署）
# 查消费组积压
/usr/local/kafka/bin/kafka-consumer-groups.sh --bootstrap-server 127.0.0.1:9092 --describe --group md-workflow-consumer
```

## 消费组 Rebalance 处理

```text
# 单机
docker exec -it $(docker ps | grep -E 'mingdaoyun-community|mingdaoyun-hap' | awk '{print $1}') bash
source /entrypoint.sh && workflowconsumerShutdown
source /entrypoint.sh && workflowrouterconsumerShutdown
# 集群
kubectl rollout restart deploy workflowconsumer
kubectl rollout restart deploy workflowrouterconsumer
```

提升消费并发：先调大对应 Kafka topic 分区数，再设置 `ENV_WORKFLOW_CONSUMER_THREADS` / `ENV_WORKSHEET_CONSUMER_THREADS`（与分区数匹配）。

# 第四部分：图标不显示

> 原文链接：https://docs-pd.mingdao.com/faq/troubleshooting/icon-not-showing

浏览器访问地址与 docker-compose.yaml 中 `ENV_ADDRESS_MAIN` 不一致时，图标无法显示（同样会导致工作流页面卡加载、文件上传失败）。处理：

```text
# 1. 编辑 /data/mingdao/script/docker-compose.yaml
# 2. 将 ENV_ADDRESS_MAIN 改为与浏览器访问地址完全一致的 URL
# 3. 重启
bash service.sh restartall
```

如需保留原访问地址同时可用，参考多地址配置说明。

# 第五部分：页面无法访问

> 原文链接：https://docs-pd.mingdao.com/faq/troubleshooting/page-not-accessible

## 基础排查

```text
docker ps -a                 # 或 kubectl get pod -A
docker logs $(docker ps | grep -E 'mingdaoyun-community|mingdaoyun-hap' | awk '{print $1}')
bash service.sh restartall   # 或 kubectl rollout restart
```

## 网络问题（ERR_CONNECTION_TIMED_OUT）

云安全组放通入站所需端口；企业防火墙确认放通外部访问；服务器 firewalld/nftables 已关闭。

## 证书问题（ERR_SSL_PROTOCOL_ERROR）

证书过期及时更新；域名不匹配核对证书 CN/SAN；自签证书客户端安装根证书。

## DNS 问题（ERR_NAME_NOT_RESOLVED）

`nslookup` / `dig` 验证解析；确认域名已注册并解析到访问入口；变更后等待缓存刷新。

# 附录：进一步支持

- 官方文档中心：https://docs-pd.mingdao.com
- 部署 FAQ：https://docs-pd.mingdao.com/faq/deployment
- 排障专题：https://docs-pd.mingdao.com/faq/troubleshooting/service-status-check
- 本文档随官方 FAQ 更新增量维护；如与官方最新内容不一致，以官方为准。
