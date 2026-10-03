# 章节触发表（正式执行版）

## 使用方式

- 本表用于每次选股前的“先读后判”流程。
- 每次任务至少读取 3 条：`L1` 必读 1 条 + `L2/L3` 至少 2 条。
- `章节编号` 暂支持两种写法：
  - 精确：`Chapter 7` / `第3章`
  - 模糊：`关键词检索: position sizing`
- 若未填写精确章节号，先按关键词检索目录与正文，再进入决策。

## 字段定义

| 字段 | 说明 |
|---|---|
| 任务场景 | 本次筛选属于哪类任务 |
| 必读级别 | 必读 / 推荐 |
| 层级 | L1-L4 |
| 书籍文件名 | 必须匹配 books_pdf 内文件名 |
| 章节编号 | 可留空，后续逐步补齐 |
| 关键词 | 用于未标章节时检索 |
| 产出规则 | 本次阅读后要抽取的可执行结论 |

## A. 长线价值配置（持有 3 个月以上）

| 任务场景 | 必读级别 | 层级 | 书籍文件名 | 章节编号 | 关键词 | 产出规则 |
|---|---|---|---|---|---|---|
| 长线建仓前风险预算 | 必读 | L1 | `L1_01_trade-your-way-to-financial-freedom_van-k-tharp.pdf` | Chapter 12 (p280), Chapter 9 (p233) | position sizing, R-multiple | 单笔风险上限、总风险暴露 |
| 长线估值判断 | 必读 | L2 | `L2_06_security-analysis_graham-dodd.pdf` | Chapter 1 (p102), Chapter 4 (p142) | margin of safety, intrinsic value | 安全边际阈值与拒绝条件 |
| 长线估值交叉验证 | 推荐 | L2 | `L2_09_valuation_mckinsey-koller.pdf` | Chapter 2 (p37), Chapter 3 (p47) | DCF, multiples | 估值区间上下沿 |
| 长线财报质量复核 | 必读 | L2 | `L2_10_financial-statement-analysis-and-security-valuation_penman.pdf` | Chapter 4 (p110), Chapter 18 (p590) | earnings quality, accruals | 财报失真排雷清单 |
| A股落地校准 | 推荐 | L4 | `L4_16_shou-ba-shou-du-cai-bao_tangchao.pdf` | 第五章第二节 (p282), 第五章第三节 (p292) | 财报初筛, 估值 | A股财务口径本地化修正 |

## B. 长线框架下波段（持有 2-12 周）

| 任务场景 | 必读级别 | 层级 | 书籍文件名 | 章节编号 | 关键词 | 产出规则 |
|---|---|---|---|---|---|---|
| 波段开仓前风控 | 必读 | L1 | `L1_02_the-new-trading-for-a-living_alexander-elder.pdf` | Chapter 39 (p154), Chapter 49-51 (p202-208) | triple screen, risk control | 入场前止损与仓位模板 |
| 趋势结构判定 | 必读 | L3 | `L3_12_technical-analysis-of-the-financial-markets_john-j-murphy.pdf` | Chapter 4 (p62), Chapter 7 (p156) | trend, support resistance, volume | 趋势成立与失效判据 |
| 入场细节确认 | 推荐 | L3 | `L3_13_japanese-candlestick-charting-techniques_steve-nison.pdf` | Chapter 4 Reversal Patterns (p31), Chapter 8 The Magic Doji (p155) | reversal, confirmation | 触发K线与否决K线 |
| 攻守切换判断 | 推荐 | L3 | `L3_15_mastering-the-market-cycle_howard-marks.pdf` | The Cycle in Attitudes toward Risk (p90), Cycle Positioning (p208) | cycle, risk appetite | 风格切换与仓位降档条件 |
| A股组合跟踪 | 推荐 | L4 | `L4_17_jia-zhi-tou-zi-shi-zhan-shou-ce_tangchao.pdf` | 第二章 (p72), 第三章财报阅读实战 (p132) | 组合跟踪, 估值边界 | 再平衡触发条件 |

## C. 短线交易（T+1 到 T+5）

| 任务场景 | 必读级别 | 层级 | 书籍文件名 | 章节编号 | 关键词 | 产出规则 |
|---|---|---|---|---|---|---|
| 短线日内风控闸门 | 必读 | L1 | `L1_02_the-new-trading-for-a-living_alexander-elder.pdf` | Chapter 49-52 (p202-210) | stop loss, trading discipline | 单笔止损与日亏阈值 |
| 尾部风险复核 | 推荐 | L1 | `L1_03_the-black-swan_nassim-n-taleb.pdf` | Prologue (p21), Anatomy of a Black Swan (p35) | tail risk, uncertainty | 黑天鹅场景降仓规则 |
| 短线信号判定 | 必读 | L3 | `L3_12_technical-analysis-of-the-financial-markets_john-j-murphy.pdf` | Chapter 4 (p62), Momentum section (p216) | breakout, momentum, volume | 进场与撤退信号 |
| 执行纪律校准 | 必读 | L3 | `L3_14_way-of-the-turtle_curtis-faith.pdf` | The First $2 Million Is the Toughest (p59), By What Measure? (p115) | rules, system execution | 连亏后缩仓与停手机制 |
| A股情绪适配 | 推荐 | L4 | `L4_18_tou-zi-zhong-zui-jian-dan-de-shi_qiuguolu.pdf` | 02 人弃我取，逆向投资的关键 (p28), 07 价值陷阱与成长陷阱 (p109) | 行业比较, 市场风格 | 主线与分歧期过滤 |

## D. 调仓与风险事件（任何周期）

| 任务场景 | 必读级别 | 层级 | 书籍文件名 | 章节编号 | 关键词 | 产出规则 |
|---|---|---|---|---|---|---|
| 加杠杆或重仓前 | 必读 | L1 | `L1_05_risk-management-and-financial-institutions_john-c-hull.pdf` | Chapter 1 (p29), Chapter 16 Scenario Analysis and Stress Testing (p375) | VaR, stress test, concentration | 压力测试与最大暴露 |
| 组合集中度过高 | 必读 | L1 | `L1_04_antifragile_nassim-n-taleb.pdf` | Chapter 2 (p47), Seneca’s Barbell (p151) | antifragile, barbell | 去集中化操作清单 |
| 价值与趋势冲突 | 推荐 | L2 | `L2_07_the-intelligent-investor_benjamin-graham.pdf` | Chapter 8 (p202), Introduction (p15) | Mr. Market, margin of safety | 长短周期分仓准则 |
| 系统偏离修复 | 推荐 | L3 | `L3_14_way-of-the-turtle_curtis-faith.pdf` | Think Like a Turtle (p83), By What Measure? (p115) | discipline, consistency | 纠偏流程与观察期 |

## 降级与容错规则

1. 缺少 `L1` 阅读结果：本次只允许输出“观察”，不得给买入建议。
2. 缺少 `L2/L3` 任一关键结论：可给方向，不给具体仓位。
3. 数据缺失 + 章节缺失同时出现：直接中止推荐并提示补充。

## 维护规则（你后续可持续迭代）

- 你每补齐一个“章节编号”，就在本表直接覆盖原空值。
- 同一本书若版本不同，可在 `章节编号` 写法中加 `版本标注`，例如：`Chapter 8 (2008版)`。
- 当某条规则连续 3 个月无效，可降级为“推荐”并增加替代条目。
