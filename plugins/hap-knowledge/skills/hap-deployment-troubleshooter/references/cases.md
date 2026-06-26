# 排障案例库（思路速记 + 反拆索引）

> 完整正文（现象/根因/排查思路/修复/官方依据）已反拆进 `sources/faq/`，走「改 source → 重生成 data/」闭环。
> 本文件保留每条的**关键排查思路精炼**（便于快速翻同款），详情点开对应 source。新案例先在文末按日期草记，攒一两条后再反拆。

## 已成形案例 — 关键思路速记

- **2026-05-25 HDP(hdpapi) 启动失败：中间库 mdaggregationwsrows 未开** → `sources/faq/hdp-start-fail-storehouse-disabled.md`
  - 思路：报错 `中间库功能未开启，系统禁止启动` 只暴露 1 项，但 **HDP 启用前置是 5 项硬条件**（MySQL 库 MDHDP / MongoDB 库 mdhdp / Flink 1.19.720 / Mongo 副本集 / 聚合表中间库 mdaggregationwsrows）。缺任一项在不同位置报不同错——改一项要顺手把 5 项全核一遍，否则改完第 5 项又因副本集没开继续报。`storehouse.enable` 无独立文档，由「聚合表功能 + mdaggregationwsrows」组合决定，新部署/迁移最易漏。

- **2026-05-25 searchapi/searchindex CrashLoop：ENV_ELASTICSEARCH_ENDPOINTS 写法错** → `sources/faq/es-endpoints-multinode-url-prefix.md`
  - 思路：日志 `ERR_INVALID_URL` 且 input 是**第二个**节点的裸 `host:port` → 立刻判定是「**微服务连 ES 的配置串解析失败**」而非 ES 集群本身挂。ES endpoints **每个**节点都要带 `http://`（TLS 用 `https://`）；别套 Kafka 的裸 `host:port` 写法——这是高发口子。

- **2026-05-22 Excel 导入频繁转圈/超时：宿主机杀毒软件干扰** → `sources/faq/excel-import-timeout-antivirus.md`
  - 思路：导入转圈，pod 实例不足只是常见原因之一。日志指向**偶发网络超时 + 扩容无效**时，要怀疑宿主机侧**安全软件（杀毒/EDR/防火墙）**拦截容器网络/进程，停用做对照测试定位。

- **2026-05-14 附件无法预览，接口 URL 端口丢失** → `sources/faq/nginx-1.29-host-port-lost.md`
  - 思路：F12 见预览接口 URL 少了端口 → nginx **1.29.4 起按 RFC3986 收紧 Host/Port 校验**，`$http_host` 非默认端口下不再带端口。修复用 `$request_port`（1.29.3+ 新增），**不要用 `$server_port`**（那是 nginx listen 端口，多层代理/对外端口≠监听端口时会拼错）。

- **2025-10 Excel 打印模板子表签名渲染成黑色** → `sources/faq/excel-print-signature-black.md`
  - 思路：升组件 + 清缓存**两步缺一不可**。关键是 **file 缓存目录 cache 不过期**——光升组件（集群 file 2.1.0 / 单机 sc 3.2.0），旧的黑色缓存仍被命中，必须清 cache（`find -mtime +7 -delete` 或停服 `rm -rf`）。停启用官方脚本，别 `docker stop`。

## 新案例草记（按日期追加，攒一两条后反拆进 sources/faq/）

<!-- 例：2026-06-XX 现象 → 排查思路 → 根因 → 现场修复 → 官方依据；成形后 reverse 成 sources/faq/<slug>.md 再重生成 -->
