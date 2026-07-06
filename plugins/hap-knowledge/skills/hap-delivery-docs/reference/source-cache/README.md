# source-cache 说明（务必先读）

本目录是**出厂快照 + 增量缓存**，性质和使用红线如下。

## 这是什么
- `<key>.json`：每个 key 一条记录，含 `url / hash / fetched_at / snapshot`。
- 出厂快照（deploy_sceneA / deploy_sceneB / deploy_streamlined / operations / migration / checklist）：sceneA/B/operations/migration/checklist 来自**用户最初上传的真实素材**（示例客户项目）；deploy_streamlined 来自重构后的精简版部署文档（已脱敏为示例值），均作为离线兜底底料与 diff 基线。

## 使用红线（重要）
快照是**历史素材原貌**，里面包含不可照抄进新文档的内容：
1. **客户名占位**（快照中已脱敏为"示例客户"）—— 新文档客户名只取自参数表，且只进交付清单正文，不要照抄快照里的占位名。
2. **真实本地路径**（如 `D:\HAP交付\...`）—— 不得写入任何新交付文档。
3. **旧端口口径**（如 MinIO “统一 9000”、文件名带“场景A/未开启Swarm”）—— 已被新标准取代：
   - MinIO 端口一律 9011-9014（见 reference/scene-a-vs-b.md）。
   - 文件名不带场景/客户名（见 reference/constraints.md A）。
4. **旧文件名**（带“场景A”“未开启Swarm”）—— 仅作历史参考，新产物按 constraints.md 命名。

## 正确用法
- 把快照当作**结构与话术参考 + 离线兜底内容**；生成时务必：
  - 用参数表的值替换所有 IP/域名/客户名/路径；
  - 按新标准修正端口（9011-9014）与命名（去场景/去客户名）；
  - 能联网时用 web_fetch 拉官方最新内容覆盖快照中过时的技术细节。
- 用 `scripts/fetch_diff.py compare/commit` 维护 hash 与更新。
