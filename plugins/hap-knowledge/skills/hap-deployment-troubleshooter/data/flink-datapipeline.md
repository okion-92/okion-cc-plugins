# Flink / 数据集成

> 由 sources/faq/ 生成，勿手改。每条 `## <slug>` 对应一个 source 文件，可在 ROUTING.md 反查。

## flink-cluster-proxy-lb — Flink 集群代理负载配置（nginx ip_hash）


### 场景
要给多节点 Flink Web 做 nginx 负载（ip_hash 会话保持）。

```nginx
upstream flink {
  server <flink节点1>:8081;
  server <flink节点2>:8081;
  server <flink节点3>:8081;
  ip_hash;
}
server {
  listen 8081;
  server_name _;
  underscores_in_headers on;
  client_max_body_size 2048m;
  gzip on;
  gzip_min_length 512;
  location / {
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_pass http://flink;
  }
}
```

## flink-datapipeline-504-timeout — 数据集成 Flink 创建任务 504 超时（临时调代理超时）


现象：工作表同步到 MySQL 创建任务时转圈 1 分钟后 504（任务其实已建好，flink job 可能起两个）。默认 `proxy_read_timeout 60s`，4.4.4 镜像起 private-datapipeline 已加 1800s。

临时（旧版本，进微服务容器改 nginx）：
```bash
docker exec -it $(docker ps |grep community|awk '{print $1}') bash
cd /usr/local/nginx/conf/conf.d
sed -ri '/private-datapipeline;/a\        proxy_read_timeout 3600s;' private.conf
/usr/local/nginx/sbin/nginx -t && /usr/local/nginx/sbin/nginx -s reload
```

## flink-dedicated-file-service — 为 Flink 单独启用 File 服务（外部对象存储场景）


### 场景
启用外部对象存储后会切 S3 模式，Flink 暂不支持 OSS 等 S3 协议存储，需单独部署一个 File 服务给 Flink。单机示例：

1. docker-compose.yaml 加 `file-flink` 服务（密钥占位）：
```yaml
file-flink:
  image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-file:1.4.0
  volumes:
    - /usr/share/zoneinfo/Etc/GMT-8:/etc/localtime
    - ./volume/data/file-flink/volume:/data/storage
  environment:
    MINIO_ACCESS_KEY: storage
    MINIO_SECRET_KEY: "<minio密钥>"
  command: ["./main", "server", "/data/storage/data"]
```
2. `docker pull .../mingdaoyun-file:1.4.0`
3. flink 服务加变量指向 file-flink：
```yaml
ENV_FLINK_S3_ACCESSKEY: "storage"
ENV_FLINK_S3_SECRETKEY: "<minio密钥>"
ENV_FLINK_S3_ENDPOINT: "file-flink:9000"
ENV_FLINK_S3_BUCKET: "mdoc"
```
4. `mkdir -p /data/mingdao/script/volume/data/file-flink/volume` → `bash service.sh restartall`
5. 进 file-flink 容器创建 bucket：
```bash
mc config host add file-flink http://127.0.0.1:9000 storage <minio密钥>
mc mb file-flink/mdoc
```
6. 再 `bash service.sh restartall`。（Flink 会在 bucket 下用 checkpoints/recovery 目录。）

## flink-sqlserver-pkix-encrypt-false — Flink 连接 SQL Server 报 PKIX/SSL 失败


现象：数据源连接失败 `Failed to initialize pool: The driver could not establish a secure connection to SQL Server by using SSL ... PKIX path building failed`。

解决：数据源【其他连接串参数】里加 `encrypt=false`。

## flink-standalone-abnormal-job — 单机 Flink 异常 job（重启后 job/task 挂掉）


### 场景
单机 Flink 重启后 job/task 挂掉、异常 job 清不掉。

思路：移走 Flink 容器内 zookeeper 数据目录后重启。
```bash
# 移走 zk 数据目录
docker exec -it $(docker ps|grep mingdaoyun-flink|awk '{print $1}') bash -c "mv /data/flink/zookeeper /data/flink/zookeeper.bakcup-\$(date '+%Y%m%d%H%M')"

# 与微服务同机的单机版：重启 flink 容器，并跳过 300s 等待
docker restart $(docker ps|grep mingdaoyun-flink|awk '{print $1}')
docker exec -it $(docker ps|grep mingdaoyun-flink|awk '{print $1}') bash -c "kill \$(ps -ef |grep 'sleep 300'|awk '{print \$2}')"

# 单独服务器部署的单机版（docker restart 会多启一个 flink，改用容器内重启）
docker exec -it $(docker ps|grep mingdaoyun-flink|awk '{print $1}') bash
kill $(ps -ef |grep -v grep|grep task|awk '{print $2}')
kill $(ps -ef |grep -v grep|grep job|awk '{print $2}')
kill $(ps -ef |grep -v grep|grep zookeeper|awk '{print $2}')
sleep 10
bash /opt/flink/bin/zookeeper.sh start 1
bash /opt/flink/bin/start-cluster.sh
```

## flink-timezone-plus8-taskmanager — Flink 表同步到库时间字段 +8 / taskmanager 宕机（单机 docker）


### 场景
Flink 表同步入库时间字段 +8 时区错乱，或 taskmanager 宕机（单机 docker）。

单机 docker 版 Flink 临时方案（新版本修复后无需）：
```bash
# Flink 容器内
cat >> conf/flink-conf.yaml << EOF
env.java.opts: "-Duser.timezone=Asia/Shanghai"
task.cancellation.timeout: 0
EOF
# 重启
kill $(ps -ef |grep -v grep|grep task|awk '{print $2}')
kill $(ps -ef |grep -v grep|grep job|awk '{print $2}')
sleep 10
bash /opt/flink/bin/start-cluster.sh
```

## flink-web-proxy-auth — 代理 Flink Web 页面并加 basic 认证


### 场景
要代理 Flink Web 页面并加 basic 认证（避免裸奔）。

### 集群（独立 nginx）
```nginx
location /flink/ {
    auth_basic "Flink";
    auth_basic_user_file /opt/.flink-password;
    rewrite ^/flink$ / break;
    rewrite ^/flink/(.*)$ /$1 break;
    proxy_pass http://flink:58081;
}
```
写认证账号密码（密码占位）：
```bash
# openssl 1.0.x：
printf "mingdao:$(openssl passwd -crypt <密码>)\n" > /opt/.flink-password
# openssl 3.0.x：
printf "mingdao:$(openssl passwd -6 <密码>)\n" > /opt/.flink-password
```

### 单机（进 app 容器改 private.conf）
```bash
docker exec -it script_app_1 bash
export | grep -i env_flink      # 取 flink url
vim /usr/local/nginx/conf/conf.d/private.conf
# 末尾 } 上方空行加 location（flink url 换成上面取到的）：
#   location /privatedeploy/mdy/monitor/flink/ {
#     auth_basic "Flink";
#     auth_basic_user_file /usr/local/nginx/conf/conf.d/.flink_passwd;
#     rewrite ^/privatedeploy/mdy/monitor/flink$ / break;
#     rewrite ^/privatedeploy/mdy/monitor/flink/(.*)$ /$1 break;
#     proxy_pass http://flink:8081;
#   }
printf "mingdao:$(openssl passwd -apr1 <密码>)\n" > /usr/local/nginx/conf/conf.d/.flink_passwd
/usr/local/nginx/sbin/nginx -t && /usr/local/nginx/sbin/nginx -s reload
# 访问 <访问地址>/privatedeploy/mdy/monitor/flink/
```

## sqlserver-enable-cdc-datapipeline — SQL Server 开启 CDC（数据集成源库准备）


### 现象 / 场景
数据集成（Flink）以 SQL Server 作为增量同步源时，源库/源表需先开启 CDC（Change Data Capture）。包含 Linux 下用 Docker 起一套 SQL Server 测试环境的步骤。

### 处理

#### Linux Docker 部署 SQL Server
```bash
# 1、拉取镜像
docker pull mcr.microsoft.com/mssql/server:2019-latest

# 2、运行（账号 SA，密码 <SA密码>）
docker run -e "ACCEPT_EULA=Y" -e "MSSQL_SA_PASSWORD=<SA密码>" \
   -p 1433:1433 --name sql1 --hostname sql1 \
   -d \
   mcr.microsoft.com/mssql/server:2019-latest

# 3、Windows 下载 SSMS 管理工具（安装时可能需重启）
# https://download.microsoft.com/download/8/a/8/8a8073d2-2e00-472b-9a18-88361d105915/SSMS-Setup-CHS.exe
```

#### 开启 CDC（库：testflink；表：test）
```sql
-- 1、创表（必须有主键）并插入数据
USE testflink
CREATE TABLE test
   (
      id int IDENTITY (1,1) NOT NULL
      , CONSTRAINT PK_TransactionHistoryArchive1_id PRIMARY KEY CLUSTERED (id)
	  , name NVARCHAR(50)
	  , quantity INT
   )
;

USE testflink
INSERT INTO test VALUES ('banana', 150);
INSERT INTO test VALUES ('orange', 154);

-- 2、开启 SQL Server Agent 服务
sp_configure 'show advanced options', 1;
GO
RECONFIGURE;
GO
sp_configure 'Agent XPs', 1;
GO
RECONFIGURE
GO

-- 3、开启库 CDC
USE testflink;
GO
EXEC sys.sp_cdc_enable_db

-- 4、查询库 CDC 是否开启
USE testflink;
GO
EXEC sys.sp_cdc_help_change_data_capture
GO

-- 5、开启表 CDC
USE testflink;
EXEC sys.sp_cdc_enable_table
@source_schema = N'dbo',
@source_name = N'test', -- 表名，需要改
@role_name = N'sa', -- 用户名，可为空null
-- 库如果不添加 filegroup_name, 默认是 PRIMARY
@filegroup_name = N'PRIMARY',
@supports_net_changes = 0;
GO

-- 6、查询表 CDC 是否开启
USE testflink;
GO
EXEC sys.sp_cdc_help_change_data_capture
GO
```

#### 扩展：自定义 filegroup
```sql
-- 添加 testflink 的 filegroup 为 testflink_CT
use testflink
go
alter database testflink add filegroup testflink_CT
go

-- 查询 filegroup
use testflink
go
sp_helpfilegroup
```

### 核验
`EXEC sys.sp_cdc_help_change_data_capture` 返回目标表的 capture instance，即表级 CDC 已开启，数据集成可正常读取增量。

