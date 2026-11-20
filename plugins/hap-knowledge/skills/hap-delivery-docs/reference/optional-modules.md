# 可选模块交付规则

在入参选择非「无」时读取本文件。由执行 skill 的助手读取本次预检收集的官方正文，编写完整项目章节，再调用既有渲染器；不是要求用户自行编写 JSON 或实施步骤。默认不添加任何新模块，旧表无可选页也等同全部无。

## 入参和依赖

「⑦ 可选模块」第 4 行起，A=固定 ID，B=名称，C=模式（下拉、默认无），D=实际节点/访问端点，E=非敏感适用性说明。密码、Token、AK/SK、Webhook 密钥只填「④ 凭据清单」。保留最后一页「⑧ 自定义项描述」。空白选择视为无；非法模式、重复 ID 和未知 ID 会报错。

| ID | 可选模式（均另有无） | 启用后的完整交付范围 |
|---|---|---|
| etcd | 单节点 / 集群 / 使用现有 | 独立 etcd；不可复用 Kubernetes 控制面 etcd 作为 Milvus 数据依赖 |
| milvus | 启用 | Milvus Operator、工作负载、Kafka/etcd/S3 依赖、认证与 HAP 接入 |
| compute | 启用 | 专属算力节点、computinginstance、workflowcompute 和工作流资源隔离 |
| hdp | 启用 | 独立 HDP 服务、数据库、Flink 前置条件和启停脚本 |
| alerts | 启用 | Alertmanager、PrometheusAlert、规则、路由和通知联调 |
| kibana | 启用 | Kibana 安装、Elasticsearch 接入、访问入口和验证 |
| victorialogs | 二进制 / Docker / 二进制（Promtail，EOL）/ Docker（Promtail，EOL） | 新环境使用 Alloy；Promtail 仅显式选择的存量维护。均含日志轮转、VictoriaLogs、Grafana 数据源和慢查询面板 |
| grafana_upgrade | 启用 | 二进制 Grafana 升级、备份、配置重建、数据保留、启动验证及回退 |
| k8s_faq | 启用 | Kubernetes 专项排障，按当前版本/内核/CPU适用条件纳入故障处理与运维章节 |
| mysql_mode | 主从 | 替换原 MySQL 部署模式；版本按当前适用官方主从页核定 |
| redis_mode | 主从 / 主从+Keepalived（EOL） | 替换原 Redis 模式；历史 EOL 分支必须说明采用原因 |
| mongodb83 | 单节点副本集 / 三节点副本集 | 核对适用条件后采用 MongoDB 8.3 分支，版本跟随本次官方页面 |
| implementation_plan | 启用 | 组件实施进度表 xlsx，仅在选择 deploy 产物时生成 |
| functional_validation | 启用 | 业务功能验证记录 xlsx，在选择 deploy 或 checklist 时生成 |

精确的有效模式和来源种子维护在 `scripts/optional_modules.py` 的 `MODULES`；链接只是发现起点，正文以本次官方页面为准。两个表单不改变部署拓扑，不要求章节 JSON；Kubernetes 专项 FAQ 属于内容模块，需要正文，但不增加物理节点。

Milvus 的 etcd 依赖须由用户显式选择「单节点/集群/使用现有」并给出端点；不要自动开启依赖。Kafka 与 S3 沿用或新增须在项目章节、端口和图中明确。其他依赖按当前官方页核对，缺少必要输入时询问该项，继续完成其他已知内容。

## 生成前编写的内容

1. `prepare --input 已填入参.xlsx` 按已选项采集对应官网正文；浏览采集、版本冲突处理和离线规则沿用主流程。数据库替代模式会排除冲突的默认安装来源。
2. 助手根据当前正文和实际节点完成下表规定的操作内容，保存为项目目录 `可选模块内容.json`。在线步骤和离线步骤按项目联网条件编写；完整保留依赖、配置、systemd/YAML、初始化、启动和验证。不能以官网链接或一句“按官方执行”替代实际步骤。
3. 技术模块启用且选择 arch 时，助手制作完整项目 SVG，通过 `prepare --architecture 项目.svg` 绑定。图中展示新增模块、实际节点/端点、已有/新建关系和访问方向；数据库模式不能继续套用历史标准图。
4. `seal --report 来源核验.json --module-content 可选模块内容.json --note "已核对所选模块、依赖、版本、完整操作、关联文档及项目架构"`。再通过 `gen_from_input.py` 生成用户选择的产物。
5. JSON/入参/项目图/来源正文改变后重新核验。生成器会检查绑定的文件哈希、模式和节点；未启用模块不能放入 JSON。

公有云迁移到私有部署不提供选项，不扩展现有迁移范围。既有单机迁移集群仍按需选择 migration；MongoDB 8.3 与单机/4.4 迁移约束冲突时先解决适用性，不能直接生成相互矛盾的方案。

## 各模块必须落实的技术内容

| 模块 | 部署章节必须具备 | 运维、验收与关联内容 |
|---|---|---|
| 独立 etcd | 确认节点和 CPU 架构；下载解压；运行用户和目录权限；逐节点配置名称、client/peer/metrics 地址和 initial-cluster；systemd、启动、健康检查；root 用户/角色、启用认证和认证后验证。使用现有模式记录端点、版本、认证和连通性验证，不重复安装 | 成员/健康/认证状态、日志、快照与恢复、容量和配额、节点故障处理；记录客户端/peer/监控实际端口；独立 etcd 凭据与 Milvus 配置一致 |
| Milvus | 先核对节点 Ready、Kafka、独立 etcd、MinIO bucket；标签/污点；按架构预置镜像；安装 Operator；namespace/S3 Secret；完整 Milvus CR、资源/副本/调度、外部依赖和认证配置；服务暴露与 HAP 所需连接配置；验证 Operator、Pod、端点和实际检索 | 日志和状态、凭据更换、依赖异常、持久数据/对象存储备份边界、升级与恢复；图中明确 Milvus 到 Kafka/etcd/S3 的访问；凭据不得写正文 |
| 专属算力 | 新节点加入 K8s、镜像、标签/污点；按安装管理器实际版本处理已有或新增 computinginstance.yaml；KubeConfig/Secret/RBAC 和资源参数；相关启停/重启脚本变更；组织内创建专属资源并分配工作流 | 验证 workflowcompute Deployment/Pod、独立 Kafka topic、并发与 CPU/内存限制；扩缩容、日志、工作流消费异常与资源回收；专属节点与微服务隔离须体现在图和资源表 |
| HDP | MySQL MDHDP、MongoDB mdhdp 及账号；聚合表前置配置；Flink 版本兼容与存量任务重启影响；HDP 镜像、完整 hdp.yaml/hdpwww 服务；启动/停止/重启脚本；ENV_HDP_ENABLE/数据库连接等当前所需参数；启动并验证功能 | 单独列出 HDP 服务与 Flink 的关系、日志、升级、数据库备份/恢复、功能验证；HDP 不是 Flink 的别名，不伪造一个新物理节点 |
| 告警通知 | PrometheusAlert 配置与服务、通知渠道和模板、Alertmanager 配置/路由/分组/恢复通知、Prometheus 告警规则与连接；端到端触发和恢复测试 | 规则变更与 reload、告警风暴/静默、通知失败排查；图标出 Prometheus→Alertmanager→PrometheusAlert→接收渠道；Webhook 用占位符，仅凭据表填写实际值 |
| Kibana | 按当前官网核对 ES 兼容版本、安装包/镜像、服务配置、ES 认证/证书、运行管理方式、访问入口/代理与验证 | 启停、日志、ES 连接排错、升级兼容；记录 Kibana 与 ES 的实际连接方向/端口和登录凭据，不凭空套用其他版本认证方式 |
| VictoriaLogs | 先处理 MongoDB 日志切割与 0 字节文件；新环境按所选二进制/Docker 分支提供完整 Alloy 配置、目录挂载、pipeline 和访问地址；Grafana/插件版本要求、数据源与慢查询面板；验证采集/查询。存量 Promtail 需显式选 EOL 分支并核对迁移说明 | 日志保留和容量、轮转、采集断点、时间/字段解析问题、Grafana 兼容；Docker 分支内置组件不要重复部署；二进制分支明确已有 Grafana 前提；不能把 Promtail 旧配置混入 Alloy |
| Grafana 升级 | 核对原安装方式；下载当前适用安装包、停服、备份旧目录、新目录解压；基于新版本重建 conf 配置，不直接覆盖旧 conf；保留/迁移 data；重写实际版本所需 systemd 并启动验证 | 验证数据源、面板、插件和子路径；明确回退条件和实际备份目录；不能把全新安装步骤当作升级步骤 |
| Kubernetes FAQ | 按当前官方故障页核对内核/CPU/架构/版本；编写症状、原因、完整检查/修复命令及验证；覆盖当前页列出的 CRI/containerd、Calico、网络等适用问题，不能无条件降级组件 | 以实际症状和适用条件路由；复核修复对现有 Pod/容器运行时影响；未部署独立新服务时不虚构端口、凭据或新节点 |
| MySQL 主从 | 两端安装/初始化与权限、my.cnf 的 server-id/日志/GTID 等当前要求、复制账号和复制初始化、主从状态验证、HAP 实际读写入口 | 全文更新连接信息、备份恢复、复制延迟、故障处理和凭据；移除不适用的 MGR/Router/组复制恢复步骤。主从不自动等于高可用，不推定 VIP |
| Redis 替代模式 | 主从实例配置、认证/复制参数、HAP 与 File 的实际连接方式；若显式选历史 Keepalived，再完整提供 VIP、网卡、VRRP、检查和主备切换脚本 | 移除不适用的 Sentinel 端口/配置/运维命令；验证复制和实际故障切换；普通主从与自动故障切换的能力界限要写清 |
| MongoDB 8.3 | 先核对官方适用条件：所有环境含测试均为 HAP 集群、MongoDB 独立部署；有既有 4.4/单机或相关迁移时继续使用适用版本。按 OS/CPU 选择包；运行用户/目录/内核要求、mongod.conf、systemd、mongosh、认证/keyFile、单/三节点副本集初始化与状态验证 | 全文同步连接串、认证、备份工具和版本兼容、恢复/迁移边界、故障处理、资源和凭据；单节点副本集不写成三节点高可用；禁止只把旧 4.4 命令中的数字替换为 8.3 |

## 项目内容 JSON 结构

这是生成器的内容接口，由助手填写真实完整内容；下面只是字段示例，不能作为已完成的部署正文。

```json
{
  "schema": 1,
  "modules": {
    "etcd": {
      "mode": "单节点",
      "nodes": "与入参 D 列完全一致的实际节点/端点",
      "review": "记录当前来源、架构与依赖、认证和实际网络方向的核对结果，不填写实际密码",
      "sections": {
        "deploy": "完整安装、配置、systemd、初始化、认证、启动和验证 Markdown，包含命令代码块",
        "ops": "完整启停、状态、日志、备份恢复、升级和异常处理操作 Markdown",
        "faq": "该模块适用于本项目的故障症状、检查命令、处理和恢复验证",
        "resource": "实际节点/共置、资源要求、CPU架构、端口、依赖和计数口径",
        "checklist": "逐项验收操作、预期结果、实际结果/执行人/日期留空的表格"
      },
      "credentials": [{
        "component": "独立 etcd", "node": "实际节点", "port": "实际端口", "user": "root",
        "key": "可选/etcd/root", "placeholder": "<强密码>",
        "config": "etcd 认证 / Milvus 依赖配置", "chapter": "独立 etcd",
        "dependency": "etcd 认证与 Milvus 使用的认证信息一致", "input_key": "独立 etcd root 密码"
      }]
    }
  },
  "documents": {}
}
```

- `modules` 必须且只能包含已启用技术模块（表单项不放这里），每项 mode、nodes 与入参一致。未选择的产物无需提供对应 section；选择 cred 时 credentials 必须为列表，无新增凭据用 `[]`。章节由既有 Markdown→Word 管线渲染，保留原版式。
- `sections.deploy` 使用 Markdown 三反引号代码块，不能把所有命令压成普通段落。完整内容以当前预检正文为依据，不在本通用技能固定最新版镜像/安装包。
- 保持既有 Word 封面、页眉页脚、纸张、字体、表格和代码样式。模块子标题以 `##`/`###` 编写；模块正文中的一级标题会降为二级，代码块里的 shell 注释不改动；代码围栏不闭合和非法 XML 控制字符会阻止生成。部署模块放在最终上线验收前；不能把网站导航或 HTML 样式直接贴进文档。
- 模块凭据字段 `key` 固定使用 `可选/<模块ID>/<字段>` 前缀；`input_key` 精确对应入参「④ 凭据清单」的凭据项名称。`placeholder` 只保存占位符；实际值由生成器直接从入参写入凭据表。
- 数据库模式替换时，`documents` 必须提供本次选择的 deploy/ops/migration/faq/resource 完整 Markdown。助手先运行对应 builder 取得基线，再整体落实模式、IP/端口/计数/备份/升级/故障处理变更，不能追加互斥步骤。没有选择的文档不要求提供。该模式的正文已经包含在完整替代文档中，无需再提供重复 section；checklist 仍提供模式验收 section，其他新增服务的 section 按常规追加。
- 同时选择 cred 的数据库模式替换，提供 `replacement_credentials`（同上述九个内容字段及可选 input_key 的完整行列表）与 `replacement_constraints`（每项四列：ID/约束/涉及位置/示例值）。替换旧凭据与约束后再追加所选模块凭据。清单保留本次实际产物列表，附加对应模块验收内容。
- 技术章节、表单、项目内容及来源核验均不代表已实际安装或验收；表单实际完成时间、结果、截图和签字不能预填为成功。实施组件按项目实际范围增删，表单生成后的范围复核属于交付检查。

## 验证新增可选能力

至少检查：默认全无与旧表；单模块开关；Milvus 未选 etcd；二进制/Docker 分支来源隔离；数据库替代模式不残留默认架构；内容/图/入参改动阻止旧核验生成；密码只进入凭据表；两个表单只按所选产物产生且进入实际交付清单。真实交付前另检查 Word 排版、项目 SVG 和实际节点/端口一致性。

覆盖范围区分“已提供选项及来源路由”“助手已编写完整项目正文”“实际生成且版式核验”三个状态。通过来源/结构测试不等于官网所有步骤已经写入固定模板；不得把模拟正文测试描述为所有组件安装步骤已验证。历史 EOL 页面按项目明确选择或版本覆盖处理，公有云迁移明确排除。
