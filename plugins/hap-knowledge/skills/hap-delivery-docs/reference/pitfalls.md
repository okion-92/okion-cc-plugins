# 踩坑记录

> 每次交付遇到新坑就往这里加一条。

## PDF 中文字体
- PyMuPDF（fitz）生成/编辑 PDF 时，中文必须嵌入 **NotoSansCJK**（如 NotoSansCJKsc-Regular.otf），否则中文显示为方块/乱码。
- 字体来源：系统 `/usr/share/fonts` 或从明道文档环境取；生成 PDF 前先确认字体文件存在。

## 文件清单与实际不一致
- 交付清单务必按**实际产出目录**核对，不要凭记忆列文件。
- 历史教训：曾引用过被删除的 Excel Sheet / 被排除的场景B文档，导致清单与实物对不上。

## 节点数：各版本单一总数，别混用
- 精简版=**6**、标准版=**17**、专业版=**26**（均为资源表全部行之和，含 HDP 行；HDP 节点即 Flink 节点，不重复算）。
- 不再用"部署15/运维17"两个数、不标"可选"。专业版各组件独立部署故节点最多。

## A/B 端口混淆
- A/B 端口已统一,切场景**不改任何端口**:MinIO 都是 9011-9014、File 都是 9001-9004(容器内均 9000)。差异只在是否组 Swarm。

## 代码块"行混乱"（已在渲染器根治，2026-05）
症状：命令块里弯引号 `" "`（复制到终端报错）、`daemon.json` 等 heredoc 单行 JSON 在单元格里乱断、多行命令被压成一坨。
根因：① 模型生成 markdown 时把直引号写成中文弯引号；② `render_deploy.js` 的 `codeBlock()` 旧实现把多行塞进单个 TextRun，docx 忽略其中的 `\n` → 压平。
根治（已改 `scripts/render_deploy.js`，每次渲染自动生效，不依赖模型）：
- `sanitizeCode()`：代码内 `" " ' '`→直引号、NBSP/全角空格→普通空格、零宽字符删除（**只动代码，不动正文中文标点**）。
- `codeParas()`：所有代码一律按行成段，`codeBlock`/`codeBlockMulti` 都走它 → 多行不再压平。
- `expandHeredocJson()`：`cat > *.json <<EOF` 后紧跟的单行长 JSON（能 JSON.parse 且 >80 字符）自动美化成多行缩进。
**生成时仍应遵守**：代码用 ASCII 标点；一条逻辑命令一行；heredoc 配置文件（daemon.json/yaml）一项一行手写好，别堆单行——渲染器只是兜底。

## docx 编辑
- 编辑既有 docx 用 unpack → 改 XML → pack 流程；新建用 docx-js。
- 表格必须同时设 columnWidths 和每个 cell 的 width，否则渲染错乱。
- 中文文档默认 A4 还是 Letter 要和素材保持一致（素材为 A4 系列，按原样）。

## 域名替换遗漏
- nocoly 替换易漏：页脚、表格内 URL、PDF“内容来源”段、pdpublic 下载链接。替换后整篇复查。

## 官方文档版本路径陷阱（2026-05 核对发现）
- docs-pdop 左侧导航的组件默认展开项指向**旧版本**（MongoDB 3.4 EOL / MySQL 5.7 EOL / K8s 1.25.4 / Istio 1.18.0），但这不是推荐版。
- 实际应使用：MongoDB **4.4**、MySQL **8.0**、K8s **1.35.3**、Istio **1.29.1**（精简版与集群版同）。3.4/5.7 官方已标 (EOL)。
- 已用 web_fetch 核对：MinIO 单节点（RELEASE.2025-04-22T22-12-26Z / 9011）、MongoDB 4.4.30 单节点、MySQL 8.0.45 单节点三页，内容与本 Skill 文档一致。
- web_fetch 白名单：只能拉"用户贴过或搜索结果出现过"的精确 URL；拉精简版具体安装页时，可能需用户提供确切 URL 或先 web_search 让其进结果池。
