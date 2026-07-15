from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductCandidate:
    name: str
    price: int
    rating: float = 0.0
    review_count: int = 0
    warranty_months: int = 0
    suitability: int = 3
    is_target: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Product name is required.")
        if self.price <= 0:
            raise ValueError("Price must be greater than zero.")
        if not 0 <= self.rating <= 5:
            raise ValueError("Rating must be between 0 and 5.")
        if self.review_count < 0 or self.warranty_months < 0:
            raise ValueError("Review count and warranty cannot be negative.")
        if not 1 <= self.suitability <= 5:
            raise ValueError("Suitability must be between 1 and 5.")
