# 数据源（本仓库）

交易策略的数字只来自：

```bash
uv run python -m research.strategy --symbol 000001
```

| 数据 | 字段 | 来源 |
|---|---|---|
| 近 1、7、15、30 个交易日 | 涨跌、高低、收盘、成交额、路径 | `obb.akshare.historical`，东方财富失败时换腾讯、新浪 |
| 趋势 | MA20、ATR14、30 日回撤、量比 | 同上，由 `research.strategy` 计算 |
| 估值 | 市盈率(TTM)、市净率、近三年分位 | `stock_zh_valuation_baidu`，失败则记缺失 |
| 财报 | 营收、利润、现金流 | 尚未接入，JSON 中 `financials` 为 `missing`，因此置信度最高为「中」 |
| 跨市场 | 北向、VIX、汇率、沪铜 | `research.conclude`，不参与止损计算 |

不直接请求 `qt.gtimg.cn`。腾讯行情只作为 AKShare / OpenBB 换源后的 `data.source=tencent`。仅腾讯可用时，不得把置信度说成「高」。

缺少近 30 个交易日、市盈率分位或 18 本 PDF 中的任一时，动作为「观察」或「回避」，不输出可执行的买入仓位。
