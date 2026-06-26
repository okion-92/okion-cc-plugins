# 账号 / 组织 / 登录 / 重置

> 由 sources/faq/ 生成，勿手改。每条 `## <slug>` 对应一个 source 文件，可在 ROUTING.md 反查。

## clear-dept-contact-redis-cache — 清理部门 / 通讯录 Redis 缓存（显示不刷新时）


### 场景
部门 / 人员 / 通讯录数据已改但前端显示不刷新，清对应 Redis 缓存键。`-a` 后为 Redis 密码（按实际改）。

### 处理
```bash
# 清理部门缓存
redis-cli -a 123456 KEYS "h:p:d:i:*"  | xargs redis-cli -a 123456 DEL

# 清理部门人员关系缓存
redis-cli -a 123456 KEYS "s:d:a1:id:*" | xargs redis-cli -a 123456 DEL

# 清理通讯录缓存
redis-cli -a 123456 KEYS "h:p:ur:is:*" | xargs redis-cli -a 123456 DEL
```

> 仅清缓存，不动数据。要清空部门**数据**见 [[reset-departments]]。

### 核验
刷新页面，部门 / 通讯录显示与实际一致。

## clear-org-member-redis-cache — 清理组织成员的 Redis 缓存（成员显示 / 权限不刷新时）


### 现象 / 场景
组织成员（用户）数据已改但前端显示 / 权限不刷新，清对应 Redis 缓存键。`-a` 后为 Redis 密码，按实际改（脱敏为 `<redis密码>`）。

> 与「清理部门 / 通讯录 Redis 缓存」键名不同（本文清的是用户 `h:p:u3*` / `h:pu:n*` 系列键）。仅清缓存，不动数据。

### 处理
1. 进入 community 容器：
```bash
docker exec -it $(docker ps | grep community | awk '{print $1}') bash
```
2. 清理缓存。

单机（Redis 密码直填）：
```bash
redis-cli -a <redis密码> --scan --pattern "h:p:u3:i2:*"  | xargs redis-cli -a <redis密码> DEL
redis-cli -a <redis密码> --scan --pattern "h:p:u3x:i2:*" | xargs redis-cli -a <redis密码> DEL
redis-cli -a <redis密码> --scan --pattern "h:pu:nor:*"   | xargs redis-cli -a <redis密码> DEL
redis-cli -a <redis密码> --scan --pattern "h:pu:nnor:*"  | xargs redis-cli -a <redis密码> DEL
```

集群（用容器内 Redis 环境变量）：
```bash
redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD --scan --pattern "h:p:u3:i2:*"  | xargs redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD DEL
redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD --scan --pattern "h:p:u3x:i2:*" | xargs redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD DEL
redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD --scan --pattern "h:pu:nor:*"   | xargs redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD DEL
redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD --scan --pattern "h:pu:nnor:*"  | xargs redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD DEL
```

### 核验
刷新页面，组织成员显示 / 权限与实际一致。

## cluster-reset-password-mongo-log — 集群版重置登录密码 / 在 MongoDB 日志中查找回密码验证码


### 现象 / 场景
集群版私有部署，用户忘记登录密码且未集成短信/邮件收不到验证码。集群版与单机版不同，验证码记录在 MongoDB 的 `mdservicedata.hk_service_log` 集合里，直接到 mongo shell 查。

官方找回密码文档：https://docs-pd.mingdao.com/faq/function/forgotpwd

### 处理
1. 登录 MongoDB shell。
2. 在登录页「忘记密码」处，输入账号点击发送验证码（提示发送失败可忽略）。
3. mongo shell 中按时间倒序捞最新验证码消息：
```javascript
use mdservicedata;
db.hk_service_log.find(
  { message: { $regex: '验证码', $options: 'i' } },
  { message: 1 }
).sort({ time: -1 })
```

### 核验
取最新一条 `message` 中的验证码，回到登录页填入完成密码重置；查不到多半是账号（手机号/邮箱）输错，核对账号表后重试。

## db-modify-app-settings — 数据库层修改应用设置/操作限制（绕开页面）


### 场景
需绕开页面、在数据库层直接改应用设置 / 操作限制（附件上限、批量数据上限等）。

### 1. 修改 MongoDB（库 mdservicedata）
```js
use mdservicedata

// 单次附件上传上限（示例改 4096）
db.syssettings.updateOne({ "name": "FileUploadLimitSize" }, { $set: { "value": "4096" } })

// 非子流程节点数据处理上限（示例改 2000）
db.syssettings.updateOne({ "name": "WorkflowBatchGetDataLimitCount" }, { $set: { "value": "2000" } })
```

### 2. 清理 Redis 缓存
```
del md:syssetting
```

### 3. 清理内存缓存
系统配置里任意功能开关随便改一个（触发内存缓存刷新）。

### 核验
- `db.syssettings.findOne({"name":"FileUploadLimitSize"}).value` 等于新设的值（如 `"4096"`），其余 syssettings 项不受影响。
- 触发内存刷新后，前端实测对应限制（如附件上传上限、批量数据上限）已按新值生效。

## delete-inactive-accounts-by-last-login — 查找某时间点以来从未登录的账号并批量停用（含 Redis 缓存清理）


> 高危：本流程会批量停用账号（UPDATE Status=4）。**操作前务必停 MySQL 服务做可恢复备份**，并先用查询脚本核对名单。

### 适用场景
按"最后登录时间"清理长期不活跃账号：找出某个时间点以来从未登录过的 AccountId 并批量停用，最后清掉 Redis 用户缓存。

### 步骤

#### 1、创建 seuser.sql（查询从未登录的 AccountId 和姓名）
```sql
vim seuser.sql
USE MDProject;SELECT AccountId,Fullname FROM AccountInfo  WHERE AccountId NOT IN (SELECT DISTINCT AccountID FROM MDLog.Account_ActionLog WHERE TYPE=1 AND CreateTime>'2020-06-24 21:58:47.272481000');
```

#### 2、执行查询脚本，结果输出到 user.txt
单机：
```bash
docker exec -it $(docker ps | grep community | awk '{print $1}') bash
mysql -h 127.0.0.1 -P 3306 -uroot -p<占位符:MYSQL密码> --default-character-set=utf8 < seuser.sql >> user.txt
```
集群（非专业版）：
```bash
docker exec -it $(docker ps | grep community | awk '{print $1}') bash
mysql -h $ENV_MYSQL_HOST -P $ENV_MYSQL_PORT -u$ENV_MYSQL_USERNAME -p$ENV_MYSQL_PASSWORD --default-character-set=utf8 < seuser.sql >> user.txt
```
集群（专业版）：
```bash
docker stack ps mdcluster 或 kubectl get pods | grep config
docker exec -it $(docker ps | grep config | awk '{print $1}') bash 或 kubectl exec -it ${configPodName} bash
mysql -h $ENV_MYSQL_HOST -P $ENV_MYSQL_PORT -u$ENV_MYSQL_USERNAME -p$ENV_MYSQL_PASSWORD --default-character-set=utf8 < seuser.sql >> user.txt
```

#### 3、停掉 MySQL 服务，进行 MySQL 数据备份（必做）

#### 4、生成批量查询脚本并执行（核对将被处理的账号）
```bash
for i in $(cat user.txt | awk '{print $1}'); do echo "USE MDProject;select * from RoutingAccount where AccountId='$i';select * from UsersCard where AccountId='$i';" >> seuselect.sql; done
# 集群示例查询：
mysql -h $ENV_MYSQL_HOST -P $ENV_MYSQL_PORT -u$ENV_MYSQL_USERNAME -p$ENV_MYSQL_PASSWORD --default-character-set=utf8 < seuselect.sql
```

#### 5、生成批量停用脚本并执行（Status=4）
```bash
for i in $(cat user.txt | awk '{print $1}'); do echo "USE MDProject;UPDATE RoutingAccount SET Status=4 WHERE AccountId='$i';UPDATE UsersCard SET Status=4 WHERE AccountId='$i';" >> deudel.sql; done
# 集群示例执行：
mysql -h $ENV_MYSQL_HOST -P $ENV_MYSQL_PORT -u$ENV_MYSQL_USERNAME -p$ENV_MYSQL_PASSWORD --default-character-set=utf8 < deudel.sql
# 执行后再查询验证：
mysql -h $ENV_MYSQL_HOST -P $ENV_MYSQL_PORT -u$ENV_MYSQL_USERNAME -p$ENV_MYSQL_PASSWORD --default-character-set=utf8 < seuselect.sql
```

#### 6、清理 Redis 缓存（进入 commuconfig 或 config 容器内执行）
```bash
redis-cli -h $ENV_REDIS_HOST -a $ENV_REDIS_PASSWORD KEYS "h:p:u3:i2:*" | xargs redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD DEL
redis-cli -h $ENV_REDIS_HOST -a $ENV_REDIS_PASSWORD KEYS "h:p:u3x:i2:*" | xargs redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD DEL
redis-cli -h $ENV_REDIS_HOST -a $ENV_REDIS_PASSWORD KEYS "h:pu:nor:*" | xargs redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD DEL
redis-cli -h $ENV_REDIS_HOST -a $ENV_REDIS_PASSWORD KEYS "h:pu:nnor:*" | xargs redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD DEL
```

#### 7、重启微服务

### 核验
- 步骤 4/5 后的 select 查询确认目标账号 Status 已为 4；
- 被停用账号无法再登录，通讯录/成员列表不再显示。

## enable-platform-login — 开启平台账号登录（被禁用仅 LDAP 时恢复）


### 场景
平台账号登录被禁用（只能 LDAP 登录），需恢复明道账号登录。

### 1. 修改 MySQL 配置
库 `MDProject`，表 `Project_Setting`，配置项 `DisabledMingdaoLogin`：
| 值 | 含义 |
|---|---|
| 1 | 禁用平台账号登录（仅允许 LDAP 登录） |
| 0 | 开启平台账号登录 |

```sql
UPDATE Project_Setting SET SettingValue = '0' WHERE SettingName = 'DisabledMingdaoLogin';
```

### 2. 清理 Redis 缓存（替换为实际组织 ID）
```
HDEL h:p:s <组织ID>
HDEL h:p:s2 <组织ID>
```

### 3. 验证
重新访问登录页，确认平台账号密码登录入口已恢复。

## force-logout-reset-password — 强制全部退出登录并要求重新修改密码


> ⚠️ **高危（数据删除操作）**：执行前请与 HAP 运维实施确认，并务必先做好快照 / 数据备份。操作不可逆。

### 场景
安全事件后，让所有用户登录态失效、下次登录强制改密。三件事：清 token、设置密码有效性时间点、清缓存。

### MySQL — 清访问令牌
```sql
USE MDAppliction;
TRUNCATE TABLE OAuth2_Access_Token;
```

### MongoDB — 设密码有效性时间点 + 清改密日志
```javascript
use mdservicedata
db.syssettings.update({"_id":ObjectId("61c702223dbd9e1db4a3e727")},{$set:{"value":1629891362}});  // value 设为当前时间戳，早于此时间的密码全部失效

use mdIdentification
db.changepasswordlog.remove({});
```

### Redis — 清登录/令牌缓存
```bash
# 单机
redis-cli -a 123456 KEYS "md:syssetting"       | xargs redis-cli -a 123456 DEL
redis-cli -a 123456 KEYS "h:a:s:i:*"           | xargs redis-cli -a 123456 DEL
redis-cli -a 123456 KEYS "h:a:sa:i:v2:*"       | xargs redis-cli -a 123456 DEL
redis-cli -a 123456 KEYS "h:api:accesstoken:*" | xargs redis-cli -a 123456 DEL
redis-cli -a 123456 KEYS "h:api:token:*"       | xargs redis-cli -a 123456 DEL

# 集群（把 -a 123456 换成 -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD）
redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD KEYS "md:syssetting"       | xargs redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD DEL
redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD KEYS "h:a:s:i:*"           | xargs redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD DEL
redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD KEYS "h:a:sa:i:v2:*"       | xargs redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD DEL
redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD KEYS "h:api:accesstoken:*" | xargs redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD DEL
redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD KEYS "h:api:token:*"       | xargs redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD DEL
```

### 核验
- `SELECT COUNT(*) FROM MDAppliction.OAuth2_Access_Token;` 应为 0；`db.syssettings.findOne({"_id":ObjectId("61c702223dbd9e1db4a3e727")}).value` 为设置的时间戳。
- Redis `redis-cli -a 123456 KEYS "h:a:s:i:*"` 无输出。
- 实测：已登录会话刷新即被踢回登录页，且任一账号登录后被强制进入改密流程。

## forgot-login-password-find-code — 私有部署忘记登录密码（日志查验证码 / 查账号表）


### 场景
忘记登录密码，且尚未集成邮件/短信，无法收到验证码——直接在微服务日志里看验证码。

### 在日志中查验证码
1. 登录界面点「忘记密码」，输入账号点发送验证码（提示发送失败可忽略）。
2. 微服务服务器执行，捞验证码：
```bash
docker exec -it $(docker ps | grep community | awk '{print $1}') bash -c 'source /entrypoint.sh && log log | grep "验证码"'
```

### 查不到验证码？多半是账号输错
进容器查账号表，确认正确的手机号/邮箱：
```bash
docker exec -it $(docker ps | grep community | awk '{print $1}') bash
mysql -h127.0.0.1 -uroot -p123456
```
```sql
SELECT MobilePhone, Email, CreateTime, Status FROM MDProject.Account;
```

### 核验
- `log log | grep "验证码"` 能捞到刚发的验证码（取最新一条），用它在登录页完成重置即登录成功。
- 若捞不到，比对 `Account` 表的 MobilePhone/Email，确认输入的账号与表中一致。

## low-to-high-migration-admin-missing — 低版本数据直迁高版本后系统配置/平台管理员不显示


### 现象 / 场景
低版本数据直接迁移到高版本后，平台管理后台的系统配置不显示，原因是平台管理员未重新初始化。

### 处理
检查 `mdservicedata` 库的 admins 集合是否为空：
```javascript
use mdservicedata;
db.admins.count();
```
如果是 0，执行插入（`aid` 改成实际的平台管理员账号 Id）：
```javascript
db.admins.insert({
  "_id" : ObjectId("630c6dd278e2a33484477aec"),
  "aid" : "<平台管理员账号Id>",
  "utime" : ISODate("2022-08-29T07:42:10.901+0000"),
  "ctime" : ISODate("2022-08-29T07:42:10.901+0000"),
  "__v" : NumberInt(0)
});
```

### 核验
`db.admins.count()` 返回 1，重新登录平台管理后台后系统配置正常显示。

## mysql-hacked-restore-account-project-id — MySQL 被黑后还原 AccountId / ProjectId 映射


> ⚠️ **高危（数据删除操作）**：执行前请与 HAP 运维实施确认，并务必先做好快照 / 数据备份。操作不可逆。

### 场景
MySQL 被黑、重新部署并还原 mongodb / file 后，MySQL 里的 AccountId、ProjectId 与原值不一致，需改回原来存在的值。
下例：旧管理员 `f0fb8754-...` → 原值 `c74bba75-...`；旧组织 `27b1142f-...` → 原值 `09c0c0df-...`。按实际替换。**先备份。**

```sql
-- AccountId 还原
update Account            set AccountId="c74bba75-bbd4-4066-bf67-edc6e9b8fb53" where AccountId="f0fb8754-65ff-415e-b1a1-82ee48ba5da1";
update AccountExpand      set AccountId="c74bba75-bbd4-4066-bf67-edc6e9b8fb53" where AccountId="f0fb8754-65ff-415e-b1a1-82ee48ba5da1";
update AccountInfo        set AccountId="c74bba75-bbd4-4066-bf67-edc6e9b8fb53" where AccountId="f0fb8754-65ff-415e-b1a1-82ee48ba5da1";
update AccountStatistic   set AccountId="c74bba75-bbd4-4066-bf67-edc6e9b8fb53" where AccountId="f0fb8754-65ff-415e-b1a1-82ee48ba5da1";
update Account_MedalGrantLog set ToAccountId="c74bba75-bbd4-4066-bf67-edc6e9b8fb53" where ToAccountId="f0fb8754-65ff-415e-b1a1-82ee48ba5da1";
update RoutingAccount     set AccountId="c74bba75-bbd4-4066-bf67-edc6e9b8fb53" where AccountId="f0fb8754-65ff-415e-b1a1-82ee48ba5da1";
update RoutingProjectExpand set CreateUser="c74bba75-bbd4-4066-bf67-edc6e9b8fb53" where CreateUser="f0fb8754-65ff-415e-b1a1-82ee48ba5da1";
update RoutingUserExpand  set AccountID="c74bba75-bbd4-4066-bf67-edc6e9b8fb53" where AccountID="f0fb8754-65ff-415e-b1a1-82ee48ba5da1";
update UsersCard          set AccountId="c74bba75-bbd4-4066-bf67-edc6e9b8fb53",LastModifyUser="c74bba75-bbd4-4066-bf67-edc6e9b8fb53" where AccountId="f0fb8754-65ff-415e-b1a1-82ee48ba5da1";

update Role           set CreateUser="c74bba75-bbd4-4066-bf67-edc6e9b8fb53",LastModifyUser="c74bba75-bbd4-4066-bf67-edc6e9b8fb53";
update RolePermission set CreateUser="c74bba75-bbd4-4066-bf67-edc6e9b8fb53",LastModifyUser="c74bba75-bbd4-4066-bf67-edc6e9b8fb53";
update UserRole       set AccountID="c74bba75-bbd4-4066-bf67-edc6e9b8fb53",CreateUser="c74bba75-bbd4-4066-bf67-edc6e9b8fb53",LastModifyUser="c74bba75-bbd4-4066-bf67-edc6e9b8fb53";

-- ProjectId 还原
update Project          set ProjectID="09c0c0df-3c1a-41ea-9058-e04a9e1a7d87" where ProjectID="27b1142f-2b6b-4351-8f33-cf0f2a2b885c";
update Project_Source   set ProjectID="09c0c0df-3c1a-41ea-9058-e04a9e1a7d87" where ProjectID="27b1142f-2b6b-4351-8f33-cf0f2a2b885c";
update Role             set EntityId="09c0c0df-3c1a-41ea-9058-e04a9e1a7d87" where EntityId="27b1142f-2b6b-4351-8f33-cf0f2a2b885c";
update RolePermission   set EntityId="09c0c0df-3c1a-41ea-9058-e04a9e1a7d87" where EntityId="27b1142f-2b6b-4351-8f33-cf0f2a2b885c";
update RoutingAccount   set ProjectID="09c0c0df-3c1a-41ea-9058-e04a9e1a7d87" where ProjectID="27b1142f-2b6b-4351-8f33-cf0f2a2b885c";
update RoutingProject   set ProjectID="09c0c0df-3c1a-41ea-9058-e04a9e1a7d87" where ProjectID="27b1142f-2b6b-4351-8f33-cf0f2a2b885c";
update RoutingProjectExpand set ProjectID="09c0c0df-3c1a-41ea-9058-e04a9e1a7d87" where ProjectID="27b1142f-2b6b-4351-8f33-cf0f2a2b885c";
update RoutingUserExpand set ProjectID="09c0c0df-3c1a-41ea-9058-e04a9e1a7d87" where ProjectID="27b1142f-2b6b-4351-8f33-cf0f2a2b885c";
update UserRole         set EntityId="09c0c0df-3c1a-41ea-9058-e04a9e1a7d87" where EntityId="27b1142f-2b6b-4351-8f33-cf0f2a2b885c";
update UsersCard        set ProjectId="09c0c0df-3c1a-41ea-9058-e04a9e1a7d87" where ProjectId="27b1142f-2b6b-4351-8f33-cf0f2a2b885c";
```
最后 Redis `flushall`。

### 核验
- `SELECT COUNT(*) FROM Account WHERE AccountId="<旧AccountId>";` 与 `SELECT COUNT(*) FROM RoutingAccount WHERE ProjectID="<旧ProjectId>";` 均为 0（旧值已全部改回原值）。
- `SELECT COUNT(*) FROM Account WHERE AccountId="<原AccountId>";` 应为 1，各 Routing*/UsersCard 表已指向原 AccountId/ProjectID。
- flushall 后用原管理员账号登录，能进入原组织、看到还原回来的应用与角色权限。

## physically-delete-resigned-users — 物理删除离职用户（Status=4）


> ⚠️ **高危（数据删除操作）**：执行前请与 HAP 运维实施确认，并务必先做好快照 / 数据备份。操作不可逆。

### 场景
彻底物理删除已离职（`RoutingAccount.Status=4`）的账号数据。**不可逆，先备份 MySQL。**

```bash
docker exec -it $(docker ps | grep community | awk '{print $1}') bash
mysql -h 127.0.0.1 -uroot -p123456
```
```sql
USE MDProject;
DELETE FROM Account_Detail   WHERE AccountId IN (SELECT AccountId FROM RoutingAccount WHERE `Status`=4);
DELETE FROM Account_Setting  WHERE AccountId IN (SELECT AccountId FROM RoutingAccount WHERE `Status`=4);
DELETE FROM AccountExpand    WHERE AccountId IN (SELECT AccountId FROM RoutingAccount WHERE `Status`=4);
DELETE FROM AccountInfo      WHERE AccountId IN (SELECT AccountId FROM RoutingAccount WHERE `Status`=4);
DELETE FROM AccountStatistic WHERE AccountId IN (SELECT AccountId FROM RoutingAccount WHERE `Status`=4);
DELETE FROM Project_DepartmentAccount WHERE AccountId IN (SELECT AccountId FROM RoutingAccount WHERE `Status`=4);
DELETE FROM Project_JobAccount        WHERE AccountId IN (SELECT AccountId FROM RoutingAccount WHERE `Status`=4);
DELETE FROM UsersCard        WHERE AccountId IN (SELECT AccountId FROM RoutingAccount WHERE `Status`=4);
DELETE FROM Account          WHERE AccountId IN (SELECT AccountId FROM RoutingAccount WHERE `Status`=4);
DELETE FROM RoutingAccount   WHERE `Status`=4;
```
退出 MySQL，清 Redis 离职用户缓存：
```bash
# 集群
redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD --scan --pattern "h:pu:nor:*"  | xargs redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD DEL
redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD --scan --pattern "h:pu:nnor:*" | xargs redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD DEL
# 单机
redis-cli -a 123456 --scan --pattern "h:pu:nor:*"  | xargs redis-cli -a 123456 DEL
redis-cli -a 123456 --scan --pattern "h:pu:nnor:*" | xargs redis-cli -a 123456 DEL
```

### 核验
- `SELECT COUNT(*) FROM RoutingAccount WHERE \`Status\`=4;` 应为 0；删前先记下该 count，删后各 Account_* 表中已无对应 AccountId。
- 在职用户不受影响：`SELECT COUNT(*) FROM RoutingAccount WHERE \`Status\`<>4;` 删前后数值一致。
- Redis 已清：`redis-cli -a 123456 --scan --pattern "h:pu:nor:*"` 无输出，离职用户登录/查询不再命中旧缓存。

## reset-departments — 重置部门（清空部门数据）


> ⚠️ **高危（数据删除操作）**：执行前请与 HAP 运维实施确认，并务必先做好快照 / 数据备份。操作不可逆。

> Redis flushall 仅限测试阶段。

### 场景
要清空 / 重置部门数据（重新导入组织架构前）。

```sql
-- MySQL
USE MDProject;
DELETE FROM Project_Department;
DELETE FROM Project_DepartmentAccount;
UPDATE UsersCard SET Department=NULL, DepartmentId=NULL;
```
```js
// MongoDB
use mdworkweixin
db.departmentRelation.remove({})
```
```
# Redis（仅测试阶段）
flushall
```

### 核验
- `SELECT COUNT(*) FROM Project_Department;`、`SELECT COUNT(*) FROM Project_DepartmentAccount;` 均为 0；`SELECT COUNT(*) FROM UsersCard WHERE DepartmentId IS NOT NULL;` 为 0。
- `db.departmentRelation.count({})` 为 0。重新导入组织架构后部门页正常显示新数据。

## reset-job-position — 重置职位数据


> ⚠️ **高危（数据删除操作）**：执行前请与 HAP 运维实施确认，并务必先做好快照 / 数据备份。操作不可逆。

### 场景
要清空 / 重置职位数据。

```sql
-- 清理 MySQL
USE MDProject;
DELETE FROM Project_Job;
DELETE FROM Project_JobAccount;
UPDATE UsersCard SET Job=NULL, JobId=NULL;
```
清理 Redis：`flushall`（**仅限测试阶段**，生产按精确前缀删见 [[clear-dept-contact-redis-cache]]）。

### 核验
- `SELECT COUNT(*) FROM Project_Job;`、`SELECT COUNT(*) FROM Project_JobAccount;` 均为 0；`SELECT COUNT(*) FROM UsersCard WHERE JobId IS NOT NULL;` 为 0。
- 通讯录/人员资料页职位字段已清空，重新导入后显示新职位。

## reset-org-structure — 重置人员与组织架构（仅保留一个初始管理员账号）


> ⚠️ **高危（数据删除操作）**：执行前请与 HAP 运维实施确认，并务必先做好快照 / 数据备份。操作不可逆。

### 场景
清空全部人员与组织架构，只保留一个初始化账号。**该账号必须是组织超级管理员 + 平台管理员。不可逆，先备份。**
下例保留账号 Id `55cc6e83-2a19-4e9a-acf2-03825e9e11a2`，按实际替换。

### 清理 MySQL
```sql
USE MDProject;
DELETE FROM Account_Detail   WHERE AccountId NOT IN ("55cc6e83-2a19-4e9a-acf2-03825e9e11a2");
DELETE FROM Account_Setting  WHERE AccountId NOT IN ("55cc6e83-2a19-4e9a-acf2-03825e9e11a2");
DELETE FROM AccountExpand    WHERE AccountId NOT IN ("55cc6e83-2a19-4e9a-acf2-03825e9e11a2");
DELETE FROM AccountInfo      WHERE AccountId NOT IN ("55cc6e83-2a19-4e9a-acf2-03825e9e11a2");
DELETE FROM AccountStatistic WHERE AccountId NOT IN ("55cc6e83-2a19-4e9a-acf2-03825e9e11a2");

DELETE FROM Project_Department;
DELETE FROM Project_DepartmentAccount;
DELETE FROM Project_Job;
DELETE FROM Project_JobAccount;
DELETE FROM Project_Organize;
DELETE FROM Project_OrganizeAccount;
DELETE FROM Project_OrganizeType;

DELETE FROM RoutingAccount WHERE AccountId NOT IN ("55cc6e83-2a19-4e9a-acf2-03825e9e11a2");
DELETE FROM Account        WHERE AccountId NOT IN ("55cc6e83-2a19-4e9a-acf2-03825e9e11a2");
DELETE FROM UsersCard      WHERE AccountId NOT IN ("55cc6e83-2a19-4e9a-acf2-03825e9e11a2");

USE MDStructure;
DELETE FROM MD_Structure;
DELETE FROM StructureLog;
```

### 清理 MongoDB
```javascript
use mdworkweixin
db.userRelation.remove({})
db.departmentRelation.remove({})
db.jobRelation.remove({})

use MDSso
db.accounts.remove({})
```

### 清理 Redis
`flushall`（仅测试阶段；生产按前缀精确删）。

### 核验
- `SELECT COUNT(*) FROM Account;` 应为 1，且 `SELECT AccountId FROM Account;` 即保留的初始账号 Id；`db.accounts.count({})`（MDSso）为 1。
- `Project_Department`/`Project_Job`/`Project_Organize` 等组织表 count 全为 0；`db.userRelation.count({})`、`db.departmentRelation.count({})`、`db.jobRelation.count({})` 均为 0。
- 用保留账号登录可进入，且确认其为组织超级管理员 + 平台管理员（误删则只剩无法登录的空组织）。

## reset-region — 重置地区数据


### 场景
要重置地区数据（地区库异常 / 需刷新）。

进入容器：`docker exec -it $(docker ps | grep community | awk '{print $1}') bash`

### 任意一台微服务容器执行
```bash
# 1. 重置地区
source /entrypoint.sh && mongodbResetRegion

# 2. 清 Redis 地区缓存
# 单机
redis-cli -a 123456 KEYS "md:city:v4:" | xargs redis-cli -a 123456 DEL
# 集群
redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD KEYS "md:city:v4:" | xargs redis-cli -h $ENV_REDIS_HOST -p $ENV_REDIS_PORT -a $ENV_REDIS_PASSWORD DEL
```

### 每台微服务容器都要执行（重启相关服务）
```bash
source /entrypoint.sh && wwwapiShutdown
source /entrypoint.sh && wwwapiconsumerShutdown
source /entrypoint.sh && apiShutdown
```

### 核验
- `redis-cli -a 123456 KEYS "md:city:v4:"` 无输出（缓存已清）；相关服务重启后会重新生成。
- 前端打开任意带地区选择的字段，省/市/区联动正常加载，确认地区库已重置刷新。

