# 模板：数据迁移文档（单机迁移集群标准版/专业版/精简版）

> 第4层"含迁移"时才生成，排生成顺序最后。出厂快照：source-cache/migration.json。
> **迁移文档不分 A/B**：数据迁移过程与 MinIO/File 是否开启 Docker Swarm（场景 A/B）完全无关，因此标准版/专业版各只出一份（场景 A/B 通用），精简版一份，共 3 份。文档说明里需写明"本迁移文档不区分场景，场景 A 与场景 B 通用"。
> 注：出厂快照 migration.json 是早期带"场景 A"字样的版本，生成时须去掉所有"场景 A/B"标识（仅在文档说明保留一句"不区分场景"的说明）。

## 文档元信息
- 标题：`数据迁移文档（单机迁移集群标准版）`／`（单机迁移集群专业版）`／`（单机迁移集群精简版）`（不带 A/B）。
- 英文副标题：`HAP Data Migration Guide — Standalone to Standard / Professional / Streamlined Cluster`（用 — 连接，不用 &）。
- 文件名：`HAP数据迁移文档_单机迁移集群标准版.docx` / `_单机迁移集群专业版.docx` / `_单机迁移集群精简版.docx`。
- 封面：用 inject_cover.py 照搬附件首页（与部署/运维文档同一套封面模板）。inject_cover 的标题替换正则匹配"XXX文档（…）"通用模式，"数据迁移文档（…）"也能正确替换。
- 来源链接（source-map 之外的迁移专属，nocoly 时替换域名）：
  - 迁移规范 https://docs-pdop.mingdao.com/migration/guide
  - 私有部署→私有部署 https://docs-pdop.mingdao.com/migration/p2p/
  - 单机迁移集群 https://docs-pdop.mingdao.com/migration/p2p/migdoc
  - MongoDB Database Tools https://www.mongodb.com/try/download/database-tools （第三方，不替换）

## 章节骨架（顺序固定）
| 章节 | 参数替换 |
|---|---|
| 文档说明 / 适用场景 / 核心思路 / 内容来源 | 域名、主地址 |
| 一、迁移整体流程 | — |
| 二、停止单机老环境（2.1 Kafka堆积检查 / 2.2 停微服务） | — |
| 三、启动临时容器（3.1~3.3） | — |
| 四、文件存储迁移（4.1 mc别名 / 4.2 同步业务桶） | MinIO 端点 901X |
| 五、数据库迁移（5.1 MySQL导出 / 5.2 MongoDB导出） | DB 节点 IP |
| 六、数据传输（6.1 / 6.2） | DB 节点 IP |
| 七、数据库还原（7.1 MySQL 四步 / 7.2 MongoDB 五步） | DB 节点 IP；MGR Router 6446 |
| 八、Elasticsearch 索引清理（8.1~8.3） | ES 节点 IP |
| 九、Redis 缓存清理（9.1） | Redis 节点 IP |
| 十、新环境微服务启动 | 域名 / VIP |

## 关键参数（迁移专属）
- ENV_ADDRESS_MAIN = 主访问地址（本环境 https://hap.domain.com）
- 目标 MinIO 端点用对外 9011（与部署一致；mc alias 的 minio_new 指向 192.168.1.51:9011）。
- **标准版**：数据库共置 .31/.32/.33，MySQL 还原走 Router 6446，MongoDB 还原走 Primary .31；ES 在 .52-54；MinIO 在 .51-54。
- **专业版**：组件独立，按上下文改 IP——MySQL 还原 .31（Router 6446 不变），MongoDB 还原 .34（Primary），ES .61-63，MinIO .71-74，Redis .41-43。传输接收端 MySQL→.31、MongoDB→.34。
- 派生方式：先做标准版全文，再按上下文（MongoDB / MySQL / ES / MinIO / Redis 关键词）定向替换 IP 得专业版；精简版见下。

---

## 精简版迁移（单机迁移集群精简版）

- 目标端为精简版单节点拓扑：MySQL 还原直连 3306（**非 Router 6446**）；MongoDB 还原到单节点 27017（**无副本集**，还原后无需 rs.initiate）；Redis 单节点。
- MinIO 目标端点 9011（单节点）。
- 流程骨架与标准版一致（停老环境→临时容器→文件迁移→DB导出/传输/还原→ES/Redis清理→微服务启动），但所有"集群/副本集/MGR"步骤简化为单节点操作。
- 命名：`HAP数据迁移文档_单机迁移集群精简版.docx`。
