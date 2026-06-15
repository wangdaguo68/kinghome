---
title: "Embedding与语义搜索"
type: concept
folder: 概念
domain: 智能系统
system: 智能系统
systems:
  - 智能系统
note_type: concept
created: 2026-06-14
updated: 2026-06-14
status: active
confidence: medium
evidence_level: medium
execution_permission: learning_only
topics:
  - Embedding
  - 语义搜索
  - 向量
tags:
  - knowledge/ai/embedding
related_questions:
  - Embedding如何表示语义？
  - 语义搜索和关键词搜索有什么区别？
  - 为什么个人知识库需要语义搜索？
---

# Embedding与语义搜索

## 一句话解释

Embedding 是把文本、图片或其他对象转成向量，使机器可以用距离和相似度计算语义关系。语义搜索不是只匹配关键词，而是找意思接近的内容。

## 关键词搜索 vs 语义搜索

| 搜索方式 | 优点 | 缺点 |
| --- | --- | --- |
| 关键词搜索 | 精准、可解释、快 | 同义词和隐含关系弱 |
| 语义搜索 | 能找意思相近内容 | 可能召回不精确，需要校验 |
| 混合搜索 | 结合两者 | 系统复杂度更高 |

## 个人知识库用法

用户问“AI算力扩张会影响哪些材料”，语义搜索应找到 HBM、ABF载板、电子布、铜箔、液冷、导热材料、电力设备等，而不是只找标题里含“材料”的页面。

## 风险和误区

- 向量相似不等于事实正确。
- 语义搜索适合找线索，不等于最终答案。
- 垃圾文档向量化后仍然是垃圾知识。

## 关联知识

- [[RAG与向量数据库]]
- [[Transformer Token与参数]]
- [[AI半导体材料与原料全景]]

