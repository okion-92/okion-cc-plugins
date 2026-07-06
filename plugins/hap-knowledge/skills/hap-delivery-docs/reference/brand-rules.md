# 品牌替换规则（mingdao ↔ nocoly）

第 1 层分类。默认品牌为 **mingdao**；若客户要求 **nocoly**，按下表替换文档中**所有** `*.mingdao.com` 域名，并从 nocoly 对应站点拉取最新内容。

## 替换规则：子域前缀保留，主域 mingdao → nocoly

| mingdao（默认） | nocoly（替换后） | 用途 |
|---|---|---|
| `docs-pd.mingdao.com` | `docs-pd.nocoly.com` | 单机/通用文档（两个 PDF 来源） |
| `docs-pdop.mingdao.com` | `docs-pdop.nocoly.com` | 集群部署文档来源（部署文档各章节） |
| `pdpublic.mingdao.com` | `pdpublic.nocoly.com` | 离线安装包下载（仅域名替换，内容不重排） |

通用正则：把任意 `XXX.mingdao.com` 替换为 `XXX.nocoly.com`（保留子域前缀 XXX，只换主域）。

## 注意

- `mingdaocloud.com`（如 `alifile.mingdaocloud.com` 翻译资源）、`marketplace.mingdao.com`（云市场）若出现：
  - 本套集群文档中**未出现** marketplace；翻译资源 `alifile.mingdaocloud.com` 出现在故障处理 PDF。
  - 替换策略：与品牌强相关的主域 `mingdao.com` 一律按上表换 nocoly；`mingdaocloud.com` 这类**第三方/CDN 域名**默认**保持不变**，除非用户明确要求一并替换。生成时如遇到 `mingdaocloud.com`，先标记并询问用户。
- 镜像仓库地址 `registry.cn-hangzhou.aliyuncs.com/mdpublic/...` 是阿里云镜像，**不替换**。
  - 注：nocoly 官方文档中镜像形如 `nocoly/hap-xxx`（Docker Hub）。但本套交付文档沿用素材中的阿里云镜像地址，除非用户明确要求改用 nocoly 镜像，否则保持阿里云地址不变。
- 替换要覆盖：正文链接、“内容来源”章节、PDF 文档说明里的来源 URL、脚注/页脚中可能出现的域名。
- 替换后务必整篇复查，避免遗漏 `pdpublic`、页脚、表格内 URL。

## 拉取行为

- nocoly 模式下，source-map.md 中所有 `docs-pdop/docs-pd` 链接对应改为 nocoly 域名后再拉取最新内容。
- 若环境无法联网（见 source-map.md 的降级说明），则仅做**域名字符串替换**，内容沿用本地缓存/素材。
