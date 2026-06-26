# MySQL / 数据库

> 由 sources/faq/ 生成，勿手改。每条 `## <slug>` 对应一个 source 文件，可在 ROUTING.md 反查。

## euler-mysql-ulimit-nofile — 华为欧拉(openEuler)单机版 MySQL 内存占用过高 / 文件描述符不足


### 现象
openEuler（华为欧拉）部署明道云单机版：MySQL 服务占用内存很高，部分服务报「无法分配文件描述符 / 内存不足」。
（同类问题在麒麟系统上也出现过。麒麟通常改 systemd `docker.service` 的 `LimitNOFILE`（默认 infinity，限制为 102400）即可；但此方式在欧拉上**不生效**——改后进微服务容器 `ulimit -n` 仍是旧的高/无限制值。）

### 处理（欧拉：在容器级别限制 ulimit）
`docker-compose.yaml` 的服务下新增 `ulimits`：
```yaml
services:
  app:
    image: registry.cn-hangzhou.aliyuncs.com/mdpublic/mingdaoyun-community:3.9.1
    ulimits:
      nofile:
        soft: 102400
        hard: 102400
    environment:
      ENV_ADDRESS_MAIN: "https://xxxxx.com:443"
```
改后重启明道云服务生效。

欧拉 22 若启动报 kafka / 内存错误，改 `docker.service` 中 docker 启动方式：
```
/usr/bin/dockerd --default-ulimit nofile=102400:102400
```
`systemctl daemon-reload && systemctl restart docker` 后再启动明道云。

### 核验
进微服务容器执行 `ulimit -n`，值为 102400；MySQL 内存回落，无文件描述符报错。

## language-auto-change-account-setting — 语言自动改变问题 — Account_Setting 重复数据


### 场景
用户界面语言自动变化（Account_Setting 有重复数据）。

用户语言自动变化，查 `Account_Setting` 通常有两条重复数据，删一条即可：
```sql
USE MDProject;
SELECT * FROM Account_Setting WHERE AccountId='<用户ID>';
-- 出现两条重复时，随便删一条
```

## login-log-queries — 登录日志查询（失败日志 / 未登录用户）


### 场景
要查登录失败日志，或某时间至今未登录的用户。

### 查登录失败日志
```sql
SELECT * FROM MDLog.Account_ActionLog WHERE Type=-1 ORDER BY CreateTime DESC;
```

### 查某时间至今未登录的用户
```sql
USE MDProject;
SELECT AccountId, Fullname FROM AccountInfo
WHERE AccountId NOT IN (
  SELECT DISTINCT AccountID FROM MDLog.Account_ActionLog
  WHERE TYPE=1 AND CreateTime > '2020-06-24 21:58:47'
);
```
（Type=1 为登录成功；改时间即查该时间后未登录的用户。）

## mysql-backup-restore-scripts — MySQL 数据备份与恢复参考脚本（HAP 业务库）


### 现象 / 场景
HAP 部署需定期备份 MySQL 业务库，或迁移/恢复时需还原。下为可直接改参数使用的备份/恢复脚本。

需备份的库列表（HAP）：`MDApplication MDCalendar MDLog MDProject MDStructure`；**7.1.0+ 若启用了 HDP，还需备份 `MDHDP`**（打开脚本中对应注释）。

> 提醒：恢复脚本会先 `drop database` 再重建，属高危操作，务必先确认备份完整、目标库可覆盖。

### 处理

#### 备份脚本 mysql_backup.sh
```bash
#!/bin/bash

# 设置变量
# 清理多少天以前的备份文件（单位：天），注意磁盘空间需足以备份及存放备份文件。
max_backup_file_age=3
# 需要备份的 mysql 主节点 ip（需根据实际情况调整）
mysql_host=127.0.0.1
# 需要备份的 mysql 主节点 端口（需根据实际情况调整）
mysql_port=3306
# 连接需要备份的 mysql 的用户（需根据实际情况调整）
mysql_user=root
# 连接需要备份的 mysql 的密码（需根据实际情况调整）
mysql_password=<MYSQL_PASSWORD>
# 备份文件存放目录（需根据实际情况调整），注意磁盘空间需足以备份及存放备份文件。
mysql_backup_dir=/data/backup/mysql
# 备份工具 mysqldump 所在绝对路径（需根据实际情况调整）
mysql_dump_command_path=/usr/local/mysql/bin/mysqldump
# 备份执行记录写入日志文件（需根据实际情况调整）
mysql_backup_log_file=/var/log/mysql_backup.log
# 需要备份的库列表：注意最新版本若有新增库，不在 db_list 中的要自行添加
db_list=(
    'MDApplication'
    'MDCalendar'
    'MDLog'
    'MDProject'
    'MDStructure'
    #'MDHDP' # 7.1.0+，如果启用了 hdp，这个库也要做下备份（打开前面的注释即可）
)


########################## 下方内容无需修改 ##########################
timestamp=$(date +"%Y%m%d%H%M%S")
mysql_backup_file=hap_mysql.bak
mysql_dump_path=$mysql_backup_dir/${mysql_backup_file}$timestamp


# 日志记录函数
mysql_backup_log_dir=$(dirname $mysql_backup_log_file)
mkdir -p $mysql_backup_log_dir
log_info() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") INFO: $1" >> "$mysql_backup_log_file"
}

log_error() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") ERROR: $1" >> "$mysql_backup_log_file"
}

# 开始备份
log_info "Starting backup."
mkdir -p "$mysql_dump_path" && log_info "Created backup directory: $mysql_dump_path"

# 循环备份每个数据库
for db_name in "${db_list[@]}"; do
    if "$mysql_dump_command_path" --set-gtid-purged=off --default-character-set=utf8mb4 -h"$mysql_host" -P"$mysql_port" -u"$mysql_user" -p"$mysql_password" "$db_name" > "$mysql_dump_path/$db_name.sql"; then
        log_info "Database '$db_name' backup succeeded."
    else
        log_error "Database '$db_name' backup failed."
    fi
done

log_info "Backup completed."

# 打包备份文件
log_info "Starting packing."
cd "$mysql_backup_dir"
if tar czf "${mysql_backup_file}$timestamp.tar.gz" "${mysql_backup_file}$timestamp"; then
    log_info "Packing finished."
    rm -rf "${mysql_backup_file}$timestamp" && log_info "Deleted '${mysql_backup_file}$timestamp'."
else
    log_error "Packing failed."
    exit 0
fi

# 查找并删除旧备份文件
log_info "Starting to delete old backup files."
files_to_delete=$(find "$mysql_backup_dir" -name "${mysql_backup_file}*" -mtime +"$max_backup_file_age")
if [ -z "$files_to_delete" ]; then
    log_info "No old backup files found to delete."
else
    echo "$files_to_delete" | while read old_file; do
        if rm -rf "$old_file"; then
            log_info "Deleted old backup file: $old_file"
        else
            log_error "Failed to delete old backup file: $old_file"
        fi
    done
fi

log_info "Completed deleting old backup files."

log_info "All operations completed."
```

#### 恢复脚本 mysql_restore.sh
注意：`mysql_restore_path` 要改为实际待还原数据目录（如 `hap_mysql.bak20231124141722`）。脚本会 **drop 现有库 → 重建 → 导入**，且对 MDProject.sql 单独去掉 `CHARACTER SET utf8 COLLATE utf8_bin`、把所有 `CHARSET=utf8` 转为 `CHARSET=utf8mb4` 再导入。
```bash
#!/bin/bash

# 设置变量
# 需要还原的 mysql 主节点 ip（需根据实际情况调整）
mysql_host=127.0.0.1
# 需要还原的 mysql 主节点 端口（需根据实际情况调整）
mysql_port=3306
# 连接需要还原的 mysql 的用户（需根据实际情况调整）
mysql_user=root
# 连接需要还原的 mysql 的密码（需根据实际情况调整）
mysql_password=<MYSQL_PASSWORD>
# 这个值取决于恢复备份的具体日期，比如 hap_mysql.bak20231124141722，实际恢复中需要修改，待还原的数据目录。
mysql_restore_path=/data/backup/mysql/hap_mysql.bak20231124141722
# 还原工具 mysql 所在绝对路径（需根据实际情况调整）
mysql_dump_command_path=/usr/local/mysql/bin/mysql
# 还原执行记录写入日志文件（需根据实际情况调整）
mysql_restore_log_file=/var/log/mysql_restore.log
# 需要还原的库列表：注意最新版本若有新增库，不在 db_list 中的要自行添加
db_list=(
    'MDApplication'
    'MDCalendar'
    'MDLog'
    'MDProject'
    'MDStructure'
    #'MDHDP' # 7.1.0+，如果启用了 hdp，这个库也要做下备份还原（打开前面的注释即可）
)


########################## 下方内容无需修改 ##########################

# 日志记录函数
mysql_restore_log_dir=$(dirname $mysql_restore_log_file)
mkdir -p $mysql_restore_log_dir
log_info() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") INFO: $1" >> "$mysql_restore_log_file"
}

log_error() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") ERROR: $1" >> "$mysql_restore_log_file"
}

##删除现有库
log_info "Starting delete."
for dbName in ${db_list[*]}
do
    if $mysql_dump_command_path -h$mysql_host -P$mysql_port -u$mysql_user -p$mysql_password -e "drop database $dbName;"; then
        log_info "$dbName mysql_delete finish"
    else
        log_error "$dbName mysql_delete error"
    fi
done

log_info "All delete Database operations completed."

##重新创建库
log_info "Starting create."
for dbName in ${db_list[*]}
do
    if $mysql_dump_command_path -h$mysql_host -P$mysql_port -u$mysql_user -p$mysql_password -e "create database $dbName;"; then
        log_info "$dbName mysql_create finish"
    else
        log_error "$dbName mysql_create error"
    fi
done

log_info "All create Database operations completed."

##开始恢复指定备份数据
log_info "Starting restore."
# 单独处理 MDProject.sql
sed -i 's/CHARACTER SET utf8 COLLATE utf8_bin //' ${mysql_restore_path}/MDProject.sql
for dbName in ${db_list[*]}
do
    sed -ri 's/CHARSET=utf8(;| )/CHARSET=utf8mb4\1/g' ${mysql_restore_path}/${dbName}.sql
    if $mysql_dump_command_path -h$mysql_host -P$mysql_port -u$mysql_user -p$mysql_password --default-character-set utf8mb4 -D $dbName < ${mysql_restore_path}/${dbName}.sql; then
        log_info "$dbName mysql_restore finish"
    else
        log_error "$dbName mysql_restore error"
    fi
done

log_info "All restore Database operations completed."

log_info "All operations completed."
```

定时备份：将 mysql_backup.sh 加入 crontab，例如每天 0 点：
```bash
echo "0 0 * * * /path/to/mysql_backup.sh" | crontab -
```

### 核验
- 备份：执行后查看 `mysql_backup_dir` 下生成 `hap_mysql.bak<时间戳>.tar.gz`，`mysql_backup.log` 中每个库均为 “backup succeeded”。
- 恢复：`mysql_restore.log` 中每个库 “mysql_restore finish”；登录平台确认应用/组织/日历等数据正常。

## mysql-binary-missing-shared-libs — MySQL 二进制启动报缺共享库（libaio / libtinfo / libncurses / libnuma）


### 场景
解压二进制 MySQL（主从部署 / 替换升级）后启动报 `error while loading shared libraries: lib*.so.*`，缺系统共享库。按发行版装对应依赖。相关：[[mysql-binary-upgrade]]。

### CentOS
```bash
# 缺 libaio.so
yum search libaio && yum install -y libaio
# CentOS 7.6 缺 libncurses.so.5
yum -y install ncurses-compat-libs
```

### Ubuntu
```bash
# 缺 libncurses.so.5 / libtinfo.so.5
ln -s /usr/lib/x86_64-linux-gnu/libncurses.so.6.3 /usr/lib/libncurses.so.5
ln -s /usr/lib/x86_64-linux-gnu/libtinfo.so.6.3  /usr/lib/libtinfo.so.5
# 22.04 LTS 缺 libtinfo.so.5
apt-get -y install libncurses5
```

### Debian 12（离线 deb）
```bash
wget http://ftp.de.debian.org/debian/pool/main/liba/libaio/libaio1_0.3.113-4_amd64.deb       && dpkg -i libaio1_0.3.113-4_amd64.deb
wget http://ftp.de.debian.org/debian/pool/main/liba/libaio/libaio-dev_0.3.113-4_amd64.deb     && dpkg -i libaio-dev_0.3.113-4_amd64.deb
wget http://ftp.de.debian.org/debian/pool/main/n/ncurses/libtinfo5_6.4-4_amd64.deb            && dpkg -i libtinfo5_6.4-4_amd64.deb
wget http://ftp.de.debian.org/debian/pool/main/n/ncurses/libncurses5_6.4-4_amd64.deb          && dpkg -i libncurses5_6.4-4_amd64.deb
```

### Debian 11（缺 libnuma.so.1）
```bash
apt-get install numactl
```

## mysql-binary-upgrade — MySQL 替换二进制升级（5.7.x→5.7.42 / 8.0.x）


### 场景
要用替换二进制方式升级 MySQL（5.7.x→5.7.42 / 8.0.x）。

### 1. 停微服务

### 2. 备份各库
```bash
mkdir -p /data/mysql_bak_$(date +%Y%m%d%H%M%S) && cd /data/mysql_bak_* && mkdir -p mysql_old
for i in MDApplication MDCalendar MDLog MDProject MDStructure; do
  /usr/local/mysql/bin/mysqldump --set-gtid-purged=off --default-character-set utf8 -h 127.0.0.1 -P3306 -uroot -p<密码> $i > mysql_old/$i.sql
done
```

### 3. 升级（5.7 示例，8.0 类似换包名）
```bash
# 平滑停止
/usr/local/mysql/bin/mysql -u root -p<密码> --execute="SET GLOBAL innodb_fast_shutdown=0" -S /usr/local/mysql/mysql.sock
/usr/local/mysql/bin/mysqladmin -u root -p<密码> shutdown -S /usr/local/mysql/mysql.sock
# 备份后替换二进制
\cp -rfp /usr/local/mysql /usr/local/mysql_bak_$(date +%Y%m%d%H%M%S)
cd ~/mdtemp && wget https://cdn.mysql.com//Downloads/MySQL-5.7/mysql-5.7.42-linux-glibc2.12-x86_64.tar.gz
tar xzvf mysql-5.7.42-linux-glibc2.12-x86_64.tar.gz
\cp -rvfp ~/mdtemp/mysql-5.7.42-linux-glibc2.12-x86_64/{bin,docs,include,lib,LICENSE,man,README,share,support-files} /usr/local/mysql/
systemctl start mysql
/usr/local/mysql/bin/mysql_upgrade -u root -p<密码> -S /usr/local/mysql/mysql.sock   # 刷新检查
systemctl restart mysql
```
> MySQL 8.0：包名换 `mysql-8.0.39-linux-glibc2.12-x86_64.tar.xz`，替换后 `chown -R mysql:mysql /usr/local/mysql/`，8.0 无需 mysql_upgrade。

## mysql-mgr-router-hdp-config — MySQL MGR+Router 部署 — HDP 连接配置（hostAliases）


### 场景
HDP 接 MySQL MGR+Router 高可用，需配连接与 hostAliases。

HDP 连接 MGR+Router 的环境变量（密码占位）：
```
ENV_HDP_MYSQL_HOST: "mysql-master"
ENV_HDP_MYSQL_PORT: "6446"
ENV_HDP_MYSQL_USERNAME: "root"
ENV_HDP_MYSQL_PASSWORD: "<MySQL root 密码>"
```

`hdp.yaml` 中为 `mysql-master` 添加 hostAliases，指向各 MGR 节点 IP（IP 占位）：
```yaml
    spec:
      hostAliases:
        - ip: "<MGR 节点1 IP>"
          hostnames:
            - "mysql-master"
        - ip: "<MGR 节点2 IP>"
          hostnames:
            - "mysql-master"
        - ip: "<MGR 节点3 IP>"
          hostnames:
            - "mysql-master"
      containers:
      - name: hdpapi
```

## role-members-empty-table-charset — 角色中的成员加载为空 — Project_OrgRoleChargeDepartment 表编码不一致


### 场景
角色里的成员加载为空（Project_OrgRoleChargeDepartment 表编码不一致）。

原因：旧版本 `Project_OrgRoleChargeDepartment` 表创建语句没加编码，导致该表编码与其他表不一致（如 `utf8mb4_0900_ai_ci` vs `utf8mb4_general_ci`），角色成员加载报错为空。

处理：
```sql
USE MDProject;
-- 检查表编码
SHOW CREATE TABLE Project_OrgRoleChargeDepartment;
-- 改成与其他表一致的 utf8mb4_general_ci
ALTER TABLE Project_OrgRoleChargeDepartment CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

## standalone-db-external-mapping — 单机版数据库（MySQL / MongoDB）对外端口映射与开启鉴权


### 适用场景
单机版（mingdaoyun-community 容器）需要把内置 MySQL / MongoDB 暴露到宿主机端口供外部连接，并设置访问密码。所有密码请替换为 `<占位符>`。

### MySQL 对外暴露

#### 1、容器启动状态下修改 MySQL 默认密码 / 授权远程访问
```bash
docker exec -i $(docker ps | grep community | awk '{print $1}') bash -c 'mysql -uroot -p<旧密码>' <<< "GRANT ALL ON *.* to root@'%' IDENTIFIED BY '<新MySQL密码>';"
```

#### 2、在 /data/mingdao/script/docker-compose.yaml 增加 ENV_MYSQL_PASSWORD
```yaml
     ENV_MYSQL_PASSWORD: "<新MySQL密码>"
```

#### 3、在同文件增加端口映射
```yaml
     - 3306:3306
```

#### 4、重启服务生效
```bash
bash ./service.sh restartall
```

### MongoDB 对外暴露

#### 1、复制出 /entrypoint.sh
```bash
docker cp $(docker ps | grep community | awk '{print $1}'):/entrypoint.sh /data/mingdao/script/volume/
```

#### 2、给 mongod 启动参数加 --auth
```bash
sed -i 's/mongod --dbpath/mongod --auth --dbpath/' /data/mingdao/script/volume/entrypoint.sh
```

#### 3、容器启动状态下为 admin 及所有业务库创建用户
（root 用户密码、各库 mingdao 用户密码均替换为 `<占位符>`）
```bash
docker exec -i $(docker ps | grep community | awk '{print $1}') /init/mongodb/mongo <<< 'use admin
db.createUser({user:"root",pwd:"<root密码>",roles:[{role:"root",db:"admin"}]})
use MDLicense
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"MDLicense"}]})
use ClientLicense
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"ClientLicense"}]})
use commonbase
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"commonbase"}]})
use MDAlert
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"MDAlert"}]})
use mdapproles
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdapproles"}]})
use mdapprove
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdapprove"}]})
use mdapps
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdapps"}]})
use mdattachment
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdattachment"}]})
use mdcalendar
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdcalendar"}]})
use mdcategory
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdcategory"}]})
use MDChatTop
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"MDChatTop"}]})
use mdcheck
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdcheck"}]})
use mddossier
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mddossier"}]})
use mdemail
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdemail"}]})
use mdform
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdform"}]})
use MDGroup
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"MDGroup"}]})
use mdgroups
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdgroups"}]})
use MDHistory
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"MDHistory"}]})
use mdIdentification
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdIdentification"}]})
use mdinbox
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdinbox"}]})
use mdkc
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdkc"}]})
use mdmap
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdmap"}]})
use mdmobileaddress
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdmobileaddress"}]})
use MDNotification
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"MDNotification"}]})
use mdpost
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdpost"}]})
use mdreportdata
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdreportdata"}]})
use mdroles
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdroles"}]})
use mdsearch
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdsearch"}]})
use mdservicedata
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdservicedata"}]})
use mdsms
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdsms"}]})
use MDSso
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"MDSso"}]})
use mdtag
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdtag"}]})
use mdtransfer
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdtransfer"}]})
use MDUser
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"MDUser"}]})
use mdworkflow
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdworkflow"}]})
use mdworksheet
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdworksheet"}]})
use mdworkweixin
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdworkweixin"}]})
use mdwsrows
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"mdwsrows"}]})
use pushlog
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"pushlog"}]})
use taskcenter
db.createUser({user:"mingdao",pwd:"<mingdao密码>",roles:[{role:"readWrite",db:"taskcenter"}]})'
```

#### 4、在 docker-compose.yaml 增加 ENV_MONGODB_URI
```yaml
     ENV_MONGODB_URI: "mongodb://mingdao:<mingdao密码>@127.0.0.1:27017"
```

#### 5、增加 entrypoint.sh 挂载
```yaml
     - ./volume/entrypoint.sh:/entrypoint.sh
```

#### 6、增加端口映射
```yaml
     - 27017:27017
```

#### 7、重启服务生效
```bash
bash ./service.sh restartall
```

### 核验
外部用对应账号/密码连接 `宿主机IP:3306`（MySQL）、`宿主机IP:27017`（MongoDB，需带鉴权）能连上；MongoDB 开启 `--auth` 后无密码连接被拒。

