#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""美元兑人民币。美元走强通常对 A 股风险资产形成压力。"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from research.factors.scoring import clip, now_iso
from research.types import FactorContext, FactorResult

ID = "fx"
NAME = "美元人民币"
WEIGHT = 1.0
RATIONALE = "美元兑人民币走强时，北向与风险资产的相对吸引力下降，A 股常承压。"


def load_frame(ctx: FactorContext) -> pd.DataFrame:
    import akshare as ak

    start = (ctx.asof - timedelta(days=220)).strftime("%Y%m%d")
    end = ctx.asof.strftime("%Y%m%d")
    return ak.currency_boc_sina(symbol="美元", start_date=start, end_date=end)


def evaluate(ctx: FactorContext, frame: pd.DataFrame | None = None) -> FactorResult:
    try:
        data = load_frame(ctx) if frame is None else frame
    except Exception as exc:
        return _fail(f"汇率不可用: {type(exc).__name__}: {exc}")
    column = (
        "央行中间价"
        if data is not None and "央行中间价" in getattr(data, "columns", [])
        else None
    )
    if data is None or data.empty or column is None:
        return _fail("汇率为空")
    mid = pd.to_numeric(data[column], errors="coerce").dropna()
    if len(mid) < 2:
        return _fail("汇率不足两期")
    window = mid.tail(21)
    change = float(window.iloc[-1] / window.iloc[0] - 1)
    return FactorResult(
        id=ID,
        name=NAME,
        weight=WEIGHT,
        rationale=RATIONALE,
        status="ok",
        direction=clip(-change / 0.02),
        source="sina",
        observed_at=now_iso(),
        detail={"usd_cny_change": round(change, 4), "bars": int(len(window))},
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


class Fx:
    id = ID
    name = NAME
    weight = WEIGHT
    rationale = RATIONALE

    def evaluate(self, ctx: FactorContext) -> FactorResult:
        return evaluate(ctx)
