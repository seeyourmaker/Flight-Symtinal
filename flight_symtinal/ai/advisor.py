"""Route recommendation logic for the /shouldibuy command."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from flight_symtinal.core.analytics import RoutePriceSnapshot


@dataclass(frozen=True)
class BuyAdvice:
    """A simple travel recommendation."""

    recommendation: str
    reasoning: str


class AdviceProvider(Protocol):
    """Interface for swappable advice providers."""

    def recommend(self, snapshot: RoutePriceSnapshot, target_price: int | None) -> BuyAdvice:
        """Return a recommendation for one route/date combination."""


class RuleBasedAdviceProvider:
    """Deterministic first-pass advisor that does not call an LLM."""

    def recommend(self, snapshot: RoutePriceSnapshot, target_price: int | None) -> BuyAdvice:
        """Generate a recommendation from existing analytics only."""
        if target_price is not None and snapshot.current_price <= target_price:
            return BuyAdvice(
                recommendation="Buy Now",
                reasoning=(
                    f"Current price {snapshot.current_price} is at or below the target "
                    f"price {target_price}."
                ),
            )

        if snapshot.observations < 3:
            return BuyAdvice(
                recommendation="Monitor",
                reasoning=(
                    f"Only {snapshot.observations} observations are available, so the trend "
                    "is still too thin to trust."
                ),
            )

        if snapshot.current_price <= snapshot.average_price:
            return BuyAdvice(
                recommendation="Buy Now",
                reasoning=(
                    f"Current price {snapshot.current_price} is at or below the average "
                    f"price {snapshot.average_price:.0f}."
                ),
            )

        if snapshot.current_price >= snapshot.highest_price:
            return BuyAdvice(
                recommendation="Wait",
                reasoning=(
                    f"Current price {snapshot.current_price} is at the top of the observed "
                    f"range, with a low of {snapshot.lowest_price}."
                ),
            )

        return BuyAdvice(
            recommendation="Monitor",
            reasoning=(
                f"Current price {snapshot.current_price} is between the low and high "
                f"range, so it is worth watching a bit longer."
            ),
        )

