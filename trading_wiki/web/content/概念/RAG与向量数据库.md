---
title: "RAG与向量数据库"
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
  - RAG
  - 向量数据库
  - 知识库
tags:
  - knowledge/ai/rag
related_questions:
  - RAG为什么适合个人知识库？
  - 向量数据库解决什么问题？
  - RAG为什么不能完全消除幻觉？
---

# RAG与向量数据库

## 一句话解释

RAG 是检索增强生成：先从外部知识库找相关资料，再让大模型基于资料回答。向量数据库常用于存储和检索语义相近的文本块。

## RAG流程

1. 文档切块。
2. 生成 Embedding。
3. 存入向量数据库。
4. 用户提问。
5. 检索相关片段。
6. 把片段放进 Prompt。
7. 模型生成答案。

## 关键设计点

| 设计点 | 影响 |
| --- | --- |
| 切块方式 | 太大噪音多，太小缺上下文 |
| Embedding模型 | 决定语义召回质量 |
| 检索策略 | 影响是否找到正确材料 |
| 重排序 | 提高相关性 |
| 引用和证据 | 降低胡编风险 |
| 权限控制 | 防止读取不该读取的内容 |

## 我的启发

个人知识库最终应该支持 RAG，但前提是 Markdown 内容结构化。现在先把每篇笔记写成“定义、原理、案例、启发、误区、关联”，以后向量检索才有质量。

## 风险和误区

- RAG 不等于不会幻觉。
- 搜到错误资料，模型会更自信地错。
- 文档质量比向量数据库品牌更重要。

## 关联知识

- [[Embedding与语义搜索]]
- [[个人知识库九大系统地图]]
- [[AI幻觉与安全边界]]

