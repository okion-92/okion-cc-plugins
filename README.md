# okion-cc-plugins

okion 的 **Claude Code 插件市场**(marketplace)。一条命令安装,自动更新。

```
okion-cc-plugins/
├── .claude-plugin/marketplace.json   ← 市场清单(列出所有插件)
├── .github/workflows/sync-skills.yml ← 每4h同步 hap-knowledge 的 skills
└── plugins/
    └── hap-knowledge/                 ← 插件:HAP 私有部署知识技能集
        ├── .claude-plugin/plugin.json
        ├── .synced-skills             ← 源管理的 skill 名单
        └── skills/{...}
```

## 安装

```
/plugin marketplace add okion-92/okion-cc-plugins
/plugin install hap-knowledge@okion-cc-plugins
```

技能带命名空间,如 `/hap-knowledge:hap-upgrade`。拿最新内容:`/plugin marketplace update`(plugin.json 未固定 version,跟随最新提交)。

## 加新插件

在 `plugins/` 下新建一个目录(含 `.claude-plugin/plugin.json` + `skills/`),再到 `marketplace.json` 的 `plugins` 数组加一项 `{ "name": "...", "source": "./plugins/你的插件" }` 即可。

## hap-knowledge 的技能从哪来

`plugins/hap-knowledge/skills/` 里有两类,**互不干扰**:

1. **同步来的**(记在 `.synced-skills`):每 4 小时由 [sync-skills](.github/workflows/sync-skills.yml) 从
   [okion-92/hap-private-knowledge](https://github.com/okion-92/hap-private-knowledge) 的 `skills/` 镜像——增/改/删都跟上。
2. **手动加的**:直接往 `plugins/hap-knowledge/skills/` 放目录并提交。**同步不会碰它**(不在 `.synced-skills` 名单里)。

> 唯一注意:别让手动 skill 跟源仓库里的 skill 重名,否则会被同步覆盖。

## 同步说明

- 频率:每 4h(`cron: 0 */4 * * *`),即源更新后最长约 4 小时同步到。立刻同步:Actions → sync-skills → Run workflow。
- 源仓库若改私有:`sync-skills.yml` 把 `SOURCE_REPO` 换成带 PAT 的地址,并加 `SRC_PAT` secret。
