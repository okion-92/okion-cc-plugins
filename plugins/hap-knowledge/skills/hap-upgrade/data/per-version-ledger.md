---
title: HAP 逐版本升级动作明细台账（3.1.0~7.3.4 集群，实时核验）
source_url: https://docs-pd.mingdao.com/version
last_verified: 2026-06-18   # 逐页抓 /upgrade/{ver}/，集群模式；DDL 路径/命令转录自官方页，执行前对页面再核
hap_version: any
tags: [upgrade, per-version, ledger, ddl]
feeds: [hap-upgrade]
---

生成跨版本升级文档时，**逐版本读 `/upgrade/{ver}/` 取真实内容，按低→高铺进文档**（不要变量化模板）。本台账是 3.1.0→7.3.4 集群路径的实测结果，可直接用；其它路径同法逐页抓。
约定：MySQL DDL 走 `mysql -h $ENV_MYSQL_HOST -P $ENV_MYSQL_PORT -u$ENV_MYSQL_USERNAME -p$ENV_MYSQL_PASSWORD --default-character-set=utf8 [-N] < {脚本}`；MongoDB 走进 config Pod 后 `source /entrypoint.sh && mongodbExecute {库} {脚本}`。下表只列各版本"增量"。

| 版本 | 服务/配置变更 | MySQL | MongoDB / 数据 | 组件 | 升级后(config Pod) |
|---|---|---|---|---|---|
| 3.4.0 | 建库 `mdintegration`(认证) | `USE MDProject;` 建 3 表（完整 DDL 见文末附录） | — | — | `fileInit` |
| 3.5.1 | — | 索引重置 `/init/mysql/Mysql_Reset_Index_MDProject.sql` | — | — | — |
| 3.6.0 | — | — | — | file→1.4.0 | — |
| 3.7.0 | 建库 `mdworksheetlog`(认证) | — | — | — | — |
| 3.8.0 | — | DML `/init/mysql/3.8.0/DML.sql`(启用自建应用库) | — | — | `fileInit` |
| 3.9.0 | 建库 `mdworksheetsearch`(认证) | — | — | ES→8.5.3 | `resetCollaborationIndex` |
| 4.0.0 | 建库 `mddatapipeline`(认证)；集群 Kafka `server.properties` 加 `message.max.bytes=10485760`/`replica.fetch.max.bytes=10485760` | `/init/mysql/4.0.0/DDL.sql` | — | — | `fileInit` |
| 4.1.0 | — | `/init/mysql/4.1.0/DDL.sql` | — | — | `fileInit` |
| 4.4.0 | **+服务 templatemessage**(3259) | — | — | — | `mongodbResetTemplateMessage` |
| 4.5.0 | **+服务 wps**(9017) | — | `mongodbExecute commonbase /init/mongodb/4.5.0/commonbase/DDL.txt`；`mdservicedata`；`mdapps` | — | `mongodbResetTemplateMessage` + 上述 3 库 |
| 4.7.0 | Flink→1.15.3.470(启用才需) | — | `mongodbExecute mdapps /init/mongodb/4.7.0/mdapps/DDL.txt` | — | 上述 |
| 5.0.0 | **+服务 reportconsumer**；Docker≥20.10.16 | — | `mongodbExecute mdapps /init/mongodb/5.0.0/mdapps/DDL.txt`；`mdmap` | file→1.5.0 | `mongodbResetTemplateMessage` + 上述 2 库 |
| 5.0.2 | （仅 ARM64：MariaDB→MySQL 迁移，**AMD64 无需**） | — | — | — | — |
| 5.1.0 | command 镜像→`mingdaoyun-command:node1018-python36`(清持久化重装扩展)；**+服务 computingschedule**(9158http+9159grpc)；**[仅单机]** 地址 `127.0.0.1`→`sc`（集群无 sc，不做） | — | — | — | — |
| 5.2.0 | — | `/init/mysql/5.2.0/DDL.sql`（集群 `-h $ENV_MYSQL_HOST`；**单机才** `-h sc`） | `mongodbExecute mdapps /init/mongodb/5.2.0/mdapps/DDL.txt` | **[仅单机]** sc→2.0.0 | `fileInit` + `mongodbResetTemplateMessage` + mdapps |
| 5.3.0 | **+服务 commandpuppeteer**(9198) | — | `mongodbExecute` mdapps/mdattachment/mdIdentification/mdkc `/init/mongodb/5.3.0/{库}/DDL.txt` | — | `mongodbResetTemplateMessage` + 上述 4 库 |
| 5.4.0 | **+服务 datamanager**(8322)；file 服务加 env `ENV_FILE_DOMAIN` | — | — | file→1.6.0 | — |
| 5.5.0 | ★**MongoDB 3.4.24→4.4.30 逐级升**(3.4→3.6→4.0→4.2→4.4 + 每级 setFeatureCompatibilityVersion)；**切换为副本集**(供 5.6.0 聚合表，命令见 [[command-library]] §MongoDB 升级) | — | 升级后**重建 mdwsrows 全部自建索引**(集群 `reIndexWithCmd.js`) | **[仅单机]** sc→3.0.0 | reIndex |
| 5.6.0 | （可选启用聚合表，见 threshold-actions §六） | — | `mongodbExecute` mdapps/mdattachment/mdservicedata `/init/mongodb/5.6.0/{库}/DDL.txt` | — | `mongodbResetTemplateMessage` + 上述 3 库 |
| 5.6.4 | — | `/init/mysql/5.6.4/DDL.sql` | — | — | MySQL |
| 5.7.0 | — | — | `mongodbExecute mdapps /init/mongodb/5.7.0/mdapps/DDL.txt` | — | `mongodbResetTemplateMessage` + mdapps |
| 5.8.0 | **+服务 workflowplugin**(8087+9087)；push +gRPC 3009；建库 `mdwfplugin`(认证) | — | — | — | `mongodbResetTemplateMessage` |
| 6.0.0 | 前置 MongoDB≥4.4 | `/init/mysql/6.0.0/DDL.sql`(组织角色ID字段) | `mongodbExecute mdapps /init/mongodb/6.0.0/mdapps/DDL.txt` | — | `fileInit` + `mongodbResetTemplateMessage` + mdapps |
| 6.1.0 | — | — | `mongodbExecute` mdmap/mdworksheet/mdattachment `/init/mongodb/6.1.0/{库}/DDL.txt` | — | `mongodbResetTemplateMessage` + 上述 3 库 |
| 6.2.0 | **+服务 payment**(9161)；建库 `mdpayment`(认证) | — | `mongodbExecute` mdapps/mdmap/mdpayment `/init/mongodb/6.2.0/{库}/DDL.txt` | file→1.7.0 · doc→2.0.0 · sc→3.1.0 | `mongodbResetTemplateMessage` + 上述 3 库 |
| 6.2.4 | — | — | — | ldoc→2.0.1（仅 LibreOffice） | — |
| 6.2.5 | — | — | — | ldoc→**2.0.2**（仅 LibreOffice，ldoc 终版） | — |
| 6.3.0 | — | `/init/mysql/6.3.0/DDL.sql`(加 `-N`) | `mongodbExecute mdapps /init/mongodb/6.3.0/mdapps/DDL.txt`；`mongodbResetRegion` | — | `fileInit` + `mongodbResetRegion` + `mongodbResetTemplateMessage` + mdapps |
| 6.4.0 | — | — | — | sc→3.2.0；Kafka 3.9.1 / Redis 8.6.3(**推荐非强制**) | — |
| 6.5.0 | — | `/init/mysql/6.5.0/DDL.sql`(加 `-N`) | `mongodbExecute` mdapps/mdattachment/mdIdentification/mdmap `/init/mongodb/6.5.0/{库}/DDL.txt` | — | MySQL + 上述 4 库 |
| 7.0.0 | **+服务 ai**(8066)+**mcp**(8165)；建库 `mdwfai`(认证) | `/init/mysql/7.0.0/DDL.sql`(组织角色停用字段，加 `-N`) | `mongodbExecute` mdapps/mdpayment/mdworksheet/mdworkweixin `/init/mongodb/7.0.0/{库}/DDL.txt` | — | `fileInit` + MySQL + 上述 4 库 |
| 7.1.0 | ★镜像改名 community→hap(sed，单机+集群) | — | — | — | — |
| 7.2.0 | — | — | `mongodbExecute` mdapps/mdmap/mdworksheet/mdworkweixin/mdinbox `/init/mongodb/7.2.0/{库}/DDL.txt`；预置数据更新到 7.2.0 | — | 上述 5 库 + 预置数据 |
| 7.2.4 | — | `/init/mysql/7.2.4/DDL.sql`(加 `-N`) | — | — | MySQL |
| 7.3.0 | **−服务 pushserver**；**+platformapi**(1317)+**openauthorization**(5322)；建库 `mdopenauth`/`mdaisearch`(认证) | — | `mongodbExecute` mdIdentification/mdopenauth `/init/mongodb/7.3.0/{库}/DDL.txt` | — | `fileInit` + 上述 2 库 |
| 7.3.4 | （终点；7.3.1~7.3.4 无结构动作）| — | 预置数据最终更新到 7.3.4 | — | 预置数据 7.3.4 |

## 执行顺序总则（固定，避免错乱）
**升级前（微服务升级之前）**：① 备份 → ② 镜像改名(跨7.1.0) → ③ 地址 127→sc(5.1.0) → ④ command 换镜像(5.1.0) → ⑤ service.yaml 改齐(新增服务/删 pushserver/push 加 gRPC/ENV_FILE_DOMAIN) → ⑥ Kafka server.properties(4.0.0) → ⑦ 认证建库(全部) → ⑧ MongoDB 引擎升 4.4 + HAP 自有组件(file/doc/sc) 升级。
**微服务升级**：`update.sh update hap {目标版本}`。
**升级后（进 config Pod，固定六段顺序）**：① `fileInit` → ② 各版本 **MySQL DDL 低→高** → ③ 各版本 **MongoDB DDL（mongodbExecute）低→高** → ④ 专项重建（`resetCollaborationIndex` 3.9 / `mongodbResetRegion` 6.3 / `mdwsrows` reIndex 5.5——均在终版上执行一次）→ ⑤ `mongodbResetTemplateMessage`（多版本要求，合并最后一次）→ ⑥ 预置数据更新到终版。
> MySQL 与 MongoDB 是独立存储，跨存储无依赖，故分块各自低→高即可；"重建/重置"类操作在最终版本执行一次比逐版本执行更正确。

## 附录：3.4.0 inline 建表 DDL（MDProject，非 /init 脚本）
```sql
USE MDProject;

CREATE TABLE `Project_Organize` (
  `AutoID` int(11) NOT NULL AUTO_INCREMENT,
  `OrganizeID` char(36) NOT NULL,
  `OrganizeTypeID` char(36) DEFAULT NULL,
  `OrganizeName` varchar(128) DEFAULT NULL,
  `ProjectID` char(36) NOT NULL,
  `Remark` text,
  `SortIndex` int(11) NOT NULL,
  `CreateUser` char(36) DEFAULT NULL,
  `LastModifyUser` char(36) DEFAULT NULL,
  `CreateTime` datetime DEFAULT NULL,
  `UpdateTime` datetime DEFAULT NULL,
  PRIMARY KEY (`AutoID`),
  KEY `IX_Project_Organize` (`ProjectID`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `Project_OrganizeAccount` (
  `AutoId` int(11) NOT NULL AUTO_INCREMENT,
  `ProjectId` char(36) NOT NULL,
  `OrganizeId` char(36) NOT NULL,
  `AccountId` char(36) NOT NULL,
  `CreateUser` char(36) DEFAULT NULL,
  `CreateTime` datetime NOT NULL,
  `UpdateTime` datetime NOT NULL,
  `LastModifyUser` char(36) DEFAULT NULL,
  PRIMARY KEY (`AutoId`),
  KEY `IX_Project_OrganizAccount_2` (`ProjectId`,`OrganizeId`,`AccountId`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `Project_OrganizeType` (
  `AutoID` int(11) NOT NULL AUTO_INCREMENT,
  `OrganizeTypeID` char(36) NOT NULL,
  `OrganizeTypeName` varchar(128) DEFAULT NULL,
  `IsSysOrganiz` int(11) NOT NULL,
  `CreateUser` char(36) DEFAULT NULL,
  `LastModifyUser` char(36) DEFAULT NULL,
  `ProjectID` char(36) DEFAULT NULL,
  `CreateTime` datetime DEFAULT NULL,
  `UpdateTime` datetime DEFAULT NULL,
  PRIMARY KEY (`AutoID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

> 转录自官方各 `/upgrade/{ver}/`（2026-06-18）。部分页只给参考链接未列脚本（已尽量补全）；执行前对照页面再核。MySQL DDL 多数版本走 `/init/mysql/{ver}/DDL.sql`，MongoDB 走 `/init/mongodb/{ver}/{库}/DDL.txt`。
> **重要核对项**：极老版本（如 3.4.0 inline 建表）的 `/init` 脚本是否存在于目标镜像、是否已被累积迁移覆盖，执行前需在目标镜像 `/init` 目录核对；缺失则说明已被后续版本累积处理，跳过即可。
