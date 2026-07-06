# HAP 私有部署交付文档 Skill — 使用说明

一个用于生成整套 HAP 集群私有部署交付文档的 Skill。支持品牌(mingdao/nocoly)、版本(集群精简版/标准/专业)、场景(A/B，仅标准/专业版)、是否迁移、中英文组合，内容跟随官方链接增量更新。

## 一、怎么安装

### Codex / Claude Code 本地安装

1. 从仓库复制整个目录 `skills/hap-delivery-docs/` 到本机技能目录，例如：
   - Codex/Claude 常见路径：`~/.claude/skills/hap-delivery-docs/`
   - Windows 示例：`C:\Users\<用户名>\.claude\skills\hap-delivery-docs\`
2. 进入 skill 根目录安装 Node 依赖：
   `npm install`
3. 安装 Python 依赖：
   `pip install openpyxl pymupdf python-docx`
4. 运行环境自检：
   `python doctor.py`

### Claude 上传式安装

1. 将 `skills/hap-delivery-docs/` 目录整体压缩为 zip。
2. 打开 Claude 设置（Settings）→ 找到 **Capabilities / Skills**（技能）相关入口。
3. 选择 **上传 / 导入 Skill（Upload skill）**，选中压缩包。
4. 启用该 Skill。

> 说明：导入入口的确切位置可能随 Claude 版本调整；若在设置里未直接看到 Skills 上传项，请查阅 support.claude.com 关于自定义 Skill 上传的最新说明，或确认你的账号套餐是否支持自定义 Skill。Claude 本身无法替你点击导入。

## 二、怎么用（接新客户）

1. 优先用 Excel 入参表：
   `python scripts/make_input_template.py HAP交付入参模板.xlsx`
2. 填写项目基础信息、版本/场景、节点 IP、域名端口、凭据和最后一个 Sheet「自定义项描述」。
3. 把填好的入参表交给 AI，或直接执行：
   `python scripts/gen_from_input.py 已填入参.xlsx 输出目录`
4. 固定产出顺序：
   常见故障处理 docx → 服务器资源要求 docx → 部署实施文档 docx → 运维文档 docx → 架构图 SVG → 架构图 PNG → 交付清单 docx → 凭据登记表 xlsx → 迁移文档 docx（若选）。
5. 密码不写入部署/运维正文，真实值只进入《凭据登记表》并需加密保管。

## 三、内容如何“跟着官方链接更新”

- Claude 用 **web_fetch** 拉取 source-map.md 登记的官方 URL 最新内容（已实测 docs-pd.mingdao.com / docs-pd.nocoly.com 可达）。
- 与 `reference/source-cache/` 的快照做 hash 对比：变了才重排该章节并提示“X 章节已同步官方更新”；没变则复用，省时。
- 若某次 web_fetch 不可用：自动回退用出厂快照（基于你最初上传的素材），并标注“未联网，基于 <日期> 快照”。
- **沙盒 bash 的 curl 拉不到 mingdao/nocoly（白名单限制），所以拉取一律走 web_fetch，不要用脚本联网。**

## 四、目录结构

```text
hap-delivery-docs/
├── SKILL.md                  主流程/决策树/生成顺序/自检
├── params-template.md        Markdown 参数表（兼容旧流程）
├── README.md                 本文件
├── doctor.py                 安装环境自检
├── package.json              Node 渲染依赖声明
├── reference/
│   ├── scene-a-vs-b.md       A/B 差异（标准/专业版，逐行 diff 提炼）
│   ├── streamlined-vs-cluster.md  精简版 vs 集群版差异（精简版核心依据）
│   ├── constraints.md        硬约束（命名/节点数/数据库模式/端口/清单核对）
│   ├── brand-rules.md        mingdao↔nocoly 替换
│   ├── source-map.md         章节→官方 URL + web_fetch 增量更新 + 降级
│   ├── pitfalls.md           踩坑
│   └── source-cache/         出厂快照 + 增量缓存
├── samples/
│   └── HAP_Deployment_Streamlined_Cluster_sample.docx
├── templates/                各文档结构骨架+来源映射+A/B分支点
├── assets/                   封面页眉页脚 XML + 架构图 SVG 基底
└── scripts/
    ├── make_input_template.py 生成 Excel 入参模板
    ├── gen_from_input.py     按入参一键生成全套交付件
    ├── gen_deploy.py         部署实施文档
    ├── gen_ops.py            运维文档
    ├── gen_mig.py            数据迁移文档
    ├── gen_chk.py            交付清单
    ├── gen_ref.py            常见故障/资源要求
    ├── gen_arch.py           架构图 SVG/PNG
    ├── gen_cred.py           凭据登记表
    └── render_deploy.js      Markdown → docx 渲染
```

## 五、以后怎么补模板/扩展

- 新文档类型或专业版专属模板：放 `templates/`，在 `SKILL.md` 生成顺序登记。
- 官方链接变动：改 `source-map.md`。
- 新踩坑/新约束：追加 `pitfalls.md` / `constraints.md`。
- 新增品牌或域名规则：改 `brand-rules.md`。
- 补新素材当出厂快照：`python scripts/fetch_diff.py commit <key> --content-file <文本>`。

## 六、依赖（生成环境）

- Node.js + npm，执行 `npm install` 安装 `docx`
- Python 包：`openpyxl`、`pymupdf`、`python-docx`
- Windows 推荐字体：微软雅黑、Consolas
- 生成前可用 `python doctor.py` 检查环境是否就绪
