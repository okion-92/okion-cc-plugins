# HAP Deployment Troubleshooting Map

用于把常见异常现象快速映射到官方页面。此文件帮助定位，不代替实时核验。

## 通用入口

| 问题方向 | 官方页面 |
|---|---|
| 版本、发布日期、架构支持、是否有附加操作 | `https://docs-pd.mingdao.com/version` |
| 部署总入口 | `https://docs-pd.mingdao.com/deployment/platform` |
| 环境变量 | `https://docs-pd.mingdao.com/deployment/env/` |
| 常用命令 | `https://docs-pd.mingdao.com/deployment/command` |
| Kubernetes 入口 | `https://docs-pd.mingdao.com/deployment/kubernetes/` |
| 组件支持版本 | `https://docs-pd.mingdao.com/deployment/component` |
| 离线资源包 | `https://docs-pd.mingdao.com/deployment/offline` |
| 部署 FAQ | `https://docs-pd.mingdao.com/faq/deployment` |
| 工作流持续排队 FAQ | `https://docs-pd.mingdao.com/faq/troubleshooting/workflow-keeps-queuing/` |

## 现象到页面映射

| 现象 | 优先页面 |
|---|---|
| 升级后异常 | `/version` + 对应 `/upgrade/{version}/` |
| 单机部署升级异常 | `/deployment/docker-compose/standalone/upgrade/hap` |
| Kubernetes 升级异常 | `/deployment/kubernetes/upgrade/hap` |
| 工作流堆积 / 工作流持续排队 / 流程排队 / 工作流不消费 | `/faq/troubleshooting/workflow-keeps-queuing/` |
| MongoDB 相关问题 | `/deployment/components/mongodb/command` 或 `/deployment/components/mongodb/createdb` |
| Kafka 安全连接问题 | `/deployment/components/kafka/secureConnection` |
| 文档预览 / LibreOffice 问题 | `/faq/integrate/docconvert/libreoffice` |
| HDP 集成问题 | `/faq/integrate/hdp/enable-hdp` |
| HDP 启动失败 / `中间库功能未开启` / `storehouse.enable` / hdpapi 启动后立即 shutdown | `/faq/integrate/hdp/enable-hdp` 5 项前置全核对：①MySQL MDHDP ②MongoDB mdhdp ③Flink 1.19.720 ④MongoDB 副本集 ⑤聚合表中间库 mdaggregationwsrows。中间库参考 `/optimize/mongodb/storage/mulitWSRows/`；参见 `cases.md` 2026-05-25 案例 |
| searchapi / searchindex 反复重启 / ERR_INVALID_URL / ES 连接失败 | `/deployment/env/` 核验 `ENV_ELASTICSEARCH_ENDPOINTS`（每个节点都要带 `http://` 前缀，逗号分隔）；参见 `cases.md` 2026-05-25 案例 |
| 离线部署准备不足 | `/deployment/offline` + `/deployment/component` |

## 处理顺序建议

### 升级后问题

1. 先确认实际版本与目标版本
2. 到 `/version` 看发布日期、详情页、附加操作和架构支持
3. 再看对应升级详情页与部署模式页面

### 启动失败或服务异常

1. 先定位部署模式
2. 再看环境变量与常用命令页
3. 如果关联具体组件，再跳到组件文档

### 工作流持续排队

1. 先看工作流监控页，区分"排队量大但仍在消费"和"一直排队完全不消费"
2. 如个别流程排队量极高，优先判断触发逻辑、死循环或批量触发；确认不需继续执行时，按 FAQ 在非暂停状态下关闭对应工作流
3. 如全部不消费，先查磁盘 `df -Th`，再查 Kafka 服务状态或 `mingdaoyun-sc` 健康日志
4. 再查 Kafka 消费组 `md-workflow-consumer` 的 `LAG` 和是否 `rebalancing`
5. 长时间 rebalancing 时，再按单机或 Kubernetes 模式重启工作流消费服务

### FAQ 类问题

1. 先确认现象是否和 FAQ 标题一致
2. 提炼 FAQ 中的前置条件和核验动作
3. 不把 FAQ 之外的推测当成官方方案
