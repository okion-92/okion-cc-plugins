# hap-private-document-release

HAP Private Document 更新发布 SOP skill，用于把 HAP 私有部署文档站相关服务按标准流程发布到「研发管理 → 发布 → 微服务」工作表，并核验后续工作流发布状态。

## 适用场景

当需要发布或更新 HAP Private Document 相关微服务时使用，例如：

- 更新 `hc-private`
- 更新 `ophc-private`
- 触发 document Jenkins 构建并上线
- 按 HAP Private Document 发布 SOP 创建微服务更新记录

常见触发说法：

- “发布微服务”
- “更新 hc/ophc”
- “HAP Private Document 更新”
- “触发 document 构建并上线”
- “按发布 SOP 走”

## 执行流程

1. 确认目标仓库的 Git 提交身份。
2. 向执行者索取 Jenkins 用户 ID 和 API token。
3. 触发 Jenkins 构建并等待成功。
4. 从构建日志提取镜像 tag。
5. 调用 HAP MCP 创建「研发管理 → 发布 → 微服务」记录，并设置 `triggerWorkflow=true`。
6. 读回记录，核验服务更新状态、环境更新结果和流程状态。

## 版本字段规则

创建微服务记录时，`版本` 字段必须动态获取，不要硬编码示例版本号。

查询位置：

- appId: `86892856-1fb7-4cee-b4a9-36caa9e8798a`
- 版本规划 worksheet: `5cc5907771f24d00018030f7`
- viewId: `5cc5907771f24d00018030f8`
- 标题字段: `5cc590776f3c6e0001e9b2d4`

执行时取当前 HAP 主发布版本。最近一次核验值：

- 版本名: `V12.3.0`
- rowId: `3fc0adc8-d414-42c0-94ca-9dff1d7cd6b2`

如果版本规划表发生变化，以实时查询结果为准。`更新说明` 默认使用 `<动态版本名> bugfix`，例如 `V12.3.0 bugfix`。

## 安全和确认

这是会触发真实发布流程的生产更新申请。执行前必须向用户确认：

- 服务名是否正确
- 镜像 tag 是否正确
- 更新环境是否正确
- 紧急程度是否正确
- 更新说明是否符合本次发布内容

Jenkins token、HAP session、账号密码等凭据不写入仓库，不写入 skill，只在执行时由用户提供或使用本机已配置的 HAP MCP。
