# 系统 / OS / 部署杂项

> 由 sources/faq/ 生成，勿手改。每条 `## <slug>` 对应一个 source 文件，可在 ROUTING.md 反查。

## app-library-install-fail-domain-change — 应用库安装失败（域名更换导致）— 重刷应用包


现象：更换域名后应用库安装失败。

原因/处理：旧地址生成的应用包路径失效，需基于新地址重新生成。
1. 登录明道，console 通过 `md.global` 获取 Config 中 `AppFileServer` 信息，确认接口地址路径是否为 `package`。
2. 调用重刷接口（基于当前新地址重新生成应用包，100 个应用约 5 分钟）：
   ```
   https://<你的域名>/package/Library/LoadLibFile
   access_token: <access_token>
   ```
3. 应用多时接口会 504，可在系统日志过滤关键字 `LoadLibraryFile` 看是否完成；完成后刷新界面重新执行应用安装即可。

## community-key-apply-url — 社区版密钥重新申请地址


### 场景
服务器 ID 变动后社区版密钥失效，需重新申请。

### 处理
替换 URL 中的服务器 ID 与密钥版本(ltv)后访问申请：
```
https://www.mingdao.com/personal?type=privatekey&ltv=3.3.0&serverId=服务器ID#apply
```

## dm8-dameng-client-disql — 达梦8(dm8) 容器版客户端 disql 连接与常用查询


### 场景
需要用达梦8(dm8) 客户端 disql 连库做查询（手头没有现成客户端时）。

镜像（arm64 dockerhub `qinchz/dm8-arm64`，容器内 disql 在 `/home/dmdba/dmdbms/bin/`；amd64 用官网离线包，`/opt/dmdbms/bin/`）：
```bash
docker pull qinchz/dm8-arm64:latest
docker run -itd --rm --name dm8-test --entrypoint bash qinchz/dm8-arm64:latest
docker exec -it dm8-test bash
cat >> ~/.bashrc << EOF
DM_HOME=/home/dmdba/dmdbms
export PATH=\$PATH:\$DM_HOME/bin
export LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:\$DM_HOME/bin
EOF
source ~/.bashrc

# 连接各库（密码占位）
/home/dmdba/dmdbms/bin/disql MDPROJECT/<密码>@<达梦IP>:<端口>
# 其余库：MDLOG / MDSTRUCTURE / MDCALENDAR / MDAPPLICATION 同法
```
常用查询：
```sql
SELECT TABLE_NAME FROM DBA_TABLES;   -- 所有表视图
SELECT TABLE_NAME FROM USER_TABLES;  -- 当前库所有表
SELECT * FROM Account;               -- 查 MDPROJECT 的 Account
```

## excel-import-timeout-antivirus — Excel 导入数据频繁转圈圈 / 请求超时 —— 宿主机杀毒软件干扰容器网络


### 现象
某客户通过 Excel 导入数据时页面频繁转圈圈，导入卡住/失败，偶发性。

### 原因
日志表现是**偶发网络超时**而非单纯算力不足；最终定位到**宿主机上的杀毒软件**拦截/拖慢了进程间或容器网络通信。

### 处理
逐层缩小：
1. 先看 Excel 相关服务 pod 实例数/资源是否不足，翻错误日志。
2. 日志更像网络问题（偶发请求超时），不是算力瓶颈 → 扩容实例无效。
3. 排查宿主机侧安全软件（杀毒/EDR/防火墙）对容器网络/进程的干扰。
4. **停用/卸载杀毒软件**后做对照测试 —— 本案例卸载后导入恢复正常。

> 「导入转圈圈/超时」pod 实例不足只是常见原因之一；当日志指向偶发网络超时、且扩容无效时，务必排查宿主机安全软件，必要时停用做对照。

### 核验
停用安全软件后重试 Excel 导入，不再转圈、能正常完成；对照测试确认是该软件导致。

## fio-disk-performance-test — FIO 磁盘性能测试（安装 / libaio 依赖 / 测试命令）


### 场景
需要实测磁盘 IOPS / 吞吐做选型或验收（确认 SSD、4K 对齐）。

### 安装 fio
```bash
# 安装包从原记录附件获取 fio-3.7-glibc2.17.tar.gz
tar xzvf fio-3.7-glibc2.17.tar.gz -C /usr/local/
ln -s /usr/local/fio/bin/fio /usr/bin/fio
fio -v
```

### 报 libaio.so.1 缺失时装依赖
```bash
ldconfig -p | grep libaio
fio --enghelp | grep libaio

# debian：在线 apt -y install libaio1 libaio-dev
#         离线 libaio-libaio-dev-0.3.112-3-debian10.tar.gz
tar xzvf libaio-libaio-dev-0.3.112-3-debian10.tar.gz && dpkg -i libaio-libaio-dev-0.3.112-3-debian10/*.deb

# centos：在线 yum -y install libaio libaio-devel
#         离线 libaio-libaio-devel-glibc2.17-centos7.tar.gz
tar xzvf libaio-libaio-devel-glibc2.17-centos7.tar.gz && rpm -ivh libaio-libaio-devel-glibc2.17-centos7/*.rpm
```
依赖仍有问题时，用附件镜像在容器内测：
```bash
docker load -i linux-tools-amd64-1.0-alpine.tar
docker run --rm -it -v /data/mdtemp/:/data/mdtemp/ registry.cn-hangzhou.aliyuncs.com/hap-mdy/linux-tools-amd64:1.0-alpine sh
```

### 测试命令（SSD 确认 4K 对齐；4k 随机 / 1M 顺序）
```bash
# 随机写
fio -direct=1 -iodepth=128 -rw=randwrite -ioengine=libaio -bs=4k   -size=5G -numjobs=1 -runtime=1000 -group_reporting -filename=iotest -name=Rand_Write_Testing
# 随机读
fio -direct=1 -iodepth=128 -rw=randread  -ioengine=libaio -bs=4k   -size=5G -numjobs=1 -runtime=1000 -group_reporting -filename=iotest -name=Rand_Read_Testing
# 顺序写
fio -direct=1 -iodepth=64  -rw=write     -ioengine=libaio -bs=1024k -size=5G -numjobs=1 -runtime=1000 -group_reporting -filename=iotest -name=Write_PPS_Testing
# 顺序读
fio -direct=1 -iodepth=64  -rw=read      -ioengine=libaio -bs=1024k -size=5G -numjobs=1 -runtime=1000 -group_reporting -filename=iotest -name=Read_PPS_Testing
```
> arm64 用附件 `linux-tools-arm64-1.0.0.tar.gz`。测完删 `iotest` 文件。

## fio-libaio-shared-library-missing — fio 报 libaio.so.1 cannot open shared object file（缺 libaio 依赖）


### 现象 / 场景
运行 fio 做磁盘性能实测时报：
```
fio: error while loading shared libraries: libaio.so.1: cannot open shared object file: No such file or directory
```
原因是系统缺少 libaio 运行库。

### 处理
```bash
#### 检查下
ldconfig -p | grep libaio
fio --enghelp | grep libaio

# debian
apt -y install libaio1 libaio-dev
# 或者安装离线附件 libaio-libaio-dev-0.3.112-3-debian10.tar.gz

# centos
yum -y install libaio libaio-devel
# 或者安装离线附件 libaio-libaio-devel-glibc2.17-centos7.tar.gz
```

#### 离线场景：用 docker 拉取 deb 包（Debian 12 示例）
缺包时可起一个干净的 debian 容器，配国内源后用 aptitude 仅下载（不安装）deb 包，再拷到内网机器 `dpkg -i`：
```bash
docker pull debian:12
docker run -itd --rm --name debian12 --entrypoint bash debian:12
docker exec -it debian12 bash
cat > /etc/apt/sources.list.d/debian.sources << EOF
Types: deb
URIs: http://mirrors.tuna.tsinghua.edu.cn/debian
Suites: bookworm bookworm-updates
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg

Types: deb
URIs: http://mirrors.tuna.tsinghua.edu.cn/debian-security
Suites: bookworm-security
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
EOF

apt update
apt-get install aptitude -y
aptitude update
# 例如安装 vim，-d：仅下载软件包，不执行安装操作
aptitude -y install -d vim
# 下载 fio
aptitude -y install -d fio
# apt-get / aptitude 默认下载路径 /var/cache/apt/archives
ls /var/cache/apt/archives
```

#### dpkg 安装时报错的两个补充
```bash
# 报命令找不到（如 update-alternatives）：补 PATH
export PATH=$PATH:/usr/local/sbin:/usr/sbin:/sbin
# 然后再执行 dpkg -i ****.deb

# 权限相关报错：重新切到 root 下再操作
su -
```
缺其他依赖可到 https://pkgs.org 搜索下载，安装命令 `dpkg -i ****.deb`。

### 核验
`ldconfig -p | grep libaio` 能列出 `libaio.so.1`；重新执行 fio 不再报缺共享库，正常输出测速结果。

## freestyle-css-hide-modules — 用 freestyle.css 自定义样式隐藏功能模块（如登录页“下次自动登录”）


### 现象 / 场景
需要隐藏 HAP 前端某些功能模块/元素（自定义样式需求），例如隐藏登录页面的“下次自动登录 / 记住密码”勾选项。HAP 支持通过自定义样式文件 `freestyle.css` 注入 CSS 覆盖默认样式。

### 处理
在自定义样式文件 `freestyle.css` 中追加对应 CSS，针对要隐藏的元素 class 设置 `display: none`。

隐藏登录页面的“下次自动登录”选项：

```css
.cbRememberPasswordDiv {
    display: none !important;
}
```

说明：
- `freestyle.css` 为平台自定义样式入口文件，注入后对所有前端页面生效。
- 要隐藏其它模块时，先用浏览器开发者工具（F12）定位目标元素的 class/id，再以相同方式写 `display: none !important;` 规则。
- `!important` 用于覆盖平台内联或后加载的样式。

### 核验
配置生效后，刷新登录页（清浏览器缓存或强制刷新），确认“下次自动登录”勾选项不再显示。

## lvm-extend-remove-swap — LVM 扩容：移除 swap 把空间用到数据盘 / 根分区


### 场景
根分区空间不足，把 swap 逻辑卷的空间释放并扩到根分区（或数据盘）。完整磁盘挂载/LVM 文档见原记录附件 `Linux磁盘挂载及扩容.md`，此处为移 swap 扩容补充。

```bash
vim /etc/fstab          # 注释掉 swap 那一行
swapoff -a
mount -a
lvdisplay               # 确认 swap LV 路径
lvremove /dev/rootvg/swap
pvdisplay
pvresize /dev/vda2      # 数据盘扩了物理卷后刷新 PV
lvdisplay
lvextend -l +100%FREE /dev/rootvg/root
xfs_growfs /            # ext4 用 resize2fs
df -hT
```
> 文件系统是 ext4 时把 `xfs_growfs /` 换成 `resize2fs /dev/rootvg/root`。

## offline-python-deps-pro — 专业版离线安装扩展代码块 Python 依赖库


### 场景
专业版环境无外网，扩展代码块需要的 Python 依赖装不上。先在有网的 command 容器里把依赖打包，再传到离线环境离线安装。以 `python-dateutil` 为例。

### 一、有网环境：打包依赖
```bash
docker exec -it $(docker ps | grep command | awk '{print $1}') bash
pip3 install --target=/usr/local/lib/python3.6/site-packages/ python-dateutil

mkdir pkgs && cd ./pkgs/
pip3 freeze > requirements.txt
pip3 download -r requirements.txt          # 下载所有 wheel/源码包到当前目录
cd ../ && tar -zcvf pkgs.tar.gz pkgs
exit

docker cp $(docker ps | grep command | awk '{print $1}'):/pkgs.tar.gz ./
```

### 二、离线专业版环境：离线安装
把 `pkgs.tar.gz` 上传到专业版环境容器内，然后：
```bash
tar -zxvf pkgs.tar.gz && cd pkgs
pip3 install --no-index --find-links="." -r requirements.txt
```

> K8s 专业版多节点持久化挂载/在线安装见 [[k8s-mount-extension-code-deps]]。

## platform-help-doc-deploy-hc — 私有部署平台版帮助文档部署（hc 镜像 + nginx 改品牌）


### 场景
平台版要部署帮助文档(hc 镜像)并改成客户品牌。

1. 拉镜像：`docker pull registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hc:1.0.0`
2. 建 `/usr/local/MDPrivateDeployment/hc.yaml`：
```yaml
version: '3'
services:
  hc:
    image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-hc:1.0.0
    ports:
      - 4000:4000
```
3. 配代理 `/usr/local/nginx/conf/conf.d/hc.conf`，并用 subs_filter 替换 Logo/品牌/域名：
```nginx
upstream mdy-hc { server <hc节点IP>:4000; }
server {
    listen 443 ssl;
    server_name <help域名>;
    ssl_certificate     <证书.pem>;
    ssl_certificate_key <证书.key>;
    subs_filter_types *;
    subs_filter 明道云 <品牌名> ig;
    subs_filter 明道 <品牌名> ig;
    subs_filter '\\u660e\\u9053\\u4e91' '<品牌名unicode>' ig;   # 明道云 编码替换
    subs_filter 'www.mingdao.com' '<门户域名>' ig;
    subs_filter 'mingdao.com' '<主域名>' ig;
    location / {
        proxy_set_header HOST <help域名>;
        proxy_pass http://mdy-hc;
        proxy_redirect http://<help域名>:4000/ https://<help域名>/;
    }
    location = /img/logo.png { root /data/www/<help域名>; }   # 替换 Logo
}
```

## process-dump-createdump — 微服务进程 dump 步骤(createdump)


### 场景
配合研发排查问题需对进程做 dump。
注意：dump 前确保服务器**可用内存 > 被 dump 进程占用内存**，否则有 OOM 风险。单机版要先在 `docker-compose.yaml` 加 `privileged: true` 重启生效，否则权限不足。

### 处理
先 `top -c` / `htop` 记录目标进程 PID 并截图（dump 与研发分析都要）。createdump 路径按容器内 dotnet 运行时版本对应目录。
```bash
PID=$(ps aux | grep dotnet | grep -v grep | awk '{print $2}')
cd /usr/local/dotnet-8-aspnetcore-runtime/shared/Microsoft.NETCore.App/8.0.25/
./createdump -u $PID   # dump 文件默认生成在 /tmp，结束输出有说明
top -H -p $PID -c      # 查看线程并截图
```
导出 dump 文件，过大可 `gzip` 压缩。

#### 用临时容器 dump（需 `--privileged --pid=host`）
```bash
# 1.启动临时容器（版本对应当前部署，例 5.3.0.1）
mkdir /tmp/mdtemp/ && cd /tmp/mdtemp/
docker run -itd --rm --name mdy --privileged --pid=host -v $(pwd):/tmp --entrypoint bash registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-community:5.3.0.1

# 2.进入临时容器
docker exec -it mdy bash

# 3.容器内 dump 指定进程（记录截图）
PROCESS_NAME1='/usr/local/dotnet-6-aspnetcore-runtime/dotnet /usr/local/MDPrivateDeployment/attachment/MD.AttachmentService.GrpcService.dll'
PID1=$(ps -auxww |grep -v grep|grep "$PROCESS_NAME1" |awk '{print $2}')
echo $PID1
/usr/local/dotnet-6-aspnetcore-runtime/shared/Microsoft.NETCore.App/6.0.14/createdump -u $PID1

PROCESS_NAME2='/usr/local/dotnet-6-aspnetcore-runtime/dotnet /usr/local/MDPrivateDeployment/worksheetexcelapi/MD.ExportExcel.WebApi.dll 80 appsettingsConsumer.json'
PID2=$(ps -auxww |grep -v grep|grep "$PROCESS_NAME2" |awk '{print $2}')
echo $PID2
/usr/local/dotnet-6-aspnetcore-runtime/shared/Microsoft.NETCore.App/6.0.14/createdump -u $PID2

# 4.退出并取走 /tmp/mdtemp/ 下文件
exit
# 5.停止临时容器
docker stop mdy
```

## sms-integration-k8s-configmap — 短信集成配置（Kubernetes 专业版，ConfigMap 挂载 appextensions.json）


### 适用场景
K8s 专业版下配置短信网关（webhook 转发）。通过 ConfigMap 挂载 appextensions.json 到微服务容器 /usr/local/MDPrivateDeployment/sms/。

### 步骤
1、创建 mingdaoyun-sms-configmap.yaml
```
cat > mingdaoyun-sms-configmap.yaml <<\EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: sms-configmap
data:
  appextensions.json: |-
  {
    "WebhookUrl": "<接收消息的API接口地址>", // 必填，如 https://api.domain.com/hooks/xxxx
    "WebhookHeaders": {}  // 可选，请求头自定义参数
  }
EOF

kubectl apply -f mingdaoyun-sms-configmap.yaml   # 确认创建无报错
```
2、修改 mingdaoyun-values.yaml，增加挂载
```
volumeMounts:
 - name: smsconfig
   mountPath: /usr/local/MDPrivateDeployment/sms/appextensions.json
   subPath: appextensions.json

volumes:
 - name: smsconfig
   configMap:
     name: sms-configmap
     items:
     - key: appextensions.json
       path: appextensions.json
```
3、重启明道云服务
```
helm upgrade -f mingdaoyun-values.yaml mingdaoyun mingdaoyun/
```

### 核验
```
# 输出需与第一步配置一致
kubectl exec -it mingdaoyun-0 -- bash -c 'cat /usr/local/MDPrivateDeployment/sms/appextensions.json'
```

## smtp-email-send-test-python — SMTP 邮件发送测试脚本(Python)


### 适用场景
排查私有部署邮件发送问题时，在服务器上用一段独立 Python 脚本直接连 SMTP 服务器发测试邮件，判断是网络/账号/SSL 问题还是平台配置问题。脚本不依赖明道云，单独可跑。

### 脚本
```python
import smtplib
from email.mime.text import MIMEText
from email.header import Header

mail_host="<smtp服务器地址>"       # 如 smtp.qq.com
mail_port=587
mail_user="<发件账号>"
mail_pass="<发件密码/授权码>"

sender = '<发件人地址>'
receivers = ['<收件人地址>']

message = MIMEText('test mail', 'plain', 'utf-8')
message['From'] = Header("test", 'utf-8')
message['To'] =  Header("test", 'utf-8')

subject = 'SMTP test'
message['Subject'] = Header(subject, 'utf-8')

try:

    smtpObj = smtplib.SMTP_SSL(mail_host, mail_port)

    #smtpObj = smtplib.SMTP()
    #smtpObj.connect(mail_host, mail_port)

    smtpObj.login(mail_user,mail_pass)
    smtpObj.sendmail(sender, receivers, message.as_string())
    print("success")
except smtplib.SMTPException as e:
    print("Error: "+ e)
```

### 核验
- 终端打印 `success`、收件箱收到主题为 `SMTP test` 的邮件 → SMTP 链路/账号正常，问题在平台配置侧。
- 报错则按异常定位：连接超时=网络/端口；认证失败=账号或授权码；SSL 报错=端口与 `SMTP_SSL`/`SMTP` 方式不匹配（587 多为 STARTTLS，465 为 SSL，按服务商调整）。

## ubuntu-debian-rc-local-autostart — Ubuntu/Debian 配置 rc-local 开机自启（HAP 服务）


### 场景
Ubuntu/Debian 上要用 rc-local 配置 HAP 服务开机自启。

```bash
# ubuntu 需先给 rc-local.service 补 [Install]（debian 跳过此步）
grep "^\[Install\]" /lib/systemd/system/rc-local.service || cat >> /lib/systemd/system/rc-local.service << EOF
[Install]
WantedBy=multi-user.target
EOF

# 没有 /etc/rc.local 则创建（此步先别加自启命令）
[[ ! -f /etc/rc.local ]] && cat > /etc/rc.local <<EOF
#!/bin/sh -e

EOF
chmod +x /etc/rc.local
systemctl daemon-reload && systemctl enable --now rc-local.service
systemctl status rc-local.service   # running 后再加自启命令

# 在 /etc/rc.local 末尾空行前加（{安装管理器绝对路径} 替换为实际路径）
echo 'sleep 30
docker system prune -f
cd {安装管理器绝对路径} && /bin/bash ./service.sh startall' >> /etc/rc.local
```

## version-mismatch-captain-json — 首页左下角版本号与微服务版本不一致


### 现象
3.6.0 前的版本升级到 3.6.0 后（且安装管理器也从 3.6.0 前升到 3.6.0 后），web 左下角版本号未更新为升级后版本。

### 处理
方法 1：清空 `captain.json` 的 value 后重启服务：
```
# 文件：/data/mingdao/script/volume/tmp/captain.json
{ "currentVersion": "", "backupDir": "", "mingdaoPort": "", "docPort": "", "webUrl": "" }
```
方法 2：`docker-compose.yaml` 增加变量：
```yaml
ENV_APP_VERSION: "xxx"
```

### 核验
重启后 web 左下角版本号显示为升级后的正确版本。

## windows-run-docs-pdop — Windows 下运行 docs-pdop 站点（nginx 静态托管）


### 场景
要在 Windows 上用 nginx 静态托管 docs-pdop 离线文档站。

1. 删除 `docs-pdop-windows-nginx` 下旧版的 `build` 文件夹。
2. 在 docs-pdop 源码下运行 `npm run build` 构建最新静态资源。
3. 拷贝新生成的 `build` 到 `docs-pdop-windows-nginx` 下。
4. 对比 docs-pdop 源码中的 `docusaurus.conf`，更新 `docs-pdop-windows-nginx/conf/nginx.conf` 中的 `sub_filter` 替换内容。
5. 运行 `docs-pdop-windows-nginx` 下的 `nginx-tool.bat` 启动 nginx。
6. 本地浏览器访问 `localhost:4000`。

## workflow-print-word-fail — 工作流"获取记录打印文件"(Word)节点失败


### 场景
集群版工作流"获取记录打印文件"节点执行失败，原因：环境变量缺失。微服务添加 `ENV_MINGDAO_INTRANET_ENDPOINT` 变量（默认 `app:8880`）。

