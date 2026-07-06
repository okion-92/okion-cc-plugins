# 模板：服务器资源要求 PDF

> 生成顺序第2位。已用 web_fetch 实测可拉取 docs-pd.mingdao.com/deployment/source。
> PyMuPDF/reportlab + NotoSansCJK。

## 来源映射（source-map res_*）
| 部分 | key | URL |
|---|---|---|
| 一、支持平台 | res_platform | https://docs-pd.mingdao.com/deployment/platform |
| 二、组件支持版本 | res_component | .../deployment/component |
| 三、服务器资源推荐 | res_source | .../deployment/source |
| 四、服务器性能要求 | res_serverreqs | .../deployment/server-reqs |

## 结构
- 封面 / 文档说明（4 来源 URL + 选型原则）
- 一、支持平台（OS/CPU架构表、ARM 说明、公有云）
- 二、组件支持版本（自建组件表、国产化替代、云产品组件）
- 三、服务器资源推荐（单机 / 集群 精简/标准/专业/HyperScale 表）
- 四、服务器性能要求（CPU/硬盘 IOPS/内网/外网带宽）
- 附录：选型决策参考 + 采购前检查清单
- 页脚：`HAP 私有部署 · 服务器资源要求 | 第 X 页 / 共 Y 页`

## 注意
- 表格数据直接取官方最新（web_fetch），与 PDF 版本可能有差异时以官方为准并提示。
- nocoly：替换来源 URL 与云市场链接域名（marketplace 若出现按 brand-rules 处理）。
