# HAP 升级指南（集群模式）

**升级路径：** `{当前版本}` → `{目标版本}`
**部署模式：** 集群模式（Kubernetes）
**服务器架构：** {AMD64 / ARM64}
**服务器网络：** {可访问互联网 / 离线}
**文档生成日期：** {YYYY-MM-DD}

---

## 提前准备

> 建议在正式开始升级操作前，先完成资源准备。此处只整理本次升级实际最终会用到的资源。
> 同类组件若跨多个版本被重复要求升级，只保留最终目标版本，并尽量给出对应的镜像拉取命令。

### 若服务器可访问互联网

保留本小节时，删除下方“若服务器离线”小节。

在对应节点提前拉取本次升级最终会用到的镜像。例如：

```bash
# HAP 微服务镜像
crictl pull registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hap:{目标版本号}

# 如果本次升级最终还需要文档预览、扩展服务或其他镜像，在这里继续补充最终版本的拉取命令
# crictl pull registry.cn-hangzhou.aliyuncs.com/mdpublic/xxx:{最终版本号}
```

```bash
crictl images | grep mingdaoyun
```

> 不要在本节输出“v6.2.0 -> 2.0.0，v6.2.4 -> 2.0.1”这类历史轨迹写法，应直接写最终要准备到什么版本。

### 若服务器离线

保留本小节时，删除上方“若服务器可访问互联网”小节。

请在可访问互联网的机器上提前下载本次升级实际最终需要的全部离线文件，并上传到对应服务器：

| 文件 | 下载链接 |
|------|----------|
| HAP 微服务离线包（按架构保留） | `{按实际架构填写 HAP 微服务离线包链接}` |
| 其他必需镜像或离线资源 | `{根据本次升级实际步骤补全，未用到则删除该行}` |
| MongoDB 预置数据包 | `{若本次升级涉及该操作，则填写对应版本下载链接；否则删除该行}` |
| MongoDB 预置脚本 | `{若本次升级涉及该操作，则填写对应脚本下载链接；否则删除该行}` |

---

## 升级前准备

### 1. 数据备份

> 升级前必须完成备份，此步骤不可跳过。

### 2. 确认当前版本

```bash
kubectl get pods -n {命名空间} -o jsonpath="{range .items[*]}{.metadata.name}{'\t'}{.spec.containers[*].image}{'\n'}{end}"
```

### 3. 检查资源

- 确认各节点磁盘空间充足
- 确认控制节点可正常执行 `kubectl` 命令
- 若计划使用滚动更新，确认各微服务节点有 40% 左右的可用内存

---

## 升级步骤

### 第一阶段：升级前操作

> 这一节统一整理所有必须在微服务升级前完成的操作，按实际执行顺序排列。

#### 1. 镜像命名或配置文件修改

{若无则删除本条}

#### 2. 创建 MongoDB 数据库

{若无则删除本条。若有，合并为一次登录和一次整理后的建库清单。}

#### 3. 更新 service.yaml 或其他配置

{若无则删除本条。若有，合并所有新增项统一写入，并直接展开官方 YAML 原文。联网版和离线版都必须在各自文档内完整展示，不得互相引用。}

#### 4. MongoDB 预置数据更新

{若无则删除本条。若有，只保留最新版本的执行命令。}

### 第二阶段：升级微服务

在控制节点 `/data/mingdao/script/kubernetes` 目录下执行：

```bash
bash update.sh update hap {目标版本号}
```

如需非滚动更新，则补充 `stop.sh` 流程。

### 第三阶段：升级后操作

> 这一节统一整理所有必须在微服务升级后完成的操作，按实际执行顺序排列。

#### 1. 进入 config Pod 执行脚本

```bash
kubectl exec -it $(kubectl get pod -n {命名空间} | grep config | awk '{print $1}') -n {命名空间} -- bash
```

```bash
# 在一次进入 Pod 后，按版本从低到高执行全部脚本
# 常规文件初始化命令：
# source /entrypoint-cluster.sh && fileInit

# 如果明确使用外部 S3 对象存储，则改为：
# source /entrypoint-cluster.sh && s3fileInit
```

---

## 升级后验证

```bash
kubectl get pods -n {命名空间}
```

---

## 官方来源

- [版本发布历史](https://docs-pd.mingdao.com/version)
- [MongoDB 预置数据更新](https://docs-pd.mingdao.com/deployment/kubernetes/data/preset/mongodb)
- [微服务升级](https://docs-pd.mingdao.com/deployment/kubernetes/upgrade/hap)

---

💡 声明：内容由 AI 生成。尽管已努力确保信息的合理性，但 AI 模型仍可能产生不准确、过时或存在偏差的内容。请在执行关键操作前，务必对照[官方文档](https://docs-pd.mingdao.com)进行核实校验。
