#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/10/3
Desc: A 股代码在 OpenBB 与各 AKShare 源之间的格式转换
"""

from __future__ import annotations

_PREFIXES = ("SH", "SZ", "BJ")


def bare_symbol(symbol: str) -> str:
    """
    去掉市场前缀，只保留 6 位数字代码。

    OpenBB 标准模型会把 symbol 转成大写，所以这里大小写都认。

    :param symbol: ``000001`` / ``sz000001`` / ``SZ000001``
    :return: 6 位数字代码
    :rtype: str
    :raises ValueError: 无法识别时
    """
    text = symbol.strip().upper()
    if text.startswith(_PREFIXES):
        text = text[2:]
    if len(text) == 6 and text.isdigit():
        return text
    raise ValueError(
        f"无法识别的 A 股代码: {symbol!r}，需要 6 位数字，可带 sh/sz/bj 前缀"
    )


def prefixed_symbol(symbol: str) -> str:
    """
    转成腾讯 / 新浪源需要的小写市场前缀形式。

    :param symbol: 任意常见写法
    :return: 如 ``sz000001``
    :rtype: str
    """
    text = symbol.strip().lower()
    if text.startswith(("sh", "sz", "bj")):
        return text
    code = bare_symbol(symbol)
    if code.startswith(("600", "601", "603", "605", "688", "900")):
        return f"sh{code}"
    if code.startswith(("430", "440", "830", "831", "832", "833", "839")):
        return f"bj{code}"
    return f"sz{code}"


def exchange_of(symbol: str) -> str:
    """
    由代码推断交易所。

    :param symbol: 任意常见写法
    :return: ``SSE`` / ``SZSE`` / ``BSE``
    :rtype: str
    """
    prefixed = prefixed_symbol(symbol)
    if prefixed.startswith("sh"):
        return "SSE"
    if prefixed.startswith("bj"):
        return "BSE"
    return "SZSE"
