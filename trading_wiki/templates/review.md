---
title: "{{title}}"
type: review
created: {{date}}
updated: {{date}}
status: pending
evidence_level: {{evidence_level}}
execution_permission: observe_only
source_hash: "{{source_hash}}"
tags:
  - trading/wiki/review
---

# {{title}}

## 摄入摘要

- 原始文件: `{{raw_path}}`
- Source archive: [[{{source_title}}]]
- 来源哈希: `{{source_hash}}`
- 默认证据强度: {{evidence_level}}
- 默认执行权限: observe_only

## 安全检查

{{safety_results}}

## 候选新建页面

勾选后可运行：

```powershell
python scripts/ingest.py apply-review --review reviews/{{review_filename}}
```

### 概念

{{concept_candidates}}

### 标的

{{stock_candidates}}

### 策略

{{strategy_candidates}}

### 模式

{{pattern_candidates}}

### 错误

{{mistake_candidates}}

## 候选更新旧页面

{{update_candidates}}

## 需要验证的事实

- [ ] 补充公告、订单、价格、产能、客户或财务验证。
- [ ] 区分事实、假设、情绪和估值表达。
- [ ] 确认每个标的映射是否有业务承接路径。

## AI 辅助提示词

```text
你是交易知识库审查助手。请基于下面 raw 摘录，输出：
1. 候选新概念
2. 候选更新的旧概念
3. 相关标的及其正面逻辑
4. 每条线索的事实强度：high / medium / low / unknown
5. 执行权限：none / observe_only / needs_verification / watchlist / candidate
6. 必须验证的事实和反证

约束：
- 群聊、传闻、小作文、单源文章不能单独提升到 watchlist 或 candidate。
- 不给买卖建议。
- 每条结论必须链接到 source archive：[[{{source_title}}]]

Raw 摘录：
{{raw_excerpt}}
```
