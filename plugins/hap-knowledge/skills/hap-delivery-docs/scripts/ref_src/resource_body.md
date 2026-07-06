# 文档说明

本文档汇总 HAP 私有部署的官方平台支持范围、组件版本要求、服务器资源推荐配置与服务器基础性能要求，作为客户进行容量规划、硬件采购与部署选型的决策依据。所有内容与明道云官方文档保持一致，章节标题与原文一致以便对照查阅。

内容来源：

- 支持平台：https://docs-pd.mingdao.com/deployment/platform
- 组件支持版本：https://docs-pd.mingdao.com/deployment/component
- 服务器资源推荐：https://docs-pd.mingdao.com/deployment/source
- 服务器性能要求：https://docs-pd.mingdao.com/deployment/server-reqs

> 选型原则：从 v7.1.0 起 mingdaoyun-community 镜像改名 mingdaoyun-hap，历史镜像名不变。本文档涵盖单机模式与集群（精简/标准/专业/HyperScale）全部档次：生产环境优先集群模式，如必须单机建议内存 ≥ 48GB；严禁生产使用机械硬盘（HDD），统一 SSD、数据库节点优先 NVMe；CPU 主频 ≥ 2.5 GHz，建议近 5 年主流型号。

# 一、支持平台

## 1.1 操作系统与 CPU 架构

| 操作系统 | x86_64 / AMD64 | ARM64 / AARCH64 |
| --- | --- | --- |
| Debian | ✅ 8.2+ | ✅ 10.2+ |
| CentOS | ✅ 7.3+ | ✅ 8.0+ |
| RedHat | ✅ 7.3+ | ✅ 8.0+ |
| Fedora | ✅ 30+ | ✅ 29+ |
| Ubuntu | ✅ 14.04+ | — |
| Amazon Linux | ✅ 2023 | — |
| EulerOS | ✅ 21.10+ | ✅ 21.10+ |
| UOS（统信） | ✅ 20 | ✅ 20 |
| 银河麒麟 | ✅ 10 | ✅ 10 |

## 1.2 ARM 架构要求

因 MongoDB 依赖，需 **ARMv8.2-A 及后续版本微架构**的 CPU。支持：华为鲲鹏 920、飞腾腾云 S5000C。不支持：鲲鹏 916、飞腾 S2500 / FT-2000+/64 / FT-1500A/16。

## 1.3 公有云平台

支持华为云（含鲲鹏服务器）、阿里云、腾讯云、微软 Azure、AWS，以及百度云、金山云、UCloud、电信/移动/联通云等。阿里云、腾讯云云市场提供简化部署镜像。

# 二、组件支持版本

## 2.1 自建组件版本

| 组件 | 单机默认 | 集群默认 | 支持版本 | 部署架构 | 国产化替代 |
| --- | --- | --- | --- | --- | --- |
| MySQL | v5.7.44 | v8.0.45 | v5.7.x / v8.x | 单节点 / 主从 / MGR | 达梦、人大金仓、OceanBase、虚谷、瀚高、GBase8c、TiDB、TDSQL、亚信、openGauss、GreatDB、GoldenDB |
| MongoDB | v4.4.30 | v4.4.30 | v4.4.30+ | 单节点 / 副本集 | DDS、TapDB |
| Redis | v8.6.3 | v8.6.3 | v3.2.13+ | 单节点 / 主从 / 哨兵 | AMDC、CacheServer、CDM、TongRDS |
| Kafka | v3.9.1 | v3.9.1 | v1.1.1+ / v2.x / v3.x | 单节点 / 集群 | ADMQ、CloudMQ、TongLINK/Q-D |
| Elasticsearch | v8.19.6 | v8.19.8 | v8.x | 单节点 / 集群 | — |
| Flink | v1.19 | v1.19 | v1.19 | 单节点 / 集群 | — |
| Nginx | v1.30.2 | v1.30.2 | v1.16+ | — | WebServer、TongHttpServer |
| MinIO | RELEASE.2025-04-22 | RELEASE.2025-04-22 | — | 单节点 / 多节点 | 兼容 S3 的 OSS/COS/OBS、RustFS |

## 2.2 云产品组件

- **阿里云**：MySQL（5.7/8.0）、MongoDB（4.x/5.x）、Redis（4.x/5.0）、Kafka（2.2）、Elasticsearch（8.5）、OSS。
- **腾讯云**：MySQL（5.7/8.0）、MongoDB（3.x/4.x/5.0）、Redis（4.x/5.0）、Kafka（2.x/3.x）、Elasticsearch（8.8.1）、COS。

# 三、服务器资源推荐

## 3.1 单机模式

微服务（按并发）：

| 并发 | 配置 | 操作系统 | 说明 |
| --- | --- | --- | --- |
| 100 以内 | 8C / 32G / 40G 系统 + 100G SSD | Debian 12 | 基础测试环境 |
| 200 以内 | 8C / 48G / 60G 系统 + 200G SSD | Debian 12 | 生产最低 48GB 内存 |
| 300 以内 | 16C / 64G / 60G 系统 + 200G SSD | Debian 12 | — |
| 300 以上 | 32C / 64G / 60G 系统 + 200G SSD | Debian 12 | 建议改用集群模式 |

可选模块：Flink 数据同步（1~20 任务 8C/32G、1~50 任务 16C/64G、50+ 集群）；Milvus 向量（标准 8C/32G、增强 16C/64G）。

## 3.2 集群精简版（并发 300+，6 节点）

| 角色 | 配置 | 服务 | 数量 |
| --- | --- | --- | --- |
| 负载 | 4C / 8G / 60G + 200G SSD | Nginx | 1 |
| 微服务 | 16C / 64G / 60G + 200G SSD | 微服务 | 2 |
| 中间件 | 8C / 32G / 60G + 500G SSD | Kafka/ES/MinIO/File | 1 |
| 数据库 | 8C / 32G / 60G + 300G SSD | MySQL/MongoDB/Redis | 1 |
| 数据同步(可选) | 8C / 32G / 60G + 200G SSD | Flink | 1 |
| 向量检索(可选) | 16C / 64G + 200G SSD | Milvus | 1 |
| 向量服务(可选) | 4C / 8G + 100G SSD | etcd | 1 |

## 3.3 集群标准版（并发 600+，17 节点）

| 角色 | 配置 | 服务 | 数量 |
| --- | --- | --- | --- |
| 负载 | 4C / 8G / 60G + 200G SSD | Nginx | 2 |
| 微服务 | 16C / 64G / 60G + 200G SSD | 微服务 | 3 |
| 缓存 | 4C / 16G / 60G + 200G SSD | Redis | 3 |
| 中间件 | 8C / 32G / 60G + 500G SSD | Kafka/ES/MinIO/File | 4 |
| 数据库 | 8C / 32G / 60G + 300G SSD | MySQL/MongoDB（共置） | 3 |
| 数据同步(可选) | 8C / 32G / 60G + 200G SSD | Flink | 2 |
| 向量检索(可选) | 16C / 64G + 200G SSD | Milvus | 2 |
| 向量服务(可选) | 4C / 8G + 100G SSD | etcd | 3 |

## 3.4 集群专业版（并发 1000+，29 节点）

| 角色 | 配置 | 服务 | 数量 |
| --- | --- | --- | --- |
| 负载 | 4C / 8G / 60G + 200G SSD | Nginx | 2 |
| 微服务 | 24C / 64G / 60G + 300G SSD | 微服务 | 5 |
| 缓存 | 8C / 32G / 60G + 200G SSD | Redis | 3 |
| 消息队列 | 8C / 32G / 60G + 500G SSD | Kafka | 3 |
| 全文检索 | 8C / 32G / 60G + 500G SSD | Elasticsearch | 3 |
| 文件存储 | 8C / 32G / 60G + 500G SSD | MinIO / HAP File | 4 |
| 关系库 | 8C / 16G / 60G + 200G SSD | MySQL | 3 |
| 文档库 | 32C / 64G / 60G + 500G SSD | MongoDB | 3 |
| 数据同步(可选) | 16C / 64G / 60G + 200G SSD | Flink | 3 |
| 向量检索(可选) | 16C / 64G + 200G SSD | Milvus | 3 |
| 向量服务(可选) | 4C / 16G + 100G SSD | etcd | 3 |

## 3.5 集群 HyperScale 旗舰版（并发 1000+ · 多可用区）

| 角色 | 配置 | 服务 | 数量 |
| --- | --- | --- | --- |
| 负载 | 4C / 8G / 60G + 200G SSD | Nginx | 3 |
| 微服务 | 24C / 64G / 60G + 300G SSD | 微服务 | 6 |
| 缓存 | 8C / 32G / 60G + 200G SSD | Redis | 5 |
| 消息队列 | 8C / 32G / 60G + 500G SSD | Kafka | 5 |
| 全文检索 | 8C / 32G / 60G + 500G SSD | Elasticsearch | 5 |
| 文件存储 | 8C / 32G / 60G + 500G SSD | 文件对象存储 | 8 |
| 关系库 | 8C / 16G / 60G + 200G SSD | MySQL | 5 |
| 文档库 | 32C / 64G / 60G + 500G SSD | MongoDB | 5 |
| 数据同步(可选) | 16C / 64G / 60G + 200G SSD | Flink | 5 |

# 四、服务器性能要求

| 项 | 要求 |
| --- | --- |
| CPU 主频 | ≥ 2.5 GHz（近 5 年处理器，单核性能优先） |
| 磁盘（必须 SSD） | 随机读/写 IOPS ≥ 15000；顺序读/写 ≥ 200 MiB/s；数据库优先 NVMe |
| 内网（集群模式） | 单机 PPS ≥ 200,000；带宽 ≥ 2 Gbps |
| 外网带宽 | ≥ 30 Mbps（文件上传下载量大时按需提高） |

# 附录：选型决策参考

- 并发 ≤ 300 且非核心生产：可单机模式（内存 ≥ 48GB、SSD）；核心生产建议集群。
- 并发 600 左右：集群标准版（17 节点，部分共置，基本高可用）。
- 并发 1000+：集群专业版（29 节点，各组件独立）；多可用区/超大规模选 HyperScale。
- 采购前核对：节点数与配置按目标档次；全 SSD（数据库 NVMe，IOPS 实测达标）；内网二层互通、带宽达标；CPU 架构统一；仅负载入口对外、其余内网隔离；预留 20%~30% 余量。
- 数据同步（Flink）/向量检索（Milvus + etcd）为可选模块，启用 AI/向量能力时再加。
- 表格数据取官方最新；如与官方《服务器资源推荐》存在差异，以官方为准。
