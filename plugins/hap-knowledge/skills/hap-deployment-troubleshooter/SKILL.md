---
name: hap-deployment-troubleshooter
description: 明道云 HAP 私有部署排障技能。基于 https://docs-pd.mingdao.com 的部署文档、FAQ、组件文档、运维页面，外加 158 条本机实战故障/配置条目，输出排查顺序、核验项和建议动作。触发：用户提到"部署失败""启动失败""服务起不来""服务挂了""升级后异常""升级后不能用""工作流堆积""工作流持续排队""流程排队""工作流不消费""工作流消费慢""md-workflow-consumer""Kafka rebalance""Kafka 问题""MongoDB 问题""预览失败""附件无法预览""附件下载失败""onlyoffice 报错""预览白屏""接口端口丢失""URL 少端口""Host 头""proxy_set_header""反向代理 Header""nginx 1.29""文档打不开""LibreOffice""HDP""离线部署问题""怎么排查""怎么定位""帮我给一份排障步骤""先排查什么""按官方文档排障"；以及实战库覆盖的"清 Redis 缓存""重置部门/组织/地区/职位""强制退出登录""重置/找回登录密码""物理删除离职用户""限制 IP/UA/来源访问""短信轰炸防护""非 ROOT 改造""log4j 漏洞修复""证书到期续期""慢查询加索引""compact 回收磁盘""磁盘满"等。
---

# HAP 私有部署排障助手

> 本 skill 由 `hap-private-knowledge` 仓库 `sources/faq/` 生成（158 条）。改知识请改 sources 再重生成，**勿直接手改本目录**。完整目录见 `sources/faq/ROUTING.md`。

实战故障/配置全部在 `data/`，本文件只给排查流程与路由。每条知识 = 一个 `## <slug>` 段，含 `现象 / 处理 / 核验`。

## 排查总则（先做这几步再动手）
1. **先定位再动手**：拿到症状先归类（属下面哪个域），别上来就改。
2. **官方优先**：能在 https://docs-pd.mingdao.com 找到依据的，先对照官方；实战库是补充与提速，不是替代官方。
3. **高危操作先备份**：凡 `data/` 里带删除 / reset / 改库 / dropDatabase / 清缓存 / 限流封 IP 的，**执行前先备份对应库表、确认影响范围**，做完走该条的 `核验` 段确认「只动了目标、其余没误伤」。
4. **脱敏**：给用户命令时，密码 / token / 内网 IP / 域名按其真实环境替换，库里是 `<占位符>`。
5. **区分已确认与待确认**：实战条目标的是历史可行解，套到用户当前版本/架构前先核对前提（单机/集群/专业版、版本号）。

## 路由：症状 → data 文件
按症状归到下面某个域，打开对应 `data/*.md`，再在文件内按 `## <slug>` 找最贴近的条目。拿不准用 `sources/faq/ROUTING.md` 全表反查。

- **`data/nginx-proxy-preview.md`** — 预览失败/白屏、附件传不上、X-Forwarded-Proto/$scheme、subs_filter 不生效、favicon、备案号、Prometheus(Alert) 子路径反代、消息红点不消失、ldoc 字体丢失。
- **`data/file-storage-minio.md`** — minio web 访问/隐藏按钮、文件存储独立域名、minio 启动 glibc/x86-64-v2 报错、mc 删文件存储对象。
- **`data/mysql-database.md`** — MySQL 内存高/文件描述符、二进制启动缺共享库、二进制升级、MGR+Router、角色成员为空(表编码)、单机库对外映射、语言自动变、登录日志查询、MySQL 备份恢复脚本。
- **`data/account-org-login.md`** — 开平台登录、忘/重置密码(单机&集群)、强制退出登录、物理删/停用账号、被黑还原 Account/Project、重置部门/组织/地区/职位、清部门/组织成员 Redis 缓存、DB 层改应用设置、低转高迁移管理员丢失。
- **`data/mongodb-workflow.md`** — 工作流堆积/串行堵塞、清流程消息、删工作流历史日志、删专属算力实例、MongoDB 升级/初始化/建索引/聚合副本集/备份/compact/慢日志/重建索引/校准行数/oplog 告警、按时间查工作流、查邮件/webhook 配置、工作流后台登录、wslog 索引重建。
- **`data/kafka-queue.md`** — Kafka 堆积查看/消费内容/重平衡监控/按时间看消息/改副本数/三副本、消费组告警、zookeeper systemd 启动失败、zk 未授权。
- **`data/elasticsearch-search.md`** — ES 写不进去(read_only 锁)、umask 致启动失败、log4j 修复、协作套件搜索初始化、ES 部署连接配置。
- **`data/flink-datapipeline.md`** — Flink 504/异常 job/时区+8/SQLServer PKIX、集群代理负载、Web 加认证、单独 File 服务、SQLServer 开 CDC。
- **`data/k8s-container-docker.md`** — K8s/Docker/istio/containerd 各类：端口占用/MTU 不通/跨主机 VXLAN、coredns 解析失败、证书续期、reset 清理、局部重启生效、挂依赖、firewalld 放行、kubeadm 初始化、内核参数 reset、临时改 grpc 代理等。
- **`data/integration-im.md`** — 钉钉连通性/QPS 流控、企微扫码双地址/集成/解绑、绑定明道与企微账号、微信门户登录。
- **`data/security-hardening.md`** — nginx 限 IP/UA/来源/禁下载/禁国外/安全响应头、iptables 限 nodePort、TLS 弱加密 CVE、SM2 加密环境变量、短信轰炸防护、Redis 改密、HTTPS 证书校验、邮箱忽略 SSL、非 ROOT 改造(单机/集群/polkit)。
- **`data/system-os-misc.md`** — fio 磁盘实测/缺 libaio、LVM 扩容移 swap、rc-local 自启、进程 dump、离线 Python 依赖、Windows 跑 docs-pdop、版本号不一致、freestyle.css 隐藏模块、社区版密钥、达梦客户端、短信 configmap、帮助文档部署、SMTP 测试、应用库重刷。

## 官方映射 / 回复模板 / 案例收件箱（references/）
`data/` 是实战故障/配置库（含已成形的真实案例，如 HDP 中间库未开、searchapi ENV 写法错、nginx 1.29 端口丢失、Excel 打印签名变黑等）。下面三份是手工沉淀，**不由 sources 生成，单独维护**：
- **`references/troubleshooting-map.md`** — 现象 → docs-pd 官方页面映射表（版本/部署/环境变量/升级/工作流排队等入口），用于回到官方核验。
- **`references/response-patterns.md`** — 回复模板（现象不完整 / 官方已覆盖 等场景的话术骨架）。
- **`references/cases.md`** — 新案例**收件箱**：未成形的现场案例先在此草记，攒一两条后反拆进 `sources/faq/` 再重生成（已成形的 5 条已入 data/）。

## 用法
1. 归类症状 → 打开对应 `data/*.md` → 找 `## <slug>` 条目（疑难杂症可对 `references/troubleshooting-map.md` 回官方核验）。
2. 把该条的 `处理` 命令按用户环境脱敏后给出；命令/配置**原样给全，不省略**，多套(单机/集群/专业版)按用户部署模式挑对应那套。
3. 收尾必给该条的 `核验`（没有核验段的，补一句「怎么确认生效」）。
4. 涉及"官方文档怎么说/路由到官方页面/速查卡"→ 转 `hap-docs-workbench`；涉及"升级路径/版本兼容/升级文档"→ 转 `hap-upgrade`；涉及"单机迁集群"→ 转 `hap-standalone-to-cluster-migration`。

## 禁止事项
凭记忆编官网没有的步骤/路径/命令 · 把历史实战解不核对版本架构就照搬 · 高危操作不备份不核验 · 产物里留真实凭据/内网地址。

## 固定声明（正式排障结论末尾建议附）
```md
---
💡 声明：部分内容为历史实战经验 + AI 整理，可能随版本变化。执行删除/重置/改库等高危操作前，务必先备份并对照 [官方文档](https://docs-pd.mingdao.com) 核实。
```
