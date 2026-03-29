"""Rate limiter for popcorn-cli leaderboard submissions.

Enforces 1 leaderboard submission per hour per problem.
"""

from __future__ import annotations

import json
import time
from pathlib import Path


RATE_LIMIT_SECONDS = 3600  # 1 hour


class RateLimiter:
    """Track and enforce leaderboard submission rate limits."""

    def __init__(self, state_path: Path | None = None):
        self.state_path = state_path or Path(__file__).parent / "results" / "rate_limit_state.json"
        self.last_submission: dict[str, float] = {}
        self._load()

    def _load(self) -> None:
        if self.state_path.exists():
            self.last_submission = json.loads(self.state_path.read_text())

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.last_submission, indent=2))

    def can_submit(self, kernel: str) -> bool:
        """Check if leaderboard submission is allowed for this kernel."""
        last = self.last_submission.get(kernel, 0.0)
        return (time.time() - last) >= RATE_LIMIT_SECONDS

    def seconds_until_allowed(self, kernel: str) -> float:
        """Seconds until next leaderboard submission is allowed."""
        last = self.last_submission.get(kernel, 0.0)
        remaining = RATE_LIMIT_SECONDS - (time.time() - last)
        return max(0.0, remaining)

    def record_submission(self, kernel: str) -> None:
        """Record a leaderboard submission timestamp."""
        self.last_submission[kernel] = time.time()
        self._save()

    def status(self) -> dict[str, str]:
        """Human-readable status for each kernel."""
        result = {}
        for kernel in ["moe", "gemm", "mla"]:
            if self.can_submit(kernel):
                result[kernel] = "READY"
            else:
                mins = self.seconds_until_allowed(kernel) / 60
                result[kernel] = f"WAIT {mins:.0f}m"
        return result
