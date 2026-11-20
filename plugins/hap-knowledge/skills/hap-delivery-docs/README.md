# HAP 私有部署交付文档

按 Excel 入参生成指定文档、架构图或整套交付件。每次生成前核对官方总入口及相关组件最新适用版本、安装链接与步骤，再用既有 Word 渲染管线输出；不直接重放未经本次核验的旧基线。

## 安装

将完整目录放入 Codex / Claude Code 的技能目录，例如 `~/.claude/skills/hap-delivery-docs/`，进入目录执行：

```text
npm install
pip install openpyxl pymupdf python-docx
python doctor.py
```

需要 Node.js 和 Python。推荐安装微软雅黑、Consolas，以保持现有 Word 和 PNG 字体。也可将完整技能目录压缩后通过支持自定义技能的客户端导入。

## 生成流程

```text
python scripts/make_input_template.py HAP交付入参模板.xlsx
python scripts/source_preflight.py prepare --version std --input 已填入参.xlsx --report 项目目录/来源核验.json
```

填写项目信息、节点 IP、凭据、端口及最后一个 Sheet 的自定义项。AI 读取来源正文，按最新适用组件版本完整调整相关基线，处理项目明确覆盖及来源冲突，保持模板版式，然后：

「⑦ 可选模块」提供独立 etcd、Milvus、专属算力、HDP、告警、Kibana、VictoriaLogs、Grafana 升级、Kubernetes 专项 FAQ、数据库替代模式及两类记录表，全部默认「无」，旧入参缺页也不启用。新环境日志采集采用当前官方 Alloy 分支，Promtail 只用于显式选择的 EOL 存量维护。AI 按 [可选模块规则](reference/optional-modules.md) 完成项目章节和关联内容，`seal` 增加 `--module-content 项目目录/可选模块内容.json`；涉及架构图时同时绑定项目 SVG。公有云迁移不包含在扩展范围内。

```text
python scripts/source_preflight.py seal --report 项目目录/来源核验.json --note "已核对版本、下载与部署步骤，并落实项目覆盖"
python scripts/gen_from_input.py 已填入参.xlsx 项目目录 --preflight 项目目录/来源核验.json
```

没有核验记录、记录过期、入参/基线已改变或可解析组件版本落后时会停止生成。预检和封存不是自动安装验证，不能代替逐节核对部署步骤。

## 按需输出

`--only` 支持 `deploy,ops,migration,arch,cred,faq,resource,checklist`；默认不含 migration，迁移需明确选择。prepare 的 `--outputs` 要覆盖随后所需输出。

```text
python scripts/source_preflight.py prepare --version std --outputs arch --input 已填入参.xlsx --architecture 项目.svg --report 项目目录/来源核验.json
# 完成本次来源与项目 SVG 核对并 seal 后：
python scripts/gen_from_input.py 已填入参.xlsx 项目目录 --only arch --architecture 项目.svg --preflight 项目目录/来源核验.json
```

架构图以真实节点及端口为准，默认清爽配色、共享调用总线、明确请求方向和服务包含关系。客户具体的 AKS / Teams / SSO、组件替换和去边框等要求不写入通用默认。

默认产出为部署、运维、故障处理、资源要求和清单的 docx，凭据表 xlsx，架构图 SVG + PNG；密码只进入凭据表，不写入其他正文。清单根据本次实际产物生成。

## 网络受限与版本固定

直接 HTTP 请求受限时，AI 使用当前可用的浏览工具采集同一批真实页面，再通过 `prepare --bundle 已采集页面.json` 导入。格式、项目指定来源与版本、离线声明见 [reference/preflight.md](reference/preflight.md)。

默认组件版本取 HAP 官方本次页面的最新适用值，不取旧模板或未经 HAP 确认的第三方上游最新版。源页面无法读取且有相应带日期缓存时才允许明确离线降级，交付目录会生成 `来源核验说明.txt`，列出未联网核验范围。没有缓存不能伪装成最新交付。

## 维护与验证

- 主指令来自源仓库 `sources/delivery/workflow.md`，执行 `python scripts/build_delivery_skill.py` 重建 `SKILL.md`。
- `reference/source-map.md` 是当前页面发现线索，不能冻结历史版本。
- `scripts/source_preflight.py` 实现来源采集/封存与各生成入口的检查，`scripts/fetch_diff.py` 负责版本、包和内容差异提取。
- `scripts/*_src/`、`build_*.py` 保留既有模板组装；`render_deploy.js` / `inject_cover.py` 保留 Word 版式。
- 执行 `python -m unittest discover -s tests -v` 验证预检失败、版本落后、项目范围、来源变更和离线处理。
- 历史模板可能存在节点数、组件版本或命名冲突，真实交付前按当前来源及项目清单校准；不要把旧样例当成最新事实。
