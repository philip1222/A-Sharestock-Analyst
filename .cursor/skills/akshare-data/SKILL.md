---
name: akshare-data
description: 使用项目自带的 akshare CLI 查询 A 股、港股、美股、基金、期货、债券、宏观等金融数据。当用户询问行情、财报、估值、资金流、净值、指数或任何需要实际取数的问题时使用。
---

# AKShare 取数

通过命令行入口取数，不要临时编写取数脚本。

## 工作流

### 1. 定位接口

```bash
uv run akshare search "A股 历史行情" --limit 10
```

离线检索，不发网络请求。可加 `--category stock` 限定类目，`--documented-only` 只看有文档的接口。

它是关键词匹配而非语义搜索：用数据本身的术语（如「龙虎榜」「北向资金」「市盈率」）比用整句问题更容易命中。查不到时换同义词或先看类目：

```bash
uv run akshare categories
```

### 2. 核对参数

```bash
uv run akshare info stock_zh_a_hist
```

输出接口描述、入参、返回列与官方示例。取数前确认日期格式与代码格式，不要凭记忆填参数。

### 3. 取数

```bash
uv run akshare call stock_zh_a_hist \
  --arg symbol=000001 --arg period=daily \
  --arg start_date=20240101 --arg end_date=20240131 \
  --arg adjust= --head 10
```

无参数接口直接调用：

```bash
uv run akshare call stock_zh_a_spot_em --head 10
```

## 参数规则

| 写法 | 用途 |
|------|------|
| `--arg key=value` | 字符串入参，不做类型推断；股票代码等带前导 0 的值必须用它 |
| `--kwargs '{"limit": 10}'` | 数字、布尔、null 等非字符串类型；可与 `--arg` 混用，`--arg` 优先 |
| `--head N` | 展示行数，默认 20，`0` 表示全量 |
| `--format table\|json\|csv` | 默认 `table`；`json` 与 `csv` 的 stdout 只含数据，行数提示走 stderr |

## 报错对照

| 报错 | 处理 |
|------|------|
| `未知接口 xxx` | 从 CLI 给出的候选里选，不要硬猜 |
| `参数不匹配` | 跑 `info` 核对入参名称与数量 |
| `ProxyError` / `ConnectionError` | 上游公开站点或本机网络问题，与代码无关，不要改 `akshare/` 源码；东方财富历史行情接口见下节换源 |
| 返回空表 | 多为日期区间无交易日或代码不存在，先缩小区间验证 |

## 东方财富 K 线端点失败时换源

东方财富的 `/api/qt/stock/kline/get` 按出口 IP 做风控，被限时连接会被直接断开，表现为 `ProxyError` 或 `ConnectionError`。全部依赖它的历史行情接口会同时失效，而同站其他端点（如 `stock_zh_a_spot_em`）仍然正常，所以这不是网络整体不通，重试也没有意义。直接换非东方财富源：

| 原接口 | 替代 | 代码格式 |
|--------|------|----------|
| `stock_zh_a_hist` | `stock_zh_a_hist_tx` 或 `stock_zh_a_daily` | 需市场前缀，如 `sz000001` |
| `stock_zh_index_daily_em` | `stock_zh_index_daily` | `sh000001` |
| `fund_etf_hist_em` | `fund_etf_hist_sina` | `sz159707` |

```bash
uv run akshare call stock_zh_a_hist_tx \
  --arg symbol=sz000001 --arg start_date=20240101 \
  --arg end_date=20240131 --arg adjust= --head 10
```

替代源的列名、字段单位与复权口径与东方财富不同，换源后先跑 `info` 核对再用。

## 何时改用 Python

需要对结果做多步计算、合并多个接口、绘图或落盘时，用 `uv run python`，并照常 `import akshare as ak` 调用。单纯取数一律走 CLI。

## 何时改用 OpenBB

只要标准化字段或 OpenBB REST / Workspace 时用：

```python
from openbb import obb
obb.akshare.historical(symbol="000001", start_date="2024-01-01", end_date="2024-01-31")
obb.akshare.quote(symbol="000001")
```

环境用 `./scripts/dev_sync.sh` 安装。日线换源由扩展内部处理；其余接口仍走 CLI。

## 补充资料

- `llms.txt`：命名约定（`_em` 东方财富、`_sina` 新浪、`_ths` 同花顺等）与返回值约定
- `docs/data/`：按类目组织的完整接口文档
