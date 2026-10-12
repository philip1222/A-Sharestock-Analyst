from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from tools.a_share_recommender.adapters import ResearchBookStrategyProvider
from tools.a_share_recommender.double_breakout import DoubleBreakoutMatcher
from tools.a_share_recommender.pipeline import (
    BookCandidate,
    BookReview,
    RecommendationPipeline,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def matching_history() -> pd.DataFrame:
    closes = [10.0, 10.0, 10.0, 10.0, 10.0, 11.0, 10.7, 10.4, 10.1, 9.95]
    opens = [9.9, 10.0, 10.0, 10.0, 10.0, 10.1, 10.9, 10.6, 10.3, 10.1]
    highs = [10.1, 10.1, 10.1, 10.1, 10.1, 11.1, 10.9, 10.7, 10.4, 10.2]
    lows = [9.8, 9.9, 9.9, 9.9, 9.9, 10.0, 10.6, 10.3, 10.0, 9.9]
    volumes = [100, 100, 100, 100, 100, 300, 130, 120, 110, 100]

    closes.extend([9.4, 11.0, 10.5, 11.2])
    opens.extend([9.9, 9.5, 10.8, 10.7])
    highs.extend([10.0, 11.1, 10.9, 11.3])
    lows.extend([9.3, 9.4, 10.4, 10.6])
    volumes.extend([90, 250, 140, 220])
    return pd.DataFrame(
        {
            "日期": pd.date_range("2026-01-01", periods=len(closes)),
            "开盘": opens,
            "收盘": closes,
            "最高": highs,
            "最低": lows,
            "成交量": volumes,
        }
    )


def non_matching_history() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "日期": pd.date_range("2026-01-01", periods=10),
            "开盘": [10.0] * 10,
            "收盘": [10.0] * 10,
            "最高": [10.1] * 10,
            "最低": [9.9] * 10,
            "成交量": [100] * 10,
        }
    )


class FakeMarket:
    def __init__(self) -> None:
        self.histories = {
            "000001": matching_history(),
            "000002": non_matching_history(),
        }

    def history(self, symbol: str) -> pd.DataFrame:
        return self.histories[symbol]

    def template_universe(self, sector: str | None = None) -> tuple[str, ...]:
        return ("000001",)


@dataclass
class FakeBooks:
    initial: tuple[BookCandidate, ...]
    reviews: tuple[BookReview, ...] = ()
    source_count: int = 18
    review_called: bool = False

    def initial_candidates(self) -> tuple[BookCandidate, ...]:
        return self.initial

    def review_template_candidates(self, candidates):
        self.review_called = True
        return self.reviews


def test_matcher_finds_full_pattern_and_price_levels():
    result = DoubleBreakoutMatcher().match("000001", matching_history())

    assert result.fit_score == 100.0
    assert result.signal == "confirmed_double_breakout"
    assert result.entry_pullback == 10.25
    assert result.entry_second_breakout == 11.1
    assert result.stop_loss == 9.4
    assert result.target_2r == 11.95


def test_matcher_loads_repository_template():
    matcher = DoubleBreakoutMatcher.from_template(
        PROJECT_ROOT / "tools" / "strategy_templates" / "yin_yang_double_breakout.json"
    )

    assert matcher.lookback_sessions == 20
    assert matcher.breakout_volume_ratio == 1.5


def test_pipeline_prefers_book_candidates_then_template():
    books = FakeBooks(initial=(BookCandidate("000001", 80.0, ("book evidence",)),))
    result = RecommendationPipeline(FakeMarket(), books).run()

    assert result.route == "books_then_template"
    assert [item.symbol for item in result.recommendations] == ["000001"]
    assert result.recommendations[0].combined_score == 94.0
    assert books.review_called is False


def test_pipeline_falls_back_to_template_then_book_review():
    books = FakeBooks(
        initial=(BookCandidate("000002", 85.0),),
        reviews=(BookReview("000001", True, 70.0, ("reviewed",)),),
    )
    result = RecommendationPipeline(FakeMarket(), books).run(sector="示例板块")

    assert result.route == "template_then_books"
    assert [item.symbol for item in result.recommendations] == ["000001"]
    assert result.recommendations[0].combined_score == 91.0
    assert books.review_called is True


def test_pipeline_rejects_non_18_book_provider():
    books = FakeBooks(initial=(), source_count=17)

    try:
        RecommendationPipeline(FakeMarket(), books)
    except ValueError as exc:
        assert "18-book" in str(exc)
    else:
        raise AssertionError("Expected the pipeline to enforce the 18-book provider")


def test_repository_book_provider_calls_existing_strategy_rules():
    calls = []

    def fake_build(symbol, as_of, horizon):
        calls.append((symbol, as_of, horizon))
        return {
            "symbol": str(symbol).zfill(6),
            "action": "买入",
            "confidence": "中",
            "confidence_reason": "规则通过",
            "evidence": [
                {
                    "book": "L3_12_technical-analysis.pdf",
                    "chapters": "Chapter 4",
                }
            ],
        }

    provider = ResearchBookStrategyProvider(
        ("1",),
        as_of=pd.Timestamp("2026-10-12").date(),
        strategy_builder=fake_build,
    )
    candidates = provider.initial_candidates()

    assert provider.source_count == 18
    assert candidates[0].symbol == "000001"
    assert candidates[0].score == 85.0
    assert calls[0][2] == "swing"
