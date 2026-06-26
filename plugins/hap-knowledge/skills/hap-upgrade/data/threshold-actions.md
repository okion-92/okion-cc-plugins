---
title: HAP 逐版本结构性阈值动作台账（跨过即触发）
source_url: https://docs-pd.mingdao.com/version
last_verified: 2026-06-18   # 全部逐页实时核验（/upgrade/{ver}/），范围 4.0.0~7.3.0
hap_version: any
tags: [upgrade, threshold-actions, ledger]
feeds: [hap-upgrade]
---

升级路径**跨过某版本**就必须执行的结构性/配置性动作（新增服务、改地址、改名、组件版本、DB 引擎、环境变量）。
区别于常规每版本 DDL（那些靠 [[crossver-rules]] 实时抓详情页）。**生成升级文档时，把路径覆盖的所有下列动作逐条并入。**

> 范围 3.1.0~7.3.0，已逐页实时核验。<3.1.0（3.0.x/2.x/1.x，2020-2022 远古版本）未扫，几乎无人从那升，需要时再补。标 √ 但仅含 DDL 的版本（如 3.5.1/3.8.0/4.1.0/4.7.0/6.2.4/6.2.5/6.3.0/6.5.0/7.2.0/7.2.4）已确认**无**结构动作。

## 一、集群新增/删除服务（service.yaml，累积——跨多版本要把每个都加上）
配置文件 `/data/mingdao/script/kubernetes/service.yaml`。所有服务用同一目标镜像，靠 `ENV_SERVERID` 区分。
**完整 YAML 模板 + 各服务 ENV_SERVERID/端口/资源参数表见 [[command-library]] §新增微服务**。本表只列路径动作：

| 版本 | 动作 | 端口 |
|---|---|---|
| 4.4.0 | 新增 `templatemessage` | 3259(gRPC) |
| 4.5.0 | 新增 `wps`（金山 WPS 集成） | 9017 |
| 5.0.0 | 新增 `reportconsumer`（消费者，无 Service 端口） | — |
| 5.1.0 | 新增 `computingschedule`；`command` 服务镜像改为 `mingdaoyun-command:node1018-python36`（清持久化重装扩展） | 9158(http)+9159(gRPC) |
| 5.3.0 | 新增 `commandpuppeteer` | 9198 |
| 5.4.0 | 新增 `datamanager` | 8322 |
| 5.8.0 | 新增 `workflowplugin`(8087+9087)；`push` 服务加 gRPC 端口 | 3009(push gRPC) |
| 6.2.0 | 新增 `payment` | 9161 |
| 7.0.0 | 新增 `ai` + `mcp` | 8066 / 8165 |
| 7.3.0 | **删除 `pushserver`**；新增 `platformapi` + `openauthorization` | 1317 / 5322 |

## 一·补、MongoDB 认证模式建库（仅当开了 MongoDB 认证；跨多版本要把覆盖到的库全建齐）
建库命令（`db.createUser` 完整语法）见 [[command-library]] §MongoDB 建库。
| 版本 | 需建库 |
|---|---|
| 3.4.0 | `mdintegration` |
| 3.7.0 | `mdworksheetlog` |
| 3.9.0 | `mdworksheetsearch` |
| 4.0.0 | `mddatapipeline` |
| 5.8.0 | `mdwfplugin` |
| 6.2.0 | `mdpayment` |
| 7.0.0 | `mdwfai` |
| 7.3.0 | `mdopenauth`、`mdaisearch` |

## 二、地址 / 环境变量
- **5.1.0：`127.0.0.1` → `sc`（⚠️ 仅单机！）**。`sc` 是单机版内置存储一体化容器名；**集群没有 sc**，存储组件是独立部署，连接地址指向各自服务/主机（如 `$ENV_MONGODB_HOST`），**集群升级不做此步**。仅单机：自定义过连接地址为 `127.0.0.1` 的改成 `sc`，涉及端口 3306/27017/6379/9092/9200/9000。
- **5.4.0：集群 file 服务新增环境变量** `ENV_FILE_DOMAIN: http://file1:9000,...`（与 `ENV_FILE_ENDPOINTS` 对齐，但要带 `http://` 前缀）。

## 二·补、Kafka / 中间件配置
- **4.0.0：集群 Kafka `server.properties` 加两项** `message.max.bytes=10485760`、`replica.fetch.max.bytes=10485760`。

## 三、DB 引擎 / 版本（前置或迁移）
- **5.0.2（仅 ARM64）**：MariaDB → MySQL，需 MySQL 数据迁移。
- **5.5.0**：MongoDB **3.4.24→4.4.30 逐级升**（3.4→3.6→4.0→4.2→4.4，每级 `setFeatureCompatibilityVersion`，不能跳级）+ **切换为副本集**（供 5.6.0 聚合表；单机内置 MongoDB 默认非副本集）。命令见 [[command-library]] §MongoDB 升级。升级后**重建 mdwsrows 库全部自定义索引**（集群 `reIndexWithCmd.js`）。
- **6.0.0**：前置要求 MongoDB ≥ 4.4。

## 四、组件版本：区分"硬要求"与"推荐版本"
**硬要求（必须满足，否则功能不可用/启动失败）：**
- **MongoDB 升到 4.4.30 + 切副本集**（5.5.0 起，6.0.0 前置）：从 3.4.24 须**逐级** 3.4→3.6→4.0→4.2→4.4（每级 `setFeatureCompatibilityVersion`）；并切换为副本集供 5.6.0 聚合表。命令见 [[command-library]] §MongoDB 升级。

**HAP 自有组件（属升级步骤，按轨迹升到最终版）：**
| 组件 | 轨迹（取最终） | 适用 |
|---|---|---|
| sc 存储组件 | 5.2.0→2.0.0 · 5.5.0→3.0.0 · 6.2.0→3.1.0 · 6.4.0→**3.2.0** | **仅单机**（集群无 sc，各存储组件独立升级） |
| file 文件服务 | 3.1.0→1.3.0 · 3.6.0→1.4.0 · 5.0.0→1.5.0 · 5.4.0→1.6.0 · 6.2.0→**1.7.0** | 单机+集群 |
| doc 文档预览（默认） | 6.2.0→**2.0.0** | 单机+集群 |
| ldoc 文档预览扩展（LibreOffice，**仅启用时**，与 doc 独立） | 6.2.4→2.0.1 · 6.2.5→**2.0.2** | 单机+集群 |

**外部数据存储——推荐版本，非强制**（只要在支持范围内即可，不必强行升到下列具体号）：
| 组件 | 推荐(集群) | 最低支持 |
|---|---|---|
| Elasticsearch | 8.19.8 | 8.x |
| Kafka | 3.9.1 | 1.1.1+ |
| Redis | 8.6.3 | 3.2.13+ |
| MySQL | 8.0.45 | 5.7.x / 8.x |

> 各版本逐条 DDL/MongoDB/数据脚本见 [[per-version-ledger]]，生成文档时按低→高铺进"升级后操作"。

## 五、镜像改名（7.1.0：mingdaoyun-community → mingdaoyun-hap）
替换命令（单机+集群 sed）见 [[command-library]] §镜像命名变更。历史镜像名保持不变，跨过 7.1.0 必做替换。

**连带影响——所有引用镜像名的命令都要按版本挑对名字：**
- 目标 **< 7.1.0**：拉镜像/进容器/tag 一律用 `mingdaoyun-community`。
- 目标 **>= 7.1.0**：一律用 `mingdaoyun-hap`。
- **跨过 7.1.0 的升级要分段**：改名 sed 执行**之前**的步骤（如旧版本下的进容器、拉旧镜像）用 `mingdaoyun-community`；**之后**的步骤用 `mingdaoyun-hap`。
- 排障/兜底写法（不确定环境处在哪侧）：`docker ps | grep -E 'mingdaoyun-community|mingdaoyun-hap'` 两个名都匹配。

## 六、条件功能（非强制，用户要启用才做）
- **5.6.0 起：启用聚合表**。依赖 Flink（MongoDB CDC 连接器）+ MongoDB 4.4+ **副本集**模式；配置文件加环境变量 `ENV_MONGODB_URI_AGGREGATIONWSROWS` 后重启。
  - 单机：用 `mingdaoyun-sc:3.0.0+` 内置 MongoDB 即满足版本要求。
  - 集群：需单独把 MongoDB 升到 4.4+。
  - MongoDB 开认证：建带 `splitVector`/`find`/`changeStream` 权限的用户。
  - 详情：`/faq/integrate/worksheet/aggtable`。

## 全局前置（与具体版本无关，跨过即检查）
- 升级到 **5.0.0+**：Docker ≥ 20.10.16。
- 升级到 **6.0.0+**：MongoDB ≥ 4.4。

## 维护
新版本发布后，按"忽略全局提示与常规 DDL、只记结构动作"的口径抓 `/upgrade/{新版本}/` 追加；删除/重命名服务（如 7.3.0 删 pushserver）务必标出。
