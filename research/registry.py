#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""显式注册表。新因子或新模型加在这里，结论器不用改。"""

from __future__ import annotations

from research.factors.a_share_flow import AShareFlow
from research.factors.a_share_tape import AShareTape
from research.factors.commodity import Commodity
from research.factors.fx import Fx
from research.factors.us_risk import UsRisk
from research.models.rules_v1 import RulesV1
from research.models.spillover_dy import SpilloverDy

FACTORS = [AShareTape(), AShareFlow(), UsRisk(), Fx(), Commodity()]
MODELS = {"rules_v1": RulesV1(), "spillover_dy": SpilloverDy()}


def get_model(name: str):
    try:
        return MODELS[name]
    except KeyError as exc:
        known = "、".join(sorted(MODELS))
        raise KeyError(f"未知模型 {name}，可选: {known}") from exc
