---
title: "{{title}}"
type: report
created: {{date}}
updated: {{date}}
status: complete
evidence_level: {{evidence_level}}
execution_permission: observe_only
source_hash: "{{source_hash}}"
tags:
  - trading/wiki/report
---

# {{title}}

## 处理结果

- 原始文件: `{{raw_path}}`
- Source archive: [[{{source_title}}]]
- Review: [[{{review_title}}]]
- 来源哈希: `{{source_hash}}`

## 文件变更

| 类型 | 路径 | 动作 |
| --- | --- | --- |
{{file_changes}}

## 安全检查

{{safety_results}}

## 下一步

1. 打开 [[{{review_title}}]]。
2. 勾选确认要新建的页面。
3. 运行 `python scripts/ingest.py apply-review --review reviews/{{review_filename}}`。
4. 人工补充每个页面里的验证清单和引用证据。
