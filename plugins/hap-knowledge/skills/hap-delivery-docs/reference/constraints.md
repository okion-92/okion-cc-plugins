# 硬约束清单（生成前必读）

> 这些是“错一次就返工”的规则。生成任何文档前先过一遍本清单。

## A. 命名规范（输出文件）

1. **输出文件名不得包含场景标识**（不出现“场景A/场景B/未开启Swarm/开启Swarm/Scenario A/B”）。
   - 现有素材文件名带“场景A”等，是历史命名，**生成新文档时必须去掉**。
2. **输出文件名不含客户名**。客户名只允许出现在「交付清单」正文的项目基本信息中。
3. 推荐命名（中文版）：
   - `HAP常见故障处理.pdf`
   - `HAP服务器资源要求.pdf`
   - `HAP部署实施文档_集群标准版.docx`（或 集群专业版）
   - `HAP运维文档_集群标准版.docx`
   - `HAP集群标准版_架构图.svg` / `.png`
   - `HAP交付清单.docx`
   - `HAP集群标准版_凭据登记表.xlsx`
   - `HAP数据迁移文档_单机迁移集群标准版.docx`
4. 英文版命名：把中文主体替换为英文，如 `HAP_Deployment_Cluster_Standard.docx`、`HAP_Operations_Cluster_Standard.docx`、`HAP_Migration_Standalone_to_Cluster_Standard.docx`、`HAP_Delivery_Checklist.docx`、`HAP_Troubleshooting_Guide.pdf`、`HAP_Server_Resource_Requirements.pdf`、`HAP_Cluster_Standard_Architecture.svg/.png`、`HAP_Cluster_Standard_Credentials.xlsx`。
5. 精简版命名：主体用"集群精简版"，如 `HAP部署实施文档_集群精简版.docx`、`HAP运维文档_集群精简版.docx`、`HAP数据迁移文档_单机迁移集群精简版.docx`、`HAP集群精简版_架构图.svg/.png`、`HAP集群精简版_凭据登记表.xlsx`（英文 `..._Streamlined`）。专业版同理用"集群专业版"。

## B. 节点数量口径（易错，按官方服务器资源推荐核定）

各版本节点数 = 资源清单**全部行之和**（含 HDP 行；HDP 节点即承载 Flink 的节点，不另算独立 Flink 节点、不重复计入）。统一用单一总数，**不再区分"含/不含 Flink"或标"可选"**：

**集群精简版（并发 300+，组件共置）= 6 节点**
- Nginx 1 + 微服务 2 + 中间件 1 + 数据库 1 + HDP 1 = **6**。

**集群标准版（并发 600+，部分共置）= 17 节点**
- Nginx 2 + 微服务 3 + Redis 3 + 中间件 4（Kafka/ES/MinIO/File 共置） + 数据库 3（MySQL+MongoDB 共置） + HDP 2 = **17**。

**集群专业版（并发 1000+，各组件独立部署，单一应用架构）= 26 节点**
- Nginx 2 + 微服务 4 + Redis 3 + Kafka 3 + Elasticsearch 3 + MinIO/文件 4 + MySQL 2 + MongoDB 3 + HDP 2 = **26**。

**关键**：
- HDP 节点 = Flink 节点（HDP 超级数据平台基于 Flink；那台/两台标 HDP 的机器即跑 Flink 的机器，不重复计算独立 Flink 节点）。
- 资源清单表把 HDP 行作为**正式节点**列出，**不再标"(可选)"**字样。
- 专业版与标准版**不是"同模板仅 IP 不同"**——专业版每个组件独立成节点（Kafka/ES/MinIO/MySQL/MongoDB 各自独立），标准版是共置（数据库3台共置、中间件4台共置）。生成专业版时按独立节点拓扑出资源清单与架构图，不能套标准版共置表。
- （另：HyperScale 旗舰版并发1000+多可用区，约 40 节点，当前 Skill 暂不覆盖，如需可后续扩展。）

## C. 数据库模式（易错，曾被纠正过 —— 仅标准版/专业版；精简版见 J）

> 以下为**集群标准版/专业版**口径。**精简版是单节点**（MySQL 3306 直连 / MongoDB 27017 无副本集 / Redis 6379 无哨兵），见 J 与 streamlined-vs-cluster.md。

- （标准/专业版）MySQL 一律是 **MGR + Router** 模式（Router 读写口 6446、只读 6447），**不是主从复制**。
- （标准/专业版）MongoDB 是**副本集**（27017，1 Primary + 2 Secondary）。
- （标准/专业版）Redis 是**哨兵模式**（6379 + Sentinel 26379），不是 Cluster。
- 标准版：数据库 3 节点为 MongoDB + MySQL **共置**；专业版：MySQL 2 台、MongoDB 3 台**各自独立**，不要把专业版描述成共置。

## D. 端口口径（易错）

- File 服务端口在 A/B **都是** 9001-9004（容器内统一 9000）。
- MinIO 端口在 A/B **都是** 9011-9014（容器内统一 9000）—— 新标准已统一，旧素材中场景 A 的 9000 不再使用。
- s3-config bucketEndPoint 与 Flink s3.endpoint 在 A/B **都按** .51→9011、.52→9012、.53→9013、.54→9014 映射（中间件 4 节点 192.168.1.51/52/53/54）。
- A/B 端口与网络策略完全一致；切场景时**不改任何端口**，差异只在是否组 Swarm（2377 仅 B 开）。
- MySQL Router 6446（读写）/ 6447（只读）；MGR 内部 33060/33061；K8s VXLAN 4789(UDP)。

## E. 文件清单核对（曾被纠正过）

- **交付清单中的文件列表，必须与实际产出的文件一一对应**。
- 生成完所有文档后，**列实际 outputs 目录**，逐个比对清单引用的文件名、数量与实际是否一致；不一致则改清单，不要凭记忆写。
- 历史教训：交付清单里曾引用了已删除/已排除的内容（如某个被删的 Excel Sheet），务必核对后再定稿。

## F. 品牌替换（mingdao / nocoly）

- 见 brand-rules.md。选 nocoly 时，所有 `*.mingdao.com` 域名按规则替换，并从 nocoly 站点拉取内容。

## G. 生成顺序（固定）

常见故障处理PDF → 服务器资源要求PDF → 部署实施文档 → 运维文档 → 架构图SVG → 架构图PNG → 交付清单 → 迁移文档（若需要）。
- 交付清单排在架构图之后、迁移文档之前，是因为清单要引用前面所有产物；迁移文档可选，排最后。

## H. PDF 中文渲染

- 用 PyMuPDF 处理/生成 PDF 时，中文必须使用 **NotoSansCJK** 字体，否则乱码（历史踩坑，详见 pitfalls.md）。

## I. 内容合规

- 从官方文档拉取内容后，用本套文档的结构与话术**重新组织**，不整段照搬原文。
- 占位符密码统一 `<强密码>`，实际值不写入文档；凭据放凭据登记表 xlsx，由客户自行填写/保管。

## J. 集群精简版专项口径（见 streamlined-vs-cluster.md）

- 命名：所有输出文件带"集群精简版"，不带场景 A/B（精简版无 A/B）、不带客户名。
- 节点数：精简版 **6 节点**（Nginx1+微服务2+中间件1+数据库1+HDP1，HDP 即 Flink 节点）。不要套用标准版 17 / 专业版 26 口径。
- 数据库模式：精简版 MySQL/MongoDB/Redis **均单节点**（3306 直连 / 27017 无副本集 / 6379 无哨兵），**严禁**写成 MGR+Router / 副本集 / 哨兵。
- K8s：精简版 1 主 1 从，**必须移除 Master 污点**（节点不够）；Nginx 单节点无 VIP。
- 端口：MinIO 9011、File 9000（单节点）；其余端口号与集群版一致。
- 架构图基底：精简版用 architecture-base-streamlined.svg。
- source-map：精简版用 `s_` 前缀的单节点版链接（mongodb/4.4/standalone、mysql-8.0、minio-single、file/v2/single-node、single-master-deployment 等）。
- 出厂快照：deploy_streamlined（基于真实重构的精简版部署文档）。
