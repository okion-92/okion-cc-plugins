# 集成（钉钉 / 企微 / 微信）

> 由 sources/faq/ 生成，勿手改。每条 `## <slug>` 对应一个 source 文件，可在 ROUTING.md 反查。

## bind-mingdao-wework-account — 手动绑定明道云账号与企业微信账号关系


### 场景
需手动把明道云账号与企业微信账号建立绑定关系（自动同步未建关系时）。

### 参数获取
- **明道云组织编号**：组织管理 》组织信息 》组织编号。
- **明道云账号Id**：点头像进个人详情，URL `.../user_082bd16d-...` 中 `user_` 后即账号Id。
- **企业微信账号Id**：企业微信字段，从企业微信管理后台获取。

### 插入绑定关系
连接 mongodb 后：
```javascript
use mdworkweixin
db.userRelation.insertMany([
  { "cid":"明道云组织编号", "cuid":"企业微信账号Id",  "unionid":"", "status":1, "pid":"明道云组织编号", "aid":"明道云账号Id"  },
  { "cid":"明道云组织编号", "cuid":"企业微信账号Id2", "unionid":"", "status":1, "pid":"明道云组织编号", "aid":"明道云账号Id2" }
]);
```
> 解绑（删 cuid）见 [[unbind-oa-wework-account-cuid]]。

## dingtalk-connectivity-test-curl — 在 integrate 容器内 curl 测试个人钉钉连通性


### 场景
钉钉集成异常时，在 integrate 容器内 curl 测试钉钉接口连通性。

```bash
# 进 integrate 容器
kubectl exec -it $(kubectl get po|grep integrate-|awk '{print $1}') -- bash

# 1. 用钉钉后台 ClientId/ClientSecret 取 access_token
curl --header "Content-Type: application/json" --request GET \
"https://oapi.dingtalk.com/gettoken?appkey=<appkey>&appsecret=<appsecret>"

# 2. 取 userid：页面用户资料地址栏 user_ 后即 accountid，到 mongodb mdworkweixin.userRelation 查
#    aid=accountid, cuid=userid
db.userRelation.find({"aid": "<accountid>"});

# 3. 发测试消息（userid_list / access_token 换实际）
curl --header "Content-Type: application/json" --request POST \
--data '{"agent_id":"<agentId>","userid_list":"<userid>","msg":{"msgtype":"markdown","markdown":{"title":"通知","text":"### 通知 \n test"}}}' \
"https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2?access_token=<access_token>"
```

## dingtalk-sync-qps-single-thread — 钉钉同步无反应/QPS 流控 — 改单线程执行


现象：钉钉同步点击无反应，日志报"当前接口次数过多，触发了 qps 流控"。把集成改为单线程执行。

### 6.2.3+ 方式（配置项）
开启钉钉日志显示：`"ThirdPartyPushLog": true`，触发时可搜关键词 `sendmessageasync`。
```bash
# 1. 建目录
mkdir -p /data/mingdao/script/volume/integrate/
# 2. 写 /data/mingdao/script/volume/integrate/appextensions.json（已有内容则追加）
{
  "MaxDegreeOfParallelism": 1
}
# 3. 挂载到 app 服务，docker-compose.yaml 的 app volumes 增加：
- ./volume/integrate/appextensions.json:/usr/local/MDPrivateDeployment/integrate/appextensions.json
# 4. 重启 HAP 微服务
```

### 6.2.0 方式（替换 dll）
把附件 `MD.Integrate.Core.dll` 挂载到容器 `/usr/local/MDPrivateDeployment/integrate/MD.Integrate.Core.dll`：
```bash
mkdir -p /data/mingdao/script/volume/integrate/
# 上传 MD.Integrate.Core.dll.tar.gz 到该目录并解压得到 MD.Integrate.Core.dll
ls -l /data/mingdao/script/volume/integrate/MD.Integrate.Core.dll
# docker-compose.yaml app 服务 volumes 新增（空格缩进）：
- ./volume/integrate/MD.Integrate.Core.dll:/usr/local/MDPrivateDeployment/integrate/MD.Integrate.Core.dll
# 重启 HAP 服务
```

## dual-address-wework-scan — 双地址部署模式下企微扫码问题处理（jweixin / OPENRESTY_EXCLUDE_URI）


### 场景
双地址（扩展地址）访问模式下，企业微信扫码登录失败。先判断用户端到 `http://res.wx.qq.com/open/js/jweixin-1.2.0.js` 是否网络通。

### 情况 1：用户端到 jweixin-1.2.0.js 网络通
放通 `GetSignatureInfo` 接口的 openresty 鉴权。

**永久生效**（改 yaml 环境变量）：
```yaml
# 已有 ENV_OPENRESTY_EXCLUDE_URI：在原值末尾追加
|/wwwapi/WorkWeiXin/GetSignatureInfo
# 没有该变量：新增
ENV_OPENRESTY_EXCLUDE_URI: "/orgsso/sso|/wwwapi/WorkWeiXin/GetSignatureInfo"
```

**临时生效**：进入 www 容器编辑 `/usr/local/openresty/nginx/conf/conf.d/mdy.conf`，找到 `/orgsso/sso` 部分追加 `|/wwwapi/WorkWeiXin/GetSignatureInfo`，重载 openresty。

### 情况 2：用户端到 jweixin-1.2.0.js 网络不通
1. 下载 `jweixin-1.2.0.js` 放到 www 容器 `/usr/local/MDPrivateDeployment/www/staticfiles/`。
2. 容器内 openresty 代理文件在 `subsfilter_root` 处加：
   ```nginx
   subs_filter https://res.wx.qq.com/open/js/jweixin-1.2.0.js /zonghang/zxbd/staticfiles/jweixin-1.2.0.js igr;
   ```
3. 同时按情况 1 放通 `GetSignatureInfo`（永久/临时同上）。

> subs_filter 不生效多为上游 gzip 压缩，见 [[nginx-subs-filter-not-working]]。

## platform-wechat-portal-login — 平台版开启外部门户微信登录


### 场景
平台版要开启外部门户的微信扫码登录。

客户按官方文档 `/faq/integrate/platform/portal/weixin` 配置微信开放平台，提供 AppID / AppSecret / 消息校验Token / 消息加解密Key。部署 yaml 加环境变量：
```yaml
ENV_WECHAT_OPEN_APPID: "<AppID>"
ENV_WECHAT_OPEN_SECRET: "<AppSecret>"
ENV_WECHAT_OPEN_TOKEN: "<消息校验Token>"
ENV_WECHAT_OPEN_AESKEY: "<消息加解密Key>"
```

## platform-wework-integration — 平台版开启企业微信集成（挂载 appextensions.json）


### 场景
平台版要开启企业微信集成（挂载 appextensions.json）。

先挂载 2 个文件到容器内（CorpId/Secret/SuiteId 等"客户提供"先占位原样挂载，Token/EncodingAESKey 用官方固定值）：
- `/usr/local/MDPrivateDeployment/integrate/appextensions.json`
- `/usr/local/MDPrivateDeployment/integrateapi/appextensions.json`
```json
{
 "MingWorkWeixin": {
   "CorpId": "<客户提供>",
   "ProviderSecret": "<客户提供>",
   "Token": "PRChy62wo9QAx",
   "EncodingAESKey": "<官方固定AESKey>",
   "Suites": [{
     "Type": 8,
     "Name": "<模板名称,客户提供>",
     "SuiteId": "<模板Id,客户提供>",
     "SuiteSecret": "<模板Secret,客户提供>",
     "Token": "PRChy62wo9QAx",
     "EncodingAESKey": "<官方固定AESKey>",
     "TemplateId": "<同 SuiteId>"
   }]
 }
}
```
明道云提供给客户的回调 URL（Token/AESKey 用上面固定值）：
- 系统事件接收：`{系统地址}/integrateapi/workwx/event/common`
- 代开发模板回调：`{系统地址}/integrateapi/workwx/message/selfbuildapp`、`/integrateapi/workwx/event/selfbuildapp`

客户按 `/faq/integrate/platform/workweixin` 配好后回填 CorpID/ProviderSecret/模板名称/模板ID/模板Secret，改配置文件后重启服务。

## unbind-oa-wework-account-cuid — OA(企业微信)账号解绑 —— 定位 cuid


> 慎重操作，执行前与相关负责人确认；解绑前做好可恢复备份。完整解绑脚本见原记录 .md 附件。

### 场景
要解绑某个企业微信账号与明道云账号的关系（定位 cuid）。

### 第三方用户 ID(cuid) 获取
1. 连 MySQL 拿 AccountId(即 cid)：
```bash
mysql -h $ENV_MYSQL_HOST -P $ENV_MYSQL_PORT -u$ENV_MYSQL_USERNAME -p$ENV_MYSQL_PASSWORD --default-character-set=utf8
```
```sql
use MDProject;
select AccountId from Account where MobilePhone="13000000000";
select AccountId from Account where Email="test@mingdao.com";
select AccountId,Fullname,ContactMobilePhone from AccountInfo where Email="test@mingdao.com";
```
2. 连 MongoDB 用上面的 cid 查 cuid：
```js
use mdworkweixin
db.userRelation.find({cuid:"xxxx-xxxx-xxxx-xxxx"})
```
3. 再执行附件中的清理关系操作（务必先备份）。

