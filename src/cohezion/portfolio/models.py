"""Cohezion Portfolio — data models for competition and project tracking."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


ProjectStatus = Literal[
    "active",       # working on it
    "running",      # kernel/job in progress (Kaggle training run)
    "complete",     # kernel finished, not yet submitted
    "submitted",    # submission on leaderboard
    "banked",       # best score saved, may re-submit
    "deferred",     # out-of-scope until later date
]


class PortfolioProject(BaseModel):
    """A single competition or project tracked in the Cohezion portfolio."""

    id: str = Field(..., description="Short slug, e.g. 'nemotron'")
    name: str
    competition: str | None = None      # Kaggle/Devpost slug
    deadline: datetime | None = None
    prize: int | None = None            # USD (0 for non-cash)
    status: ProjectStatus = "active"
    score: float | None = None          # Best public leaderboard score
    score_label: str | None = None      # e.g. "0.84 public" or "187.4 pts"
    kernel: str | None = None           # Kaggle kernel slug (for training/submit)
    worktree: str | None = None         # Local git worktree path fragment
    last_session: str | None = None     # Most recent session ID that touched this
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notes: list[str] = Field(default_factory=list)

    def days_to_deadline(self) -> int | None:
        if self.deadline is None:
            return None
        deadline = self.deadline if self.deadline.tzinfo else self.deadline.replace(tzinfo=UTC)
        delta = deadline - datetime.now(UTC)
        return max(0, delta.days)

    def is_urgent(self) -> bool:
        """True when deadline is within 7 days."""
        days = self.days_to_deadline()
        return days is not None and days <= 7


class PortfolioSummary(BaseModel):
    """Lightweight summary for list endpoints."""

    id: str
    name: str
    competition: str | None
    deadline: datetime | None
    prize: int | None
    status: ProjectStatus
    score_label: str | None
    days_to_deadline: int | None
    is_urgent: bool
