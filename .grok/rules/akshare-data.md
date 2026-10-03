# 取数走 akshare CLI

需要行情、基本面、宏观等数据时，执行项目命令行入口，不要临时写 `python -c "import akshare ..."` 或新建一次性脚本：

```bash
uv run akshare search "A股 历史行情"          # 离线检索接口名
uv run akshare info stock_zh_a_hist           # 查看入参与输出列
uv run akshare call stock_zh_a_hist \
  --arg symbol=000001 --arg period=daily \
  --arg start_date=20240101 --arg end_date=20240131 \
  --arg adjust= --head 10
```

顺序固定为 `search` 定位接口 → `info` 核对参数 → `call` 取数。只有当结果需要多步计算、绘图或落盘时，才改用 Python。

## call 参数约定

- `--arg key=value` 的值一律当字符串，不做类型推断；股票代码等带前导 0 的入参必须用它。
- `--kwargs '{"limit": 10}'` 用于数字、布尔、null 等非字符串类型，可与 `--arg` 同时使用，`--arg` 优先级更高。
- `--head N` 默认 20 行，`0` 表示全量。
- `--format table|json|csv` 默认 `table`；`json` 与 `csv` 的 stdout 只含数据，行数提示走 stderr。

## 失败处理

- `未知接口 xxx`：从 CLI 给出的候选里选，不要硬猜接口名。
- `参数不匹配`：先跑 `info` 核对入参。
- `ProxyError` / `ConnectionError` 等网络报错来自上游公开站点或本机网络，不是代码缺陷，不要改 `akshare/` 源码绕过。

## 东方财富 K 线端点失败时换源

东方财富的 `/api/qt/stock/kline/get` 按出口 IP 做风控，被限时连接会被直接断开，表现为 `ProxyError` 或 `ConnectionError`。全部依赖它的历史行情接口会同时失效，而同站其他端点仍然正常，所以这不是网络整体不通。此时直接换非东方财富源，不要反复重试：

| 原接口 | 替代 | 代码格式 |
|--------|------|----------|
| `stock_zh_a_hist` | `stock_zh_a_hist_tx` 或 `stock_zh_a_daily` | 需市场前缀，如 `sz000001` |
| `stock_zh_index_daily_em` | `stock_zh_index_daily` | `sh000001` |
| `fund_etf_hist_em` | `fund_etf_hist_sina` | `sz159707` |

替代源的列名、字段单位与复权口径与东方财富不同，换源后先跑 `info` 核对再用。

## OpenBB（可选）

标准化 A 股日线 / 快照用 `obb.akshare.historical` / `obb.akshare.quote`。环境用 `./scripts/dev_sync.sh` 安装（会 `uv sync` + `openbb-build`，并挂上 pull 后自动同步）。其余接口一律走 `uv run akshare`。

接口命名约定与类目划分见 `llms.txt`，分类接口文档见 `docs/data/`。
