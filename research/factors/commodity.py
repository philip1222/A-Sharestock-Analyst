#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""沪铜连续合约。铜价上行通常对应中国工业需求与风险偏好改善。"""

from __future__ import annotations

import pandas as pd

from research.factors.scoring import clip, now_iso
from research.types import FactorContext, FactorResult

ID = "commodity"
NAME = "沪铜"
WEIGHT = 0.8
RATIONALE = "铜价跟踪全球工业需求。它上行时中国周期与风险资产往往同步改善。"


def load_frame(ctx: FactorContext) -> pd.DataFrame:
    del ctx
    import akshare as ak

    return ak.futures_zh_daily_sina(symbol="CU0")


def evaluate(ctx: FactorContext, frame: pd.DataFrame | None = None) -> FactorResult:
    try:
        data = load_frame(ctx) if frame is None else frame
    except Exception as exc:
        return _fail(f"沪铜不可用: {type(exc).__name__}: {exc}")
    if data is None or data.empty or "close" not in data.columns:
        return _fail("沪铜为空")
    close = pd.to_numeric(data["close"], errors="coerce").dropna()
    if "date" in data.columns:
        dated = data.copy()
        dated["date"] = pd.to_datetime(dated["date"], errors="coerce")
        dated = dated[dated["date"].dt.date <= ctx.asof]
        close = pd.to_numeric(dated["close"], errors="coerce").dropna()
    if len(close) < 2:
        return _fail("沪铜不足两根 K 线")
    window = close.tail(21)
    change = float(window.iloc[-1] / window.iloc[0] - 1)
    return FactorResult(
        id=ID,
        name=NAME,
        weight=WEIGHT,
        rationale=RATIONALE,
        status="ok",
        direction=clip(change / 0.06),
        source="sina",
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


class Commodity:
    id = ID
    name = NAME
    weight = WEIGHT
    rationale = RATIONALE

    def evaluate(self, ctx: FactorContext) -> FactorResult:
        return evaluate(ctx)
