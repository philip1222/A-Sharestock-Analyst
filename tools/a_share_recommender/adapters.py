"""AKShare market adapter and bridge to the repository's 18-book rules."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Callable, Sequence

import pandas as pd

from tools.a_share_recommender.double_breakout import DoubleBreakoutMatch
from research.strategy import BOOKS, build
from tools.a_share_recommender.pipeline import BookCandidate, BookReview


StrategyBuilder = Callable[[str, date, str], dict[str, Any]]


class ResearchBookStrategyProvider:
    """Call the existing deterministic rules derived from the 18-book list."""

    source_count = len(BOOKS)

    def __init__(
        self,
        symbols: Sequence[str],
        *,
        as_of: date,
        horizon: str = "swing",
        strategy_builder: StrategyBuilder = build,
    ) -> None:
        self.symbols = tuple(symbols)
        self.as_of = as_of
        self.horizon = horizon
        self.strategy_builder = strategy_builder
        self.errors: dict[str, str] = {}
        self._cache: dict[str, dict[str, Any]] = {}

    def initial_candidates(self) -> Sequence[BookCandidate]:
        candidates = []
        for symbol in self.symbols:
            result = self._evaluate(symbol)
            if result is not None and result.get("action") == "买入":
                candidates.append(self._candidate(result))
        return tuple(candidates)

    def review_template_candidates(
        self, candidates: Sequence[DoubleBreakoutMatch]
    ) -> Sequence[BookReview]:
        reviews = []
        for candidate in candidates:
            result = self._evaluate(candidate.symbol)
            if result is None:
                continue
            reviews.append(
                BookReview(
                    symbol=str(result["symbol"]).zfill(6),
                    approved=result.get("action") == "买入",
                    score=self._score(result),
                    reasons=self._reasons(result),
                )
            )
        return tuple(reviews)

    def _evaluate(self, symbol: str) -> dict[str, Any] | None:
        key = str(symbol)
        if key in self._cache:
            return self._cache[key]
        try:
            result = self.strategy_builder(key, self.as_of, self.horizon)
        except Exception as exc:
            self.errors[key] = f"{type(exc).__name__}: {exc}"
            return None
        normalized = str(result["symbol"]).zfill(6)
        self._cache[key] = result
        self._cache[normalized] = result
        return result

    @classmethod
    def _candidate(cls, result: dict[str, Any]) -> BookCandidate:
        return BookCandidate(
            symbol=str(result["symbol"]).zfill(6),
            score=cls._score(result),
            reasons=cls._reasons(result),
        )

    @staticmethod
    def _score(result: dict[str, Any]) -> float:
        action_score = {"买入": 80.0, "观察": 50.0, "回避": 20.0}
        confidence_bonus = {"高": 10.0, "中": 5.0, "低": 0.0}
        return action_score.get(str(result.get("action")), 0.0) + confidence_bonus.get(
            str(result.get("confidence")), 0.0
        )

    @staticmethod
    def _reasons(result: dict[str, Any]) -> tuple[str, ...]:
        reasons = [str(result.get("confidence_reason", "18本书规则评估"))]
        for item in result.get("evidence", ()):
            if item.get("book") and item.get("chapters"):
                reasons.append(f"{item['book']} — {item['chapters']}")
        return tuple(reasons)


class AkshareMarketDataProvider:
    """Retrieve historical bars and a practical limit-up-based scan universe."""

    def __init__(
        self,
        akshare_module,
        *,
        as_of: date | None = None,
        history_days: int = 120,
        universe_days: int = 35,
        max_universe: int = 50,
    ) -> None:
        self.ak = akshare_module
        self.as_of = as_of or date.today()
        self.history_days = history_days
        self.universe_days = universe_days
        self.max_universe = max_universe

    def history(self, symbol: str) -> pd.DataFrame:
        start = self.as_of - timedelta(days=self.history_days)
        return self.ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=self.as_of.strftime("%Y%m%d"),
            adjust="",
        )

    def template_universe(self, sector: str | None = None) -> Sequence[str]:
        sector_symbols: set[str] | None = None
        if sector:
            constituents = self.ak.stock_board_industry_cons_em(symbol=sector)
            sector_symbols = {
                str(value).zfill(6) for value in constituents["代码"].tolist()
            }

        candidates: dict[str, None] = {}
        for offset in range(self.universe_days):
            query_date = self.as_of - timedelta(days=offset)
            try:
                pool = self.ak.stock_zt_pool_em(date=query_date.strftime("%Y%m%d"))
            except (KeyError, TypeError, ValueError):
                continue
            if "代码" not in pool.columns:
                continue
            for value in pool["代码"].tolist():
                symbol = str(value).zfill(6)
                if sector_symbols is not None and symbol not in sector_symbols:
                    continue
                candidates[symbol] = None
                if len(candidates) >= self.max_universe:
                    return tuple(candidates)
        return tuple(candidates)
