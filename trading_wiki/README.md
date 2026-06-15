# Trading Wiki

Markdown-first trading knowledge base for daily market and industry cognition.

## Folder Layout

The usable knowledge layer follows the mobile wiki style:

```text
策略/
概念/
模式/
股票/
错误/
```

The audit layer keeps source traceability:

```text
raw/
sources/
reviews/
reports/
```

## Daily Workflow

1. Put the day's raw text under `raw/`.

2. Run ingest. By default this creates source/review/report files and also materializes knowledge notes under `概念/`, `股票/`, `策略/`, `模式/`, and `错误/`.

   ```powershell
   python scripts/ingest.py --date 2026-06-11 --input raw/2026-06-11-wechat-finance.md --source-type social
   ```

3. Open the generated knowledge notes and refine them.

   Example outputs:

   ```text
   概念/PCB钻针.md
   概念/AI硬件产业链全面爆发.md
   股票/金安国纪.md
   错误/把微信搜索摘要当完整正文.md
   ```

4. If you only want audit files and do not want to create knowledge pages:

   ```powershell
   python scripts/ingest.py --date 2026-06-11 --input raw/2026-06-11-wechat-finance.md --source-type social --no-materialize
   ```

## Evidence Rule

Low-quality sources such as public WeChat search snippets, rumors, group chat excerpts, and short posts default to:

```yaml
evidence_level: low
execution_permission: observe_only
```

They can create or update cognition pages, but they cannot become trade instructions without later verification.

## Candidate Syntax

The script detects these raw sections:

```markdown
## 概念
- PCB钻针：AI服务器PCB高层数带来钻针耗材变化

## 标的
- 中船特气：WF6纯度、客户、产能需要验证

## 策略
- 涨价链验证框架

## 模式
- 搜索摘要到source archive

## 错误
- 把微信搜索摘要当完整正文
```

## Tests

```powershell
python -m unittest tests.test_ingest -v
```
