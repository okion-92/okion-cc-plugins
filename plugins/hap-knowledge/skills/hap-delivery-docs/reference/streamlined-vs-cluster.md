# 集群精简版 vs 集群标准版/专业版 差异说明（核心参考）

> 精简版是**架构层面的根本不同**，不是场景 A/B 那种微小差异。
> 第 2 层版本维度：精简版 与 标准版/专业版 并列。**精简版不走第 3 层场景 A/B**（场景 A/B 仅适用于标准版/专业版的 MinIO 多节点部署形态）。
> 出厂模板见 source-cache/deploy_streamlined.json（基于真实精简版文档）。

## 一句话区别

- **集群精简版**：适用并发 300+ 的中小规模。所有存储组件**单节点**（MySQL/MongoDB/Redis/Kafka/ES/MinIO/File 各 1 个实例），K8s **1 主 1 从**，**6 节点**。节省资源，但存储层有单点故障风险。
- **集群标准版/专业版**：适用并发 600+/1000+。组件**集群化**（MongoDB 副本集、MySQL MGR+Router、Redis 哨兵、Kafka/ES/MinIO 多节点），K8s 三 Master。标准版组件共置 **17 节点**；专业版各组件独立部署 **26 节点**。高可用。

## 精简版节点拓扑（6 节点）

| 节点角色 | 示例 IP | 部署组件 |
|---|---|---|
| Nginx | 192.168.1.20 | Nginx 反向代理（单节点，无 Keepalived VIP） |
| 微服务 01 | 192.168.1.21 | K8s Master+Node + Istio + 微服务 |
| 微服务 02 | 192.168.1.22 | K8s Node + 微服务 |
| 中间件 | 192.168.1.51 | Kafka + ZooKeeper + ES + MinIO + File（全部单节点共置） |
| 数据库 | 192.168.1.31 | MySQL + MongoDB + Redis（全部单节点共置） |
| HDP（Flink 节点） | 192.168.1.30 | 超级数据平台服务 / Flink |

## 精简版与集群版的逐项差异（生成各文档时据此分支）

### 1. 数据库层（最大差异）
| 组件 | 精简版 | 标准/专业版 |
|---|---|---|
| MySQL | **单节点**（3306，直连） | MGR + Router（6446 读写 / 6447 只读 / 33060 / 33061） |
| MongoDB | **单节点**（27017，无副本集） | 副本集（27017，1 Primary + 2 Secondary + keyFile） |
| Redis | **单节点**（6379，无哨兵） | 哨兵模式（6379 + Sentinel 26379） |
| 部署方式 | 3 组件共置 1 台数据库节点 | MySQL+MongoDB 共置 3 台；Redis 独立 3 台 |

### 2. 中间件层
| 组件 | 精简版 | 标准/专业版 |
|---|---|---|
| Kafka | **单节点**（9092 + ZK 2181，单 broker） | 3 节点集群（含 2888/3888 ZK 选主） |
| Elasticsearch | **单节点**（9200，discovery.type=single-node，无证书集群） | 3 节点集群（9200/9300 + x-pack TLS 证书） |
| MinIO | **单节点**（9011，单实例，单节点 Swarm） | 多节点（4 节点 EC 纠删码 / Swarm 集群或独立） |
| File | **单节点**（9000，单实例） | 4 节点（9001-9004） |
| 部署方式 | Kafka+ES+MinIO+File 共置 1 台中间件节点 | 分布在 3~4 台 |

### 3. 微服务层（K8s）
| 项 | 精简版 | 标准/专业版 |
|---|---|---|
| K8s 拓扑 | **1 主 1 从**（单 Master，single-master-deployment） | 三 Master（multi-master-deployment） |
| 关键步骤 | 必须**移除 Master 污点**让 Pod 调度到 Master（2 台节点不够） | 不移除（Master 充足） |
| Master 宕机 | kubectl 暂不可用，业务容器不受影响 | 三 Master 高可用，自动容灾 |

### 4. 负载层
| 项 | 精简版 | 标准/专业版 |
|---|---|---|
| Nginx | **单节点**（无 VIP） | 双节点 + Keepalived VIP 漂移 |
| upstream | 2 个微服务节点 | 3 个微服务节点 |

### 5. Flink / HDP
- **HDP 节点即 Flink 节点**（HDP 超级数据平台基于 Flink），不另算独立 Flink 节点。
- 精简版：1 台 HDP/Flink 节点（192.168.1.30）；s3.endpoint 指向单节点 MinIO 9011。
- 标准/专业版：2 台 HDP/Flink 节点。

### 6. 节点数口径（=资源表全部行之和，含 HDP 行）
- 精简版：**6 节点**（Nginx1+微服务2+中间件1+数据库1+HDP1）。
- 标准版：**17 节点**（Nginx2+微服务3+Redis3+中间件4+数据库3+HDP2）。
- 专业版：**26 节点**（Nginx2+微服务4+Redis3+Kafka3+ES3+MinIO/File4+MySQL2+MongoDB3+HDP2）。详见 constraints.md B。

## 不随版本变化的内容（精简版与集群版一致）
- 操作系统初始化（防火墙/SELinux/内核/时间同步）
- Docker / containerd 安装方式
- Istio 1.29.1、HAP 微服务镜像与管理器、监控 Prometheus/Grafana
- 端口号本身（MySQL 3306、MongoDB 27017、Redis 6379、Kafka 9092、ES 9200、MinIO 9011、File 9000、K8s 6443、HAP www 8880/18880(按需)、安装管理器 38880(ENV_CAPTAIN_ENDPOINT)、管理入口 38881）
- 镜像版本（精简版与集群版用同一批镜像）

## 命名（精简版）
- 文件名带"集群精简版"，不带场景 A/B（精简版无 A/B）、不带客户名。
  - `HAP部署实施文档_集群精简版.docx` / `HAP_Deployment_Streamlined_Cluster.docx`
  - `HAP运维文档_集群精简版.docx`、`HAP数据迁移文档_单机迁移集群精简版.docx`、`HAP集群精简版_架构图.svg/.png`、`HAP集群精简版_凭据登记表.xlsx`
- 交付清单、两个 PDF（故障处理/资源要求）与版本无关，命名不变。
