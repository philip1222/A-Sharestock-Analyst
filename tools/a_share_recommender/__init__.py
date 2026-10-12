"""A-share recommendation workflow built around reusable strategy adapters."""

from tools.a_share_recommender.double_breakout import (
    DoubleBreakoutMatch,
    DoubleBreakoutMatcher,
)
from tools.a_share_recommender.pipeline import (
    BookCandidate,
    BookReview,
    Recommendation,
    RecommendationPipeline,
)

__all__ = [
    "BookCandidate",
    "BookReview",
    "DoubleBreakoutMatch",
    "DoubleBreakoutMatcher",
    "Recommendation",
    "RecommendationPipeline",
]
