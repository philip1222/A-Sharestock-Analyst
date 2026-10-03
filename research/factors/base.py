#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""因子协议。新增因子实现 evaluate，并在 registry 登记。"""

from __future__ import annotations

from typing import Protocol

from research.types import FactorContext, FactorResult


class Factor(Protocol):
    id: str
    name: str
    weight: float
    rationale: str

    def evaluate(self, ctx: FactorContext) -> FactorResult:
        """取数并给出 -1..1 的方向。失败时返回 missing 或 error，不要抛到结论器外。"""
