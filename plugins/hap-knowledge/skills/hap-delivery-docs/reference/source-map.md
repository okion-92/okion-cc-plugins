# 章节 → 官方来源 URL 映射（链接驱动更新）

> 本文件让“文档内容跟着官方链接走”而非固化。生成各章节时，按下表拉取对应 URL 的最新内容，
> 用本套文档结构与话术重组（合规：不整段照搬）。
> 品牌为 nocoly 时，先按 brand-rules.md 把域名换成 nocoly 再拉取。

## 官方总入口与运行时实拉规则

- 集群部署总入口：https://docs-pdop.mingdao.com/deployment/cluster/
- 通用组件入口：https://docs-pd.mingdao.com/deployment/component/
- 通用资源入口：https://docs-pd.mingdao.com/deployment/source/

先从入口及相关组件导航发现当前适用的最新版本页，再读取专属页面。下表只保留历史 URL 作为匹配线索；版本路径不能作为当前推荐版本锁。新旧版本页同时存在时核对适用形态/CPU架构，优先 HAP 官方当前适用最新版本，并记录实际 URL。脚本会按相同章节结构中的版本路径发现候选；结构变化或存在歧义时须通过浏览工具核对后用 --source 指定，不能猜测。


> 本文件只固定“应读取哪个官方页面”，不固定“当前版本是什么”。版本号、安装包名、下载链接、配置文件和 systemd 步骤都必须在每次生成前从对应专属页面重新核对。

来源优先级：
1. 当前项目明确覆盖（版本/模式/排除项，仅当前项目生效）。
2. 下表的组件专属安装页。
3. 官方架构或组件汇总页，仅交叉检查；与专属页冲突时列出差异，不静默混用。
4. `source-cache/` 历史快照，仅在专属页访问失败时降级使用。

2026-08-20 路径核对示例：MySQL 单节点 `mysql/mysql-8.4/`、MySQL MGR `mysql/mysql-8.4/mgr/`、Elasticsearch 单节点 `elasticsearch/`、Elasticsearch 集群 `elasticsearch/elasticsearch-cluster/` 均可访问。这些记录只证明路径有效；页面内版本仍必须运行时提取。

## 拉取通道（已实测确认）

**关键：使用当前运行环境中可用的网页读取/浏览工具访问官方页，不在生成脚本中强绑某一个联网工具。**
- 正确工作流：`prepare` 采集官方页 → 保存正文/链接/时间 → 对比并更新相关完整章节 → `seal` 绑定来源、内容和入参 → 调用原生成器。`fetch_diff.py` 可辅助对比和维护缓存，不能代替来源门禁。
- 如直接打开 URL 受限，先用搜索工具定位该官方页，再读取；不得因工具受限就默认沿用旧版本。

## 增量更新机制（先对比再更新，省成本）

每次生成某章节：
1. 用当前可用的网页读取工具拉取该 URL 最新内容。
2. 计算内容指纹（hash），与 `source-cache/<key>.json` 中上次记录的 hash 比对。
3. **hash、来源 URL 与安装包都一致** → 直接复用已排版基线，跳过重排。
4. **任一项不一致** → 对该章节的下载、解压、用户/目录、配置文件、systemd、初始化和验证步骤做完整更新，不得只替换版本字符串。
5. 完成对应基线章节更新和核验后，再 `commit` 缓存快照（内容 + hash + 来源 URL + 安装包 + 抓取日期）。不得在基线仍是旧内容时先提交新缓存。

缓存文件格式（`source-cache/<key>.json`）：
```json
{ "url": "...", "hash": "sha256:...", "fetched_at": "ISO-8601", "versions": {}, "package_urls": [], "snapshot": "正文快照（用于离线降级与 diff）" }
```

## 降级说明（官方页无法读取时）

- 若官方页读取失败/被限制：回退使用 `source-cache/` 快照或用户粘贴的最新内容；只做域名替换与参数替换，并在产出时标注“本次未联网，内容基于 <缓存日期> 快照”。
- Skill 内置的聚合历史快照（deploy_sceneA/B 等）仅供历史结构参考，不能代替本次所选组件的来源核验；缺少对应逐组件缓存时不能封存为正式最新交付。

---

## 部署文档章节映射（docs-pdop.mingdao.com） — 标准版 / 专业版共用

> 标准版与专业版共用对应集群安装章节作为发现线索；实际模式、共置关系和节点数以本次入参及官方适用说明核定，不固定为历史示例数量。精简版的单节点来源线索见文末 `s_` 前缀表，数据库模式被显式覆盖时改用对应所选来源。

| key | 章节 | URL |
|---|---|---|
| docker | Docker 安装 | https://docs-pdop.mingdao.com/deployment/cluster/installation/docker |
| mongodb | MongoDB 副本集 | https://docs-pdop.mingdao.com/deployment/cluster/installation/mongodb/4.4/replica-set |
| mysql_mgr | MySQL MGR 集群 | https://docs-pdop.mingdao.com/deployment/cluster/installation/mysql/mysql-8.4/mgr/ |
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

## 常见故障处理和服务器资源要求 docx 来源映射（docs-pd.mingdao.com）

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

> 精简版专属。注意路径与集群版不同：mongodb 用 4.4/standalone、mysql 用 mysql-8.4/、minio 用 minio-single、file 用 v2/single-node、k8s 用 single-master-deployment。
> 增量更新与降级机制同上（实际链接拉取 + source-cache 对比）。
>
> **版本路径核对备注**：左侧导航的默认展开项可能指向历史页，不能用导航默认值覆盖下表的专属链接。若专属页返回 404，先在官方站点定位替代页并记录差异，不得直接沿用模板旧版本。

| key | 章节 | URL |
|---|---|---|
| s_docker | Docker 安装 | https://docs-pdop.mingdao.com/deployment/cluster/installation/docker |
| s_mongodb | MongoDB 单节点 | https://docs-pdop.mingdao.com/deployment/cluster/installation/mongodb/4.4/standalone |
| s_mysql | MySQL 8.4 单节点 | https://docs-pdop.mingdao.com/deployment/cluster/installation/mysql/mysql-8.4/ |
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
