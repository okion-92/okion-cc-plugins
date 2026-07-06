# 模板：架构图（条件式动态渲染）

## 出几份（与部署/运维 A/B 独立成档对齐）
- **标准版/专业版各出场景 A、场景 B 两套，精简版一套，共 5 套**（每套含 .svg + .png）。
- 文件名：`HAP集群标准版_场景A_架构图.svg/.png`、`_场景B_`、`HAP集群专业版_场景A_`、`_场景B_`、`HAP集群精简版_架构图.svg/.png`。
- A/B 差异：标题副标题（A=未开启/B=开启 Docker Swarm）+ 中间件层标注（A=各节点独立单节点 swarm / B=同一 Swarm 集群 overlay 2377/4789）。
- 专业版基于标准版基底改：数据库层拆 MySQL(.31-33)+MongoDB(.34-36)，中间件层拆 Kafka(.51-53)/ES(.61-63)/MinIO+File(.71-74)/Flink(.81-82)，标题标注 26 节点独立部署。

> 基底：标准/专业版用 assets/architecture-base-sceneA.svg（集群拓扑版式，含 CSS 配色/箭头 marker）；精简版用 assets/architecture-base-streamlined.svg（6节点扁平，见文末）。
> 生成顺序第5(SVG)、第6(PNG)。PNG 由 scripts/svg_to_png.py 转出（cairosvg，2x）。

## 渲染原则：按参数真实增减层级，不只是替换 IP

### 各层与控制参数
| 层 | 是否绘制 | 内容随参数 |
|---|---|---|
| 外部用户/终端 | 始终 | — |
| 上游 LB/网关 | **仅当参数有“上游LB/网关IP”** | 客户侧已有，文档不负责部署，仅画在图上；无此参数则**省略该层**并把箭头从用户直连 Nginx VIP |
| Nginx VIP (Keepalived) | 始终 | VIP |
| Nginx 双节点 | 始终 | Nginx IP×2、MASTER/BACKUP priority |
| K8s 微服务层 (default ns) | 始终 | K8s IP×3、配置、域名:443 |
| HDP/Flink 计算层 (flink ns) | 始终（HDP 节点即 Flink 节点，正式节点） | HDP/Flink IP、JobManager UI 28081、s3 endpoint 192.168.1.51:9011 |
| 数据库层 | 始终 | DB IP×3、MongoDB 27017、MySQL MGR 3306、Router 6446 |
| 缓存层 Redis | 始终 | Redis IP×3、6379/Sentinel 26379 |
| 中间件层 | 始终 | 中间件 IP×4、MinIO 9011-9014、File 9001-9004、Kafka 9092/ES 9200 |

### 节点数动态
- 上表层级为**标准版**视角（DB/Redis/中间件按共置×3/×3/×4）。
- 专业版各组件独立节点时，相应增加节点框（MySQL×2/MongoDB×3/Redis×3/Kafka×3/ES×3/MinIO+File×4 各自成层），共 26 节点。
- 节点数量、IP 全部跟参数表。
- viewBox 高度按实际层数调整：标准版基底 760×1340；精简版基底 760×920；增减层后重算。

### A/B 差异（仅中间件层标注 + 底部链路说明）
- 标题副标题：A=`未开启 Docker Swarm 集群`；B=`开启 Docker Swarm 集群`。
- 中间件层：
  - A：`各节点独立运行`、`单节点 docker swarm（2377/4789 不互通）`、`MinIO 9011-9014`
  - B：`Docker Swarm 集群统一编排`、`overlay 2377/4789 互通`、`MinIO 9011-9014`
- MinIO 端口两场景相同(9011-9014)。

### 品牌
- 域名（hap.domain.com 等）来自参数；标题不含品牌名差异（mingdao/nocoly 仅影响文档内链接，架构图一般不出现 docs 域名）。

## 配色规范（沿用基底 CSS 类，勿改）
c-gray(用户) / c-blue(网关·Nginx) / c-rose(VIP) / c-coral(Nginx反代) / c-blue+c-purple(K8s default+flink) / c-teal(数据库) / c-rose(Redis) / c-amber(中间件)。
字体 class：.th(标题14/500) .t(14) .ts(12)。箭头 marker#arrow。


## HDP/Flink 节点的画法（重要)

HDP/Flink 节点（标准版 .61/.62、专业版 .81/.82、精简版 .30）**本质是 K8s Worker**：通过 kubeadm join 加入 K8s 集群，打污点 `hap=flink` 后只调度 Flink 工作负载（JobManager + TaskManager），跑在 `namespace: flink` 中。
画法必须把 HDP/Flink **放进 K8s 集群框内的 `namespace: flink` 子区域**，与 `namespace: default`（HAP 微服务）并列；**不要画成 K8s 之外的独立盒子**——那样会误导客户以为 Flink 是独立部署。
- 标准/专业版基底已是这种画法（K8s 集群框内有 default + flink 双 namespace 子区域）。
- 精简版基底同样如此（重构后 K8s 框内含 default 子区域容纳 .21/.22 + flink 子区域容纳 .30）。
- 底部链路说明里建议加一句"HDP/Flink 节点 .30（或对应 IP）作为 K8s Worker 加入集群，跑在 namespace: flink 中"加深印象。

## 字体（避免 PNG 中文方框）
- SVG 的 font-family **必须含 `Noto Sans CJK SC`**（环境实际可用的中文字体）；不要只写 PingFang/YaHei（环境无此字体，cairosvg 转 PNG 时中文会变成 □□ 方框）。
- 基底 SVG 已设 `font-family="Noto Sans CJK SC, WenQuanYi Zen Hei, sans-serif"`，重绘时保持。
- 转 PNG 后**务必 view 一次 PNG** 核对：① 中文无方框；② 无文字超出节点框/viewBox 右边界（长图例行控制在 ~700px 内，超长则拆行并相应加高 viewBox 与背景 rect）。

## 生成流程
1. 取基底 SVG → 按参数替换 IP/域名/端口文本。
2. 按"上游网关有无""专业版独立节点"增删层与重算坐标/viewBox（HDP/Flink 层始终绘制）。
3. 按 A/B 改中间件层标注与副标题。
4. 存 `HAP集群标准版_架构图.svg` → svg_to_png.py 转同名 .png。

---

## 精简版架构图

- 基底：`assets/architecture-base-streamlined.svg`（6节点扁平拓扑，已含单节点存储/1主1从K8s/HDP-Flink 节点/监控说明）。
- 按参数替换 IP/域名；节点角色固定为精简版 6 类。
- 不画 Keepalived VIP、不画副本集/MGR/哨兵/Swarm集群编排。
- HDP/Flink 为正式节点（6 节点之一），始终绘制。
- 输出 `HAP集群精简版_架构图.svg` → svg_to_png.py 转 `.png`。
