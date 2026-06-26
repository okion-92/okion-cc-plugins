# okion-cc-plugins

**okion 的 Claude Code 插件市场(marketplace)。** 一条命令安装,内容自动更新。

一个仓库 = 一个 marketplace + 多个插件。每个插件是一组技能(skills)。

```
okion-cc-plugins/
├── .claude-plugin/
│   └── marketplace.json          # 市场清单:列出所有插件
├── .github/workflows/
│   └── sync-skills.yml           # 每 4h 把私有源的 skills 同步进 hap-knowledge
├── README.md
└── plugins/
    ├── hap-knowledge/            # 插件①:HAP 私有部署知识(自动同步)
    │   ├── .claude-plugin/plugin.json
    │   ├── .synced-skills        # 由同步管理的 skill 名单
    │   └── skills/<各skill>/
    └── okion-private/            # 插件②:okion 自用技能(手动维护)
        ├── .claude-plugin/plugin.json
        └── skills/
```

---

## 安装

```
/plugin marketplace add okion-92/okion-cc-plugins
/plugin install hap-knowledge@okion-cc-plugins      # 安装 HAP 知识插件
/plugin install okion-private@okion-cc-plugins       # 安装自用插件
```

- 技能带插件命名空间,例如 `/hap-knowledge:hap-upgrade`、`/hap-knowledge:hap-deployment-troubleshooter`。
- 取最新内容:`/plugin marketplace update`(插件未固定 version,跟随最新提交)。

## 插件清单

| 插件 | 内容 | 维护方式 |
|---|---|---|
| `hap-knowledge` | HAP 私有部署知识(部署排障、升级等) | **自动**:每 4h 从私有源 `hap-private-knowledge/skills/` 同步 |
| `okion-private` | okion 自用/私有技能 | **手动**:直接往 `plugins/okion-private/skills/` 放目录提交 |

---

## hap-knowledge 的自动同步怎么工作

[sync-skills.yml](.github/workflows/sync-skills.yml) 每 4 小时(`cron: 0 */4 * * *`)把
[okion-92/hap-private-knowledge](https://github.com/okion-92/hap-private-knowledge)(私有)的 `skills/`
镜像进 `plugins/hap-knowledge/skills/`:**增/改/删都跟上**。

- **白名单保护**:只动记在 `.synced-skills` 里的 skill(=源仓库来的)。你**手动**往 `hap-knowledge/skills/` 放的目录(不在名单里)永不被同步碰。
  - 唯一注意:别让手动 skill 跟源仓库里的 skill 重名,否则会被覆盖。
- **立即同步**:不想等 4h,去 Actions → sync-skills → Run workflow。
- **延迟语义**:每 4h 定时,所以源更新后**最长约 4 小时**同步到。要更快就把 cron 调密。

源仓库是私有的,所以同步用一个密钥 `SRC_PAT` 鉴权 clone(见下)。插件仓库本身是公开的,skills 是物理拷贝进来的,因此**别人下载插件不需要任何源仓库权限**。

## 加新东西

- **给 okion-private 加技能**:`plugins/okion-private/skills/<技能名>/SKILL.md`(+ 可选 `data/`、`references/`),提交即可。
- **加一个全新插件**:`plugins/<插件名>/` 下放 `.claude-plugin/plugin.json` + `skills/`,再到 `marketplace.json` 的 `plugins` 数组加一项 `{ "name": "<插件名>", "source": "./plugins/<插件名>" }`。

> 提交后无需手动做 Codex 兼容——见下。

## Codex 兼容(自动)

每个 skill 除了 Claude Code 用的 `SKILL.md`,还自动带两份 Codex 兼容文件,由 [scripts/gen-codex.mjs](scripts/gen-codex.mjs) 从 `SKILL.md` 的 frontmatter 生成:

- `agents/openai.yaml` — 描述符(display_name / short_description / default_prompt / policy)。**缺则补,已有的手工版不覆盖**。
- `AGENTS.md` — 每个 skill 一份 + 每个插件根一份(列出该插件所有技能),Codex 在该目录下工作时自动读取。**每次按 SKILL.md 重生成**。

两条触发,标准一致、全自动:

| 场景 | 谁来生成 | 时延 |
|---|---|---|
| 同步来的 skill(hap-knowledge) | `sync-skills.yml` 镜像后跑生成,同一次提交 | 随同步,≤4h |
| **手动**加的 skill(任意插件) | `codex-compat.yml` 在 push 到 `plugins/**` 时跑生成 | 立即(<1 分钟) |

所以你以后手动往任何插件加 skill,**只写 `SKILL.md`、提交即可**,Codex 兼容文件会自动补齐,标准与同步来的完全一致。

---

## 维护:把 SRC_PAT 换成更安全的 fine-grained token(推荐)

当前 `SRC_PAT` 存的是一个经典 PAT(权限偏宽)。换成**只读、只授权源仓库**的 fine-grained token 更稳妥。**只需替换密钥值,不用改 workflow。**

1. GitHub → 头像 → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**。
2. 配置:
   - **Resource owner**:`okion-92`
   - **Repository access**:**Only select repositories** → 勾 `hap-private-knowledge`
   - **Permissions** → **Repository permissions** → **Contents**:**Read-only**(Metadata 会自动 Read-only)
   - **Expiration**:按需(到期需重配)
3. **Generate** 后复制 token(只显示一次)。
4. 回到本仓库 → **Settings** → **Secrets and variables** → **Actions** → 找到 `SRC_PAT` → **Update** → 粘贴新值保存。
5. 去 Actions → sync-skills → **Run workflow** 跑一次,确认仍能成功 clone。

> token 到期后同步会开始失败(clone 鉴权失败),按上面步骤重新生成并更新 `SRC_PAT` 即可。
