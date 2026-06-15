---
title: "Transformer Token与参数"
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
  - Transformer
  - Token
  - 参数
tags:
  - knowledge/ai/foundation
related_questions:
  - Transformer为什么适合大模型？
  - Token是什么？
  - 参数越多一定越好吗？
---

# Transformer Token与参数

## 一句话解释

Transformer 是大模型的关键架构，Token 是模型处理信息的基本单位，参数是模型在训练中学到的可调权重。三者共同决定模型如何读入信息、建立关联并生成输出。

## 核心原理

| 概念 | 简明解释 | 关键点 |
| --- | --- | --- |
| Token | 文本被切成的计算单位 | 可能是字、词、词片段或符号 |
| Embedding | Token 的向量表示 | 把离散符号变成可计算空间 |
| Attention | 让模型判断哪些 Token 彼此相关 | 长文本理解和上下文关系 |
| Transformer | 以 Attention 为核心的深度网络架构 | 支持大规模并行训练 |
| 参数 | 模型学习到的权重 | 存储统计规律和能力倾向 |

## 典型案例

用户输入一句话，模型先把它拆成 Token，再映射为向量，通过多层 Transformer 计算上下文关系，最后预测下一个 Token，不断生成完整回答。

## 我的启发

理解 Token 很重要，因为它直接影响上下文长度、调用成本、提示词设计和模型输出边界。AI 产品不是只看“模型聪明”，还要看 Token 成本、响应速度和上下文管理。

## 风险和误区

- 参数多不等于一定更好，数据、训练方法、推理优化和任务匹配同样重要。
- Token 不是人类语义的天然单位，它只是模型计算单位。
- Transformer 很强，但不是所有 AI 问题都只能用 Transformer。

## 关联知识

- [[Embedding与语义搜索]]
- [[Scaling Law与大模型训练]]
- [[AI应用层与Agent生态]]

