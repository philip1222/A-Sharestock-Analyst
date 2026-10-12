"""Quantified matcher for the Yin-Jin Yang-Sheng double-breakout pattern."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd


_COLUMN_ALIASES = {
    "date": ("date", "日期"),
    "open": ("open", "开盘"),
    "close": ("close", "收盘"),
    "high": ("high", "最高"),
    "low": ("low", "最低"),
    "volume": ("volume", "成交量"),
}


@dataclass(frozen=True)
class DoubleBreakoutMatch:
    """Structured evidence and price levels produced by the matcher."""

    symbol: str
    fit_score: float
    signal: str
    limit_up_date: str | None
    yin_jin_date: str | None
    breakout_date: str | None
    second_breakout_date: str | None
    entry_pullback: float | None
    entry_second_breakout: float | None
    stop_loss: float | None
    target_2r: float | None
    evidence: dict[str, bool | float | str | None]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DoubleBreakoutMatcher:
    """Score an OHLCV series against the configured chart pattern."""

    def __init__(
        self,
        *,
        lookback_sessions: int = 20,
        limit_up_pct: float = 9.5,
        limit_volume_ratio: float = 2.0,
        yin_jin_pct: float = -5.0,
        pullback_volume_ratio: float = 0.65,
        breakout_volume_ratio: float = 1.5,
    ) -> None:
        self.lookback_sessions = lookback_sessions
        self.limit_up_pct = limit_up_pct
        self.limit_volume_ratio = limit_volume_ratio
        self.yin_jin_pct = yin_jin_pct
        self.pullback_volume_ratio = pullback_volume_ratio
        self.breakout_volume_ratio = breakout_volume_ratio

    @classmethod
    def from_template(cls, path: Path) -> DoubleBreakoutMatcher:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rules = payload["rules"]
        return cls(
            lookback_sessions=int(rules["lookback_sessions"]),
            limit_up_pct=float(rules["limit_up_pct"]),
            limit_volume_ratio=float(rules["limit_up_volume_ratio_vs_previous_5"]),
            yin_jin_pct=float(rules["yin_jin_daily_pct"]),
            pullback_volume_ratio=float(rules["pullback_volume_ratio_vs_limit_up"]),
            breakout_volume_ratio=float(rules["breakout_volume_ratio_vs_previous_5"]),
        )

    @staticmethod
    def _normalize(frame: pd.DataFrame) -> pd.DataFrame:
        renamed: dict[str, str] = {}
        for canonical, aliases in _COLUMN_ALIASES.items():
            match = next((name for name in aliases if name in frame.columns), None)
            if match is None:
                raise ValueError(f"Missing required OHLCV column: {canonical}")
            renamed[match] = canonical

        data = frame.rename(columns=renamed)[list(_COLUMN_ALIASES)].copy()
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
        for column in ("open", "close", "high", "low", "volume"):
            data[column] = pd.to_numeric(data[column], errors="coerce")
        data.dropna(inplace=True)
        data.sort_values("date", inplace=True)
        data.reset_index(drop=True, inplace=True)
        data["daily_pct"] = data["close"].pct_change() * 100
        data["volume_ma5"] = data["volume"].shift(1).rolling(5).mean()
        return data

    @staticmethod
    def _date_value(data: pd.DataFrame, index: int | None) -> str | None:
        if index is None:
            return None
        return data.loc[index, "date"].strftime("%Y-%m-%d")

    def match(self, symbol: str, frame: pd.DataFrame) -> DoubleBreakoutMatch:
        data = self._normalize(frame)
        if len(data) < 8:
            return self._empty(symbol, "insufficient_history")

        recent_start = max(5, len(data) - self.lookback_sessions - 1)
        limit_mask = (
            (data["daily_pct"] >= self.limit_up_pct)
            & (data["volume_ma5"] > 0)
            & (data["volume"] >= data["volume_ma5"] * self.limit_volume_ratio)
        )
        limit_indexes = data.index[limit_mask & (data.index >= recent_start)].tolist()
        if not limit_indexes:
            return self._empty(symbol, "no_recent_high_volume_limit_up")

        limit_indexes_with_later_yin = [
            index
            for index in limit_indexes
            if bool((data.loc[index + 1 :, "daily_pct"] <= self.yin_jin_pct).any())
        ]
        limit_index = (
            limit_indexes_with_later_yin[-1]
            if limit_indexes_with_later_yin
            else limit_indexes[-1]
        )
        after_limit = data.loc[limit_index + 1 :]
        if after_limit.empty:
            return self._empty(symbol, "limit_up_is_latest_bar", limit_up=True)

        yin_indexes = after_limit.index[
            after_limit["daily_pct"] <= self.yin_jin_pct
        ].tolist()
        yin_index = yin_indexes[-1] if yin_indexes else None
        pullback_end = (
            yin_index if yin_index is not None else int(after_limit.index[-1])
        )
        pullback = data.loc[limit_index + 1 : pullback_end]
        limit_volume = float(data.loc[limit_index, "volume"])
        volume_ratio = (
            float(pullback["volume"].median() / limit_volume)
            if not pullback.empty and limit_volume > 0
            else float("inf")
        )
        pullback_exists = bool(
            not pullback.empty
            and float(pullback["close"].min()) < float(data.loc[limit_index, "close"])
        )
        volume_contracts = volume_ratio <= self.pullback_volume_ratio

        breakout_index: int | None = None
        breakout_bullish = False
        breaks_pressure = False
        breakout_volume = False
        pressure: float | None = None
        if yin_index is not None:
            pressure_frame = data.loc[limit_index + 1 : yin_index]
            pressure = float(pressure_frame["high"].max())
            for index in data.loc[yin_index + 1 :].index:
                row = data.loc[index]
                bullish = bool(row["close"] > row["open"])
                above_pressure = bool(row["close"] > pressure)
                expanded = bool(
                    pd.notna(row["volume_ma5"])
                    and row["volume"] >= row["volume_ma5"] * self.breakout_volume_ratio
                )
                if bullish and above_pressure and expanded:
                    breakout_index = int(index)
                    breakout_bullish = bullish
                    breaks_pressure = above_pressure
                    breakout_volume = expanded
                    break

        second_index: int | None = None
        if breakout_index is not None:
            first_breakout_high = float(data.loc[breakout_index, "high"])
            for index in data.loc[breakout_index + 1 :].index:
                if float(data.loc[index, "close"]) > first_breakout_high:
                    second_index = int(index)
                    break

        score = 20.0
        score += 10.0 if pullback_exists else 0.0
        score += 15.0 if volume_contracts else 0.0
        score += 15.0 if yin_index is not None else 0.0
        score += 5.0 if breakout_bullish else 0.0
        score += 15.0 if breaks_pressure else 0.0
        score += 10.0 if breakout_volume else 0.0
        score += 10.0 if second_index is not None else 0.0

        entry_pullback: float | None = None
        entry_second: float | None = None
        stop_loss: float | None = None
        target_2r: float | None = None
        if breakout_index is not None:
            breakout = data.loc[breakout_index]
            entry_pullback = round(
                (float(breakout["open"]) + float(breakout["close"])) / 2,
                3,
            )
            entry_second = round(float(breakout["high"]), 3)
            stop_loss = round(float(breakout["low"]), 3)
            risk = max(0.0, entry_pullback - stop_loss)
            target_2r = round(entry_pullback + 2 * risk, 3)

        if second_index is not None:
            signal = "confirmed_double_breakout"
        elif breakout_index is not None:
            signal = "first_breakout_confirmed"
        elif yin_index is not None:
            signal = "yin_jin_near_trigger"
        else:
            signal = "watching_pullback"

        return DoubleBreakoutMatch(
            symbol=symbol,
            fit_score=score,
            signal=signal,
            limit_up_date=self._date_value(data, limit_index),
            yin_jin_date=self._date_value(data, yin_index),
            breakout_date=self._date_value(data, breakout_index),
            second_breakout_date=self._date_value(data, second_index),
            entry_pullback=entry_pullback,
            entry_second_breakout=entry_second,
            stop_loss=stop_loss,
            target_2r=target_2r,
            evidence={
                "recent_high_volume_limit_up": True,
                "pullback_exists": pullback_exists,
                "pullback_volume_ratio": round(volume_ratio, 4),
                "pullback_volume_contracts": volume_contracts,
                "yin_jin_decline": yin_index is not None,
                "breakout_bullish": breakout_bullish,
                "breaks_pressure": breaks_pressure,
                "breakout_volume_expands": breakout_volume,
                "second_breakout": second_index is not None,
                "pressure": round(pressure, 3) if pressure is not None else None,
            },
        )

    @staticmethod
    def _empty(
        symbol: str, reason: str, *, limit_up: bool = False
    ) -> DoubleBreakoutMatch:
        return DoubleBreakoutMatch(
            symbol=symbol,
            fit_score=20.0 if limit_up else 0.0,
            signal="not_matched",
            limit_up_date=None,
            yin_jin_date=None,
            breakout_date=None,
            second_breakout_date=None,
            entry_pullback=None,
            entry_second_breakout=None,
            stop_loss=None,
            target_2r=None,
            evidence={"reason": reason},
        )
