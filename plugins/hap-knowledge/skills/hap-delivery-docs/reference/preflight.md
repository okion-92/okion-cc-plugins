# 来源预检与生成记录

## 工作方式

`source_preflight.py prepare` 每次读取总入口及所选产物涉及的专属页，沿相同章节结构选择新版本路径，记录正文、实际 URL、提取到的版本与安装包。HTTP 无法读取时可由浏览工具采集，不能把搜索摘要或旧模板当作本次正文。

默认使用 HAP 官方当前适用的最新组件版本，不自动替换成未经 HAP 确认的上游最新版本。发现页面结构变化或版本/架构存在歧义，AI 应阅读总入口及相关页面后指定实际来源。`--source KEY=URL` 和 `--pin COMPONENT=VERSION --reason 原因` 仅用于本项目明确覆盖，不修改通用来源映射。

## 浏览采集文件

浏览工具完成本次读取后，将结果保存为 UTF-8 JSON，URL 为键，正文应完整包含安装链接、镜像、配置与命令；`links` 保存入口发现的官方子页地址：

```json
{
  "https://docs-pdop.mingdao.com/deployment/cluster/": {
    "content": "本次浏览工具读取的总入口正文，而非搜索摘要",
    "links": ["https://docs-pdop.mingdao.com/deployment/cluster/installation/mysql/mysql-8.4/mgr/"],
    "fetched_at": "2026-11-19T08:00:00+00:00"
  }
}
```

上面的日期和 URL 只是格式示例，实际必须使用本次采集时间及本次发现的链接。对 `prepare` 报告中的所有必需来源完成采集后：

```text
python scripts/source_preflight.py prepare --version std --outputs arch --input 入参.xlsx --architecture 项目.svg --bundle 已采集页面.json --report 项目目录/来源核验.json
```

未出现在 bundle 中的页面仍尝试直接读取。不要把无法读取的页面伪装成成功；来源失败会阻止后续生成。链接只允许 HAP 官方文档域名，安装包只记录而不下载或执行。

## 更新基线与封存

1. 读取报告旁的 `*-pages/*.txt`，核对组件版本及完整配置过程，处理专属页与汇总页的冲突。
2. 在当前项目使用的技能副本中更新对应基线和生成逻辑，保留 Word 版式；客户具体覆盖只在项目副本生效。
3. 审核自定义 Sheet 和项目架构图，检查节点、端口、包含关系与命名。
4. `seal --report ... --note "核对说明"` 检查快照、可解析的版本落后情况，再绑定基线文件与入参/项目 SVG 指纹。
5. 生成时再次核对。源码、入参、来源正文或项目 SVG 变化后必须重新核验。实时记录有效期为24小时，不跨日长期复用。

`seal` 是执行者登记已完成的语义审核，不是自动将网页命令合并进 Word，也不证明安装包可安装。脚本能提取常见版本格式，但部署步骤的语义和不常见镜像格式仍由执行者逐节核对；不能只把一个新版本号加到无关文件中让检查通过。

## 离线降级

只有本次页面确实无法读取，且已有对应来源 key 的带日期缓存时，`prepare --allow-offline` 才允许使用它。`seal` 也需 `--allow-offline`；交付目录的 `来源核验说明.txt` 会列出离线来源、历史日期和读取失败原因。缓存不可用时停止该项生成，不能编造最新版本。

本仓库原有 `deploy_sceneA/B` 等聚合快照不能冒充逐组件的实时页面。首次离线使用若没有组件级缓存，先补齐真实来源，或将其作为明确说明未核验范围的人工草稿处理，不能封存为“最新版本交付”。

## 按需生成

新增能力读取入参的「可选模块」页，缺页/空白/无均不启用。已选技术模块须由助手按照 [可选模块交付规则](optional-modules.md) 完成项目章节 JSON，并在封存时传 `seal --module-content 项目目录/可选模块内容.json`；项目内容哈希也绑定到核验记录。完整数据库模式替换必须包含受影响文档和凭据的替代内容。两个可选表单不需要技术章节 JSON。

```text
python scripts/gen_from_input.py 入参.xlsx 输出目录 --only arch --architecture 项目.svg --preflight 来源核验.json
python scripts/gen_from_input.py 入参.xlsx 输出目录 --only deploy,ops,migration,checklist --preflight 来源核验.json
```

默认不包含迁移；生成清单时根据本次真正生成的文件组装，不引用未选择的产物。输出目录原有的其他文件不做替换。架构图为本项目的 SVG + PNG；若包含附图位图，按当前图像编辑工具工作流处理，不把项目图改成默认示意图。
