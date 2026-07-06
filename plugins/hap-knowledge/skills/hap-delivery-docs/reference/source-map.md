# 章节 → 官方来源 URL 映射（链接驱动更新）

> 本文件让“文档内容跟着官方链接走”而非固化。生成各章节时，按下表拉取对应 URL 的最新内容，
> 用本套文档结构与话术重组（合规：不整段照搬）。
> 品牌为 nocoly 时，先按 brand-rules.md 把域名换成 nocoly 再拉取。

## 本次实拉确认（2026-05-26）

> 全部集群版（标准/专业）+ 单节点版（精简）章节链接已于 2026-05-26 用 web_fetch 逐一实拉确认有效，并据此生成 5 份部署实施文档（标准版场景A/场景B、专业版场景A/场景B、精简版）。
> 实拉核对的当前版本：MySQL **8.0.45**（+ shell/router 8.0.45）、MongoDB **4.4.30**、Docker **28.5.2**、Redis **8.0.4**、Kafka **3.9.1**（JDK 21 / 21.0.8+9）、Elasticsearch **8.19.8**（+ analysis-ik）、MinIO **RELEASE.2025-04-22T22-12-26Z**、File **2.1.0**、K8s **1.35.3**（containerd 2.2.2 / runc / calico v3.31.4 / etcd 3.6.6-0 / pause 3.10.1 / crictl v1.35.0）、Istio **1.29.1**、HAP **7.2.4**（+ doc 2.0.0 + command node1018-python36）、Flink **1.19.720**、Nginx **1.28.2**、node_exporter 1.9.1 / cadvisor v0.52.1 / kafka_exporter 1.9.0 / kube-state-metrics 2.3.0 / Prometheus **3.5.0** / Grafana **12.1.2**。
> 场景 A/B 差异仅在 MinIO（第九章）与 File（第十章）：A=四节点各自独立单节点 Swarm（每节点一份单服务 yaml、无 placement、各自启停、不开 2377）；B=四节点同一 Swarm 集群（一份完整 yaml 带 placement node.id、仅 Node01 启停、开 2377）。端口两场景一致（MinIO 9011-9014 / File 9001-9004）。

## 拉取通道（已实测确认）

**关键：拉取最新内容用 Claude 对话层的 web_fetch，不要用沙盒 bash 的 curl。**
- 沙盒 bash 的 curl 被 egress 白名单拦截（`host_not_allowed`），拉不到 mingdao/nocoly。
- 对话层 web_fetch **可以**抓取 mingdao/nocoly 公开文档（已实测 docs-pd.mingdao.com、docs-pd.nocoly.com 均可）。
- 正确工作流：**Claude 用 web_fetch 抓取 → 整理内容 → 传给沙盒脚本组装进 docx/PDF**。
- web_fetch 限制：只能抓“用户提供过或搜索结果出现过”的 URL。首次抓某 nocoly 链接前，可能需要先用 web_search 让该域名出现在结果中（已验证 nocoly 站点真实存在、结构与 mingdao 一致）。

## 增量更新机制（先对比再更新，省成本）

每次生成某章节：
1. 用 **web_fetch** 拉取该 URL 最新内容。
2. 计算内容指纹（hash），与 `source-cache/<key>.json` 中上次记录的 hash 比对。
3. **hash 一致** → 直接复用模板中已排版段落，跳过重排。
4. **hash 不一致** → 仅对该章节重新整合，并向用户高亮提示“X 章节检测到官方更新，已同步”。
5. 更新缓存快照（内容 + hash + 抓取日期）。

缓存文件格式（`source-cache/<key>.json`）：
```json
{ "url": "...", "hash": "sha256:...", "fetched_at": "2026-05-25", "snapshot": "正文快照（用于离线降级与 diff）" }
```

## 降级说明（web_fetch 也不可用时）

- 若某次 web_fetch 失败/被限制：回退使用 `source-cache/` 快照或用户粘贴的最新内容；只做域名替换与参数替换，并在产出时标注“本次未联网，内容基于 <缓存日期> 快照”。
- Skill 已内置一份**出厂快照**（source-cache/ 下：deploy_sceneA / deploy_sceneB / deploy_streamlined / operations / migration / checklist 等），即使完全离线也能产出真实文档。

---

## 部署文档章节映射（docs-pdop.mingdao.com） — 标准版 / 专业版共用

> 标准版与专业版**安装方法相同、用同一批集群版链接**（MongoDB 副本集、MySQL MGR、Redis 哨兵、Kafka/ES/MinIO 集群、K8s 三 Master）；差异只在**节点数与拓扑**（标准版共置 17 节点 / 专业版各组件独立 26 节点），不在安装步骤。精简版（6 节点）另见文末 `s_` 前缀表。

| key | 章节 | URL |
|---|---|---|
| docker | Docker 安装 | https://docs-pdop.mingdao.com/deployment/cluster/installation/docker |
| mongodb | MongoDB 副本集 | https://docs-pdop.mingdao.com/deployment/cluster/installation/mongodb/4.4/replica-set |
| mysql_mgr | MySQL MGR 集群 | https://docs-pdop.mingdao.com/deployment/cluster/installation/mysql/mysql-8.0/mgr |
| redis | Redis 哨兵 | https://docs-pdop.mingdao.com/deployment/cluster/installation/redis/sentinel |
| kafka | Kafka 集群 | https://docs-pdop.mingdao.com/deployment/cluster/installation/kafka/kafka-cluster |
| es | Elasticsearch 集群 | https://docs-pdop.mingdao.com/deployment/cluster/installation/elasticsearch/elasticsearch-cluster |
| minio | MinIO 集群 | https://docs-pdop.mingdao.com/deployment/cluster/installation/minio/minio-cluster |
| file_preconf | 上传预置文件 | https://docs-pdop.mingdao.com/deployment/cluster/installation/file/v2/upload-preconf-files |
| file_multinode | File 多节点 | https://docs-pdop.mingdao.com/deployment/cluster/installation/file/v2/multi-node |
| k8s | K8s 1.35.3 三 Master | https://docs-pdop.mingdao.com/deployment/cluster/installation/kubernetes/kubernetes-1.35.3/multi-master-deployment |
| istio | Istio 1.29.1 | https://docs-pdop.mingdao.com/deployment/cluster/installation/istio/istio-1.29.1/istio |
| istio_notes | Istio 注意事项 | https://docs-pdop.mingdao.com/deployment/cluster/installation/istio/pointsToNote |
| service | HAP 微服务 | https://docs-pdop.mingdao.com/deployment/cluster/installation/service |
| flink | Flink | https://docs-pdop.mingdao.com/deployment/cluster/installation/flink |
| nginx | Nginx | https://docs-pdop.mingdao.com/deployment/cluster/installation/nginx/deploy-nginx |
| nginx_keepalived | Nginx + Keepalived 高可用（双 Nginx VIP） | https://docs-pdop.mingdao.com/deployment/cluster/installation/nginx/nginx-keepalived |
| prometheus | Prometheus | https://docs-pdop.mingdao.com/deployment/cluster/installation/monitor/prometheus |
| grafana | Grafana | https://docs-pdop.mingdao.com/deployment/cluster/installation/monitor/grafana |

## 两个 PDF 来源映射（docs-pd.mingdao.com）

故障处理 PDF：
| key | 章节 | URL |
|---|---|---|
| faq_deployment | 部署问题 | https://docs-pd.mingdao.com/faq/deployment |
| faq_servicecheck | 服务运行状况检查 | https://docs-pd.mingdao.com/faq/troubleshooting/service-status-check |
| faq_workflow_queue | 工作流持续排队 | https://docs-pd.mingdao.com/faq/troubleshooting/workflow-keeps-queuing |
| faq_icon | 图标不显示 | https://docs-pd.mingdao.com/faq/troubleshooting/icon-not-showing |
| faq_page | 页面无法访问 | https://docs-pd.mingdao.com/faq/troubleshooting/page-not-accessible |

服务器资源要求 PDF：
| key | 章节 | URL |
|---|---|---|
| res_platform | 支持平台 | https://docs-pd.mingdao.com/deployment/platform |
| res_component | 组件支持版本 | https://docs-pd.mingdao.com/deployment/component |
| res_source | 服务器资源推荐 | https://docs-pd.mingdao.com/deployment/source |
| res_serverreqs | 服务器性能要求 | https://docs-pd.mingdao.com/deployment/server-reqs |

## 离线安装包（pdpublic.mingdao.com，仅域名替换，内容不重排）

这些是下载链接，nocoly 模式下仅替换域名为 `pdpublic.nocoly.com`，无需拉取页面内容。完整清单见部署文档正文（docker/mysql/mongodb/redis/kafka/es/nginx/k8s/flink/监控等离线包）。

---

## 集群精简版章节映射（单节点版，docs-pdop.mingdao.com）

> 精简版专属。注意路径与集群版不同：mongodb 用 4.4/standalone、mysql 用 mysql-8.0/、minio 用 minio-single、file 用 v2/single-node、k8s 用 single-master-deployment。
> 增量更新与降级机制同上（web_fetch 拉取 + source-cache 对比）。
>
> **⚠️ 版本路径核对备注（重要）**：下表版本路径（MongoDB **4.4**、MySQL **8.0**、K8s **1.35.3**、Istio **1.29.1**）已于 2026-05 用 web_fetch 逐一核对，确认为官方当前**有效**版本，页面真实存在、内容与本 Skill 文档一致。
> 注意：官方文档站**左侧导航的默认展开项会指向更旧版本**（MongoDB 3.4 EOL、MySQL 5.7 EOL、K8s 1.25.4、Istio 1.18.0）——这是导航父节点的默认入口，**不代表推荐版本**；3.4/5.7 在官方已明确标注 (EOL)。生成时**坚持使用下表的 4.4/8.0/1.35.3/1.29.1**。
> 实际生成时仍建议用 web_fetch 复核一次：若某版本页返回 404（官方下线该版本），再回退到官方导航当时的有效版本，并提示用户。

| key | 章节 | URL |
|---|---|---|
| s_docker | Docker 安装 | https://docs-pdop.mingdao.com/deployment/cluster/installation/docker |
| s_mongodb | MongoDB 单节点 | https://docs-pdop.mingdao.com/deployment/cluster/installation/mongodb/4.4/standalone |
| s_mysql | MySQL 8.0 单节点 | https://docs-pdop.mingdao.com/deployment/cluster/installation/mysql/mysql-8.0/ |
| s_redis | Redis 单节点 | https://docs-pdop.mingdao.com/deployment/cluster/installation/redis/ |
| s_kafka | Kafka 单节点 | https://docs-pdop.mingdao.com/deployment/cluster/installation/kafka/ |
| s_es | Elasticsearch 单节点 | https://docs-pdop.mingdao.com/deployment/cluster/installation/elasticsearch/ |
| s_minio | MinIO 单节点 | https://docs-pdop.mingdao.com/deployment/cluster/installation/minio/minio-single |
| s_file | File 单节点 | https://docs-pdop.mingdao.com/deployment/cluster/installation/file/v2/single-node |
| s_file_preconf | 上传预置文件 | https://docs-pdop.mingdao.com/deployment/cluster/installation/file/v2/upload-preconf-files |
| s_k8s | K8s 1.35.3 单 Master | https://docs-pdop.mingdao.com/deployment/cluster/installation/kubernetes/kubernetes-1.35.3/single-master-deployment |
| s_istio | Istio 1.29.1 | https://docs-pdop.mingdao.com/deployment/cluster/installation/istio/istio-1.29.1/istio |
| s_istio_notes | Istio 注意事项 | https://docs-pdop.mingdao.com/deployment/cluster/installation/istio/pointsToNote |
| s_service | HAP 微服务 | https://docs-pdop.mingdao.com/deployment/cluster/installation/service |
| s_flink | Flink | https://docs-pdop.mingdao.com/deployment/cluster/installation/flink |
| s_nginx | Nginx | https://docs-pdop.mingdao.com/deployment/cluster/installation/nginx/deploy-nginx |
| s_nginx_keepalived | Nginx + Keepalived（精简版单 Nginx 默认不用，扩展双 Nginx 时备用） | https://docs-pdop.mingdao.com/deployment/cluster/installation/nginx/nginx-keepalived |
| s_prometheus | Prometheus | https://docs-pdop.mingdao.com/deployment/cluster/installation/monitor/prometheus |
| s_grafana | Grafana | https://docs-pdop.mingdao.com/deployment/cluster/installation/monitor/grafana |
