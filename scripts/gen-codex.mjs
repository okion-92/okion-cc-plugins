// 给 plugins/*/skills/* 生成 Codex 兼容文件：
//   - agents/openai.yaml  （缺则补，不覆盖已有的手工版）
//   - AGENTS.md           （每次按 SKILL.md 重生成，幂等）
// 以及每个插件根的 AGENTS.md（列出该插件所有技能）。
// 数据源是各 skill 的 SKILL.md frontmatter（name / description）。
import { readdirSync, readFileSync, writeFileSync, existsSync, mkdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const PLUGINS_DIR = 'plugins';

// 从 SKILL.md 取 frontmatter 的 name / description（description 为单行，沿用本库约定）
function parseFrontmatter(md) {
  const m = md.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  const fm = m ? m[1] : '';
  const pick = (k) => {
    const r = fm.match(new RegExp(`^${k}:\\s*(.*)$`, 'm'));
    return r ? r[1].trim().replace(/^["']|["']$/g, '') : '';
  };
  return { name: pick('name'), description: pick('description') };
}

// 取第一句作为短描述（按中英句号/换行断），限长
function firstSentence(desc) {
  const cut = desc.split(/。|\.\s|\n|；/)[0].trim();
  return (cut.length > 120 ? cut.slice(0, 117) + '…' : cut) + (cut.endsWith('。') ? '' : '。');
}

function genOpenaiYaml(name, desc) {
  const display = name.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  const short = firstSentence(desc).replace(/"/g, '\\"');
  return `interface:
  display_name: "${display}"
  short_description: "${short}"
  default_prompt: "Use $${name} to handle the request."

policy:
  allow_implicit_invocation: true
`;
}

function genSkillAgents(name, desc) {
  return `# ${name}

> Codex / Claude Code 兼容入口。本目录是 \`${name}\` 技能。

${firstSentence(desc)}

完整说明见 \`SKILL.md\`；参考资料在 \`data/\`、\`references/\`、\`assets/\`（如有）。
`;
}

function genPluginAgents(plugin, skills) {
  const lines = skills.map((s) => `- **${s.name}** — ${firstSentence(s.description)}`).join('\n');
  return `# ${plugin} — 技能清单

本插件包含以下技能（Codex / Claude Code 兼容）。各技能详情见对应目录的 \`SKILL.md\` / \`AGENTS.md\`：

${lines}
`;
}

const isDir = (p) => existsSync(p) && statSync(p).isDirectory();
let wrote = 0;

for (const plugin of (isDir(PLUGINS_DIR) ? readdirSync(PLUGINS_DIR) : [])) {
  const skillsDir = join(PLUGINS_DIR, plugin, 'skills');
  if (!isDir(skillsDir)) continue;
  const skills = [];
  for (const skill of readdirSync(skillsDir)) {
    const dir = join(skillsDir, skill);
    const skillMd = join(dir, 'SKILL.md');
    if (!isDir(dir) || !existsSync(skillMd)) continue;
    const { name, description } = parseFrontmatter(readFileSync(skillMd, 'utf8'));
    if (!name) { console.warn(`skip (no name in frontmatter): ${skillMd}`); continue; }
    skills.push({ name, description, dir });

    // agents/openai.yaml — 缺则补，不覆盖
    const agentsDir = join(dir, 'agents');
    const yaml = join(agentsDir, 'openai.yaml');
    if (!existsSync(yaml)) {
      mkdirSync(agentsDir, { recursive: true });
      writeFileSync(yaml, genOpenaiYaml(name, description));
      wrote++; console.log('+ openai.yaml', yaml);
    }
    // AGENTS.md — 每次重生成（幂等）
    writeFileSync(join(dir, 'AGENTS.md'), genSkillAgents(name, description));
  }
  if (skills.length) {
    writeFileSync(join(PLUGINS_DIR, plugin, 'AGENTS.md'), genPluginAgents(plugin, skills));
    console.log(`plugin ${plugin}: ${skills.length} skills`);
  }
}
console.log(`done. new openai.yaml: ${wrote}`);
