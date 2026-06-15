# Trading Wiki Ingest Design

## Goal

Build a Markdown-first trading knowledge base that can sediment daily market information into auditable source archives, concept pages, stock pages, review files, and ingest reports. This is phase B: Markdown plus automation scripts. Phase C, local retrieval Q&A, is intentionally left as a later extension.

The target behavior follows the reference article flow:

1. Save the day's raw source material.
2. Create a clean daily source archive.
3. Detect new concepts, stocks, strategies, patterns, and mistakes.
4. Update existing pages through a reviewable change set.
5. Record source quality, evidence strength, execution permission, and safety warnings.
6. Produce a concise ingest report showing what was created, updated, skipped, or needs verification.

## Non-Goals

- Do not build a full chat UI in this phase.
- Do not require a vector database in this phase.
- Do not auto-upgrade rumors, group chat screenshots, or short social posts into facts.
- Do not produce buy or sell instructions. The wiki can store hypotheses, catalysts, validation tasks, and execution permissions, but it must not present low-quality evidence as a tradable conclusion.

## Repository Layout

The first implementation should create these directories under `D:\software\trading_wiki`:

```text
raw/
sources/
concepts/
stocks/
strategies/
patterns/
mistakes/
reviews/
reports/
templates/
scripts/
```

Directory responsibilities:

- `raw/`: Original daily inputs. Examples: WeChat article text, group chat excerpts, copied research notes, OCR text from screenshots.
- `sources/`: Clean daily source archives such as `2026-06-11.md`.
- `concepts/`: Concept pages such as `AI PCB钻针三重通胀.md` and `MLCC设备国产替代.md`.
- `stocks/`: Stock or company pages.
- `strategies/`: Strategy pages.
- `patterns/`: Reusable market behavior or trading pattern pages.
- `mistakes/`: Mistake and postmortem pages.
- `reviews/`: Human review files for proposed wiki changes.
- `reports/`: Machine-generated ingest reports and diff summaries.
- `templates/`: Markdown templates for each page type.
- `scripts/`: Local automation entry points.

## Data Model

All durable knowledge should remain readable Markdown. Pages should use a small YAML frontmatter block for filtering and later retrieval:

```yaml
---
title: Page Title
type: concept
created: 2026-06-11
updated: 2026-06-11
status: active
evidence_level: low
execution_permission: observe_only
tags:
  - trading/wiki
---
```

Allowed `type` values:

- `source`
- `concept`
- `stock`
- `strategy`
- `pattern`
- `mistake`
- `review`
- `report`

Allowed evidence levels:

- `high`: Official action, company filing, formal announcement, order or production evidence with direct attribution.
- `medium`: Credible media, sell-side report, conference notes, repeated channel checks, or cross-validated industry feedback.
- `low`: Group chat, rumor, single-source social post, short-form article, or valuation narrative.
- `unknown`: Insufficient source clarity.

Allowed execution permissions:

- `none`: Cannot be used for trading decisions.
- `observe_only`: Can be tracked, but cannot independently create a trade.
- `needs_verification`: Requires confirmation before any action.
- `watchlist`: Can be added to watchlist after independent verification.
- `candidate`: Has enough evidence for deeper research, still not an instruction.

## Daily Source Archive

`sources/YYYY-MM-DD.md` should preserve what the source can and cannot prove. It should include:

- Source location: raw input path and external link if available.
- Source boundary: what this material is, what it is not, and what it cannot prove.
- Evidence strength table.
- Themes observed that day.
- Candidate page updates.
- Validation checklist.
- Links to created or updated wiki pages.

The source archive is the audit root for that day's changes. Any new claim added to a concept or stock page should link back to a source archive.

## Concept Page Template

Concept pages should mirror the reference screenshots:

```text
概念定义
与相近页面的区别
产业链结构
关键事实与催化
核心受益标的
验证清单
执行权限 / 事实强度
引用来源
变更记录
```

Important constraints:

- The definition must distinguish the concept from adjacent concepts.
- The page must separate demand-side logic, supply-side logic, equipment/material links, and listed company mapping.
- The `关键事实与催化` table must include current handling, evidence strength, and execution permission.
- The `核心受益标的` table must include positive logic and required verification.
- Low-quality sources can create observation items but cannot upgrade execution permission by themselves.

## Stock Page Template

Stock pages should summarize why a company appears in the wiki without turning it into a recommendation:

```text
公司定位
相关概念
正面逻辑
待验证事项
风险与反证
证据记录
变更记录
```

Each stock page should link back to relevant concepts and source archives.

## Ingest Script

The first script should be `scripts/ingest.py`.

Expected command:

```powershell
python scripts/ingest.py --date 2026-06-11 --input raw/2026-06-11.md
```

Responsibilities:

1. Create missing directories.
2. Read the raw input file.
3. Create or update `sources/YYYY-MM-DD.md`.
4. Generate a candidate change review in `reviews/YYYY-MM-DD-wiki-change-review.md`.
5. Generate a report in `reports/YYYY-MM-DD-ingest.md`.
6. Create placeholder pages for obvious candidate concepts, stocks, strategies, patterns, and mistakes when requested by the review file.
7. Run basic safety checks:
   - no raw frontmatter corruption
   - no unresolved template placeholders in generated reports
   - no execution permission above `observe_only` for low evidence
   - no page created without source links

The first implementation should not depend on a paid model API. It can generate structured prompts and review sections for the user to paste into an AI assistant. A later iteration can add an optional model provider.

## AI Assistance Boundary

The automation should divide work into deterministic and judgment-based parts.

Deterministic:

- Directory creation.
- Date naming.
- Template rendering.
- Source archive scaffolding.
- Report generation.
- Safety checks.

Judgment-based:

- Identifying real new concepts.
- Deciding whether an existing page should be updated.
- Distinguishing rumor from fact.
- Mapping companies to concepts.
- Assigning evidence level beyond simple source-type defaults.

Judgment-based output should first land in a review file, not directly overwrite high-value wiki pages.

## Review File

`reviews/YYYY-MM-DD-wiki-change-review.md` should be the human checkpoint. It should include:

- Source hash and input file path.
- Proposed new pages.
- Proposed updates to existing pages.
- Claims that require verification.
- Claims rejected or downgraded due to weak evidence.
- Safety warnings.
- Manual action checklist.

The user can approve items by editing checkboxes. Future automation can read checked items and materialize changes.

## Reports

`reports/YYYY-MM-DD-ingest.md` should summarize:

- Raw file processed.
- Source archive created or updated.
- Candidate new pages.
- Candidate updates.
- Safety check results.
- Any warnings.
- Next manual review path.

This should be similar to the article screenshot that says how many files were created, how many were updated, and whether safety checks passed.

## Phase C Extension Point

Phase C should add local retrieval Q&A after phase B has stable Markdown data. The likely implementation will index `sources/`, `concepts/`, `stocks/`, `strategies/`, `patterns/`, and `mistakes/`, then answer research questions with citations back to Markdown files.

Phase B should preserve frontmatter, headings, and backlinks so phase C can index cleanly.

## Testing

The first implementation should include a small fixture raw input and tests or smoke checks that verify:

- `scripts/ingest.py --date YYYY-MM-DD --input raw/YYYY-MM-DD.md` creates expected files.
- Existing files are not overwritten without review.
- Low evidence cannot produce high execution permission.
- Generated Markdown has no unresolved required placeholders.
- Reports link to the review file and source archive.

## Phase B Decisions

- Use Obsidian wikilinks for internal knowledge pages and normal Markdown links for external URLs.
- Treat OCR as manual input in phase B. Screenshot OCR text should be saved under `raw/` before ingest.
- Keep model provider integration out of the first implementation. The script should generate prompt-ready review sections first, then optional API integration can be added after the deterministic workflow is stable.
