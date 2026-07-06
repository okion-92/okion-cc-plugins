# 模板：常见故障处理 PDF

> 生成顺序第1位。内容跟随官方 FAQ（web_fetch 拉取，source-cache 兜底）。
> 生成用 PyMuPDF/reportlab；中文必须用 NotoSansCJK（pitfalls.md）。封面版本 V1.0 + 编制日期。

## 来源映射（source-map faq_*，nocoly 时替换域名）
| 部分 | key | URL |
|---|---|---|
| 一、部署问题 | faq_deployment | https://docs-pd.mingdao.com/faq/deployment |
| 二、服务运行状况检查 | faq_servicecheck | .../faq/troubleshooting/service-status-check |
| 三、工作流持续排队 | faq_workflow_queue | .../faq/troubleshooting/workflow-keeps-queuing |
| 四、图标不显示 | faq_icon | .../faq/troubleshooting/icon-not-showing |
| 五、页面无法访问 | faq_page | .../faq/troubleshooting/page-not-accessible |

## 结构
- 封面（标题/版本/日期/编制部门）
- 文档说明（内容来源 5 个 URL + 镜像命名提示 v7.1.0 mingdaoyun-hap）
- 五个部分（与官方章节顺序、标题一致以便对照）
- 附录：进一步支持（按品牌 mingdao/nocoly 调整）+ 文档维护说明
- 页脚：`HAP 私有部署 · 常见故障处理 | 第 X 页 / 共 Y 页`

## 注意
- 章节标题与原文保持一致（便于对照官方）。
- nocoly：替换所有来源 URL 域名 + pdpublic 下载链接。
- 增量更新：每部分按 key 对比 hash，变化的重排并提示。
