# 文件存储 / MinIO

> 由 sources/faq/ 生成，勿手改。每条 `## <slug>` 对应一个 source 文件，可在 ROUTING.md 反查。

## file-minio-hide-web-buttons — 文件存储 minio web 界面隐藏删除/上传/创建按钮


### 现象 / 场景
开放了文件存储 minio web 控制台访问，但不希望用户在界面上看到删除、上传、创建 bucket 等按钮，需要在代理层用 subs_filter 注入 CSS 隐藏。

### 处理

#### 明道云单机版（改 www 容器的 private.conf）
```bash
mkdir /data/mingdao/script/volume/nginx/
docker cp $(docker ps |grep "community"|awk '{print $1}'):/usr/local/nginx/conf/conf.d/private.conf /data/mingdao/script/volume/nginx/

#### 修改
把 /data/mingdao/script/volume/nginx/private.conf 中
#location ^~/minio {
	#proxy_set_header   Host $host;
    #proxy_pass http://private-file;
#}
#### 改为：
location ^~/minio {
	proxy_set_header Accept-Encoding "";
	sub_filter_once off;
	# 隐藏删除按钮
	subs_filter '</head>' '<style type="text/css">button.btn.btn-danger {display: none;} a.fiad-action {display: none;} #delete-checked {display: none;} .bucket-dropdown {display: none;}</style></head>';
	# 隐藏上传、创建bucket按钮（可选）
	subs_filter '</head>' '<style type="text/css">a.feba-btn.feba-upload {display: none;} a#show-make-bucket {display: none;}</style></head>';
	proxy_set_header   Host $host;
	proxy_pass http://private-file;
}

#### /data/mingdao/script/docker-compose.yaml 中挂载，例如：
    volumes:
      - ./volume/data/:/data/
      - ./volume/nginx/private.conf:/usr/local/nginx/conf/conf.d/private.conf
      - ../data:/data/mingdao/data
      - /usr/share/zoneinfo/Etc/GMT-8:/etc/localtime

#### 重启明道云服务
管理器目录下 bash service.sh restartall

#### 访问：明道云访问地址 + /minio，例如 http://<访问地址>:8880/minio
用户：mdstorage
密码：<minio密码>
```

#### file 独立部署版（独立 nginx 代理）
```nginx
upstream mimio {
   # file文件存储ip端口
   server <file存储IP>:9000;
}

server {
   listen 9000;
   server_name _;

   underscores_in_headers on;
   client_max_body_size    2048m;
   gzip  on;
   gzip_proxied any;
   gzip_disable "msie6";
   gzip_vary on;
   gzip_min_length 512;
   gzip_comp_level 6;
   gzip_buffers 16 8k;
   gzip_types text/plain text/css application/json application/x-javascript application/javascript application/octet-stream text/xml application/xml application/xml+rss text/javascript image/jpeg image/gif image/png;
   location / {
        proxy_set_header Accept-Encoding "";
        sub_filter_once off;
        # 隐藏删除按钮
        subs_filter '</head>' '<style type="text/css">button.btn.btn-danger {display: none;} a.fiad-action {display: none;} #delete-checked {display: none;} .bucket-dropdown {display: none;}</style></head>';
        # 隐藏上传、创建bucket按钮（可选）
        subs_filter '</head>' '<style type="text/css">a.feba-btn.feba-upload {display: none;} a#show-make-bucket {display: none;}</style></head>';
        proxy_set_header Host $host;
        proxy_pass http://mimio;
   }
}
```

被隐藏元素的 CSS 选择器对照（按 inline-block 改回即恢复显示）：
- 删除按钮 `button.btn.btn-danger`
- 右键菜单 `a.fiad-action`
- 顶部菜单 `#delete-checked`
- 左侧删除 bucket `.bucket-dropdown`
- 上传 `a.feba-btn.feba-upload`
- 创建 bucket `a#show-make-bucket`

### 核验
重载 nginx 后访问 /minio，删除/上传/创建按钮不再显示，文件正常浏览下载。

## file-storage-independent-domain — 文件存储服务支持独立域名


### 场景
要给文件存储服务配置独立访问域名。

1. 微服务代理增加（如有扩展地址）：`proxy_set_header pdfileaddr http://file-ext.domain.com`
2. 微服务配置文件增加主独立域名：`ENV_FILE_ADDRESS_MAIN: "http://file.domain.com"`
3. 文件存储服务增加：`ENV_FILE_DOMAIN: "http://file.domain.com,http://file-ext.domain.com"`
4. 文件存储前加 Nginx 代理满足跨域：
```nginx
server {
    listen 19000;
    server_name file.domain.com;
    access_log /data/logs/weblogs/mdy-9000.log main;
    error_log  /data/logs/weblogs/mdy-9000.error.log;
    location / {
        if ($request_method = OPTIONS) { return 204 ""; }
        proxy_set_header HOST $http_host;
        proxy_pass http://127.0.0.1:9000;
        proxy_hide_header Access-Control-Allow-Origin;
        add_header Access-Control-Allow-Headers authorization,content-type;
        add_header Access-Control-Allow-Origin "http://mdy.domain.com";
    }
}
```

## minio-enable-web-access — 明道存储 minio 开启 web 访问


### 场景
要开启明道存储 minio 的 web 控制台访问。

微服务节点 www 容器内 `/usr/local/nginx/conf/conf.d/private.conf` 取消 minio location 的注释，再重载：
```bash
/usr/local/nginx/sbin/nginx -s reload
```
浏览器访问 `http(s)://<访问地址>/minio`：
- 单机：用户 `mdstorage`，密码见单机存储配置（占位 `<minio密码>`）。
- 集群：ak/sk 查看 `file.yaml`。

## minio-glibc-cpu-x86-64-v2 — MinIO 容器启动报 Fatal glibc error: CPU does not support x86-64-v2


### 现象 / 场景
MinIO 镜像运行报错：`Fatal glibc error: CPU does not support x86-64-v2`。多见于较老 CPU / 部分虚拟化平台，新版 MinIO 镜像基于 x86-64-v2 指令集编译，旧 CPU 不支持导致无法启动。

参考：https://github.com/minio/minio/issues/18365

### 处理
改用 MinIO 官方提供的 `cpuv1`（针对旧 CPU 兼容）镜像：

```bash
docker pull minio/minio:RELEASE.2025-04-22T22-12-26Z-cpuv1

# 阿里云镜像（国内拉取更快）
docker pull registry.cn-hangzhou.aliyuncs.com/hap-mdy/minio:RELEASE.2025-04-22T22-12-26Z-cpuv1
```

> 较早可用版本：`RELEASE.2024-08-17T01-24-54Z-cpuv1`（同样有 `registry.cn-hangzhou.aliyuncs.com/hap-mdy/minio:...-cpuv1` 与 `quay.io/minio/minio:...-cpuv1`）。

拉取后将编排文件 / 启动命令里的 MinIO 镜像 tag 替换为 `-cpuv1` 版本并重启。

### 核验
容器启动不再报 `CPU does not support x86-64-v2`，`docker ps` 中 MinIO 容器正常 Up，文件上传 / 预览功能恢复。

## minio-mc-delete-file-storage-objects — 用 mc 命令删除文件存储（MinIO）中的对象数据


> 高危：`mc rm --recursive --force` 会不可逆删除整个文件夹下的对象，删除前务必确认路径与备份。

### 适用场景
需要按对象/文件夹/日期批量清理文件存储（MinIO）中的对象数据时使用。

### 步骤

#### 1、添加文件存储服务（mc config）
```bash
mc config host add cluster http://127.0.0.1:9000 storage <占位符:SecretKey>
```
- cluster：文件存储服务的别名
- http://127.0.0.1:9000：文件存储服务的 URL 地址
- storage：文件存储服务的 Access Key
- 第四个参数：文件存储服务的 Secret Key

#### 2、查看桶名
```bash
mc ls cluster
```

#### 3、查看对象文件
```bash
# 查看桶中文件夹下的所有对象文件
mc ls cluster/mdoc/doc/20221130

# 查看指定的对象文件
mc ls cluster/mdoc/doc/20221130/5V262g6Q8U6C9ocL9jeDdk4ocqck2Aaqe1aR6tcGbn6d4lcO2md33zfb3ufw4G8o.mdy
```

#### 4、删除指定的对象文件
```bash
mc rm cluster/mdoc/doc/20221130/5V262g6Q8U6C9ocL9jeDdk4ocqck2Aaqe1aR6tcGbn6d4lcO2md33zfb3ufw4G8o.mdy
```

#### 5、删除指定的文件夹
```bash
mc rm --recursive --force cluster/mdoc/doc/20221130
```

#### 6、批量删除桶中的多个文件夹
以删除 mdoc/doc/20221127 到 mdoc/doc/20221130 为例：

1. 创建一个文件保存要删除的文件夹名称，如 data.list：
```
20221127
20221128
20221129
20221130
```
2. 创建一个 for.sh 循环脚本：
```bash
for i in `cat data.list`
do
    mc rm --recursive --force cluster/mdoc/doc/${i}
done
```
3. 放入后台执行 for.sh 批量删除文件夹：
```bash
nohup bash -x for.sh &
```
4. 查看 nohup.out 观察删除进度：
```bash
tail -n 10 -f nohup.out
```

#### 7、更多用法
- 更多删除示例：`mc rm --help`
- mc 更多使用方法：`mc --help`

### 核验
`mc ls cluster/<桶/路径>` 确认目标对象/文件夹已不再列出。

