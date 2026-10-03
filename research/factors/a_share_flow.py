#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""北向资金净流入。正流入通常对应风险偏好回升。"""

from __future__ import annotations

import pandas as pd

from research.factors.scoring import clip, now_iso
from research.types import FactorContext, FactorResult

ID = "a_share_flow"
NAME = "北向资金"
WEIGHT = 1.0
RATIONALE = (
    "北向净流入反映境外资金对 A 股的风险偏好，是外部市场传到 A 股最直接的资金渠道之一。"
)


def load_frame() -> pd.DataFrame:
    import akshare as ak

    return ak.stock_hsgt_fund_flow_summary_em()


def evaluate(ctx: FactorContext, frame: pd.DataFrame | None = None) -> FactorResult:
    del ctx
    try:
        data = load_frame() if frame is None else frame
    except Exception as exc:
        return _fail(f"北向资金不可用: {type(exc).__name__}: {exc}")
    if data is None or data.empty:
        return _fail("北向资金为空")
    needed = {"交易日", "板块", "资金净流入"}
    if not needed.issubset(data.columns):
        return _fail("北向资金列缺失")
    north = data[data["板块"].astype(str).isin(["沪股通", "深股通"])]
    if north.empty:
        return _fail("未找到沪股通/深股通记录")
    latest = north["交易日"].astype(str).max()
    day = north[north["交易日"].astype(str) == latest]
    net = float(pd.to_numeric(day["资金净流入"], errors="coerce").sum())
    return FactorResult(
        id=ID,
        name=NAME,
        weight=WEIGHT,
        rationale=RATIONALE,
        status="ok",
        direction=clip(net / 50.0),
        source="eastmoney",
        observed_at=now_iso(),
        detail={"trade_date": latest, "net_inflow_yi": round(net, 4)},
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


class AShareFlow:
    id = ID
    name = NAME
    weight = WEIGHT
    rationale = RATIONALE

    def evaluate(self, ctx: FactorContext) -> FactorResult:
        return evaluate(ctx)
