# 安全 / 防护 / 漏洞

> 由 sources/faq/ 生成，勿手改。每条 `## <slug>` 对应一个 source 文件，可在 ROUTING.md 反查。

## email-ignore-ssl-verification — 邮箱服务器忽略 SSL 验证


### 临时方案
1. 进微服务容器：`docker exec -it $(docker ps | grep community | awk '{print $1}') bash`
2. 编辑 `/usr/local/MDPrivateDeployment/email/Config/appsettings.json`
3. 添加配置 `"CertificateValidation": true`（json 格式，注意上一行末尾加英文逗号）
4. 单独重启邮件服务：`source /entrypoint.sh && emailShutdown`

### 永久方案
1. `mkdir -p /data/mingdao/script/volume/email`
2. 写入配置文件：
```bash
cat > /data/mingdao/script/volume/email/appextensions.json <<EOF
{
 "CertificateValidation": true
}
EOF
```
3. 修改 `/data/mingdao/script/docker-compose.yaml`，在 `volumes:` 下加一行（注意对齐）：
```
- ./volume/email/appextensions.json:/usr/local/MDPrivateDeployment/email/appextensions.json
```
4. 重启微服务：`bash service.sh restartall`


### 变体：未勾选 SSL + 25 端口报「建立 SSL 链接错误」
现象：系统管理配置邮件服务时未勾选「使用 SSL 链接」、端口填 25，但发送失败，日志提示建立 SSL 链接错误。
- 信创版本 / arm64：可先尝试加 `"CertificateValidation": true`（同上方两个方案的位置）。
- 通用修复：改用 `"ComponentType": 1`。**微服务版本需 ≥ 2.10.0。**

临时方案：编辑容器内 `/usr/local/MDPrivateDeployment/email/Config/appsettings.json` 加 `"ComponentType": 1`（注意上一行末尾加英文逗号），再 `source /entrypoint.sh && emailShutdown`。
永久方案：写入 `/data/mingdao/script/volume/email/appextensions.json`：
```bash
cat > /data/mingdao/script/volume/email/appextensions.json <<EOF
{
 "ComponentType": 1
}
EOF
```
挂载方式同上，`bash service.sh restartall` 生效。

## https-cert-verify-openssl — HTTPS 证书校验（公私钥匹配 / 查看证书）


### 场景
要校验 HTTPS 证书公私钥是否匹配、查看证书内容。

```bash
# 公钥、私钥的 md5 需一致才匹配
openssl x509 -noout -modulus -in server.pem | openssl md5
openssl rsa  -noout -modulus -in server.key | openssl md5

# 查看证书信息
openssl x509 -in server.pem -text -noout
```

## iptables-limit-k8s-nodeport — 通过 iptables 限制 k8s nodePort 端口访问


> k8s 集群各节点都要执行。示例端口 31680。

### 场景
要用 iptables 限制 k8s nodePort 端口的访问来源。

```bash
# 禁止所有来源访问 31680
iptables -t raw -I PREROUTING -p tcp --dport 31680 -j DROP
# 允许单 IP
iptables -t raw -I PREROUTING -s 192.168.1.30 -p tcp --dport 31680 -j ACCEPT
# 允许网段
iptables -t raw -I PREROUTING -s 192.168.1.0/24 -p tcp --dport 31680 -j ACCEPT
# 检查
iptables -t raw -L PREROUTING -v -n --line-numbers
```

## k8s-tls-weak-cipher-cve-2016-2183 — 修复 K8s SSL/TLS 弱加密算法漏洞 (CVE-2016-2183)


### 场景
扫描发现 etcd(2379)、kubelet、apiserver(6443) 使用不安全加密算法。各处指定安全 cipher（保存后服务自动重启）：

1. `/etc/kubernetes/manifests/etcd.yaml` 加：
```
    - --cipher-suites=TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256,TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384,TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305,TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305
```
2. `/etc/kubernetes/manifests/kube-apiserver.yaml` 加 `- --tls-cipher-suites=`（同上算法串）。
3. 每个节点 `/var/lib/kubelet/config.yaml` 加：
```yaml
tlsCipherSuites:
 - TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
 - TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
 - TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305
 - TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
 - TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
 - TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305
```
随后 `systemctl restart kubelet`。

验证：
```bash
nmap --script ssl-enum-ciphers 127.0.0.1 -p 2379
echo | openssl s_client -connect 127.0.0.1:2379 -tls1_2 2>/dev/null | grep "Cipher"
```

## nginx-deny-file-download — nginx 禁止文件下载接口（按角色场景返回 403）


### 场景
按需求场景禁止部分用户下载文件，在 nginx 层拦截下载类接口返回 403。

### 处理
涉及的下载接口：
```
/wwwapi/file/downChatFile
/wwwapi/file/downLinkFile
/wwwapi/file/downKcFile
/wwwapi/file/downDocument
/wwwapi/file/excelFile
/wwwapi/download/worksheetexcel
/file/mdoc/exportexcel
```

nginx 配置加 location：
```nginx
location ~ (/wwwapi/file/downChatFile|/wwwapi/file/downLinkFile|/wwwapi/file/downKcFile|/wwwapi/file/downDocument|/wwwapi/file/excelFile|/wwwapi/download/worksheetexcel|/file/mdoc/exportexcel) {
    return 403;
}
```
按实际需要拦截的角色范围增删上面的接口列表。

### 核验
reload nginx 后，访问对应下载接口返回 403。

## nginx-deny-foreign-ip — Nginx 禁用国外 IP 访问主站（周更 IP 库）


### 场景
要禁止国外 IP 访问主站（每周自动更新 IP 库）。

用脚本每周拉取 APNIC IP 库，nginx deny 拒绝。`/usr/local/nginx/conf/black_nginx.sh`：
```bash
#!/bin/bash
rm -f legacy-apnic-latest black_`date +%F`.conf && wget http://ftp.apnic.net/apnic/stats/apnic/legacy-apnic-latest
awk -F '|' '{if(NR>2)printf("%s %s/%d%s\n","deny",$4,24,";")}' legacy-apnic-latest > black_`date +%F`.conf \
  && rm -f /usr/local/nginx/conf/black.conf \
  && ln -s $PWD/black_`date +%F`.conf /usr/local/nginx/conf/black.conf \
  && /usr/local/nginx/sbin/nginx -s reload
```
crontab：`0 0 * * 5 /bin/bash /usr/local/nginx/conf/black_nginx.sh`
> 注意：IP 库周期性拉取间隔内新增的国外 IP 不在限制内。

### 核验
- `ls -l /usr/local/nginx/conf/black.conf` 指向当天 `black_<date>.conf`，文件内含 `deny ...;` 条目；`nginx -t` 通过。
- 国内 IP 访问主站正常；用国外 IP（或库内某网段）访问应被拒，确认 deny 生效且未误封内网/国内段。

## nginx-limit-by-user-agent — Nginx 按 User-Agent 限制访问（仅钉钉/企微/移动端）


### 场景
要限制只有钉钉 / 企微 / 移动端 UA 才能访问。

### 仅允许钉钉访问（location / 下）
```nginx
if ($http_user_agent !~* "DingTalk") { return 403; }
```

### 仅允许企业微信访问
```nginx
if ($http_user_agent !~* "wxwork|Go-http-client") { return 403; }
```
常见 UA（放行白名单参考）：
- 企业微信：`wxwork`
- 金山 WPS：`Go-http-client`
- 大象慧云：`Blackbox Exporter|Hutool`
- E 签宝：`Apache-HttpAsyncClient|node-fetch|Java`
- 工作流下载本平台附件需放行：`grab`

### 仅允许移动端访问
```nginx
# server 块
if ($http_user_agent ~* "(android|iphone|ipad)") { set $mobile_request 'true'; }
# location / 块
if ($mobile_request != 'true') { return 403; }
```

模拟 UA 测试：`curl -A "wxwork" http://<地址>:<端口>`

### 核验
- `nginx -t` 通过、reload 后：白名单 UA 放行 `curl -I -A "wxwork" http://<地址>:<端口>` 返回 200。
- 非白名单 UA 被拦：`curl -I -A "Mozilla" http://<地址>:<端口>` 返回 403，确认限制生效且未误伤需放行的 UA（如工作流附件下载的 `grab`）。

## nginx-limit-ip-444 — Nginx 限制 IP 访问（return 444 无响应）


### 场景
要只放行指定 IP/域名，其余访问直接 444 不响应。

`444` 表示服务器不返回任何信息并关闭连接（威慑恶意访问）。仅允许指定 server_name/IP，其余 444：
```nginx
server {
  listen 80;
  listen 443 ssl;
  server_name <允许的IP或域名>;
  ssl_certificate conf.d/cert/fullchain.pem;
  ssl_certificate_key conf.d/cert/privkey.pem;
  location / {
    return 444;   # 无响应
  }
}
```

### 核验
- `nginx -t` 通过、reload 后：用允许的 server_name/IP 访问正常打开。
- 用非白名单 Host 访问：`curl -I -H "Host: <随意域名>" http://<服务器IP>/` 连接被直接关闭（curl 报 Empty reply / 52），确认 444 生效且未误伤白名单。

## nginx-limit-origin-referer — nginx 层限制 Origin 和 Referer（防盗链/来源限制）


### 场景
要在 nginx 层做防盗链、限制 Referer/Origin 来源。

需在容器外部署一个代理 nginx（参考 docs-pd `/deployment/proxy/nginx_default`、`/http`、`/https`）。示例在 `/wwwapi` location 加 Referer 白名单 + Origin 限制：

```nginx
location /wwwapi {
    # Referer 白名单（防盗链）
    valid_referers pdemo.test.net *.test.com;
    if ($invalid_referer) { return 403; }

    # Origin 限制
    set $flag 0;
    if ($http_origin) { set $flag "${flag}1"; }                       # origin 有值 -> 01
    if ($http_origin !~ ^https?://demo\.test\.cn[/]?$) { set $flag "${flag}2"; }  # 不匹配 -> 012
    if ($flag = "012") { return 403; }

    proxy_set_header Host $http_host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_pass http://hap;
}
```
Origin 限制到具体 IP 的写法：把正则换成 `^http?://172\.31\.11\.6:81[/]?$`（按实际 IP:端口替换）。

### 核验
- `nginx -t` 通过、reload 后：合法来源访问 `/wwwapi` 正常（白名单 Referer / 匹配的 Origin 返回非 403）。
- 伪造来源被拦：`curl -I -e "http://evil.test" http://<地址>/wwwapi` 与 `curl -I -H "Origin: http://evil.test" http://<地址>/wwwapi` 均返回 403，确认防盗链生效且未误伤白名单来源。

## nginx-security-response-headers — Nginx 响应头安全策略优化


### 场景
安全扫描提示响应头缺失（CSP / Referrer-Policy 等），在 nginx server 段补齐后 reload。

### 处理
```nginx
server_name mdy.domain.com;

add_header Content-Security-Policy "default-src 'self' mdy.domain.com 'unsafe-inline' 'unsafe-eval' blob: data: ;";
add_header 'Referrer-Policy' 'origin';
add_header X-Download-Options noopen;
add_header X-Permitted-Cross-Domain-Policies none;
```
`server_name` / CSP 中的域名换成实际访问域名。

### 核验
`curl -I https://mdy.domain.com` 可见上述响应头；功能正常（CSP 过严会拦截资源，按需放宽）。

## non-root-maintenance-cluster-pro — 非 ROOT 用户维护权限改造（集群专业版）


### 适用场景
初次部署用 root，后续要求统一用无 sudo 权限的普通用户（例 mingdao）维护集群专业版（文件存储 + 微服务）。配合 polkit 让普通用户可执行 systemctl（见 non-root-systemctl-polkit）。

### 步骤

#### 一、数据备份
1、备份文件存储
```bash
cp -r /usr/local/MDPrivateDeployment /usr/local/MDPrivateDeployment-root.bak
cp -r /data/file /data/file-root.bak
```
2、备份微服务
```bash
cp -r /usr/local/MDPrivateDeployment /usr/local/MDPrivateDeployment-root.bak
cp -r /data/mingdao /data/mingdao-root.bak
```
3、停止服务
```bash
# 停文件存储（第一台文件存储服务器执行即可）
docker stack rm file
# 停微服务（第一台微服务服务器执行即可）
docker stack rm mdCluster
```

#### 二、设置非 root 用户（加入 docker 组）
```bash
gpasswd -a mingdao docker
```

#### 三、权限变更
1、文件存储
```bash
chown -R mingdao.docker /usr/local/MDPrivateDeployment
chown -R mingdao.docker /data/file
```
2、微服务
```bash
chown -R mingdao.docker /usr/local/MDPrivateDeployment
chown -R mingdao.docker /data/file
```
3、脚本注释【微服务服务器】（非 root 无法写 /proc、/sys，注释掉相关行）
```bash
su - mingdao   # 切换到非 root 用户
vim /data/mingdao/script/run.sh
# 注释掉以下行（以实际内容为准）：
# echo 1 > /proc/sys/vm/overcommit_memory
# echo "never" > /sys/kernel/mm/transparent_hugepage/enabled
# echo "never" > /sys/kernel/mm/transparent_hugepage/defrag
```

#### 四、服务启动（su - mingdao 切到非 root 用户后）
1、启动文件存储（第一台文件存储服务器执行即可）
```bash
docker stack deploy -c /usr/local/MDPrivateDeployment/clusterMode/file.yaml file
```
2、启动微服务（第一台微服务服务器执行即可）
```bash
docker stack deploy -c /data/mingdao/script/cluster.yaml mdCluster
```

### 回退（在 root 用户下操作）
停服务：
```bash
docker stack rm file
docker stack rm mdCluster
```
恢复文件存储：
```bash
mv /usr/local/MDPrivateDeployment /usr/local/MDPrivateDeployment-mingdao.bak
mv /data/file /data/file-mingdao.bak
cp -r /usr/local/MDPrivateDeployment-root.bak /usr/local/MDPrivateDeployment
cp -r /data/file-root.bak /data/file
```
恢复微服务：
```bash
mv /usr/local/MDPrivateDeployment /usr/local/MDPrivateDeployment-mingdao.bak
mv /data/mingdao /data/mingdao-mingdao.bak
cp -r /usr/local/MDPrivateDeployment-root.bak /usr/local/MDPrivateDeployment
cp -r /data/mingdao-root.bak /data/mingdao
```
启动服务：
```bash
docker stack deploy -c /usr/local/MDPrivateDeployment/clusterMode/file.yaml file
docker stack deploy -c /data/mingdao/script/cluster.yaml mdCluster
```

### 核验
切到普通用户后 `docker stack ps mdCluster` / `docker stack ps file` 正常返回，服务全部 running，无权限报错。

## non-root-maintenance-standalone — 非 ROOT 用户维护权限改造（单机版）


### 适用场景
单机版部署后改为无 sudo 普通用户（例 mdy）维护。路径中的 `smv-manager-2.10.1` 按实际版本目录替换。

### 步骤

#### 一、停止明道服务（root 下操作）
```bash
bash /data/smv-manager-2.10.1/service.sh stopall
```

#### 二、数据及配置目录备份（root）
```bash
cp -r /data/smv-manager-2.10.1 /data/smv-manager-2.10.1.bak202305
cp -r /data/mingdao /data/mingdao.bak202305
```

#### 三、添加非 root 用户到 docker 组（root）
```bash
gpasswd -a mdy docker   # 如无 docker 用户组先新增：groupadd docker
```

#### 四、重启 docker（root）
```bash
systemctl restart docker
```

#### 五、目录权限变更（root）
```bash
chown -R mdy.docker /data/smv-manager-2.10.1
chown -R mdy.docker /data/mingdao
```

#### 六、检查非 root 用户 umask 是否 0022（root）
```bash
su - mdy
echo 'umask 0022' >> ~/.bashrc
```

#### 七、修改环境检测脚本（非 root 下操作）
```
修改 /data/smv-manager-2.10.1/service.sh，注释掉 236 行 checkRoot（以实际行号为准）
```

#### 八、启动服务（非 root 下操作）
```bash
bash /data/smv-manager-2.10.1/service.sh startall
```

### 回退
```bash
# 停服务
bash /data/smv-manager-2.10.1/service.sh stopall
# 取消注释 service.sh 第 236 行 checkRoot
# 权限回退
chown -R root.root /data/smv-manager-2.10.1
chown -R root.root /data/mingdao
# 重启 docker
systemctl restart docker
# 重启服务
bash /data/smv-manager-2.10.1/service.sh startall
```

### 核验
切到普通用户 mdy 执行 `service.sh startall` 不报权限/checkRoot 错误，容器全部 running。

## non-root-systemctl-polkit — 普通用户调用 systemctl（polkit 授权，非 Root 改造组件维护）


### 现象 / 场景
非 Root 改造场景下，普通用户执行 `systemctl` 管理组件服务（start/stop/restart）时被拒绝，提示权限不足。systemd 的服务管理权限由 polkit 控制，对应动作为 `org.freedesktop.systemd1.policy` 文件里的 `manage-units`。

### 处理
编辑 `/usr/share/polkit-1/actions/org.freedesktop.systemd1.policy`，将 `manage-units` 动作 `<defaults>` 中的授权全部改为 `yes`：
```xml
<defaults>
  <allow_any>yes</allow_any>
  <allow_inactive>yes</allow_inactive>
  <allow_active>yes</allow_active>
</defaults>
```
然后重启 polkit：
```bash
systemctl restart polkit
```

### 核验
切到普通用户执行 `systemctl restart <服务>` 不再报权限错误，命令正常生效。

## sm2-encrypt-env-variables — 私有部署 SM2 方式加密配置文件环境变量（数据库密码等敏感变量）


### 现象 / 场景
不希望 docker-compose.yaml / 日志里明文出现数据库密码等敏感环境变量，用微服务镜像自带的 SM2 国密加密：把环境变量 base64 编码 → 用 SM2 公钥加密 → 私钥配进编排文件，启动时解密注入。

参考：https://kdocs.cn/l/cmvkH7CJ2gGi

### 处理

#### 一、环境变量 base64 编码
1. 复制需要加密的环境变量（示例，真实值替换为 `<占位符>`）：
```
MINIO_DOMAIN=<file域名>:8880/file
TLS=false
ENV_MINGDAO_PROTO=http
ENV_MINGDAO_HOST=<内网IP>
ENV_MINGDAO_PORT=8880
ENV_MYSQL_HOST=<内网IP>
ENV_MYSQL_PORT=33306
ENV_MYSQL_USERNAME=root
ENV_MYSQL_PASSWORD=<MySQL密码>
COMPlus_ThreadPool_ForceMinWorkerThreads=100
COMPlus_ThreadPool_ForceMaxWorkerThreads=500
```
- 变量名与值之间冒号改成等号，去掉值的引号（如上）。

2. base64 编码（`-w0` 不换行）：
```bash
echo 'MINIO_DOMAIN=<file域名>:8880/file
TLS=false
ENV_MINGDAO_PROTO=http
ENV_MINGDAO_HOST=<内网IP>
ENV_MINGDAO_PORT=8880
ENV_MYSQL_HOST=<内网IP>
ENV_MYSQL_PORT=33306
ENV_MYSQL_USERNAME=root
ENV_MYSQL_PASSWORD=<MySQL密码>
COMPlus_ThreadPool_ForceMinWorkerThreads=100
COMPlus_ThreadPool_ForceMaxWorkerThreads=500' | base64 -w0
```
得到「环境变量的 base64 编码值」，后续使用。

#### 二、生成 SM2 密钥对
```bash
docker run -it --entrypoint bash $(docker images | grep community | head -n1 | awk '{print $3}') -c '/Housekeeper/main -config /Housekeeper/config.yaml -encrypt sm2-gen'
```
输出 pem 格式公私钥及对应 base64：分别记录 `SM2 Private Key base64 encode` 与 `SM2 Public Key base64 encode` 的值（密钥示例略，用 `<SM2私钥base64>` / `<SM2公钥base64>` 占位）。

#### 三、用公钥加密环境变量
```bash
docker run -it --entrypoint bash $(docker images | grep community | head -n1 | awk '{print $3}') -c '/Housekeeper/main -config /Housekeeper/config.yaml -encrypt sm2-encrypt -publickey <SM2公钥base64> -content <环境变量base64编码值>'
```
- `-publickey` 后跟 `SM2 Public Key base64 encode` 值。
- `-content` 后跟第一步得到的环境变量 base64 编码值。

得到 `sm2-encrypt` 的密文值（记为 `<sm2-encrypt密文>`），后续使用。

#### 四、配置加密值进入环境变量
修改 docker-compose.yaml，新增/修改加密变量：
```yaml
...
ENV_ENCRYPT_TYPE: "sm2"
ENV_ENCRYPT_SECRET: "<SM2私钥base64>"
ENV_ENCRYPT_CONTENT: "<sm2-encrypt密文>"
...
```
- `ENV_ENCRYPT_TYPE: "sm2"` 启用 SM2 环境变量加密。
- `ENV_ENCRYPT_SECRET` 为 `SM2 Private Key base64 encode` 私钥值。
- `ENV_ENCRYPT_CONTENT` 为第三步 `sm2-encrypt` 密文值。

### 核验
重启后 `docker logs` 应能看到解密注入：
```
SetEnvironment: ENV_MYSQL_HOST=<内网IP>
SetEnvironment: ENV_MYSQL_PASSWORD=<MySQL密码>
...
```
- 默认 docker logs 会把解密后的变量值记录出来；不希望记录则加变量 `ENV_ENCRYPT_QUIET: "true"` 再重启即可。

## sms-bombing-rate-limit — 短信轰炸防护（注册/找回密码/邀请 限频 appextensions.json）


### 场景
注册/找回密码验证码被刷（短信轰炸）。建 `appextensions.json` 挂到容器内两个路径，按 IP / 账号限频。

挂载点：
- `/usr/local/MDPrivateDeployment/wwwapi/appextensions.json`
- `/usr/local/MDPrivateDeployment/api/appextensions.json`

内容（数值按实际调整，`0` 代表不限制）：
```json
{
  "AppSettings": {
    "SameIPRegLimitCount": "100",            // 注册验证码每个IP N天限制数量
    "SameIPRegLimitCountDays": "1",
    "SameMobilePhoneRegLimitCount": "3",     // 注册验证码每个账号 N天限制数量
    "SameMobilePhoneRegLimitCountDays": "1",
    "SameIPFindPasswordLimitCount": "100",   // 找回密码每个IP N天限制数量
    "SameIPFindPasswordLimitCountDays": "1",
    "SameMobilePhoneFindPasswordLimitCount": "100", // 找回密码每个账号 N天限制数量
    "SameMobilePhoneFindPasswordLimitCountDays": "1",
    "SameIPInviteLimitCount": "100",         // 每个IP邀请 N天限制数量
    "SameIPInviteLimitCountDays": "1",
    "SameUserInviteLimitCount": "100",       // 每个用户邀请 N天限制数量
    "SameUserInviteLimitCountDays": "1"
  }
}
```
> 改完重启对应容器生效。JSON 实际不支持 `//` 注释，落盘时去掉注释。

### 核验
- 两个挂载点文件均已就位且为合法 JSON（无 `//` 注释残留）：`docker exec <容器> cat /usr/local/MDPrivateDeployment/wwwapi/appextensions.json`。
- 重启后实测：同一账号/IP 连续请求找回密码或注册验证码，达到 `SameMobilePhoneRegLimitCount` 等阈值后被拒（提示超频），正常单次请求不受影响。

## standalone-redis-port-password — 单机版映射 Redis 端口到宿主机并修改密码


### 场景
单机版 Redis 默认不映射到宿主机。确有必要映射出去时，**必须**先改高强度密码——数据库端口暴露到公网风险极高。

下列三条缺一不可：
1. 做好定期备份（防被黑丢数据）。
2. 端口设访问白名单（限制来源 IP）。
3. 改高强度密码——**不要带 `$ & # @` 等特殊字符**（无法传入容器/设置失败），需特殊字符只用 `_` 和 `-`。

### 修改密码步骤（示例新密码 f8K5ZT3aQXTb）
```bash
# 1. 先备份（云盘快照或数据目录备份）

# 2. community 容器运行中改 redis 密码（默认 123456），返回 OK 即成功
docker exec -it $(docker ps | grep community | awk '{print $1}') bash -c "redis-cli -a 123456 config set requirepass f8K5ZT3aQXTb"

# 3. 检查
docker exec -it $(docker ps | grep community | awk '{print $1}') bash -c "redis-cli -a f8K5ZT3aQXTb <<< 'config get requirepass'"
```
4. 在 `/data/mingdao/script/docker-compose.yaml` 增加环境变量：
```yaml
ENV_REDIS_PASSWORD: "f8K5ZT3aQXTb"
```
5. 同文件增加端口映射：
```yaml
- 6379:6379
```
6. 重启生效：`bash service.sh restartall`

> 数据安全说明：https://docs.pd.mingdao.com/deployment/secure.html

### 核验
- 改密成功：`docker exec -it $(docker ps | grep community | awk '{print $1}') bash -c "redis-cli -a <新密码> <<< 'config get requirepass'"` 返回新密码；用旧密码 `123456` 连接应被拒（NOAUTH/WRONGPASS）。
- 端口映射生效：宿主机 `redis-cli -h 127.0.0.1 -p 6379 -a <新密码> ping` 返回 PONG。
- restartall 后业务正常（容器内 ENV_REDIS_PASSWORD 已为新密码），确认白名单已限制来源、未把无密码端口暴露公网。

