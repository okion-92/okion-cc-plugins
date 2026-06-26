---
title: HAP 升级官方页面与 URL 规律
source_url: https://docs-pd.mingdao.com/version
last_verified: 2026-03-11   # 继承自 skill 快照，未对实时页复核；维护时需重抓 /version
hap_version: any
tags: [upgrade, docs, reference]
feeds: [hap-upgrade, hap-docs-workbench]
---

## 站点
- 基础 URL：`https://docs-pd.mingdao.com`（Docusaurus，路径即页面；英文加 `/en/` 前缀）
- **唯一兼容性准则**：`/version` 实时页面。任何本地快照表都不能当结论——本文件只给 URL 规律，不存版本兼容数据。

## 关键页面
| 用途 | URL |
|---|---|
| 版本发布历史 ⭐ | `/version` |
| 升级详情页 | `/upgrade/{应用版本}/`（如 `/upgrade/7.2.0/`） |
| 镜像命名变更历史 | `/imagenamehistory` |
| 单机-数据备份 | `/deployment/docker-compose/standalone/data/backup` |
| 单机-MongoDB 预置数据 | `/deployment/docker-compose/standalone/data/preset/mongodb` |
| 单机-HAP 微服务升级 | `/deployment/docker-compose/standalone/upgrade/hap` |
| 单机-存储组件升级 | `/deployment/docker-compose/standalone/upgrade/sc` |
| 集群-MongoDB 预置数据 | `/deployment/kubernetes/data/preset/mongodb` |
| 集群-HAP 微服务升级 | `/deployment/kubernetes/upgrade/hap` |
| 离线资源包 | `/deployment/offline` |
| 组件支持版本 | `/deployment/component` |
| MongoDB 新建库/常用命令 | `/deployment/components/mongodb/createdb`、`/command` |

> 集群模式**没有**存储组件升级步骤，别在集群升级文档里生成该步。

## `/version` 字段含义
| 字段 | 含义 |
|---|---|
| 含附加操作 | `√`=升级有额外必做操作，必须访问对应 `/upgrade/{ver}/` 详情页 |
| AMD64 / ARM64 | `✅`=支持，空白=不支持 |

## 版本命名与维护策略
- 主版本：第三位为 `0`（v7.2.0）；修复版本：第三位 >0（v7.1.1）。
- 默认维护最新 3 个主版本；同主版本选第三位最大的修复版本升。
- 超维护范围版本仍可下载使用，但不再修功能问题。
