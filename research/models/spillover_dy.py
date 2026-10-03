#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""Diebold-Yilmaz 连通性。外部市场解释本股波动的份额，再乘近期冲击方向。"""

from __future__ import annotations

from datetime import date
from typing import Sequence

import pandas as pd

from research.factors.scoring import clip, now_iso
from research.models.diebold_yilmaz import TARGET, connectedness
from research.models.rules_v1 import DISCLAIMER, stance_of
from research.panel import SPEC_BY_ID, SPECS, load_panel
from research.types import Conclusion, FactorResult

ID = "spillover_dy"
NOTE = "分数来自 Diebold-Yilmaz 广义方差分解，只描述其他序列对本股波动的解释份额和近期冲击方向。"


def run(symbol: str, asof: str, factors: Sequence[FactorResult]) -> Conclusion:
    del factors
    frame, skipped = load_panel(symbol, date.fromisoformat(asof))
    return conclude_panel(symbol, asof, frame, skipped)


def conclude_panel(
    symbol: str,
    asof: str,
    frame: pd.DataFrame,
    skipped: Sequence[FactorResult] | None = None,
) -> Conclusion:
    skipped_items = list(skipped or [])
    present = set(frame.columns)
    for spec in SPECS:
        if spec.id not in present and all(item.id != spec.id for item in skipped_items):
            skipped_items.append(
                FactorResult(
                    id=spec.id,
                    name=spec.name,
                    weight=0.0,
                    rationale=spec.rationale,
                    status="missing",
                    observed_at=now_iso(),
                    message="有效样本不足，未进入 VAR",
                )
            )
    result = connectedness(frame) if not frame.empty else None
    if result is None:
        for spec in SPECS:
            if spec.id in present and all(item.id != spec.id for item in skipped_items):
                skipped_items.append(
                    FactorResult(
                        id=spec.id,
                        name=spec.name,
                        weight=0.0,
                        rationale=spec.rationale,
                        status="missing",
                        observed_at=now_iso(),
                        message="有效样本不足，未进入 VAR",
                    )
                )
        return Conclusion(
            symbol=symbol,
            asof=asof,
            model=ID,
            stance="中性",
            score=0.0,
            confidence=0.0,
            used=[],
            skipped=[item.as_dict() for item in skipped_items],
            disclaimer=f"{DISCLAIMER}{NOTE}",
        )
    row = result.theta.loc[TARGET]
    external = [name for name in result.theta.columns if name != TARGET]
    external_share = float(row[external].sum()) if external else 0.0
    signed = 0.0
    used: list[FactorResult] = []
    for name in result.theta.columns:
        spec = SPEC_BY_ID[name]
        share = float(row[name])
        response = float(result.girf.loc[TARGET, name])
        sign = 0.0 if abs(response) < 1e-8 else float(response > 0) * 2 - 1
        recent = float(result.recent[name])
        if name != TARGET and external_share > 1e-8:
            signed += share / external_share * sign * clip(recent)
        used.append(
            FactorResult(
                id=name,
                name=spec.name,
                weight=round(share, 4),
                rationale=spec.rationale,
                status="ok",
                direction=0.0 if name == TARGET else round(sign * clip(recent), 4),
                observed_at=now_iso(),
                detail={
                    "fevd_share": round(share, 4),
                    "to": round(float(_to(result.theta, name)), 4),
                    "from": round(float(1.0 - result.theta.loc[name, name]), 4),
                    "net": round(
                        float(
                            _to(result.theta, name)
                            - (1.0 - result.theta.loc[name, name])
                        ),
                        4,
                    ),
                    "girf": round(response, 4),
                    "recent_z": round(recent, 4),
                    "spillover_index": round(result.spillover_index, 4),
                    "lag": result.lag,
                    "observations": result.observations,
                },
            )
        )
    loaded_external = len(external)
    intended_external = len(SPECS) - 1
    confidence = external_share * loaded_external / intended_external
    return Conclusion(
        symbol=symbol,
        asof=asof,
        model=ID,
        stance=stance_of(signed),
        score=round(clip(signed), 4),
        confidence=round(confidence, 4),
        used=[item.as_dict() for item in used],
        skipped=[item.as_dict() for item in skipped_items if item.id not in present],
        disclaimer=f"{DISCLAIMER}{NOTE}",
    )


def _to(theta: pd.DataFrame, name: str) -> float:
    return float(theta[name].sum() - theta.loc[name, name])


class SpilloverDy:
    id = ID

    def run(
        self, symbol: str, asof: str, factors: Sequence[FactorResult]
    ) -> Conclusion:
        return run(symbol, asof, factors)
