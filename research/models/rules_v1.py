#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""可解释加权。缺失因子不记成中性利好，只从分母里拿掉。"""

from __future__ import annotations

from typing import Sequence

from research.types import Conclusion, FactorResult, Stance

ID = "rules_v1"
DISCLAIMER = "研究输出，仅供对照数据与因子，不构成交易建议，也不代表应当买入或卖出。"
THRESHOLD = 0.15


def stance_of(score: float) -> Stance:
    if score > THRESHOLD:
        return "偏多"
    if score < -THRESHOLD:
        return "偏空"
    return "中性"


def run(symbol: str, asof: str, factors: Sequence[FactorResult]) -> Conclusion:
    used = [
        item for item in factors if item.status == "ok" and item.direction is not None
    ]
    skipped = [item for item in factors if item not in used]
    weight = sum(item.weight for item in used)
    total = sum(item.weight for item in factors) or 1.0
    score = (
        0.0
        if weight == 0
        else sum(item.direction * item.weight for item in used) / weight
    )
    score = max(-1.0, min(1.0, score))
    return Conclusion(
        symbol=symbol,
        asof=asof,
        model=ID,
        stance=stance_of(score),
        score=round(score, 4),
        confidence=round(weight / total, 4),
        used=[item.as_dict() for item in used],
        skipped=[item.as_dict() for item in skipped],
        disclaimer=DISCLAIMER,
    )


class RulesV1:
    id = ID

    def run(
        self, symbol: str, asof: str, factors: Sequence[FactorResult]
    ) -> Conclusion:
        return run(symbol, asof, factors)
