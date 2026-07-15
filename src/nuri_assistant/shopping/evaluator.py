from __future__ import annotations

import math
from dataclasses import dataclass

from .models import ProductCandidate


@dataclass(frozen=True)
class PurchaseAssessment:
    product: ProductCandidate
    score: float
    evidence_level: str
    reasons: tuple[str, ...]


def _score_product(product: ProductCandidate, cheapest_price: int) -> PurchaseAssessment:
    price_score = cheapest_price / product.price * 25
    rating_score = (product.rating / 5 * 30) if product.rating else 15
    review_score = min(math.log10(product.review_count + 1) / 4, 1) * 10
    warranty_score = min(product.warranty_months / 24, 1) * 10
    suitability_score = product.suitability / 5 * 25
    score = round(price_score + rating_score + review_score + warranty_score + suitability_score, 1)

    facts = sum(
        (
            product.rating > 0,
            product.review_count > 0,
            product.warranty_months > 0,
            product.suitability != 3,
        )
    )
    evidence_level = "high" if facts >= 3 else "medium" if facts >= 2 else "low"
    reasons = (
        f"Price: {product.price:,}",
        f"Rating: {product.rating:.1f}/5" if product.rating else "Rating not provided",
        f"Reviews: {product.review_count:,}" if product.review_count else "Review count not provided",
        f"Fit score: {product.suitability}/5",
    )
    return PurchaseAssessment(product, score, evidence_level, reasons)


def evaluate_purchase(products: list[ProductCandidate]) -> list[PurchaseAssessment]:
    """Rank user-provided products without claiming live market research."""

    if not products:
        raise ValueError("Add at least one product before evaluating.")
    cheapest_price = min(product.price for product in products)
    return sorted(
        (_score_product(product, cheapest_price) for product in products),
        key=lambda assessment: assessment.score,
        reverse=True,
    )
