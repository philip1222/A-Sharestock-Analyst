#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""美股风险偏好。VIX 上升通常压制 A 股风险资产。"""

from __future__ import annotations

import os
from datetime import timedelta

import pandas as pd

from research.factors.scoring import clip, now_iso
from research.types import FactorContext, FactorResult

ID = "us_risk"
NAME = "美股风险"
WEIGHT = 1.0
RATIONALE = "VIX 衡量全球风险偏好。它上升时外资风险预算收缩，A 股易跟随承压。"


def load_vix(ctx: FactorContext) -> tuple[pd.DataFrame, str]:
    from openbb import obb

    start = (ctx.asof - timedelta(days=40)).isoformat()
    end = ctx.asof.isoformat()
    try:
        frame = obb.cboe.index.historical(
            symbol="VIX", start_date=start, end_date=end
        ).to_dataframe()
        return frame, "cboe"
    except Exception:
        if not os.environ.get("FRED_API_KEY"):
            raise RuntimeError("CBOE 不可用且未配置 FRED_API_KEY") from None
        frame = obb.fred.economy.fred_series(
            symbol="VIXCLS", start_date=start, end_date=end
        ).to_dataframe()
        return frame, "fred"


def _level_column(frame: pd.DataFrame) -> pd.Series:
    for name in ("close", "value", "VIXCLS"):
        if name in frame.columns:
            return pd.to_numeric(frame[name], errors="coerce").dropna()
    numeric = frame.select_dtypes(include="number")
    if numeric.empty:
        return pd.Series(dtype=float)
    return pd.to_numeric(numeric.iloc[:, 0], errors="coerce").dropna()


def evaluate(
    ctx: FactorContext, frame: pd.DataFrame | None = None, source: str = "cboe"
) -> FactorResult:
    try:
        data, used = (frame, source) if frame is not None else load_vix(ctx)
    except Exception as exc:
        return _fail(f"VIX 不可用: {type(exc).__name__}: {exc}")
    level = _level_column(data)
    if level.empty:
        return _fail("VIX 为空")
    last = float(level.iloc[-1])
    return FactorResult(
        id=ID,
        name=NAME,
        weight=WEIGHT,
        rationale=RATIONALE,
        status="ok",
        direction=clip((20.0 - last) / 10.0),
        source=used,
        observed_at=now_iso(),
        detail={"vix": round(last, 4)},
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


class UsRisk:
    id = ID
    name = NAME
    weight = WEIGHT
    rationale = RATIONALE

    def evaluate(self, ctx: FactorContext) -> FactorResult:
        return evaluate(ctx)
