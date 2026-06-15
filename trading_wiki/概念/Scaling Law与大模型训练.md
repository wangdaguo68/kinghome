---
title: "Scaling Law与大模型训练"
type: concept
folder: 概念
domain: 智能系统
system: 智能系统
systems:
  - 智能系统
  - 范式系统
note_type: concept
created: 2026-06-14
updated: 2026-06-14
status: active
confidence: medium
evidence_level: medium
execution_permission: learning_only
topics:
  - Scaling Law
  - 大模型训练
  - 算力
tags:
  - knowledge/ai/scaling
related_questions:
  - 大模型为什么会随着规模变强？
  - Scaling Law有什么投资和产品意义？
  - 训练和推理有什么区别？
---

# Scaling Law与大模型训练

## 一句话解释

Scaling Law 指模型性能会随着参数、数据和计算量扩大呈现可预测的改善趋势。它解释了为什么大模型时代算力、数据和训练工程变成核心资源。

## 核心原理

| 变量 | 含义 | 约束 |
| --- | --- | --- |
| 参数规模 | 模型容量 | 太大但数据不足会低效 |
| 数据规模 | 训练语料和质量 | 数据质量和去重很关键 |
| 计算量 | 训练所需算力 | 依赖 GPU、网络、存储、能耗 |
| 训练方法 | 优化、对齐、微调 | 决定能力能否稳定释放 |

## 训练 vs 推理

| 阶段 | 做什么 | 产业影响 |
| --- | --- | --- |
| 训练 | 学习统计规律和能力 | 拉动 GPU、HBM、网络、数据中心 |
| 推理 | 根据用户输入生成输出 | 影响成本、延迟、应用商业模式 |

## 我的启发

Scaling Law 不只是技术概念，也是产业判断框架：如果能力提升仍依赖更大算力，就会传导到 AI 服务器、HBM、电力、液冷和资本开支；如果算法效率大幅提升，成本结构和受益环节会变化。

## 风险和误区

- Scaling Law 是经验规律，不是永恒定律。
- 规模提升不自动解决幻觉、推理可靠性和价值对齐。
- 模型能力增强不等于应用一定赚钱。

## 关联知识

- [[AI芯片HBM与先进封装]]
- [[AI数据中心电源液冷与HVDC]]
- [[范式理论与科学革命]]

