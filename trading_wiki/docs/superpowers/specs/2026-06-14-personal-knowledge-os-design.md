# Personal Knowledge OS Redesign

## Objective

Turn the local Trading Wiki site into a personal knowledge operating system. Trading remains one domain, but the same interface must support psychology, neuroscience, Buddhism, books, methods, questions, cases, and long-term cognition notes.

## Information Model

The site uses three levels:

1. Domain: the high-level world a note belongs to, such as 交易, 心理学, 脑科学, 佛学, AI, 写作, 个人成长.
2. Topic map: a structured map under a domain, such as AI全产业链地图 or future maps like 认知偏差地图.
3. Note: the actual Markdown page. Notes can be concepts, stocks, strategies, patterns, mistakes, sources, books, people, methods, questions, or cases.

Existing notes remain valid. If a note does not declare a domain, it falls back to 交易 for existing trading folders. Future notes can add frontmatter fields:

```yaml
domain: 心理学
note_type: concept
topics:
  - 认知偏差
confidence: medium
related_questions:
  - 为什么人会确认偏误？
```

## Interface

The default screen becomes a knowledge workspace, not a graph-only page.

- Left side: domain navigation, search, type filters.
- Center: switchable workspace views.
  - 首页: domain cards, topic maps, recent updates, notes needing verification or thinking.
  - 目录: searchable note list grouped by selected domain.
  - 阅读: focused Markdown reading view.
  - 关系: graph view for the selected note or filtered result.
  - 表格: dense database-style list.
- Right side: context panel for the selected note: metadata, outgoing links, backlinks, headings, and extracted checklist items.

## Behavior

- Search is global within the selected domain. Choosing 全部 searches everything.
- Domain selection scopes the dashboard, list, table, and graph.
- Clicking a note selects it and updates the reader and context panel.
- Graph remains available but is not the default way to browse.
- The current Markdown renderer remains local and file-based.

## Validation

The implementation must:

- Build `web/data/wiki-index.json` without breaking existing ingestion tests.
- Render the site from `http://127.0.0.1:8765/web/index.html`.
- Show current trading notes under the 交易 domain.
- Keep future domains visible even before notes exist, so the knowledge base feels extensible.
- Avoid requiring a backend or database.
