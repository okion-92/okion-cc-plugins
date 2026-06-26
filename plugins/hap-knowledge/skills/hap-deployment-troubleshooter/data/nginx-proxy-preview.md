# Nginx / 代理 / 预览

> 由 sources/faq/ 生成，勿手改。每条 `## <slug>` 对应一个 source 文件，可在 ROUTING.md 反查。

## attachment-large-file-upload-fail — 附件功能上传大文件失败（代理层大小限制）


### 场景
协作-文件是分片上传（大文件切多片），附件字段是完整上传——附件传大文件失败基本是**代理层有上传大小限制**。

典型：上传一半报 `net::ERR_CONNECTION_RESET`（Chrome 看不出原因，换 Firefox 网络响应能看到真实报错，如腾讯云 `stgw 413 Request Entity Too Large`）。

排查：HAP 自身 nginx 代理已设 `client_max_body_size`，若前面还有云负载均衡/WAF/外层 nginx，需在**那一层**调大请求体限制（如腾讯云 CLB 配置）。

## custom-favicon-icon — 私有部署自定义 favicon 图标


### 场景
想把浏览器标签页图标换成客户自定义 favicon。

1. nginx 配置增加 location：
```nginx
location = /favicon.ico {
    root /data/www/;
}
```
2. 把自定义 `favicon.ico` 放到 `/data/www/` 下。
3. 重载：`/usr/local/nginx/sbin/nginx -s reload`

注意：
- 文件名必须为 `favicon.ico`。
- 也可放其他路径，改 location 里的 `root` 绝对路径即可。

## doc-intranet-ip-exposure — doc 2.0.0 预览避免内网 IP 暴露在前端元素


### 场景
升级 v6.2.0+ / doc 2.0.0 后，文件预览把内网 IP 暴露在前端元素里。

旧 docker-compose 集群环境，微服务 `docker-compose.yaml` 有环境变量 `ENV_MINGDAO_INTRANET_ENDPOINT`，默认是当前微服务节点内网 IP+端口。

升级到 v6.2.0+ 且 doc 同步升到 2.0.0 后，微服务把该变量传给 doc，doc 用它获取文件地址；若是内网 IP，会暴露在前端元素。

处理：`ENV_MINGDAO_INTRANET_ENDPOINT` 默认值是 `app:8880`，可**删除该环境变量**——微服务自身走 `app` 服务名能访问；doc 独立部署，需加 hosts 解析把 `app` 指向微服务 IP：
```yaml
    extra_hosts:
      - "app:<微服务节点 IP>"
```

## excel-print-signature-black — Excel 打印模板子表签名渲染成黑色 —— 升 file/sc 组件 + 清 cache 缓存（缓存不过期是关键）


### 现象
用 Excel 打印模板导出的文件，子表里几个签名（图片）渲染成纯黑色块。

### 原因
file/sc 渲染组件旧版缺陷；且 **file 缓存目录 cache 不过期** —— 即使升级到新版，旧的黑色缓存仍被命中。

### 处理
两步缺一不可：
1. **升组件到最新**（重新拉镜像）：集群客户 file 升到 **2.1.0**；单机客户 sc 升到 **3.2.0**。
2. **清 file 缓存目录 cache**（关键，否则升级也不生效）：
   - 缓存目录：集群 `/data/file/volume/cache/`；单机 mingdao 版 `/data/mingdao/script/volume/data/storage/cache/`；单机 Nocoly 版 `/data/hap/script/volume/data/storage/cache/`
   - 方式一（推荐，不停服）：`find <缓存目录> -type f -mtime +7 -delete`
   - 方式二（彻底，方式一没解决再用）：停服 → `rm -rf <缓存目录>/*` → 起服。副作用：用户再次访问若工作表缩略图多，会触发重建致 CPU 飙高卡顿

启停用官方脚本（**不要用 `docker stop` / `docker-compose stop sc`**）：
```bash
# 集群
bash /usr/local/MDPrivateDeployment/clusterMode/stop.sh
bash /usr/local/MDPrivateDeployment/clusterMode/start.sh
# 单机（mingdao 版 / Nocoly 版命令一致）
bash /usr/local/MDPrivateDeployment/service.sh stopall
bash /usr/local/MDPrivateDeployment/service.sh restartall
```

### 核验
重新用 Excel 打印模板导出，子表签名图片正常显示（非黑块）。若仍黑，确认缓存目录已清干净（方式一→方式二）。

## ldoc-font-cache-multi-replica — ldoc(LibreOffice) 预览字体丢失 — 启动前加载字体缓存


### 场景
挂载字体后部分文件预览出现字体丢失，pod 资源监控常见 CPU 100% 占满。解决：启动 ldoc 前加载字体缓存，有助于正确识别处理中文字体。

集群在 ldoc 容器启动命令里先跑 `mkfontscale && mkfontdir && fc-cache -fv` 再启动：
```yaml
    spec:
      containers:
      - name: ldoc
        image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-ldoc:2.0.2
        command: ["/bin/sh", "-c"]
        args: ["mkfontscale && mkfontdir && fc-cache -fv && java -jar /app.jar"]
        resources:
          limits:
            cpu: "2"
            memory: 4Gi
```

> 多副本 cookie-ip-hash 粘性配置另见原记录的金山文档链接（无权限未抓取）。

## message-red-dot-not-clear — 消息侧栏红点计数不消失


### 场景
消息侧栏红点计数不消失 / 计数消除不掉。

三种可能原因（逐一排查）：
1. 网络层不支持 websocket（需网络层放通 websocket 协议）。
2. 消息服务异常（重启 `chatmq`、`chatgrpc` 服务）。
3. 代理层未配置 `location ~ /mds2`（nginx 代理加该 location）。

### 计数消除不掉（旧版本 bug，record 145d740c）
属于已修复的 bug，旧版本临时处理：进容器后重启 chatgrpc。
```bash
docker exec -it $(docker ps | grep community | awk '{print $1}') bash
source /entrypoint.sh && chatgrpcShutdown
```

## nginx-1.29-host-port-lost — 附件预览失败 / 接口端口丢失 —— nginx 1.29.4 起按 RFC3986 丢端口（用 $request_port 修）


### 现象
非默认端口部署（如 `<客户域名>:8888`），附件无法预览，F12 看到预览接口 URL 端口丢失（少了 `:8888`），弹窗"下载失败"。

### 原因
nginx **1.29.4**（2025-12-09）起按 RFC 3986 严格校验 Host/Port（CHANGES："validation of host and port ... changed to follow RFC 3986"），`$http_host` 在非默认端口下不再附带端口。修复变量 `$request_port` 自 **1.29.3**（2025-10-28）起可用 —— 故修复下限是 1.29.3、故障触发下限是 1.29.4，是不同版本点。

### 处理
反代 Host 头补回真实端口，reload：
```nginx
proxy_set_header Host $http_host:$request_port;
```
更稳的写法（用 `$host` 避免 client 篡改 Host 头被透传）：
```nginx
proxy_set_header Host $host:$request_port;
```

> **用 `$request_port`，不要用 `$server_port`**。`$server_port` 是 nginx 自己 `listen` 的端口，多层代理或对外端口≠监听端口时会拼错；`$request_port`（1.29.3+ 新增）才是客户端请求里的真实端口，正是为此场景引入。

### 核验
reload 后 F12 看预览接口 URL 端口完整（带 `:8888`），附件能正常预览。

### 官方依据
- `$request_port` 变量文档（标 `(1.29.3)`）：https://nginx.org/en/docs/http/ngx_http_core_module.html#var_request_port
- 引入版本 CHANGES（nginx 1.29.3）：https://nginx.org/en/CHANGES
- Host/端口校验收紧背景：https://blog.nginx.org/blog/nginx-open-source-1-29-3-and-1-29-4

## nginx-forward-proxy — 用 Nginx 实现正向代理（让内网机器经代理访问互联网）


### 现象 / 场景
Server A 可访问互联网、Server B 不能。在 Server A 上部署 Nginx 正向代理，Server B 配全局代理后即可经 A 访问互联网。本文用 Nginx 实现正向代理（依赖 `ngx_http_proxy_connect_module`，附件 nginx-1.22.1 安装包已编译好该模块）。

### 处理
1. 将 `nginx-1.22.1.tar.gz`（已带 `ngx_http_proxy_connect_module`）解压到 Server A 的 `/usr/local/` 下。
2. 配置主文件 `/usr/local/nginx/conf/nginx.conf`（按常规 Nginx 主文件配置）。
3. 创建 `/usr/local/nginx/conf/conf.d/`，将附件 `forward_proxy.conf` 上传到该目录下。
4. 启动 nginx 即可。

正向代理配好后，在 Server B 上用 curl 走代理测试能否访问互联网：
```bash
curl --proxy http://<ServerA_IP>:<代理端口> https://<外网地址>
```

> 附件中另含 `nginx1.22.1-glibc2.17.tar.gz` / `nginx1.26.1-glibc2.17.tar.gz`（glibc2.17 兼容版）与源码 `nginx-1.22.1.tar.gz`，按目标系统 glibc 版本选用。

### 核验
Server B 经代理 curl 外网地址返回正常响应即配置生效。

## nginx-log-analysis-commands — Nginx 日志过滤分析帮助命令


### 场景
要从 nginx 访问日志统计慢请求 / Top 路径排查问题。

### 处理
日志字段以 `|` 分隔（`$3`=请求 URL，`$NF`=请求时长秒）。

```bash
# 按请求方法/路径归集 Top20（去掉 ? 后参数）
tail -n 10000 access.log | awk -F'|' '{print $3}' | awk -F'?' '{print $1}' | sort | uniq -c | sort -n | tail -n20

# 过滤请求时长超过 10 秒的日志
tail -n 10000 access.log | grep -v /mds2/ | awk -F'|' '$NF>10{print $3,$NF}'

# 统计每秒请求日志数量（取时间戳前 21 字符）
awk '{print $3}' mdy.log | cut -c 1-21 | uniq -c | sort -n | tail -n 10
```

## nginx-show-icp-beian — 登录页底部显示网站备案号（外部 nginx sub_filter）


### 场景
在登录页底部显示 ICP/公安备案号，用外部 nginx 的 `sub_filter` 改写响应内容。备案号、备案链接按实际替换。

> 必须在 `location / {}` 和 `location ~ /mds2 {}` 两处下方都配置，否则部分页面不显示。
> 旧写法（`location = /` + 无 `Accept-Encoding ""`）在新版本已失效，统一用下面带 `location ~ (/$|/network)` 的新版。

### 通用要点
- `proxy_set_header Accept-Encoding "";` 必加（否则上游 gzip 压缩导致 sub_filter 不生效）。
- 定位：`position: absolute; top: 640px;`（范围 640~660）；**开启企微扫码时改 740**。

### 仅显示 ICP 备案
```nginx
location ~ (/$|/network) {
    proxy_set_header Accept-Encoding "";
    sub_filter '</body>' '<p style="position:absolute;top:640px;padding:20px 0;text-align:center;bottom:20px;width:100%;"><a target="_blank" href="https://beian.miit.gov.cn">沪ICP备20220823号-1</a></p></body>';
    proxy_pass http://mdy;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### ICP + 公安备案（带公安图标）
```nginx
location ~ (/$|/network) {
    proxy_set_header Accept-Encoding "";
    sub_filter '</body>' '<p style="position:fixed;bottom:20px;width:100%;text-align:center;padding:10px 0;margin:0;font-size:12px;line-height:20px;z-index:9999;"><img src="https://beian.mps.gov.cn/img/logo01.dd7ff50e.png" style="width:20px;height:20px;vertical-align:middle;margin-right:5px;display:inline-block;" alt="备案图标"/><a target="_blank" href="https://beian.miit.gov.cn">沪ICP备20220823号-1</a>&nbsp;&nbsp;<a target="_blank" href="https://www.beian.gov.cn/portal/registerSystemInfo/" style="color:#666;text-decoration:none;vertical-align:middle;">沪公网安备 31010502011103号</a></p></body>';
    proxy_pass http://mdy;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```
> 只要公安/只要 ICP 时删掉对应 `<a>` 段即可。改完 `nginx -s reload`。

## nginx-subs-filter-not-working — Nginx subs_filter 不生效（gzip 压缩导致）


### 场景
平台版替换默认指向 www.mingdao.com / help.mingdao.com 的链接时，代理层 subs_filter 不生效——上游 gzip 压缩了内容。

server 块：
```nginx
subs_filter_types *;
subs_filter 'mingdao.com' '<自定义域名>' igr;
subs_filter 'help.mingdao.com' '<自定义help域名>' igr;
```
location 块（关键：清空 Accept-Encoding 让上游不压缩才能替换）：
```nginx
location / {
    proxy_set_header Accept-Encoding "";
}
```
改后登出重登或 F12 禁用缓存刷新测试跳转。

## preview-fail-x-forwarded-proto — 预览文件失败 —— 未获取到访问协议(X-Forwarded-Proto / $scheme)


### 现象
预览失败，控制台报错，通常是没有通过 `X-Forwarded-Proto` 头获取到服务的访问协议导致。
（端口丢失导致的预览失败是另一回事，见 nginx 1.29 Host 头丢端口的处理。）

### 处理
- **Nginx 代理转发**：将 `$scheme` 改为实际协议 `https`/`http`。
- **阿里云 SLB 等负载均衡做 HTTPS 卸载**：在 监听器 → 高级配置 中勾选 `X-Forwarded-Proto` 字段。

### 核验
重载配置后预览正常，请求头中 `X-Forwarded-Proto` 与实际访问协议一致。

## prometheus-subpath-proxy — Prometheus 子路径反代供页面访问


### 场景
要用 nginx 子路径反代 Prometheus 供页面访问。

```nginx
location ~ /privatedeploy/mdy/monitor/prometheus/ {
    rewrite ^/privatedeploy/mdy/monitor/prometheus/(.*) /$1 break;
    proxy_pass http://localhost:9090;
    proxy_set_header Host $host;
}
```
访问地址：`<访问地址>/privatedeploy/mdy/monitor/prometheus/graph`

## prometheusalert-send-alerts-config — PrometheusAlert 安装与配置告警发送（Alertmanager + 企微模版）


### 场景
私有部署监控需要把 Prometheus 告警通过 PrometheusAlert 转发到企业微信机器人。本文给出 PrometheusAlert 安装、Alertmanager 路由、Prometheus 告警规则、企微告警模版的完整配置。

### 处理

#### 1. 安装 PrometheusAlert
```bash
# 下载需要版本
https://github.com/feiyu563/PrometheusAlert/releases/download/v4.8.2/linux.zip

# 解压后移动至安装目录
unzip linux.zip && mv linux /usr/local/prometheusalert

# 添加执行权限
chmod +x /usr/local/prometheusalert/PrometheusAlert

# 配置启动、停止脚本
cat > /usr/local/prometheusalert/start_PrometheusAlert.sh <<EOF
cd /usr/local/prometheusalert && nohup ./PrometheusAlert &
EOF

cat > /usr/local/prometheusalert/stop_PrometheusAlert.sh <<EOF
kill $(pgrep -f 'PrometheusAlert')
EOF

# 启动
bash /usr/local/prometheusalert/start_PrometheusAlert.sh

# 启动后可使用浏览器打开以下地址查看：http://127.0.0.1:8080
# 默认登录帐号和密码在安装目录 conf/app.conf 中有配置
```

#### 2. 配置 Alertmanager
```yaml
route:
  group_by: ['alertname']
  group_wait: 30s # 首次收到一个 group 告警时会先等待 group_wait 时长再发送该 group (收集属于同一 group 的其它警报，一起发送)
  group_interval: 2m # 收到相同 group 的新告警，会等待 group_interval 时长之后让该 group 解除冷却，再发送一次消息
  repeat_interval: 4h # 当一个 group 的警报一直存在时，要至少冷却 repeat_interval 时长才能重复发送该 group
  receiver: 'workweixin'
receivers:
  - name: 'workweixin'
    webhook_configs:
      - url: 'http://127.0.0.1:8080/prometheusalert?type=wx&tpl=prometheus-wx&wxurl=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=<企微机器人key>'
        send_resolved: true
```
- url 中 wxurl=xxx 注意替换为实际的企微机器人地址

#### 3. 配置 Prometheus 告警规则
```yaml
groups:
- name: 容器CPU
  rules:
  - alert: 微服务容器 CPU 使用率较高
    expr: irate(container_cpu_usage_seconds_total{container!="",pod!="",namespace="default"}[2m])*100 > 500
    for: 3m
    labels:
      level: Warning
    annotations:
      description: "容器名: {{$labels.pod}}, CPU 使用率: {{ $value | printf \"%.2f\" }}%"

- name: 容器MEM
  rules:
  - alert: 微服务容器内存占用较高
    expr: container_memory_working_set_bytes{namespace="default"} / 1073741824 > 5
    for: 3m
    labels:
      level: Warning
    annotations:
      description: "容器名: {{$labels.pod}}, 内存占用: {{ $value | printf \"%.2f\" }}G"
```

#### 4. 配置 PrometheusAlert 企微告警模版
```markdown
{{ range $k,$v:=.alerts }}{{if eq $v.status "resolved"}}## Prometheus-恢复消息
> 事件: **{{$v.labels.alertname}}**
> 告警级别: {{$v.labels.level}}
> 开始时间: {{GetCSTtime $v.startsAt}}
> 结束时间: {{GetCSTtime $v.endsAt}}
> 主机: {{$v.labels.instance}}
> <font color="info">**事件详情: {{$v.annotations.description}}**</font>
{{else}}## Prometheus-告警消息
> 事件: **{{$v.labels.alertname}}**
> 告警级别: {{$v.labels.level}}
> 开始时间: {{GetCSTtime $v.startsAt}}
> 主机: {{$v.labels.instance}}
> <font color="warning">**事件详情: {{$v.annotations.description}}**</font>
{{end}}{{end}}
```

### 核验
配置生效后：触发一条满足规则的告警（或手动 curl PrometheusAlert 的 webhook），企微机器人收到格式化告警消息；恢复后收到“恢复消息”。

## prometheusalert-subpath-proxy — PrometheusAlert 子路径代理配置


### 场景
要用 nginx 子路径反代 PrometheusAlert 供页面访问。

```nginx
location /privatedeploy/mdy/prometheusalert/ {
    proxy_pass http://localhost:8085;   # PrometheusAlert 实际端口
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # 子路径：替换 HTML 中的路径
    sub_filter_once off;
    sub_filter 'href="/' 'href="/privatedeploy/mdy/prometheusalert/';
    sub_filter 'src="/'  'src="/privatedeploy/mdy/prometheusalert/';
    sub_filter 'action="/' 'action="/privatedeploy/mdy/prometheusalert/';
    sub_filter "url: '\/template\/addtpl'" "url: '\/privatedeploy\/mdy\/prometheusalert\/template\/addtpl'";
    sub_filter "sendurl='\/prometheusalert" "sendurl='\/privatedeploy\/mdy\/prometheusalert\/prometheusalert";

    proxy_redirect / /privatedeploy/mdy/prometheusalert/;
    rewrite ^/privatedeploy/mdy/prometheusalert/(.*)$ /$1 break;
}
```
访问地址：`<访问地址>/privatedeploy/mdy/prometheusalert/`

