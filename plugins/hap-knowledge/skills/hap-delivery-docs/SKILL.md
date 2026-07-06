---
name: hap-delivery-docs
description: "Generate a complete HAP (Mingdao/明道云 超级应用平台) private-deployment delivery documentation suite. Use whenever the user wants to produce, update, or regenerate HAP 私有部署/私有化部署 交付文档 for a cluster deployment — including 部署实施文档 (deployment guide), 运维文档 (operations), 数据迁移文档 (migration), 交付清单 (delivery checklist), 常见故障处理 (troubleshooting PDF), 服务器资源要求 (server resource requirements PDF), 架构图 (architecture diagram SVG/PNG), and 凭据登记表 (credentials xlsx). Triggers include mentions of: HAP 私有部署/私有化部署交付, 明道云 HAP 集群部署文档, mingdao/nocoly 私有部署, 集群精简版/集群标准版/集群专业版, 场景A/场景B (Swarm), or producing a 交付文档 suite for a named enterprise client. Handles brand (mingdao↔nocoly), version (streamlined/standard/professional cluster — 精简版 single-node 6 nodes, 标准版 co-located 17 nodes, 专业版 dedicated-node 26 nodes), scene (A no-Swarm / B Swarm, only for standard/professional), optional migration doc, and language (CN/EN). NOT for public-cloud HAP config, non-HAP products, or single-machine (单机) standalone deployments unless explicitly requested."
license: Proprietary
---

# HAP 私有部署交付文档生成 Skill

## 入参驱动一键生成（首选路径，2026-06 固化）

整套交付件已固化为可参数化生成。**优先走入参表**：

```
# 1) 给用户一份入参模板（占位/示例，无客户信息），让其按项目填写
python scripts/make_input_template.py HAP交付入参模板.xlsx

# 2) 用户填好后（项目信息/节点IP/凭据/可选项），一键生成该项目全套真实交付件
python scripts/gen_from_input.py <填好的入参.xlsx> <outdir>
```

`gen_from_input.py` 自动：按入参选定的【版本+场景】跑全部 8 类生成 → 用实际值替换占位（`192.168.1.x`→真实 IP、`hap.domain.com`→真实域名、`某示例客户`→真实客户名、实施目录占位）→ 凭据实际值回填《凭据登记表》对应行（按一致性约束同值多处填）。
- 密码**不写入**部署/运维等文档（保留 `<强密码>` 占位），真实密码只进《凭据登记表》并提示加密保管。
- 架构图为拓扑示意：仅替换域名，IP 保持标准示意（缩写范围无法精确替换；真实 IP 以部署/凭据文档为准）。
- **生成前必须读取入参 Excel 的最后一个 Sheet「自定义项描述」**：该 Sheet 只作为当前项目的个性化约束，先把其中的项目约束整理成执行清单，再决定直接生成还是先准备专项覆盖；如涉及入口软件、主/扩展地址、端口、systemd、节点归属、版本号、目录或特殊附件配置，必须按该 Sheet 调整后再交付。除非用户明确要求，不要把某个项目的具体内容固化进 skill 或模板。
- 微服务端口默认口径：**www 主地址端口为 8880，www 扩展地址端口为 18880（按需启用）；安装管理器/`ENV_CAPTAIN_ENDPOINT` 保持 38880，不得把 38880 当作 www 默认服务端口**。
- 无入参表时，可直接调用下列各 `gen_*.py` 单独生成（占位版）。

## 这个 Skill 做什么

按「品牌 / 版本 / 场景 / 迁移 / 语言」分类，产出一整套 HAP 集群私有部署交付文档。内容**跟随官方链接最新版**（增量更新），而非固化历史步骤。文件名规范：标准/专业版不体现场景 A/B；精简版带"集群精简版"；均不含客户名（客户名仅出现在交付清单正文）。

## 第一步永远是：读参考文件，再收参数

收到任务后，**先 `view` 本 Skill 的 reference/ 全部文件**，它们是生成逻辑的依据：
- `reference/scene-a-vs-b.md` — A/B 真实差异（标准/专业版的生成分支依据）
- `reference/streamlined-vs-cluster.md` — **精简版 vs 集群版差异（精简版生成的唯一依据）**
- `reference/constraints.md` — 硬约束（命名/节点数/数据库模式/端口/清单核对）
- `reference/brand-rules.md` — mingdao↔nocoly 替换
- `reference/source-map.md` — 章节→官方URL + 增量更新 + 联网降级
- `reference/pitfalls.md` — 踩坑（PDF字体、端口混淆等）

然后让用户填 `params-template.md`（或从对话中提取）。参数缺失时用缺省拓扑值并明确告知。

## 五层分类决策树

```
1 品牌    mingdao（默认）        | nocoly（域名 *.mingdao.com→*.nocoly.com，从nocoly拉取）
2 版本    集群精简版(单节点/6节点) | 集群标准版(共置/17节点) | 集群专业版(独立部署/26节点)   ← 架构不同，见 streamlined-vs-cluster.md 与 constraints.md B
3 场景    [精简版不适用]          | A/B（仅标准/专业版：未开Swarm独立 vs 开Swarm集群，见 scene-a-vs-b.md）
4 迁移    含迁移文档            | 不含
5 语言    中文 | 英文 | 中英    ← 英文为全文翻译
```
**关键**：
- 第 2 层是**三种版本**：①集群精简版（单节点存储、1主1从K8s、无副本集/MGR/哨兵、**6节点**）；②集群标准版（组件共置、**17节点**）；③集群专业版（各组件独立部署、**26节点**）。三版本节点数=资源表全部行之和（含 HDP 行，HDP 即 Flink 节点）。标准版与专业版**不是同模板**——专业版每组件独立成节点，见 constraints.md B。
- 精简版**不走第 3 层场景 A/B**（A/B 仅描述标准/专业版的 MinIO 多节点形态；精简版 MinIO 是单节点，无此区分）。
- 输出文件名：精简版带"集群精简版"；标准/专业版不出现 A/B。均不含客户名。

## 固定生成顺序（务必遵守）

1. 常见故障处理 PDF
2. 服务器资源要求 PDF
3. 部署实施文档 docx
4. 运维文档 docx
5. 架构图 SVG
6. 架构图 PNG（由 SVG 转出）
7. 交付清单 docx（引用前面所有产物 → 生成后按实际 outputs 目录核对）
8. 数据迁移文档 docx（若第4层选“含”）
（凭据登记表 xlsx 在交付清单引用时一并产出，留空待客户填。）

## 部署实施文档：已固化为确定性管线（2026-06，跨机一致，优先用此法）

部署实施文档（5 形态：专业版A/B、标准版A/B、精简版）已**固化**为脚本+基线源，换台机器结果不变，不再每次重新 web_fetch 重排。**生成部署实施文档时一律走这条管线**，不要回退到「web_fetch 现攒 markdown」（那样会漂移）：

> **一句话口径（避免误解）**：①**内容**=官方链接（docs-pdop/docs-pd）逐字拉取并核对后**沉淀进 `deploy_src` 基线**，不是临时编的；②**格式**=客户源文档 `final/files/*.docx`（版式/章节/封面/样式）；③**日常生成 = 用 `gen_deploy.py` 确定性重放基线**（不每次现拉，保证跨机一致）；④**仅当官方文档更新**时才执行「刷新基线」（重新 web_fetch→逐字更新 `deploy_src`/`fix_monitor.py`→重跑核验）。即：**链接内容→固化基线（可刷新）→确定性重放**，三者缺一不可。

```
python scripts/gen_deploy.py pro  B  <outdir> [交付日期]   # 集群专业版 场景B（29节点）
python scripts/gen_deploy.py pro  A  <outdir> [交付日期]   # 集群专业版 场景A
python scripts/gen_deploy.py std  B  <outdir> [交付日期]   # 集群标准版 场景B（17节点）
python scripts/gen_deploy.py std  A  <outdir> [交付日期]   # 集群标准版 场景A
python scripts/gen_deploy.py lite    <outdir> [交付日期]   # 集群精简版（6节点，无场景）
```

- 基线源：`scripts/deploy_src/deploy_head.md`（文档说明~五ES，含每组件完整配置）、`scripts/deploy_src/deploy_tail.md`（K8s~验收，含**逐字官方监控章**）。组件配置全量参数化、零删减；MongoDB 51 库全列；监控章 node_exporter/cadvisor/kafka_exporter/kube-state-metrics(展开式)/Prometheus RBAC/prometheus.yml(3×metric_relabel)/Grafana/Nginx反代逐字照搬。
- 生成器：`build_scene.py`(专业版A/B)、`build_standard.py`(标准版,从专业版基线 remap 到共置拓扑+微服务3/Flink2)、`build_streamlined.py`(精简版,单节点)；`gen_minio_file.py`(MinIO/File,每节点 s3-config 指本机、ENV_FILE_DOMAIN 真实IP,场景A/B分支)；`fix_monitor.py`(监控逐字模板,build_monitor() 被各 builder 复用)。
- 渲染：`render_deploy.js`(标题样式 H1 2E74B5 sz32/H2 sz26/H3 1F4D78 sz24、代码块表格、表格 indent108) + `inject_cover.py`(封面/页眉页脚 1:1)。
- 结构基准 = `final/files/*.docx`：每组件一个 H1（共18章+文档说明）、文档说明含「## 集群X版架构 / ## 节点 IP 规划 / ## 关键端口与版本」、标准/专业版标题+封面+页眉页脚+文件名带场景，精简版不带。
- 前置依赖（换机一次性）：skill 根目录 `npm install docx`；`pip install openpyxl pymupdf python-docx`；系统含微软雅黑(msyh)+Consolas。
- 刷新基线（官方有更新时再做，非常规步骤）：web_fetch 官方页 → 重排 `deploy_src/*.md` 与 `fix_monitor.py` → 重跑上面命令核验。**日常生成不刷新，保证确定性。**
- 改 IP/域名：基线用 192.168.1.x 示例拓扑；交付时整体替换为客户网段（专业版IP方案见 `templates/deployment.md`）。

## 运维文档：已固化为确定性管线（2026-06，跨机一致，优先用此法）

运维文档（5 形态：标准版A/B、专业版A/B、精简版）同样**固化**为脚本+基线源。**生成运维文档时一律走这条管线**：

```
python scripts/gen_ops.py std  A  <outdir> [交付日期]   # 集群标准版 场景A（17节点）
python scripts/gen_ops.py std  B  <outdir> [交付日期]   # 集群标准版 场景B
python scripts/gen_ops.py pro  A  <outdir> [交付日期]   # 集群专业版 场景A（29节点）
python scripts/gen_ops.py pro  B  <outdir> [交付日期]   # 集群专业版 场景B
python scripts/gen_ops.py lite    <outdir> [交付日期]   # 集群精简版（6节点，无场景）
```

- 基线源：`scripts/ops_src/ops_base.md`（=客户参考文档 `final/files/HAP运维文档_集群标准版_场景A_.docx` 抽取并参数化的标准版场景A 全文，11 章：文档说明/组件维护/常用命令/数据存储/备份/还原/清理/升级/监控/安全/排障）；`scripts/ops_src/ops_lite.md`（精简版单节点全文，单独编写）。
- 顶部统一含**高危操作提示**（删除/还原前咨询官方或做完整组件集群快照）。端口随部署口径（MinIO 9011-9014/File 9001-9004；精简版 MinIO 9011/File 9000）。示例 IP 192.168.1.x，交付时整体替换。
- 派生器：`ops_build.py`——标准B=场景A→B（MinIO/File 改同一 Swarm·Node01 编排、9.1 放通 2377/7946/4789、2.3/7.2.1/10.7 命令改 Node01）；专业A=标准→独立拓扑（MySQL .31-.33 / MongoDB .34-.36 / Kafka .51-.53 / ES .61-.63 / MinIO+File .71-.74 / Flink .81-.83 / K8s 5 节点，按行上下文 remap + 散文块整改）；专业B=专业A+场景B；精简版直接用 ops_lite.md（单节点，无副本集/MGR/哨兵/SECONDARY）。
- 渲染同部署：`render_deploy.js` + `inject_cover.py`，封面标题「运维文档（集群X版 · 场景 X）」/精简版不带场景。
- 刷新基线：仅当客户格式或官方内容更新时，更新 `ops_src/*.md` 与 `ops_build.py` 后重跑核验；日常不刷新。

## 数据迁移文档：已固化（2026-06，跨机一致，**不分场景**）

数据迁移文档（3 形态：标准版/专业版/精简版，**单机迁移集群，不分 A/B**）已固化。生成时一律走：

```
python scripts/gen_mig.py std  <outdir> [交付日期]   # 单机迁移集群标准版
python scripts/gen_mig.py pro  <outdir> [交付日期]   # 单机迁移集群专业版
python scripts/gen_mig.py lite <outdir> [交付日期]   # 单机迁移集群精简版
```

- 基线：`scripts/mig_src/mig_base.md`（=客户参考迁移文档抽取+**脱敏**后的标准版全文，12 章：停老环境→临时容器→文件迁移→DB 导出/传输/还原→ES/Redis 清理→新环境启动→验证回切→附录）。
- 目标选择规则（已落实）：标准版/专业版 **MinIO 选节点1、MongoDB 选主节点、MySQL 走 MGR Router 6446**（专业版 MinIO .71 / MongoDB .34；标准版 .51 / .31）；精简版**单节点目标**（MinIO .51 / MongoDB .31 单实例 / MySQL 直连 3306，无 Router）。
- 派生器 `mig_build.py`：std=去场景；pro=独立拓扑 IP remap（MinIO→.71/MongoDB→.34/ES→.61）；lite=单节点目标（6446→3306、副本集/MGR/哨兵→单实例）。老环境内置 MinIO 凭据为占位符。

## 交付清单：已固化（2026-06，5 份）

交付清单（5 形态：标准版A/B、专业版A/B、精简版）已固化。**客户名为占位「某示例客户」，交付时改为实际客户名**。

```
python scripts/gen_chk.py std A <outdir> [交付日期]   # 标准版 场景A
python scripts/gen_chk.py std B <outdir> [交付日期]
python scripts/gen_chk.py pro A <outdir> [交付日期]   # 专业版 场景A
python scripts/gen_chk.py pro B <outdir> [交付日期]
python scripts/gen_chk.py lite  <outdir> [交付日期]   # 精简版（无场景）
```

- 基线：`scripts/chk_src/chk_base.md`（=客户参考清单抽取+**脱敏**：客户名/真实域名/真实本地路径/真实 IP 全部去除，文件清单规范到本套命名）。7 章：交付概述/文档清单/详细说明/验收记录/部署验收清单/后续支持/签字。
- 派生器 `chk_build.py`：版本（17/29/6 节点 + 拓扑描述）、场景（A/B 文件名与 Swarm 措辞）、IP remap（专业版）、文件清单按本套命名（部署/运维带场景，迁移/架构图/凭据无场景）。
- 交付时务必填：客户名、交付日期、域名（基线用 hap.domain.com 占位）、并按实际产出目录核对文件清单。

## 脱敏红线（迁移/清单固化时严格遵守，已执行）

客户参考文档**仅作格式与结构来源**；固化进 skill 的基线与脚本**不得含任何客户真实信息**：真实 IP→192.168.1.x 示例、客户名→占位、真实域名→hap.domain.com、真实本地路径→占位、内置凭据→占位。一次性脱敏脚本不入库。每次固化后全盘扫描**客户真实标识**（真实域名 / 客户名称 / 内置凭据串 / 真实网段 IP / 本地实施路径）应 0 命中。

## 常见故障处理 / 服务器资源要求：已固化（2026-06，**docx**，版本/场景无关，全集群通用）

两份通用文档（常见故障处理、服务器资源要求）**全集群版本共用、不分场景**，各一份，**输出 docx**（与其他交付文档同管线/同版式，不再做 PDF）。生成：

```
python scripts/gen_ref.py faq       <outdir> [日期]   # HAP常见故障处理.docx
python scripts/gen_ref.py resource  <outdir> [日期]   # HAP服务器资源要求.docx
```

- **内容来自官方链接实拉**（客户参考文档的「内容来源」即这些链接）：故障处理 = docs-pd /faq/deployment、/faq/troubleshooting/{service-status-check,workflow-keeps-queuing,icon-not-showing,page-not-accessible}；资源 = /deployment/{platform,component,source,server-reqs}。
- **结构对齐客户参考**：故障处理按「第一~五部分（每部分=一个官方 FAQ 页，每条问题为 ## 标题、命令/yaml 进代码块）+ 附录：进一步支持」；资源按「一支持平台 / 二组件支持版本 / 三服务器资源推荐（单机各档 + 集群精简/标准/专业/HyperScale 全档）/ 四性能要求 / 附录：选型决策参考」。
- 基线：`scripts/ref_src/faq_body.md`、`scripts/ref_src/resource_body.md`（官方实拉整理，无客户信息）。渲染走 `render_deploy.js` + `inject_cover.py`（同其他交付文档）。
- 刷新：官方 FAQ/资源页更新时改 `ref_src/*.md` 重跑。

## 架构图：已固化（2026-06，树形图，SVG + PNG，5 份）

架构图 5 份（标准A/B、专业A/B、精简）已固化，**一次出 SVG + PNG**：

```
python scripts/gen_arch.py std A <outdir>    # 标准版 场景A
python scripts/gen_arch.py pro B <outdir>    # 专业版 场景B
python scripts/gen_arch.py lite  <outdir>    # 精简版（无场景）
```

- `gen_arch.py` 自包含（拓扑参数内置，无需外部基线），按版本/场景参数化布局，PyMuPDF 直接 SVG→PNG（前置 `pip install pymupdf` + 微软雅黑）。
- **树形图**：请求主干（用户→上游网关→Nginx→K8s，带 HTTPS/转发/upstream 标签）→ **K8s 枢纽**（同一集群两个 namespace 子带：`default` 微服务 / `flink` Flink）→ **扇出**到 6 个后端叶子（MySQL/MongoDB/Redis/Kafka/ES/MinIO+File）。
- 底部独立 **数据集成流**：`Kafka ─①消费→ Flink(ns:flink) ─②写入 s3→ MinIO`，Flink↔Kafka/MinIO 调用关系直接清晰。
- 拓扑随版本（标准共置 17 / 专业独立 29 / 精简单节点 6），MinIO/File 叶子带场景 A/B Swarm 标注；全脱敏（192.168.1.x / hap.domain.com / MinIO 9011-9014）。

## 凭据登记表：已固化（2026-06，xlsx，5 份）

凭据登记表 5 份（标准A/B、专业A/B、精简）已固化，**内容从已固化部署基线 deploy_src 抽取的真实凭据项**（非手写固定行）：

```
python scripts/gen_cred.py std A <outdir>    # 标准版 场景A
python scripts/gen_cred.py pro B <outdir>    # 专业版 场景B
python scripts/gen_cred.py lite  <outdir>    # 精简版（无场景）
```

- 两个 Sheet：① 凭据登记表（组件/节点·IP/端口/用户名/配置项/占位符/**实际值（黄色待填）**/配置文件/章节/一致性依赖）；② 一致性约束（A MinIO 三处一致 / B Redis / C MySQL / D ES / E File / F MongoDB keyFile / G API Token / H Keepalived）。
- 版本差异：标准共置（MySQL+MongoDB .31-.33）/ 专业独立（.31-.74）/ 精简单节点（.31/.51，MySQL 3306 直连无 6446、无 keyFile/哨兵/Keepalived，约束减为 6 组）。占位符与基线一致（mingdao / storage / `<强密码>` / `HAP-Nginx-Keepalived-Auth`），实际值留空加密待填。场景 A/B 仅 MinIO 编排说明不同，凭据相同。
- 刷新：部署基线凭据项变化时同步改 `gen_cred.py` 的拓扑/行定义。

> 至此交付套件 **8 类全部固化为一键驱动**：gen_deploy / gen_ops / gen_mig / gen_chk / gen_ref / gen_arch / gen_cred。

## 单份文档的生成流程

对每份文档：
1. 查 `source-map.md` 取该文档/章节的官方 URL（精简版用 `s_` 前缀的单节点版链接；nocoly 则先换域名）。
2. **增量更新（用 web_fetch 拉取，不用沙盒 curl）**：web_fetch 拉最新 → 与 `source-cache/<key>.json` 的 hash 比对 → 变了才重排该节并提示用户；没变则复用模板段落。web_fetch 不可用则用出厂快照/用户粘贴内容并标注。
3. 按 `templates/` 的结构骨架 + 本套话术**重组**内容（不照搬原文，合规）。
4. 套用参数表（IP/域名/端口/客户名）。
5. **版本分支**：精简版按 `streamlined-vs-cluster.md` 走单节点架构（无副本集/MGR/哨兵/集群）；标准/专业版按 `scene-a-vs-b.md` 在 MinIO/File 处分 A/B。
6. nocoly 品牌：全篇域名替换并复查页脚/表格/来源段。
7. 产出到 `/mnt/user-data/outputs/`，文件名按 constraints.md 命名规范（精简版带"集群精简版"；标准/专业版无 A/B；均无客户名）。

## 架构图：按参数动态渲染（不只是替换）

- **选基底**：精简版用 `assets/architecture-base-streamlined.svg`（6节点扁平拓扑）；标准/专业版用 `assets/architecture-base-sceneA.svg`（集群拓扑）。
- 按参数**条件式增减**：
  - 无“上游 LB/网关”参数 → 省略该层（精简版基底默认无网关层）。
  - 节点数/IP 跟随参数；HDP 节点（即 Flink 节点）作为正式节点绘制，不再标"可选"。
  - 精简版：保持单节点呈现（数据库/中间件各 1 框，标注"单节点/无副本集/无哨兵"），无 Keepalived VIP。
  - 标准/专业版：场景 A/B 改中间件层标注（独立运行 vs Swarm 集群编排；2377/4789 是否互通；MinIO 端口两场景同为 9011-9014）。
- SVG 完成后转 PNG（同名）。精简版文件名 `HAP集群精简版_架构图.svg/.png`。

## 工具与脚本（见 scripts/）

- 编辑既有 docx：`unpack.py` → 改 XML → `pack.py`（来自 docx skill）。
- 新建 docx：docx-js。生成前先读 `/mnt/skills/public/docx/SKILL.md`。
- xlsx（凭据登记表）：openpyxl；先读 `/mnt/skills/public/xlsx/SKILL.md`。
- PDF：PyMuPDF，中文用 NotoSansCJK（见 pitfalls.md）；先读 `/mnt/skills/public/pdf/SKILL.md`。
- 拉取+对比：`scripts/fetch_diff.py`（增量更新与缓存）。
- SVG→PNG：`scripts/svg_to_png.py`。
- **部署实施文档渲染（推荐）**：`scripts/render_deploy.js`（markdown→docx）。把各章节整理成 markdown（命令放进 ```fenced``` 围栏代码块，渲染为浅底等宽**多行**代码框，从源头避免命令被压平成一行），表格用 `|` 语法。**渲染器已内置代码净化兜底**：自动把代码内弯引号/全角空格转 ASCII、按行成段（多行不再压平）、`cat > *.json <<EOF` 的单行 JSON 自动美化为多行（见 pitfalls.md「代码块行混乱」）；但生成时仍应主动用 ASCII 标点、一条命令一行、heredoc 配置一项一行。环境变量 `COVER_TITLE / COVER_EN / COVER_DATE` 传封面信息。用法：`COVER_TITLE=... COVER_EN=... COVER_DATE=... node scripts/render_deploy.js <md> <out.docx> <文档名>`。
- **封面 1:1 照搬附件**：`scripts/inject_cover.py` + `assets/cover_block_template.xml`（封面块原始 XML）+ `assets/header_template.xml` / `assets/footer_template.xml`。渲染器先输出 `__COVER_PLACEHOLDER__` 占位，再用本脚本把附件首页封面块整段注入、替换页眉页脚，仅改标题/英文副标题/日期三处文字。用法：`python3 scripts/inject_cover.py <docx> <标题> <英文副标题> <日期>`。要 1:1 复刻新附件首页时，把该附件 `word/document.xml` 的封面段（body 开头到第一个分页符）整段替换进 `assets/cover_block_template.xml`，页眉页脚同理替换两个 template。
- **场景 A/B 的 MinIO+File 章节（每节点完整展开）**：`scripts/gen_minio_file.py`。按场景生成第九章（MinIO）+ 第十章（File）的完整 markdown，4 个节点逐个展开 yaml/脚本（不简写）。场景 A=每节点一份单服务 yaml（无 placement，各节点各自 init/启停，不开 2377）；场景 B=一份完整 yaml 带 placement node.id（仅 Node01 init/启停，开 2377）。用法：`python3 scripts/gen_minio_file.py <A|B> <4个中间件节点IP逗号分隔> <3个Redis哨兵IP逗号分隔> <out.md>`。
- **A/B 独立成档**：标准版/专业版各出场景 A、场景 B 两份独立 docx（共 5 份：标准A/标准B/专业A/专业B/精简版）。文件名带场景（`_场景A`/`_场景B`），封面标题、英文副标题、页眉页脚均带对应场景标识；文档说明声明本文档场景并指明与另一场景差异。精简版单节点不分 A/B。组装：`头部（说明~第八章）` + `gen_minio_file.py 生成的第九/十章` + `尾部（上传预置~验收）`。

## 收尾自检（每次必做）

- [ ] **先确认版本**：精简版 or 标准/专业版？精简版走 streamlined-vs-cluster.md，不分 A/B。
- [ ] 文件名规范：精简版带"集群精简版"；标准/专业版无场景A/B；均无客户名（客户名仅交付清单正文）。
- [ ] 交付清单引用的文件 = 实际 outputs 目录文件（数量/名称逐一核对）。
- [ ] **节点数口径**：精简版 6 / 标准版 17 / 专业版 26（=资源表全部行之和，含 HDP 行，HDP 即 Flink 节点；不标"可选"、不分两个数）。详见 constraints.md B。
- [ ] **数据库模式**：精简版 = MySQL/MongoDB/Redis 单节点；标准/专业版 = MGR+Router、副本集、哨兵。**最易错**：别把精简版写成集群、也别把集群写成单节点。
- [ ] 标准/专业版：A/B 端口未因切场景被改动（MinIO 9011-9014、File 9001-9004 固定）；差异仅 Swarm 形态。
- [ ] 架构图基底选对（精简版 streamlined / 集群版 sceneA）。
- [ ] nocoly 时域名替换无遗漏。
- [ ] 生成顺序正确；迁移文档按选择产出。

## 扩展（用户后续补素材）

- 新模板（如专业版专属、新文档类型）：放 `templates/`，在本文件「生成顺序/流程」登记。
- 官方链接调整：改 `source-map.md`。
- 新踩坑：追加 `pitfalls.md`。
- 新约束：追加 `constraints.md`。
