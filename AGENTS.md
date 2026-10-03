# AGENTS.md

AKShare 金融数据接口库。约 1000 个公开接口，绝大多数返回 `pandas.DataFrame`，多数无需 API Key。

## 股票问题自动进入选股流程

本文件随仓库分发。Cursor、Codex、Grok 以及其他会读取 `AGENTS.md` 的终端，在克隆或关联本仓库后就会加载它。用户不需要安装 Skill、粘贴提示词、拷贝书籍 PDF，也不需要说「使用某个技能」。

只要问题涉及某只股票的行情、走势、估值、能不能买、交易策略或选股，就直接执行，不要先向用户确认流程：

1. 用户给了 6 位代码或中文名称时，先跑策略入口。名称可直接传入，命令会解析成唯一代码：

```bash
uv run python -m research.strategy --symbol 000001
uv run python -m research.strategy --symbol 平安银行
```

2. 问题还涉及其他市场对这只股票的影响，或只要多空环境时，再跑：

```bash
uv run python -m research.conclude --symbol 000001
```

3. 只索要某张原始表、某个接口字段，没有买卖或策略含义时，走下面的 `akshare` CLI，不跑策略。
4. 没有代码也没有名称的「帮我选股」，说明当前流程一次只评估一只，请用户给出代码或名称。不要假装已经做完全市场筛选。
5. 回答使用命令 JSON 里的动作、近 1 / 7 / 15 / 30 个交易日窗口和价位。`evidence` 已写明对应书籍章节。PDF 不在仓库里，缺失不改变动作，不要要求用户补装。
6. 保留 JSON 里的免责声明。不要在命令结果之外另编交易建议，也不要改写动作。

`--horizon short|swing|value` 对应短线、波段、长线，没说明时用默认波段。

## 取数时走 CLI，不要临时写脚本

需要行情、基本面、宏观等数据时，直接执行项目自带的命令行入口：

```bash
uv run akshare search "A股 历史行情"          # 离线检索接口名
uv run akshare info stock_zh_a_hist           # 查看入参与输出列
uv run akshare call stock_zh_a_hist \
  --arg symbol=000001 --arg period=daily \
  --arg start_date=20240101 --arg end_date=20240131 \
  --arg adjust= --head 10
```

不要为了取一次数而写 `python -c "import akshare ..."` 或新建临时脚本。只有在需要对结果做多步计算、绘图或落盘时，才改用 Python。

### 推荐顺序

1. `search` 定位接口名，而不是凭记忆猜。
2. `info` 确认参数格式与返回列。
3. `call` 取数。

命令成功返回前不要声称已经取到数据，更不要凭印象编造行情数值。回答里带上取数时间与数据源。涉及买卖或策略时只转述 `research.strategy` 的结果，不要在命令之外另给交易建议。

### call 的参数约定

- `--arg key=value`：值一律按字符串传入，不做类型推断。股票代码等带前导 0 的入参必须用这种方式。
- `--kwargs '{"limit": 10}'`：需要数字、布尔、null 等非字符串类型时使用。两者可同时出现，`--arg` 优先级更高。
- `--head N`：默认 20 行，`0` 表示全量。
- `--format table|json|csv`：默认 `table`。需要被下游程序解析时用 `json` 或 `csv`，这两种格式只向 stdout 输出数据本身，行数提示走 stderr。

### 失败处理

- `未知接口 xxx`：CLI 已给出最接近的候选，从候选里选，不要硬猜。
- `参数不匹配`：先跑 `info` 核对入参。
- 网络类报错（`ProxyError`、`ConnectionError` 等）：上游公开站点或本机网络的问题，不是代码缺陷，不要试图改 `akshare/` 的源码来绕过。

### 东方财富 K 线端点失败时换源

东方财富的 `/api/qt/stock/kline/get` 按出口 IP 做风控，被限时连接会被直接断开，表现为 `ProxyError` 或 `ConnectionError`。全部依赖它的历史行情接口会同时失效，而同站其他端点仍然正常，所以这不是网络整体不通。此时直接换非东方财富源，不要反复重试：

| 原接口 | 替代 | 代码格式 |
|--------|------|----------|
| `stock_zh_a_hist` | `stock_zh_a_hist_tx` 或 `stock_zh_a_daily` | 需市场前缀，如 `sz000001` |
| `stock_zh_index_daily_em` | `stock_zh_index_daily` | `sh000001` |
| `fund_etf_hist_em` | `fund_etf_hist_sina` | `sz159707` |

替代源的列名、字段单位与复权口径与东方财富不同，换源后先跑 `info` 核对再用。

## OpenBB（可选）

本仓库的 `uv sync` 会一并装上 `extensions/openbb_akshare`（依赖已锁进 `uv.lock`）。环境安装统一走 `./scripts/dev_sync.sh`，不要再单独敲 `uv sync` / `openbb-build`。

当前只覆盖两条：

```python
from openbb import obb
obb.akshare.historical(symbol="000001", start_date="2024-01-01", end_date="2024-01-31")
obb.akshare.quote(symbol="000001")
```

日线失败时扩展内部会按东方财富 → 腾讯 → 新浪换源。龙虎榜、北向资金、宏观等没有 OpenBB 标准模型的接口，仍然走上面的 `akshare` CLI，不要为了这些需求去装 OpenBB。

## 研究结论

用户要某只 A 股的购买/多空结论时，跑研究流水线，不要临场把因子写进一次性脚本：

```bash
uv run python -m research.conclude --symbol 000001
```

stdout 是 JSON：立场（偏多 / 中性 / 偏空）、分数、置信度、各因子贡献与缺失项。这是研究输出，回答里保留免责声明，不要把它说成交易指令。要原始行情仍走 `akshare` CLI。新增因子放到 `research/factors/` 并在 `research/registry.py` 登记。

默认 `rules_v1` 是加权打分。`--model spillover_dy` 用本股、标普 500、VIX、美元人民币、沪铜、北向净买额做 Diebold-Yilmaz 连通性；缺哪列就丢掉哪列。需要 API Key 的源不参与。

## 交易策略

用户要某只 A 股的交易策略、买卖计划或入场止损时，跑策略入口，不要临场重算均线或仓位：

```bash
uv run python -m research.strategy --symbol 000001
```

它会取近 1、7、15、30 个交易日的行情，并尝试百度股市通的市盈率、市净率及近三年分位。stdout 是 JSON：动作（买入 / 观察 / 回避）、止损、2R 止盈、每 1 万元风险 1% 的股数模板、证据所对应的书籍章节。书籍 PDF 不是运行条件。这是研究用交易计划，不是下单指令。

## 环境

Python >= 3.11，依赖用 uv 管理。克隆后或 `.venv` 不存在时跑一次：

```bash
./scripts/dev_sync.sh
```

它会执行 `uv sync`、`uv run openbb-build`，并把 `post-merge` / `post-checkout` 钩子拷进 `.git/hooks`。之后 `git pull` 或切分支若改到 `uv.lock`、`pyproject.toml`、`extensions/`，会自动再同步。不要把这两步拆开手敲。

`uv run` 会自动使用 `.venv`，无需手动激活。

## 修改源码时

- 公开接口必须在 `akshare/__init__.py` 里导出，否则用户无法以 `ak.xxx()` 调用。
- 同步更新 `docs/data/` 下对应文档与 `docs/changelog.md`。
- 格式化与检查：`uv run ruff format .` 与 `uv run ruff check .`。
- 测试：`uv run pytest`。

## 更多上下文

- `llms.txt`：接口命名约定、类目划分、返回值约定。
- `docs/data/`：按类目组织的接口文档。
