#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""研究流水线的公共数据结构。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Literal

Status = Literal["ok", "missing", "error"]
Stance = Literal["偏多", "中性", "偏空"]


@dataclass
class FactorContext:
    """一次研究请求的上下文。"""

    symbol: str
    asof: date


@dataclass
class FactorResult:
    """单个因子的观测与方向。"""

    id: str
    name: str
    weight: float
    rationale: str
    status: Status
    direction: float | None = None
    source: str | None = None
    observed_at: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    message: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Conclusion:
    """模型给出的研究结论。"""

    symbol: str
    asof: str
    model: str
    stance: Stance
    score: float
    confidence: float
    used: list[dict[str, Any]]
    skipped: list[dict[str, Any]]
    disclaimer: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
