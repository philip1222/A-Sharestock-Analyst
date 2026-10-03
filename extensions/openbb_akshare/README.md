# openbb-akshare

可选的 [OpenBB](https://github.com/OpenBB-finance/OpenBB) V5 provider，把本仓库的 AKShare 接到 `obb.akshare`。

本仓库根目录的 `./scripts/dev_sync.sh` 会 `uv sync`（经 `dev` 组安装本扩展）并注册 OpenBB。依赖版本锁在根目录 `uv.lock`。全量 / 冷门接口继续走 `uv run akshare` CLI。

## 当前覆盖

| 命令 | 含义 | 换源 |
|------|------|------|
| `obb.akshare.historical` | A 股历史行情 | 日线：东方财富 → 腾讯 → 新浪；周/月线仅东方财富 |
| `obb.akshare.quote` | A 股快照 | 东方财富 → 腾讯 → 新浪 |

```python
from openbb import obb

hist = obb.akshare.historical(
    symbol="000001",
    start_date="2024-01-01",
    end_date="2024-01-31",
    adjust="",
)
print(hist.to_dataframe().head())

quote = obb.akshare.quote(symbol="000001")
print(quote.to_dataframe())
```

`provider` 只有 `akshare` 时可以省略。返回值是 OpenBB 标准字段（`open` / `close` / `last_price`…），`source` 标明实际命中的上游。`change_percent` 是归一化小数。

REST 对应：

```bash
uvicorn openbb_core.api.rest_api:app --port 8000
# GET /api/v1/akshare/historical?symbol=000001&start_date=2024-01-01
# GET /api/v1/akshare/quote?symbol=000001
```

## 不在这里的接口

龙虎榜、北向资金、宏观、基金持仓等中国特色接口没有对应的 OpenBB 标准模型，继续用：

```bash
uv run akshare search "龙虎榜"
uv run akshare call <接口名> --arg ...
```
