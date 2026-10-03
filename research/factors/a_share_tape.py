#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""本股趋势：近端涨跌。数据来自 obb.akshare，内部已换源。"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from research.factors.scoring import clip, now_iso
from research.types import FactorContext, FactorResult

ID = "a_share_tape"
NAME = "本股趋势"
WEIGHT = 1.5
RATIONALE = "个股自身趋势是结论的锚。外部市场只解释环境，不替代这只股票自己的价格方向。"


def load_frame(ctx: FactorContext) -> pd.DataFrame:
    from openbb import obb

    start = (ctx.asof - timedelta(days=40)).isoformat()
    result = obb.akshare.historical(
        symbol=ctx.symbol,
        start_date=start,
        end_date=ctx.asof.isoformat(),
        adjust="",
    )
    return result.to_dataframe()


def evaluate(ctx: FactorContext, frame: pd.DataFrame | None = None) -> FactorResult:
    try:
        data = load_frame(ctx) if frame is None else frame
    except Exception as exc:
        return _fail(f"本股行情不可用: {type(exc).__name__}: {exc}")
    if data is None or data.empty or "close" not in data.columns:
        return _fail("本股行情为空")
    close = pd.to_numeric(data["close"], errors="coerce").dropna()
    if len(close) < 2:
        return _fail("本股行情不足两根 K 线")
    window = close.tail(21)
    change = float(window.iloc[-1] / window.iloc[0] - 1)
    source = None
    if "source" in data.columns:
        source = str(data["source"].iloc[-1])
    return FactorResult(
        id=ID,
        name=NAME,
        weight=WEIGHT,
        rationale=RATIONALE,
        status="ok",
        direction=clip(change / 0.08),
        source=source or "akshare",
        observed_at=now_iso(),
        detail={"lookback_return": round(change, 4), "bars": int(len(window))},
    )


def _fail(message: str) -> FactorResult:
    return FactorResult(
        id=ID,
        name=NAME,
        weight=WEIGHT,
        rationale=RATIONALE,
        status="missing",
        observed_at=now_iso(),
        message=message,
    )


class AShareTape:
    id = ID
    name = NAME
    weight = WEIGHT
    rationale = RATIONALE

    def evaluate(self, ctx: FactorContext) -> FactorResult:
        return evaluate(ctx)
