#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""跨市场日频面板。只用已接入、无需 API Key 的源。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable, Literal

import pandas as pd

from research.factors.scoring import now_iso
from research.models.diebold_yilmaz import MIN_ROWS
from research.types import FactorResult

LOOKBACK_DAYS = 420
Loader = Callable[[str, date], pd.Series]


@dataclass(frozen=True)
class SeriesSpec:
    id: str
    name: str
    kind: Literal["price", "flow"]
    align: Literal["local", "prior"]
    rationale: str


SPECS: tuple[SeriesSpec, ...] = (
    SeriesSpec(
        "a_share",
        "本股收益",
        "price",
        "local",
        "个股自身收益是连通性的接收对象。",
    ),
    SeriesSpec(
        "us_equity",
        "标普500",
        "price",
        "prior",
        "上一美股交易日的标普500收益，对齐到随后的 A 股交易日。",
    ),
    SeriesSpec(
        "vix",
        "VIX",
        "price",
        "prior",
        "上一交易日的 VIX 变化，对齐到随后的 A 股交易日。",
    ),
    SeriesSpec(
        "fx",
        "美元人民币",
        "price",
        "local",
        "美元兑人民币中间价的日变化。",
    ),
    SeriesSpec(
        "copper",
        "沪铜",
        "price",
        "local",
        "沪铜连续合约的日收益。",
    ),
    SeriesSpec(
        "northbound",
        "北向净买额",
        "flow",
        "local",
        "北向当日成交净买额。取不到时从面板中去掉。",
    ),
)
SPEC_BY_ID = {spec.id: spec for spec in SPECS}


def load_panel(symbol: str, asof: date) -> tuple[pd.DataFrame, list[FactorResult]]:
    """拉取并对齐面板。单列失败只记入 skipped。"""
    loaded: dict[str, pd.Series] = {}
    skipped: list[FactorResult] = []
    for spec in SPECS:
        try:
            loaded[spec.id] = LOADERS[spec.id](symbol, asof)
        except Exception as exc:
            skipped.append(_missing(spec, f"{type(exc).__name__}: {exc}"))
    if "a_share" not in loaded:
        return pd.DataFrame(), skipped
    others = {key: value for key, value in loaded.items() if key != "a_share"}
    aligned = align_panel(loaded["a_share"], others)
    frame, dropped = complete_cases(aligned)
    for name in dropped:
        skipped.append(_missing(SPEC_BY_ID[name], "有效重叠样本不足"))
    return frame, skipped


def align_panel(a_share: pd.Series, others: dict[str, pd.Series]) -> pd.DataFrame:
    """本股交易日为主轴。美股和 VIX 用严格早于当日的最近一条。"""
    master = pd.DatetimeIndex(pd.to_datetime(a_share.index)).normalize()
    master = master[~master.duplicated(keep="last")].sort_values()
    base = _changes(a_share, "price").reindex(master)
    columns = {"a_share": base}
    for name, series in others.items():
        spec = SPEC_BY_ID[name]
        changed = _changes(series, spec.kind)
        if spec.align == "prior":
            columns[name] = _prior_value(changed, master)
        else:
            columns[name] = changed.reindex(master)
    return pd.DataFrame(columns, index=master)


def complete_cases(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """丢掉重叠太短的列，再用共同交易日。"""
    if frame.empty or "a_share" not in frame.columns:
        return pd.DataFrame(), list(frame.columns)
    dropped = [
        column
        for column in frame.columns
        if int(frame[column].notna().sum()) < MIN_ROWS
    ]
    kept = [column for column in frame.columns if column not in dropped]
    if "a_share" not in kept:
        return pd.DataFrame(), list(frame.columns)
    return frame[kept].dropna(how="any"), dropped


def _changes(series: pd.Series, kind: str) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    values.index = pd.DatetimeIndex(pd.to_datetime(values.index)).normalize()
    values = values[~values.index.duplicated(keep="last")].sort_index().dropna()
    if kind == "price":
        values = values.pct_change()
    return values.dropna()


def _prior_value(series: pd.Series, master: pd.DatetimeIndex) -> pd.Series:
    left = pd.DataFrame({"date": master}).sort_values("date")
    right = series.rename("value").reset_index()
    right.columns = ["date", "value"]
    right["date"] = pd.to_datetime(right["date"])
    merged = pd.merge_asof(
        left,
        right.sort_values("date"),
        on="date",
        direction="backward",
        allow_exact_matches=False,
    )
    return pd.Series(merged["value"].to_numpy(), index=master)


def _missing(spec: SeriesSpec, message: str) -> FactorResult:
    return FactorResult(
        id=spec.id,
        name=spec.name,
        weight=0.0,
        rationale=spec.rationale,
        status="missing",
        observed_at=now_iso(),
        message=message,
    )


def _window_start(asof: date) -> date:
    return asof - timedelta(days=LOOKBACK_DAYS)


def _dated(values: pd.Series, dates) -> pd.Series:
    series = pd.Series(
        pd.to_numeric(values, errors="coerce").to_numpy(),
        index=pd.to_datetime(dates),
    )
    return series.dropna()


def _load_a_share(symbol: str, asof: date) -> pd.Series:
    from openbb import obb

    frame = obb.akshare.historical(
        symbol=symbol,
        start_date=_window_start(asof).isoformat(),
        end_date=asof.isoformat(),
        adjust="",
    ).to_dataframe()
    dates = frame["date"] if "date" in frame.columns else frame.index
    return _dated(frame["close"], dates)


def _load_us_equity(symbol: str, asof: date) -> pd.Series:
    del symbol
    import akshare as ak

    frame = ak.index_us_stock_sina(symbol=".INX")
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame[frame["date"].dt.date.between(_window_start(asof), asof)]
    return _dated(frame["close"], frame["date"])


def _load_vix(symbol: str, asof: date) -> pd.Series:
    del symbol
    from openbb import obb

    frame = obb.cboe.index.historical(
        symbol="VIX",
        start_date=_window_start(asof).isoformat(),
        end_date=asof.isoformat(),
    ).to_dataframe()
    dates = frame["date"] if "date" in frame.columns else frame.index
    level = frame["close"] if "close" in frame.columns else frame.iloc[:, 0]
    return _dated(level, dates)


def _load_fx(symbol: str, asof: date) -> pd.Series:
    del symbol
    import akshare as ak

    frame = ak.currency_boc_sina(
        symbol="美元",
        start_date=_window_start(asof).strftime("%Y%m%d"),
        end_date=asof.strftime("%Y%m%d"),
    )
    return _dated(frame["央行中间价"], frame["日期"])


def _load_copper(symbol: str, asof: date) -> pd.Series:
    del symbol
    import akshare as ak

    frame = ak.futures_zh_daily_sina(symbol="CU0")
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame[frame["date"].dt.date.between(_window_start(asof), asof)]
    return _dated(frame["close"], frame["date"])


def _load_northbound(symbol: str, asof: date) -> pd.Series:
    del symbol
    import akshare as ak

    frame = ak.stock_hsgt_hist_em(symbol="北向资金")
    frame["日期"] = pd.to_datetime(frame["日期"])
    frame = frame[frame["日期"].dt.date.between(_window_start(asof), asof)]
    series = _dated(frame["当日成交净买额"], frame["日期"])
    if series.empty:
        raise RuntimeError("近期北向成交净买额为空")
    if len(series) < MIN_ROWS:
        raise RuntimeError(f"近期北向成交净买额只有 {len(series)} 个交易日")
    return series


LOADERS: dict[str, Loader] = {
    "a_share": _load_a_share,
    "us_equity": _load_us_equity,
    "vix": _load_vix,
    "fx": _load_fx,
    "copper": _load_copper,
    "northbound": _load_northbound,
}
