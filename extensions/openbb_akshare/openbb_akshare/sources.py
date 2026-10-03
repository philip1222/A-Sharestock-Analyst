#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/10/3
Desc: 把 AKShare DataFrame 映射成 OpenBB 行，并在东方财富 K 线失败时换源
"""

from __future__ import annotations

from typing import Any, Callable, List, Mapping, MutableMapping, Sequence

import pandas as pd

from openbb_akshare.symbols import bare_symbol, exchange_of, prefixed_symbol

NETWORK_ERROR_NAMES = frozenset(
    {
        "ProxyError",
        "ConnectionError",
        "ConnectTimeout",
        "ReadTimeout",
        "Timeout",
        "ChunkedEncodingError",
        "RemoteDisconnected",
        "SSLError",
        "ProtocolError",
    }
)

HIST_COLUMN_ALIASES = {
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
    "涨跌幅": "change_percent",
    "涨跌额": "change",
    "换手率": "turnover",
}

QUOTE_COLUMN_ALIASES = {
    "代码": "symbol",
    "名称": "name",
    "最新价": "last_price",
    "今开": "open",
    "最高": "high",
    "最低": "low",
    "昨收": "prev_close",
    "涨跌额": "change",
    "涨跌幅": "change_percent",
    "成交量": "volume",
    "成交额": "amount",
    "买入": "bid",
    "卖出": "ask",
    "code": "symbol",
    "zxj": "last_price",
    "zd": "change",
    "zdf": "change_percent",
}

# 东方财富历史成交量单位是手，OpenBB 的 volume 按股计。
_LOT_SOURCES = frozenset({"eastmoney"})


def is_network_failure(exc: BaseException) -> bool:
    """
    判断异常是否属于上游站点 / 本机网络故障，而不是参数错误。

    :param exc: 捕获到的异常
    :return: 是否应按换源处理
    :rtype: bool
    """
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if type(current).__name__ in NETWORK_ERROR_NAMES:
            return True
        module = type(current).__module__
        name = type(current).__name__
        if "urllib3" in module or "requests" in module:
            if any(
                token in name
                for token in ("Proxy", "Connection", "Timeout", "Protocol", "SSL")
            ):
                return True
        current = current.__cause__ or current.__context__
    return False


def _rename(frame: pd.DataFrame, aliases: Mapping[str, str]) -> pd.DataFrame:
    """只重命名存在的列，避免源与源之间缺列时报错。"""
    mapping = {src: dest for src, dest in aliases.items() if src in frame.columns}
    return frame.rename(columns=mapping)


def _as_bare_code(value: Any) -> str:
    """把快照里的代码列收成 6 位数字，兼容 sz000001 / 1 / 000001。"""
    text = str(value).strip()
    try:
        return bare_symbol(text)
    except ValueError:
        digits = "".join(ch for ch in text if ch.isdigit())
        return digits.zfill(6) if digits else text


def _records(frame: pd.DataFrame) -> List[dict]:
    """把 DataFrame 转成 JSON 友好的行列表。"""
    if frame.empty:
        return []
    clean = frame.where(pd.notna(frame), None)
    return clean.to_dict(orient="records")


def history_rows(frame: pd.DataFrame, *, source: str, symbol: str) -> List[dict]:
    """
    把历史行情表映射成 OpenBB EquityHistorical 行。

    :param frame: AKShare 返回值
    :param source: 实际命中的源名
    :param symbol: 6 位股票代码
    :return: 行字典列表
    :rtype: list
    """
    renamed = _rename(frame, HIST_COLUMN_ALIASES)
    if "date" not in renamed.columns and renamed.index.name in {"date", "日期"}:
        renamed = renamed.reset_index()
        renamed = _rename(renamed, HIST_COLUMN_ALIASES)
    if "volume" in renamed.columns and source in _LOT_SOURCES:
        renamed = renamed.copy()
        renamed["volume"] = pd.to_numeric(renamed["volume"], errors="coerce") * 100
    if "change_percent" in renamed.columns:
        renamed = renamed.copy()
        renamed["change_percent"] = (
            pd.to_numeric(renamed["change_percent"], errors="coerce") / 100
        )
    rows = _records(renamed)
    for row in rows:
        row["symbol"] = symbol
        row["source"] = source
    return rows


def quote_rows(frame: pd.DataFrame, *, source: str, symbol: str | None) -> List[dict]:
    """
    把快照表映射成 OpenBB EquityQuote 行。

    :param frame: AKShare 返回值
    :param source: 实际命中的源名
    :param symbol: 指定代码时过滤，None 表示全表
    :return: 行字典列表
    :rtype: list
    """
    renamed = _rename(frame, QUOTE_COLUMN_ALIASES)
    if "symbol" in renamed.columns:
        renamed = renamed.copy()
        renamed["symbol"] = renamed["symbol"].map(_as_bare_code)
        if symbol:
            renamed = renamed[renamed["symbol"] == symbol]
    if "change_percent" in renamed.columns:
        renamed = renamed.copy()
        renamed["change_percent"] = (
            pd.to_numeric(renamed["change_percent"], errors="coerce") / 100
        )
    rows = _records(renamed)
    for row in rows:
        code = str(row.get("symbol") or symbol or "")
        row["symbol"] = code
        row["source"] = source
        row["asset_type"] = "stock"
        if code:
            row["exchange"] = exchange_of(code)
        if row.get("last_price") is not None and row.get("close") is None:
            row["close"] = row["last_price"]
    return rows


def first_successful(
    attempts: Sequence[tuple[str, Callable[[], Any]]],
) -> tuple[str, Any]:
    """
    按顺序尝试取数，网络类失败才换下一个源。

    :param attempts: ``(源名, 无参可调用对象)`` 列表
    :return: ``(源名, 返回值)``
    :raises RuntimeError: 全部失败时，带上各源的错误摘要
    """
    errors: list[str] = []
    last_exc: BaseException | None = None
    for name, caller in attempts:
        try:
            return name, caller()
        except Exception as exc:  # 上游站点改版、限流、断连都可能落到这里
            last_exc = exc
            if is_network_failure(exc):
                errors.append(f"{name}: {type(exc).__name__}: {exc}")
                continue
            raise
    message = "全部历史行情源均失败"
    if errors:
        message = f"{message}；" + "；".join(errors)
    raise RuntimeError(message) from last_exc


def default_history_attempts(
    *,
    symbol: str,
    start: str,
    end: str,
    period: str,
    adjust: str,
    callers: Mapping[str, Callable[..., pd.DataFrame]] | None = None,
) -> list[tuple[str, Callable[[], pd.DataFrame]]]:
    """
    组装历史行情换源顺序。

    日线：东方财富 → 腾讯 → 新浪。周线 / 月线只有东方财富提供，失败后不再硬试日线源。

    :param symbol: 6 位代码或带前缀代码
    :param start: YYYYMMDD
    :param end: YYYYMMDD
    :param period: daily / weekly / monthly
    :param adjust: ``""`` / ``qfq`` / ``hfq``
    :param callers: 可注入的取数函数，测试用
    :return: 有序尝试列表
    """
    import akshare as ak

    funcs: MutableMapping[str, Callable[..., pd.DataFrame]] = {
        "eastmoney": ak.stock_zh_a_hist,
        "tencent": ak.stock_zh_a_hist_tx,
        "sina": ak.stock_zh_a_daily,
    }
    if callers:
        funcs.update(callers)

    code = bare_symbol(symbol)
    prefixed = prefixed_symbol(symbol)
    attempts: list[tuple[str, Callable[[], pd.DataFrame]]] = [
        (
            "eastmoney",
            lambda: funcs["eastmoney"](
                symbol=code,
                period=period,
                start_date=start,
                end_date=end,
                adjust=adjust,
            ),
        )
    ]
    if period == "daily":
        attempts.append(
            (
                "tencent",
                lambda: funcs["tencent"](
                    symbol=prefixed,
                    start_date=start,
                    end_date=end,
                    adjust=adjust,
                ),
            )
        )
        attempts.append(
            (
                "sina",
                lambda: funcs["sina"](
                    symbol=prefixed,
                    start_date=start,
                    end_date=end,
                    adjust=adjust,
                ),
            )
        )
    return attempts


def default_quote_attempts(
    callers: Mapping[str, Callable[[], pd.DataFrame]] | None = None,
) -> list[tuple[str, Callable[[], pd.DataFrame]]]:
    """
    组装快照换源顺序：东方财富全市场快照优先，新浪次之。

    :param callers: 可注入的取数函数，测试用
    :return: 有序尝试列表
    """
    import akshare as ak

    funcs: MutableMapping[str, Callable[[], pd.DataFrame]] = {
        "eastmoney": ak.stock_zh_a_spot_em,
        "tencent": ak.stock_zh_a_spot_tx,
        "sina": ak.stock_zh_a_spot,
    }
    if callers:
        funcs.update(callers)
    order = ("eastmoney", "tencent", "sina")
    return [(name, funcs[name]) for name in order if name in funcs]


def fetch_history_rows(
    *,
    symbol: str,
    start: str,
    end: str,
    period: str = "daily",
    adjust: str = "",
    callers: Mapping[str, Callable[..., pd.DataFrame]] | None = None,
) -> List[dict]:
    """取历史行情并映射成 OpenBB 行。"""
    source, frame = first_successful(
        default_history_attempts(
            symbol=symbol,
            start=start,
            end=end,
            period=period,
            adjust=adjust,
            callers=callers,
        )
    )
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return []
    return history_rows(frame, source=source, symbol=bare_symbol(symbol))


def fetch_quote_rows(
    *,
    symbol: str,
    callers: Mapping[str, Callable[[], pd.DataFrame]] | None = None,
) -> List[dict]:
    """取快照并映射成 OpenBB 行。"""
    source, frame = first_successful(default_quote_attempts(callers))
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return []
    return quote_rows(frame, source=source, symbol=bare_symbol(symbol))
