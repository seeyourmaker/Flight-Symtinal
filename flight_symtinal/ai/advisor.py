"""Deterministic route recommendation logic for the /shouldibuy command."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from flight_symtinal.core.analytics import RoutePriceSnapshot


@dataclass(frozen=True)
class BuyAdvice:
    """A simple travel recommendation."""

    recommendation: str
    reasoning: str


@dataclass(frozen=True)
class RouteMetrics:
    """Derived metrics used for a buy/wait/monitor decision."""

    current_price: int
    lowest_price: int
    highest_price: int
    average_price: float
    observations: int
    distance_from_low_pct: float
    distance_from_average_pct: float
    target_price: int | None


@dataclass(frozen=True)
class DecisionResult:
    """Final recommendation plus the score used to produce it."""

    recommendation: str
    score: int
    reasoning: str
    metrics: RouteMetrics


class AdviceProvider(Protocol):
    """Interface for swappable advice providers."""

    def recommend(self, snapshot: RoutePriceSnapshot, target_price: int | None) -> DecisionResult:
        """Return a recommendation for one route/date combination."""


class RuleBasedAdviceProvider:
    """Deterministic first-pass advisor that does not call an LLM."""

    def recommend(self, snapshot: RoutePriceSnapshot, target_price: int | None) -> DecisionResult:
        """Generate a recommendation from existing analytics only."""
        metrics = _build_metrics(snapshot, target_price)
        score = _score(metrics)
        recommendation = _score_to_recommendation(score)
        reasoning = _build_reasoning(metrics, score, recommendation)
        return DecisionResult(
            recommendation=recommendation,
            score=score,
            reasoning=reasoning,
            metrics=metrics,
        )


def _build_metrics(snapshot: RoutePriceSnapshot, target_price: int | None) -> RouteMetrics:
    """Compute the numeric inputs used by the scoring system."""
    distance_from_low_pct = _percent_above(snapshot.current_price, snapshot.lowest_price)
    distance_from_average_pct = _percent_above(snapshot.current_price, int(round(snapshot.average_price)))
    return RouteMetrics(
        current_price=snapshot.current_price,
        lowest_price=snapshot.lowest_price,
        highest_price=snapshot.highest_price,
        average_price=snapshot.average_price,
        observations=snapshot.observations,
        distance_from_low_pct=distance_from_low_pct,
        distance_from_average_pct=distance_from_average_pct,
        target_price=target_price,
    )


def _score(metrics: RouteMetrics) -> int:
    """Convert analytics into a transparent score from 0 to 100."""
    score = 50

    if metrics.target_price is not None:
        if metrics.current_price <= metrics.target_price:
            score += 30
        elif metrics.current_price <= metrics.target_price * 1.05:
            score += 15
        else:
            score -= 10

    if metrics.distance_from_average_pct < 0:
        score += min(20, int(abs(metrics.distance_from_average_pct)))
    else:
        score -= min(15, int(metrics.distance_from_average_pct))

    if metrics.distance_from_low_pct <= 15:
        score += 15
    elif metrics.distance_from_low_pct <= 30:
        score += 5
    else:
        score -= 5

    if metrics.observations < 3:
        score -= 20
    elif metrics.observations < 5:
        score -= 5
    else:
        score += 5

    return max(0, min(100, score))


def _score_to_recommendation(score: int) -> str:
    """Map the numeric score to a plain-English recommendation."""
    if score >= 75:
        return "BUY NOW"
    if score >= 45:
        return "MONITOR"
    return "WAIT"


def _build_reasoning(metrics: RouteMetrics, score: int, recommendation: str) -> str:
    """Explain the recommendation in plain English."""
    parts = [
        f"Score {score}/100.",
        f"Current fare is {metrics.distance_from_average_pct:.1f}% above average and {metrics.distance_from_low_pct:.1f}% above the lowest observed fare.",
    ]

    if metrics.target_price is not None:
        if metrics.current_price <= metrics.target_price:
            parts.append(f"It is already at or below the target price of {metrics.target_price}.")
        else:
            parts.append(f"The target price is {metrics.target_price}.")

    if recommendation == "BUY NOW":
        parts.append("The fare is in a strong buying zone based on the current trend.")
    elif recommendation == "WAIT":
        parts.append("The fare is still relatively expensive compared with the historical range.")
    else:
        parts.append("There is not enough edge yet to buy confidently, so keep watching.")

    return " ".join(parts)


def _percent_above(current: int, baseline: int) -> float:
    """Return how far the current price is above the baseline in percent."""
    if baseline <= 0:
        return 0.0
    return ((current - baseline) / baseline) * 100
