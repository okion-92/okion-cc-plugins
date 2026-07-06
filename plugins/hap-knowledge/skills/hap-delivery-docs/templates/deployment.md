# 模板：部署实施文档（集群标准版/专业版）

> 结构骨架 + 章节→来源映射 + A/B 分支点。正文内容运行时由 web_fetch 拉取（source-map.md），出厂快照（source-cache/deploy_sceneA.json / deploy_sceneB.json）兜底。
> 生成方式：编辑既有素材 docx（unpack→改XML→pack）或用 docx-js 新建。优先以出厂快照素材为基底替换参数，再按 web_fetch 最新内容增量更新变化章节。

## 文档元信息（以客户参考文档 final/files/*.docx 为格式基准，2026-06 校准）
- 标题：`部署实施文档（集群专业版 · 场景 B）`、`部署实施文档（集群标准版 · 场景 A）` 等——**标准/专业版正文标题、封面、页眉页脚、文件名都带场景 A/B**（客户实际交付即如此：文件名 `HAP部署实施文档_集群专业版_场景B.docx`）。精简版不带场景。
  - 注：这一条**以客户参考文档为准**，覆盖 constraints.md A「不带场景」的旧约定（旧约定仍适用于交付清单/PDF 等版本无关文档）。
- 英文副标题：`HAP Professional Cluster Deployment Guide — Scenario B (With Swarm)`（用 — 连接，不用 &）。
- 封面：inject_cover.py 照搬 cover_block_template.xml（已与客户封面一致：HAP sz96 + 私有部署交付 sz36 + 描边标题 sz56 + 英文斜体 sz28 + 元信息表 文档版本/编制日期/编制部门=明道云研发部运维实施团队）。
- 版本 V1.0 / 编制日期=参数表交付日期。页面 Letter（与素材一致）。
- 标题样式（render_deploy.js 已对齐客户 styles.xml）：H1 2E74B5 sz32 / H2 2E74B5 sz26 / H3 1F4D78 sz24，H1 无下边框。

## 章节骨架（顺序固定，**每组件一个 H1 章节**——对齐客户参考文档，共 18 章 + 文档说明）

> 关键格式：每个数据库/中间件组件**各占一个 H1 章节**（不要把 MongoDB/MySQL/Redis 挤进「数据库部署」一个章），标题用描述式 `N、<类别>部署 — <组件>（<节点角色> 01/02/03 · <IP>）`；每章首行用 `> 原文链接：<docs-pdop URL>` 注明来源。子节用 `## N.M`。

| 序 | 章节（H1 标题范式） | source-map key | A/B 分支 |
|---|---|---|---|
| — | 文档说明（集群架构 + 节点 IP 规划 + 关键端口版本，内联，不单设 H1） | — | 措辞声明场景 |
| 一 | 服务器资源清单（拓扑表 + 1.2 网络互通端口表） | res_source | 1.2 端口表 B 增 2377 行 |
| 二 | 操作系统初始化（所有节点） | docker | 否 |
| 三 | Docker 安装（中间件/对象存储节点 + Nginx 节点） | docker | 否 |
| 四 | 数据库部署 — MongoDB 副本集（MongoDB 节点 01/02/03） | mongodb | 否 |
| 五 | 数据库部署 — MySQL MGR 集群（MySQL 节点 01/02/03 + Router） | mysql_mgr | 否 |
| 六 | 数据库部署 — Redis 哨兵（Redis 节点 01/02/03） | redis | 否 |
| 七 | 中间件部署 — Kafka 集群（Kafka 节点 01/02/03） | kafka | 否 |
| 八 | 中间件部署 — Elasticsearch 集群（ES 节点 01/02/03） | es | 否 |
| 九 | 中间件部署 — MinIO 集群（对象存储节点 01-04） | minio | **是（核心差异）** |
| 十 | 中间件部署 — HAP 文件服务（对象存储节点 01-04） | file_multinode | **是（核心差异）** |
| 十一 | 上传预置文件到 MinIO | file_preconf | 否 |
| 十二 | Kubernetes 三 Master 集群（微服务节点 01-05） | k8s | 否 |
| 十三 | Istio 服务网格（K8s 集群） | istio / istio_notes | 否 |
| 十四 | HAP 微服务部署（K8s 集群，含 ConfigMap） | service | 否 |
| 十五 | Flink 部署（HDP / Flink 节点） | flink | **是（s3.endpoint）** |
| 十六 | Nginx 反向代理 + Keepalived（Nginx 节点 01/02 · VIP） | nginx / nginx_keepalived | 否 |
| 十七 | 监控部署（Prometheus + Grafana） | prometheus / grafana | 否 |
| 十八 | 部署后验收 | — | 否 |

> 标准版章节同序；精简版见文末（单节点、不分 A/B）。组装脚本参考：`work/restructure_deploy.py`（把分组式 md 重构为每组件 H1）。

## 内容与配置规则（**内容以官方 web_fetch 实拉为准**）
- 正文命令/配置一律 **web_fetch 拉官方页**（source-map.md 的 URL，干净带围栏代码），把示例 IP/密码替换为本套参数 / `<强密码>`；source-cache 快照仅离线兜底（快照命令被压平，不可直接用）。
- **多节点组件逐节点列完整配置**：MySQL my.cnf（3 份，差 server-id/report_host/local_address）、Kafka server.properties（3 份，差 broker.id/advertised.listeners）、ES elasticsearch.yml（3 份，差 node.name/publish_host）、Redis（Master + 2×Slave 各一份完整 conf，从节点带 slaveof）。**不要「一份配置 + 文字描述差异」**。
- **s3-config.json 每节点指向本机 MinIO**（对象存储节点 .x1→9011 / .x2→9012 / .x3→9013 / .x4→9014），不是都指向同一节点（gen_minio_file.py 已实现）。

## A/B 分支点（仅这几处，详见 reference/scene-a-vs-b.md）
1. 1.2 端口表：B 增加 `2377 Swarm 管理` 行；A 不加。
2. 5.3.1 Swarm 初始化：A=各节点独立 init；B=Node01 init + 其余 join + 记录 node.id。
3. 5.3.3 minio.yaml：A=每节点单服务无 placement；B=完整4服务带 placement。端口 A/B 同为 9011-9014。
4. 5.4 file.yaml：A=每节点单服务；B=完整4服务带 placement。端口 A/B 同为 9001-9004。
5. 启停脚本/执行：A=每节点分别；B=仅 Node01。
6. s3-config / Flink endpoint：A/B 统一按 901X 映射（不再分支）。

## 内容来源链接清单（部署文档正文“内容来源”章节，nocoly 时替换域名）
docker, mongodb, mysql_mgr, redis, kafka, es, minio, file_preconf, file_multinode, k8s, istio, istio_notes, service, flink, nginx, prometheus, grafana（完整 URL 见 source-map.md）

## 专业版差异（注意：与标准版不是"同模板仅IP不同"；节点数以官方 res_source 实拉为准）
专业版各组件**独立部署**。**节点数以 web_fetch docs-pd/deployment/source 的「专业版(1000+)」表为准**——2026-06 实拉为：Nginx2 + 微服务5 + Redis3 + Kafka3 + ES3 + MinIO/File4 + MySQL3 + MongoDB3 = 26 核心，加数据同步 Flink3 = **29 节点**（Milvus/etcd 为向量检索可选，默认不计）。⚠️ 旧 constraints.md B 写的「26 节点/微服务4/MySQL2」**已过时且与 MGR 需≥3 自相矛盾**，以实拉为准。
- 参考配置表取 res_source 的"专业版"表（各用途单独成行）。
- 资源清单/IP规划/架构图按**独立节点**拓扑出（Kafka/ES/MinIO/MySQL/MongoDB 各自成层）；章节命名用独立角色名（MySQL 节点 / MongoDB 节点 / Kafka 节点 / ES 节点），不要套标准版「数据库节点/中间件节点」共置命名。
- 数据库仍是 MGR+Router / 副本集 / 哨兵（与标准版同模式，只是节点更独立）。
- 示例 IP 拓扑（gen_credentials.py pro 对齐）：Nginx .11/.12 VIP .20 / 微服务 .21-.25 / MySQL .31-.33 / MongoDB .34-.36 / Redis .41-.43 / Kafka .51-.53 / ES .61-.63 / 对象存储 .71-.74 / Flink .81-.83。

---

## 精简版部署文档（集群精简版）

- 走单节点架构，**不分场景 A/B**，6 节点。规则见 reference/streamlined-vs-cluster.md。
- **章节骨架同集群版的「每组件一个 H1」18 章结构**（与客户参考 `final/files/HAP部署实施文档_集群精简版.docx` 一致）：文档说明 → 一、服务器资源清单 → 二、操作系统初始化 → 三、Docker 安装 → 四、MongoDB 单节点 → 五、MySQL 单节点 → 六、Redis 单节点 → 七、Kafka 单节点 → 八、ES 单节点 → 九、MinIO 单节点 → 十、HAP 文件服务单节点 → 十一、上传预置文件 → 十二、K8s 单 Master（**含移除 Master 污点**）→ 十三、Istio → 十四、HAP 微服务 → 十五、Flink → 十六、Nginx（单节点无 VIP）→ 十七、监控 → 十八、部署后验收。
- 节点：Nginx .20 / K8s .21·.22 / 中间件 .51（Kafka+ES+MinIO+File 共置）/ 数据库 .31（MySQL+MongoDB+Redis 共置）/ Flink .30。
- 配置走 `s_` 前缀单节点链接（web_fetch 实拉、全量参数化）：MySQL 单实例直连 3306（systemd 参数内联，无 my.cnf 文件、无 MGR/Router）、MongoDB 无副本集无 keyFile、Redis 无哨兵、Kafka replication=1 / zookeeper.connect=127.0.0.1、ES `discovery.type=single-node` 且 transport SSL 关闭、MinIO 单服务 9011、File 单实例 9000（ENV_FILE_CACHE 指 redis）、ConfigMap 用单节点直连地址。
- 生成器：`work/build_streamlined.py`（直接产出 18 章 markdown，无需 restructure，因单节点无组件拆分）。
- 命名：`HAP部署实施文档_集群精简版.docx`（不带场景）。

## 生成器脚本（已沉淀，下次直接复用）
- 标准/专业版：`work/build_scene.py <A|B>` → 读 deploy_head/tail + minio_file_<scene> → 输出每组件 18 章 `deploy_<scene>_v2.md`。
- 精简版：`work/build_streamlined.py` → 直接输出 `deploy_streamlined.md`。
- 三者均经 `render_deploy.js` + `inject_cover.py` 出 docx；配置块完整、IP/密码参数化。
