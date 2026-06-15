---
title: "{{title}}"
type: source
created: {{date}}
updated: {{date}}
status: active
evidence_level: {{evidence_level}}
execution_permission: observe_only
source_type: {{source_type}}
source_hash: "{{source_hash}}"
tags:
  - trading/wiki/source
---

# {{title}}

## 来源定位

- 原始文件: `{{raw_path}}`
- 外部链接: {{source_url}}
- 摄入时间: {{generated_at}}
- 来源哈希: `{{source_hash}}`

## 使用边界

本页是 {{date}} 的清洗版 source archive，用于保存当日信息的传播路径、关键原始节点、证据强度和后续引用依据。

它不是公告页，不是正式研报，也不是复盘权威结论。低质量来源只能用于记录热度、提出假设和生成验证清单，不能直接升级为交易事实。

## 证据强度分层

| 层级 | 信息类型 | 本源代表 | 处理方式 |
| --- | --- | --- | --- |
| 高 | 公告/官方行动/订单证据 | 待补充 | 可作为事实锚，但仍需映射到具体公司和时间 |
| 中 | 可信媒体/研报/会议纪要/多源验证 | 待补充 | 可进入验证表，跟踪订单、产能、价格和收入确认 |
| 低 | 群聊/传闻/小作文/单源文章 | 当前输入 | 只能作为热度和假设来源，不能单独提升执行权限 |
| 未知 | 无法定位来源 | 待补充 | 暂不进入核心结论 |

## 当日主题

{{themes}}

## 候选页面更新

{{candidate_links}}

## 验证清单

- [ ] 把低质量来源中的事实性表达降级为假设。
- [ ] 为每条重要催化补充公告、订单、价格、产能、客户或财务验证。
- [ ] 将新增概念与相近页面区分清楚，避免重复建页。
- [ ] 检查所有标的映射是否有明确业务承接路径。

## 原始摘录

```text
{{raw_excerpt}}
```
