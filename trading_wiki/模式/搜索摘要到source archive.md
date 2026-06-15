---
title: "搜索摘要到source archive"
type: pattern
folder: 模式
created: 2026-06-11
updated: 2026-06-11
status: active
evidence_level: low
execution_permission: observe_only
source_links:
  - "[[2026-06-11 微信财经产业舆情]]"
tags:
  - trading/wiki/pattern
---

# 搜索摘要到source archive

## 模式定义

当只能读取微信搜索结果标题和摘要，无法进入完整正文时，把搜索摘要保存为 source archive，并明确标记为低证据。

## 触发条件

- 微信文章跳转触发反爬。
- 搜索结果摘要能看到产业关键词。
- 需要快速建立当日舆情索引。

## 典型路径

1. 搜索日期 + 产业关键词。
2. 保存标题、摘要、检索词、时间。
3. 写入 `sources/YYYY-MM-DD.md`。
4. 只生成观察级概念页。
5. 后续用完整正文、公告、订单验证。

## 风险

- 摘要不完整，可能断章取义。
- 搜索结果可能混入噪声。
- 标题党会放大热度。

## 关联错误

- [[把微信搜索摘要当完整正文]]

## 变更记录

- 2026-06-11: 按模式页重写。
