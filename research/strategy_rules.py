#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""把行情窗口和估值分位收成交易计划。规则对应章节触发表的产出项，不摘录正文。"""

from __future__ import annotations

from typing import Any

import pandas as pd

WINDOWS = (1, 7, 15, 30)
MIN_BARS = 31
RISK_FRACTION = 0.01
ACCOUNT_TEMPLATE = 10_000.0
MAX_STOP_PCT = 0.08
DRAWDOWN_VETO = -0.20
PE_PERCENTILE_CAP = 0.80
MIN_AMOUNT = 2e7
DISCLAIMER = (
    "研究用交易计划，依据行情窗口和章节触发表中的规则模板计算，"
    "不构成下单指令，也不代表应当买入或卖出。A 股实行 T+1。"
)

EVIDENCE = {
    "swing": [
        {
            "level": "L1",
            "book": "L1_02_the-new-trading-for-a-living_alexander-elder.pdf",
            "chapters": "Chapter 39, Chapter 49-51",
            "rule": "入场前先定止损，止损过宽则不做。",
        },
        {
            "level": "L3",
            "book": "L3_12_technical-analysis-of-the-financial-markets_john-j-murphy.pdf",
            "chapters": "Chapter 4, Chapter 7",
            "rule": "收盘站上均线且中期收益为正才视为趋势成立，并用成交量确认。",
        },
        {
            "level": "L2",
            "book": "L2_07_the-intelligent-investor_benjamin-graham.pdf",
            "chapters": "Chapter 8",
            "rule": "没有估值分位时只观察，不给出买入。",
        },
    ],
    "short": [
        {
            "level": "L1",
            "book": "L1_02_the-new-trading-for-a-living_alexander-elder.pdf",
            "chapters": "Chapter 49-52",
            "rule": "单笔止损先于入场信号。",
        },
        {
            "level": "L3",
            "book": "L3_12_technical-analysis-of-the-financial-markets_john-j-murphy.pdf",
            "chapters": "Chapter 4, Momentum",
            "rule": "短线只在动量与趋势同向时给出计划。",
        },
        {
            "level": "L3",
            "book": "L3_14_way-of-the-turtle_curtis-faith.pdf",
            "chapters": "By What Measure?",
            "rule": "目标按 2 倍初始风险测算，不临时放大。",
        },
    ],
    "value": [
        {
            "level": "L1",
            "book": "L1_01_trade-your-way-to-financial-freedom_van-k-tharp.pdf",
            "chapters": "Chapter 12, Chapter 9",
            "rule": "用固定风险比例换算股数，而不是凭感觉下仓。",
        },
        {
            "level": "L2",
            "book": "L2_06_security-analysis_graham-dodd.pdf",
            "chapters": "Chapter 1, Chapter 4",
            "rule": "估值分位过高或市盈率为负时拒绝买入。",
        },
        {
            "level": "L4",
            "book": "L4_16_shou-ba-shou-du-cai-bao_tangchao.pdf",
            "chapters": "第五章",
            "rule": "缺少财报时不得把结论升到高置信。",
        },
    ],
}

TASKS = {
    "swing": "长线框架下波段",
    "short": "短线交易",
    "value": "长线价值配置",
}


def evaluate(
    frame: pd.DataFrame,
    *,
    symbol: str,
    asof: str,
    horizon: str = "swing",
    valuation: dict[str, Any] | None = None,
    references_ready: bool = True,
    missing_books: list[str] | None = None,
    source: str | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """根据已对齐的日线计算窗口、止损和动作。行情不足时不抛异常。"""
    if horizon not in EVIDENCE:
        raise KeyError(f"未知周期 {horizon}，可选: {'、'.join(EVIDENCE)}")
    data = _prepare(frame)
    missing: list[str] = []
    vetoes: list[str] = []
    del missing_books
    if data is None or len(data) < MIN_BARS:
        return _empty(
            symbol,
            asof,
            horizon,
            "行情不足 30 个交易日",
            missing,
            source,
            observed_at,
        )
    windows = {str(n): _window(data, n) for n in WINDOWS}
    close = float(data["close"].iloc[-1])
    ma20 = float(data["close"].tail(20).mean())
    atr = _atr(data)
    peak = float(data["close"].tail(30).max())
    drawdown = close / peak - 1
    ret15 = windows["15"]["return"]
    ret7 = windows["7"]["return"]
    if close > ma20 and ret15 > 0:
        structure = "上行"
    elif close < ma20 and ret15 < 0:
        structure = "下行"
    else:
        structure = "震荡"
    recent_low = float(data["low"].tail(7).min())
    stop = min(recent_low, close - 1.5 * atr)
    stop = min(stop, close * (1 - 0.01))
    risk = close - stop
    stop_pct = risk / close
    target = close + 2 * risk
    amount = data["amount"] if "amount" in data.columns else None
    if amount is not None and float(amount.tail(20).median()) < MIN_AMOUNT:
        vetoes.append("近 20 日成交额中位数低于 2000 万")
    if drawdown <= DRAWDOWN_VETO:
        vetoes.append("近 30 日自高点回撤超过 20%")
    if stop_pct > MAX_STOP_PCT:
        vetoes.append("止损距离超过 8%，单笔风险过宽")
    value_state, value_note = _value_gate(valuation, missing, vetoes)
    action, confidence, reason = _action(
        structure=structure,
        ret7=ret7,
        vetoes=vetoes,
        value_state=value_state,
    )
    lots = int((ACCOUNT_TEMPLATE * RISK_FRACTION / risk) // 100 * 100)
    plan_status = "active" if action == "买入" else "reference_only"
    return {
        "symbol": symbol,
        "asof": asof,
        "task": TASKS[horizon],
        "horizon": horizon,
        "action": action,
        "confidence": confidence,
        "confidence_reason": reason,
        "windows": windows,
        "path": _path(data),
        "trend": {
            "structure": structure,
            "close": round(close, 4),
            "ma20": round(ma20, 4),
            "atr14": round(atr, 4),
            "drawdown_30": round(drawdown, 4),
            "volume_ratio": _volume_ratio(data),
        },
        "valuation": valuation,
        "valuation_note": value_note,
        "vetoes": vetoes,
        "missing": missing,
        "plan": {
            "status": plan_status,
            "entry": round(close, 4),
            "stop": round(stop, 4),
            "stop_pct": round(stop_pct, 4),
            "take_profit": round(target, 4),
            "r_multiple": 2,
            "invalidation": "日收盘跌破止损价则计划失效",
            "position_template": (
                f"按每 {ACCOUNT_TEMPLATE:.0f} 元账户风险 {RISK_FRACTION:.0%} 测算，"
                f"约 {lots} 股（100 股为一手）"
                if lots >= 100
                else "按每 10000 元账户风险 1% 测算，不足 1 手"
            ),
        },
        "evidence": EVIDENCE[horizon],
        "data": {
            "source": source,
            "observed_at": observed_at,
            "bars": int(len(data)),
            "financials": "missing",
            "books_on_disk": references_ready,
        },
        "disclaimer": DISCLAIMER,
    }


def _action(
    *,
    structure: str,
    ret7: float,
    vetoes: list[str],
    value_state: str,
) -> tuple[str, str, str]:
    hard = [
        item
        for item in vetoes
        if "回撤" in item or "成交额" in item or "市盈率为负" in item
    ]
    if hard or structure == "下行":
        return "回避", "中", "趋势或风控闸门未通过"
    if structure == "上行" and ret7 > 0 and not vetoes and value_state == "ok":
        return "买入", "中", "趋势、估值分位和风控同时通过；缺少财报，置信度不超过中"
    if value_state != "ok":
        return "观察", "低", "估值分位不足，按规则不给出买入"
    if vetoes:
        return "观察", "低", "止损或流动性闸门未通过"
    return "观察", "低", "趋势未同时满足上行与近 7 日为正"


def _value_gate(
    valuation: dict[str, Any] | None, missing: list[str], vetoes: list[str]
) -> tuple[str, str]:
    if not valuation or valuation.get("pe_ttm") is None:
        missing.append("市盈率(TTM)")
        return "missing", "没有市盈率，不能确认安全边际"
    if valuation.get("pe_percentile") is None:
        missing.append("市盈率历史分位")
        return "missing", "有市盈率但分位样本不足"
    pe = float(valuation["pe_ttm"])
    percentile = float(valuation["pe_percentile"])
    if pe <= 0:
        vetoes.append("市盈率为负")
        return "veto", "市盈率为负"
    if percentile > PE_PERCENTILE_CAP:
        vetoes.append("市盈率近三年分位高于 80%")
        return "veto", "估值分位过高"
    return "ok", "市盈率分位未高于 80%"


def _prepare(frame: pd.DataFrame) -> pd.DataFrame | None:
    if frame is None or frame.empty or "close" not in frame.columns:
        return None
    data = frame.copy()
    if "date" not in data.columns:
        if isinstance(data.index, pd.DatetimeIndex) or data.index.name in {
            "date",
            "日期",
        }:
            data = data.reset_index()
        if "date" not in data.columns and "index" in data.columns:
            data = data.rename(columns={"index": "date"})
        if "日期" in data.columns and "date" not in data.columns:
            data = data.rename(columns={"日期": "date"})
    if "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
        data = data.sort_values("date")
    for column in ("open", "high", "low", "close"):
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")
    if "high" not in data.columns:
        data["high"] = data["close"]
    if "low" not in data.columns:
        data["low"] = data["close"]
    data = data.dropna(subset=["close", "high", "low"])
    return data if not data.empty else None


def _window(data: pd.DataFrame, n: int) -> dict[str, Any]:
    segment = data.iloc[-n:]
    base = float(data["close"].iloc[-(n + 1)])
    last = float(data["close"].iloc[-1])
    start = data["date"].iloc[-(n + 1)] if "date" in data.columns else None
    end = data["date"].iloc[-1] if "date" in data.columns else None
    amount = None
    if "amount" in segment.columns:
        amount = round(
            float(pd.to_numeric(segment["amount"], errors="coerce").sum()), 2
        )
    return {
        "trading_days": n,
        "start": None
        if start is None or pd.isna(start)
        else str(pd.Timestamp(start).date()),
        "end": None if end is None or pd.isna(end) else str(pd.Timestamp(end).date()),
        "return": round(last / base - 1, 4),
        "high": round(float(segment["high"].max()), 4),
        "low": round(float(segment["low"].min()), 4),
        "close": round(last, 4),
        "amount": amount,
    }


def _path(data: pd.DataFrame) -> list[dict[str, Any]]:
    tail = data.tail(30)
    rows = []
    for _, row in tail.iterrows():
        item: dict[str, Any] = {"close": round(float(row["close"]), 4)}
        if "date" in tail.columns and pd.notna(row["date"]):
            item["date"] = str(pd.Timestamp(row["date"]).date())
        rows.append(item)
    return rows


def _atr(data: pd.DataFrame) -> float:
    prev = data["close"].shift(1)
    true_range = pd.concat(
        [
            data["high"] - data["low"],
            (data["high"] - prev).abs(),
            (data["low"] - prev).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return float(true_range.tail(14).mean())


def _volume_ratio(data: pd.DataFrame) -> float | None:
    if "volume" not in data.columns or len(data) < 31:
        return None
    volume = pd.to_numeric(data["volume"], errors="coerce")
    base = float(volume.iloc[-31:-1].mean())
    if base <= 0:
        return None
    return round(float(volume.iloc[-1]) / base, 4)


def _empty(
    symbol: str,
    asof: str,
    horizon: str,
    reason: str,
    missing: list[str],
    source: str | None,
    observed_at: str | None,
) -> dict[str, Any]:
    missing = [reason, *missing]
    return {
        "symbol": symbol,
        "asof": asof,
        "task": TASKS[horizon],
        "horizon": horizon,
        "action": "观察",
        "confidence": "低",
        "confidence_reason": reason,
        "windows": {},
        "path": [],
        "trend": None,
        "valuation": None,
        "valuation_note": None,
        "vetoes": [],
        "missing": missing,
        "plan": None,
        "evidence": EVIDENCE[horizon],
        "data": {
            "source": source,
            "observed_at": observed_at,
            "bars": 0,
            "financials": "missing",
        },
        "disclaimer": DISCLAIMER,
    }
