"""Two-path recommendation pipeline binding book analysis to chart matching."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol, Sequence

import pandas as pd

from tools.a_share_recommender.double_breakout import (
    DoubleBreakoutMatch,
    DoubleBreakoutMatcher,
)


@dataclass(frozen=True)
class BookCandidate:
    symbol: str
    score: float
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class BookReview:
    symbol: str
    approved: bool
    score: float
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class Recommendation:
    symbol: str
    route: str
    combined_score: float
    book_score: float
    book_reasons: tuple[str, ...]
    template: DoubleBreakoutMatch

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["template"] = self.template.to_dict()
        return payload


class BookStrategyProvider(Protocol):
    """Adapter implemented by the existing 18-book strategy module."""

    source_count: int

    def initial_candidates(self) -> Sequence[BookCandidate]: ...

    def review_template_candidates(
        self, candidates: Sequence[DoubleBreakoutMatch]
    ) -> Sequence[BookReview]: ...


class MarketDataProvider(Protocol):
    """Market-data boundary used by the pipeline and tests."""

    def history(self, symbol: str) -> pd.DataFrame: ...

    def template_universe(self, sector: str | None = None) -> Sequence[str]: ...


@dataclass(frozen=True)
class PipelineResult:
    route: str
    recommendations: tuple[Recommendation, ...]
    diagnostics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "route": self.route,
            "recommendations": [item.to_dict() for item in self.recommendations],
            "diagnostics": self.diagnostics,
        }


class RecommendationPipeline:
    """Run the mandatory book-first path and template-first fallback path."""

    def __init__(
        self,
        market: MarketDataProvider,
        books: BookStrategyProvider,
        matcher: DoubleBreakoutMatcher | None = None,
        *,
        minimum_fit_score: float = 60.0,
    ) -> None:
        if books.source_count != 18:
            raise ValueError(
                "The recommendation workflow requires an 18-book strategy provider."
            )
        self.market = market
        self.books = books
        self.matcher = matcher or DoubleBreakoutMatcher()
        self.minimum_fit_score = minimum_fit_score

    def run(self, *, sector: str | None = None) -> PipelineResult:
        self.match_errors: dict[str, str] = {}
        initial = tuple(self.books.initial_candidates())
        initial_matches = self._match_symbols(item.symbol for item in initial)
        matched_initial = {
            symbol: match
            for symbol, match in initial_matches.items()
            if match.fit_score >= self.minimum_fit_score
        }
        if matched_initial:
            by_symbol = {item.symbol: item for item in initial}
            recommendations = tuple(
                self._recommend(
                    route="books_then_template",
                    template=match,
                    book_score=by_symbol[symbol].score,
                    book_reasons=by_symbol[symbol].reasons,
                )
                for symbol, match in matched_initial.items()
            )
            return PipelineResult(
                route="books_then_template",
                recommendations=self._rank(recommendations),
                diagnostics={
                    "book_candidates": len(initial),
                    "template_matches": len(recommendations),
                    "fallback_used": False,
                    "template_errors": self.match_errors,
                    "book_errors": getattr(self.books, "errors", {}),
                },
            )

        universe = tuple(dict.fromkeys(self.market.template_universe(sector)))
        fallback_matches = tuple(
            match
            for match in self._match_symbols(universe).values()
            if match.fit_score >= self.minimum_fit_score
        )
        reviews = {
            item.symbol: item
            for item in self.books.review_template_candidates(fallback_matches)
        }
        recommendations = tuple(
            self._recommend(
                route="template_then_books",
                template=match,
                book_score=reviews[match.symbol].score,
                book_reasons=reviews[match.symbol].reasons,
            )
            for match in fallback_matches
            if match.symbol in reviews and reviews[match.symbol].approved
        )
        return PipelineResult(
            route="template_then_books",
            recommendations=self._rank(recommendations),
            diagnostics={
                "book_candidates": len(initial),
                "initial_template_matches": len(matched_initial),
                "market_universe": len(universe),
                "fallback_template_matches": len(fallback_matches),
                "book_reviews": len(reviews),
                "fallback_used": True,
                "template_errors": self.match_errors,
                "book_errors": getattr(self.books, "errors", {}),
            },
        )

    def _match_symbols(
        self, symbols: Sequence[str] | Any
    ) -> dict[str, DoubleBreakoutMatch]:
        matches: dict[str, DoubleBreakoutMatch] = {}
        for symbol in symbols:
            normalized = str(symbol).zfill(6)
            try:
                matches[normalized] = self.matcher.match(
                    normalized, self.market.history(normalized)
                )
            except Exception as exc:
                self.match_errors[normalized] = f"{type(exc).__name__}: {exc}"
        return matches

    @staticmethod
    def _recommend(
        *,
        route: str,
        template: DoubleBreakoutMatch,
        book_score: float,
        book_reasons: tuple[str, ...],
    ) -> Recommendation:
        bounded_book_score = min(100.0, max(0.0, float(book_score)))
        combined = round(template.fit_score * 0.7 + bounded_book_score * 0.3, 2)
        return Recommendation(
            symbol=template.symbol,
            route=route,
            combined_score=combined,
            book_score=bounded_book_score,
            book_reasons=book_reasons,
            template=template,
        )

    @staticmethod
    def _rank(items: Sequence[Recommendation]) -> tuple[Recommendation, ...]:
        return tuple(sorted(items, key=lambda item: item.combined_score, reverse=True))
