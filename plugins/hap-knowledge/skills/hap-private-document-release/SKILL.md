---
name: hap-private-document-release
description: HAP Private Document 更新发布 SOP（标准流程）。从 Jenkins 构建到写入「研发管理-发布-微服务」工作表并核验的端到端发布流程。触发：用户提到"发布微服务""更新发布""更新 hc/ophc""HAP Private Document 更新""触发 document 构建并上线""按发布 SOP 走""走标准发布流程"等。涉及提交身份、Jenkins 用户名/token 等认证信息时，一律提示用户当场授权或输入，绝不硬编码——本 skill 可多人多机共用。
---

# HAP Private Document 更新发布 SOP（标准流程）

Jenkins 构建 → 取镜像值 → 写「研发管理 → 发布 → 微服务」工作表 → 工作流自动发布 → 读回核验。

> 本 skill 不含任何账号、邮箱、token 等个人凭据，均由执行者当场提供；这些只存在各自本机记忆里。

## 初次使用准备（首次必做，缺一不可）

第一次在某仓库/某会话执行前，先确认并向用户索取以下两项，缺失则停下来让用户填写或授权：

1. **提交身份（commit author）**：检查目标仓库 local 身份
   ```bash
   git -C <repo> config --local user.email
   ```
   若为空或与用户的 sourcecode 账号不符，提示用户给出其姓名/邮箱后设置（注意：全局身份可能是别的账号，会被继承盖错，必须在本仓库 local 覆盖）：
   ```bash
   git -C <repo> config --local user.name  "<用户提供的名字>"
   git -C <repo> config --local user.email "<用户提供的邮箱>"
   ```
2. **Jenkins 凭据**：向用户索取其 Jenkins **登录用户 id**（注意是用户 id，不是邮箱；带域名可能 500）和 **API token**，或让用户用 `! <命令>` 自行运行带凭据的 curl。凭据仅在本次会话内存使用，不写盘、不写入 skill。

两项就绪后再进入下面的步骤。

## 认证（每次都要用户提供，不硬编码）

- **Jenkins**：`https://nextci.mingdao.net/`，basic-auth 用 `<JENKINS_USER>:<TOKEN>`，由用户提供。
- **HAP MCP**：若调用返回 `10001 Http Headers verification failed`，是 token 过期，按本机已有的 HAP MCP 自修流程处理（node reauth → kill mcp-remote → 让用户 `/reload-plugins`）；本机无该流程则提示用户走 `/hap-mcp:setup`。

## 步骤

### 1. 触发 Jenkins 构建
前置：代码已推送目标分支（HAP_Document 远端走 sourcecode.mingdao.net）。
```bash
CRUMB=$(curl -s -u "$JENKINS_USER:$TOKEN" "https://nextci.mingdao.net/crumbIssuer/api/json" | grep -o '"crumb":"[^"]*"' | cut -d'"' -f4)
curl -u "$JENKINS_USER:$TOKEN" -H "Jenkins-Crumb: $CRUMB" -X POST \
  "https://nextci.mingdao.net/job/<job>/buildWithParameters?BRANCH=origin/<branch>"
```
BRANCH 需带 `origin/` 前缀。轮询 `/job/<job>/lastBuild/api/json` 至 `building:false`、`result:SUCCESS`。

### 2. 从控制台尾部取值
- 末尾出现 `{"success":true}` 才算成功（`error_code:1` 是发消息接口返回，与构建无关）。
- 镜像串形如 `hub.mingdao.com/private/<svc>:<tag>`，按**最后一个冒号**切：服务=`<svc>`、版本号=`<tag>`（YYYYMMDD_HHMM）。

### 3. 写微服务工作表（HAP MCP `create_record`）
appId `86892856-1fb7-4cee-b4a9-36caa9e8798a`，worksheet `5ba9e096ca6edd0001c9d4da`。

| 字段 | ID | 取值 |
|---|---|---|
| 更新的服务（关联） | `5e22b0e044a07d00010e102d` | `/hc`→hc-private(`ab28007a-36e1-4d2d-8e1f-6fb17ca28e92`)、`/ophc`→ophc-private(`3bf1c547-1479-4723-bcad-4c00c5e8589b`)。其它服务先查服务列表 `5dd7b13a44d0ca000162e790` 取 rowId |
| 服务版本号 | `5bbef4c8442bf3ca1009e7f6` | 镜像 tag |
| 更新环境（多选） | `5ba9e0d4442bf3b958fa9eab` | 用户指定：生产/梅花/沙盒/沙盒2，传选项值数组如 `["生产"]` |
| 紧急程度（评分） | `5da7fde89da28200014ce5fb` | 用户指定 1-5，传字符串如 `"3"` |
| 版本（关联） | `5e2298bd681ea5000146c199` | **动态获取当前默认发布版本**：查版本规划 `5cc5907771f24d00018030f7` 取 rowId；**查询必带 viewId `5cc5907771f24d00018030f8`**，否则报 430028；标题字段 `5cc590776f3c6e0001e9b2d4`。不要硬编码示例版本号，执行时优先取该视图下当前 HAP 主发布版本（通常为最新已发布 HAP 版本；当前核验值为 `V12.3.0`，rowId `3fc0adc8-d414-42c0-94ca-9dff1d7cd6b2`），如表内版本变化则以实时查询结果为准 |
| 更新说明 | `5c77a4d1442bf213144e35ad` | 默认 `<动态版本名> bugfix`，例如实时查到 `V12.3.0` 则填 `V12.3.0 bugfix` |

**常用默认值**（用户不另行说明时以此为准，执行者可按各自约定调整）：
| 字段 | ID | 默认 |
|---|---|---|
| 集群（多选） | `617fc605a0673108fbc4ed66` | 默认 |
| 配置（单选） | `5bbee773442bf3ca1009e510` | 否 |
| Redis/Kafka（单选） | `62a7f157fe536211a3ab871b` | 否 |
| 服务更新状态（单选） | `5bac8d88442bf3b070e3436a` | 未更新 |

`triggerWorkflow=true`（走镜像 Tag 预检 + 后续发布流程）。这是**真实生产更新申请**，建成功后工作流/运维据此操作生产，执行前向用户确认无误。

### 4. 读回核验（`get_record_details`，参数名是 `row_id`）
看：「服务更新状态」是否被工作流改写为"已更新"、对应环境字段（如「公网更新」）是否"更新成功"、`_processStatus` 是否有审批挂起。
hc/ophc 这类 nginx 文档站属可自动更新，预检通过后通常 1 分钟内直通完成；卡住则看流程节点。
