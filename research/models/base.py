#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""模型协议。新增模型实现 run，并在 registry 登记。"""

from __future__ import annotations

from typing import Protocol, Sequence

from research.types import Conclusion, FactorResult


class Model(Protocol):
    id: str

    def run(
        self, symbol: str, asof: str, factors: Sequence[FactorResult]
    ) -> Conclusion:
        """把因子结果收成一份研究结论。"""
