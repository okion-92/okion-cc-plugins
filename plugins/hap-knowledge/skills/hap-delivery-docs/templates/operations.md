# 模板：运维文档（集群标准版/专业版）

> 结构骨架。出厂快照：source-cache/operations.json。
> 运维文档**适用架构=标准版 17 节点**（含 HDP/Flink 2 台），与部署文档同口径（17）。专业版运维则为 26 节点。

## 文档元信息
- **A/B 独立成档**（与部署文档一致）：标准版/专业版各出场景 A、场景 B 两份；精简版单节点不分 A/B。共 5 份。
- 标题：`运维文档（集群标准版 · 场景 A）`／`运维文档（集群标准版 · 场景 B）`／`运维文档（集群专业版 · 场景 A）`／`运维文档（集群专业版 · 场景 B）`／`运维文档（集群精简版）`。
- 英文副标题：`HAP Standard/Professional/Streamlined Cluster Operations and Maintenance — Scenario A (Without Swarm) / B (With Swarm)`。**注意英文用 and 而非 &**（封面副标题里的 & 若未转义会破坏 document.xml；脚本已加转义，但仍建议用 and）。
- 文件名：`HAP运维文档_集群标准版_场景A.docx` 等（带场景，与部署文档命名一致）；精简版 `HAP运维文档_集群精简版.docx`。
- 封面：用 inject_cover.py 照搬附件首页（与部署文档同一套封面模板），标题/英文副标题/页眉页脚均带对应场景标识。
- 适用架构段：标准版 17 节点 / 专业版 26 节点（各组件独立）/ 精简版 6 节点（单节点）。

## 章节骨架
| 章节 | A/B 分支 | 备注 |
|---|---|---|
| 文档说明 / 适用架构 / 运维原则 | **措辞** | 声明本场景、指明与另一场景差异 |
| 一、组件维护信息（1.1 数据库/1.2 中间件/1.3 微服务/1.4 Nginx） | **1.2 是** | MinIO+File 安装路径列：A=“单节点 docker swarm”；B=“Swarm 集群统一编排”。端口 A/B 同为 901X/900X |
| 二、常用命令（2.1~2.8） | **2.3 是** | A=每节点各自 docker stack；B=仅 Node01 docker service/docker stack 统一管理 |
| 三、数据存储介绍 | 否 | |
| 四、数据备份（4.1~4.6） | 否 | 在 SECONDARY/Slave 执行 |
| 五、数据还原（5.1~5.6） | 否 | |
| 六、数据清理（6.1~6.5） | 否 | |
| 七、版本升级（7.1~7.4 含回滚） | **7.2.1 是** | A=4 节点各自改 yaml 滚动重启；B=仅 Node01 改一份 yaml，docker stack deploy 滚动 |
| 八、资源监控 | 否 | Prometheus/Grafana |
| 九、安全管理 | **9.1 是** | A=无需 2377/7946/4789；B=4 中间件节点间须放通 2377/7946/4789 |
| 十、故障排查 | **10.7 是** | A=每节点独立排查 docker stack；B=Node01 docker node ls/service ps 统一排查 |

## A/B 分支点（措辞/命令级，集中在 MinIO+File 相关处）
1. 文档说明 / 适用架构：声明场景 A（未开启 Swarm）或 B（开启 Swarm），并指明另一场景文档。
2. 1.2 组件表 MinIO+File 行安装路径列描述（单节点 swarm vs Swarm 集群编排）。
3. 2.3 标题与命令：A 节点各自管理（docker stack）；B 经 Node01 Swarm 统一管理（docker service / docker stack）。
4. 7.2.1 MinIO/File 升级：A 各节点改本机 yaml；B 仅 Node01 改完整 yaml 后 docker stack deploy。
5. 9.1 网络访问控制：A 无需 Swarm 端口；B 须放通 2377/7946/4789。
6. 10.7 MinIO/File 故障排查：A 每节点独立；B Node01 统一调度（docker node ls / service ps / service update --force）。
> 派生方式：先做场景 A 全文，再用脚本替换上述 6 处差异点得场景 B（参见已沉淀流程）。专业版在标准版基础上按组件独立节点改 IP（MySQL .31-33 / MongoDB .34-36 / Kafka .51-53 / ES .61-63 / MinIO+File .71-74 / Flink .81-82）。

## 参数替换
全部节点 IP / VIP / 域名 / 端口（按 params-template）。专业版按独立节点 IP。

---

## 精简版运维（集群精简版）

精简版运维**比集群版简单很多**（无副本集/MGR/哨兵/集群滚动），按单节点口径出文档：
- 适用架构段：**6 节点**（Nginx 单 / K8s 1主1从 / 中间件单节点 / 数据库单节点 / HDP-Flink 1 台），非 17 节点。
- 组件维护表：MySQL 单节点 3306（无 Router/MGR 行）、MongoDB 单节点 27017（无副本集行）、Redis 单节点 6379（无 Sentinel 行）；中间件 Kafka/ES/MinIO/File 各单实例。
- 备份还原：单节点直接 mysqldump / mongodump / redis BGSAVE / mc mirror；**无"在 SECONDARY/Slave 执行"**的说法，直接在本节点操作。
- 数据清理、版本升级、监控、安全、故障排查：保留，但去掉集群特有项（MGR 恢复、副本集选主、哨兵切换、ES 集群分片、Swarm 多节点）。
- 命名：`HAP运维文档_集群精简版.docx`。不分 A/B。
