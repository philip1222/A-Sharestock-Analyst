#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""研究入口用的代码校验。与 openbb_akshare.symbols.bare_symbol 口径一致，避免结论模块依赖 OpenBB。"""

from __future__ import annotations

_PREFIXES = ("SH", "SZ", "BJ")


def bare_symbol(symbol: str) -> str:
    text = symbol.strip().upper()
    if text.startswith(_PREFIXES):
        text = text[2:]
    if len(text) == 6 and text.isdigit():
        return text
    raise ValueError(
        f"无法识别的 A 股代码: {symbol!r}，需要 6 位数字，可带 sh/sz/bj 前缀"
    )
