---
name: a-share-stock-analysis
description: 用户询问股票行情、走势、估值、买卖、交易策略或选股时使用。仓库已自动加载本流程，无需用户安装或点名。先跑 research.strategy。
---

# A股交易策略

用户问一只股票怎么交易时，按下面顺序做，不要另写取数脚本。

## 1. 先出计划

```bash
uv run python -m research.strategy --symbol 000001
```

周期：短线 `--horizon short`，波段默认 `swing`，长线 `--horizon value`。用户没说周期时用默认波段。

命令已计算近 1、7、15、30 个交易日的涨跌、高低点、路径、均线、ATR、止损、2R 止盈，以及市盈率/市净率近三年分位。回答里的价格和仓位模板以这份 JSON 为准。

跨市场环境另跑 `uv run python -m research.conclude --symbol 000001`，不把它混进止损价。

## 2. 核对技能材料

- 章节触发表：`references/BOOK_CHAPTER_MAP_TEMPLATE.md`
- 书单：`BOOKLIST.md`
- 数据字段：`references/DATA_SOURCE_TEMPLATE.md`
- 书籍 PDF：`references/books_pdf/`，应有 18 本

JSON 的 `evidence` 列出本次要对照的书和章节。PDF 若在 `references/books_pdf/` 可以打开核对，不在也不要要求用户拷贝，更不要因此改动作。

## 3. 判决顺序

`L1 风险 -> L3 时机 -> L2 价值 -> L4 本地化`

- 动作只有 `买入`、`观察`、`回避`。
- 缺少估值分位或财报时，不给出买入，置信度不超过「中」。书籍 PDF 缺失不影响动作。
- `plan.status` 为 `reference_only` 时，止损和止盈只是测算，不是入场指令。
- 主源与腾讯价差若超过 1.5%，在回答里标明冲突，不得给高置信买入。命令本身已在东方财富失败时换腾讯或新浪，并把实际 `data.source` 写进 JSON。

## 4. 回答结构

- 任务类型与动作、置信度
- 近 1 / 7 / 15 / 30 个交易日的涨跌和高低点
- 交易计划：入场、止损、止盈、失效条件、每 1 万元风险 1% 的股数模板
- 证据：JSON 里的书籍章节，加上数据源和 `observed_at`
- 缺失项与否决项
- 原样保留免责声明：这是研究用交易计划，不是下单指令
