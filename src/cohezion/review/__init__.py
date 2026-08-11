"""Delegated code review: deterministic spec from `ocr`, inference on our own path."""

from cohezion.review.delegate import (
    DelegatedReview,
    ReviewFile,
    build_prompt,
    collect,
    run_review,
)


__all__ = [
    "DelegatedReview",
    "ReviewFile",
    "build_prompt",
    "collect",
    "run_review",
]
