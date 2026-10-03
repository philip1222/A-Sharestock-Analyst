#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""因子共用的数值裁剪与时间戳。"""

from __future__ import annotations

from datetime import datetime, timezone


def clip(value: float, limit: float = 1.0) -> float:
    return max(-limit, min(limit, value))


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
