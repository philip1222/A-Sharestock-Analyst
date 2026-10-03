#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/10/3
Desc: 包入口。Provider 懒加载，避免未装 openbb-core 时拖垮普通测试。
"""

from typing import Any

__all__ = ["akshare_provider"]


def __getattr__(name: str) -> Any:
    """按需导出 Provider，entry point 与 `from openbb_akshare import akshare_provider` 都走这里。"""
    if name == "akshare_provider":
        from openbb_akshare.provider import akshare_provider

        return akshare_provider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
