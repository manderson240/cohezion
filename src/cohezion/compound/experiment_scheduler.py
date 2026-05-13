"""Smart experiment scheduler that auto-retires converged experiments
and proposes replacements using HIHO balance.

Designed to be called at the end of each iteration in overnight_evo_loop.py
to dynamically update the experiment schedule.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any


logger = logging.getLogger(__name__)


class ExperimentScheduler:
    """Dynamic scheduler that retires converged experiments and adds new ones.

    Integrates:
    - ExperimentAnalytics: detects retirement candidates
    - AutoresearchEngine: proposes replacements
    - SessionMetricsAggregator: tracks HIHO balance
    """

    def __init__(
        self,
        min_keeps: int = 10,
        cv_threshold: float = 0.05,
    ):
        self.min_keeps = min_keeps
        self.cv_threshold = cv_threshold
        self._retired: set[str] = set()

    def check_retirements(
        self,
        jsonl_path=None,
        n_records: int = 200,
    ) -> list[str]:
        """Check which experiments have converged and should be retired."""
        from cohezion.compound.experiment_analytics import (
            compute_experiment_stats,
            find_retirement_candidates,
            load_experiment_records,
        )
        records = load_experiment_records(n=n_records, jsonl_path=jsonl_path)
        stats = compute_experiment_stats(records)
        candidates = find_retirement_candidates(
            stats,
            min_keeps=self.min_keeps,
            cv_threshold=self.cv_threshold,
        )
        new_retirees = [c for c in candidates if c not in self._retired]
        self._retired.update(new_retirees)
        return new_retirees

    def propose_replacements(
        self,
        retired_labels: list[str],
        n: int | None = None,
    ) -> list[dict[str, Any]]:
        """Propose replacement experiments for retired ones."""
        if not retired_labels:
            return []
        from cohezion.compound.autoresearch import AutoresearchEngine
        from cohezion.compound.experiment_analytics import (
            compute_hiho_balance,
            load_experiment_records,
        )

        records = load_experiment_records(n=500)
        hiho = compute_hiho_balance(records)

        engine = AutoresearchEngine()
        n_proposals = n or len(retired_labels)
        return asyncio.run(engine.generate_next_experiments(
            n=n_proposals,
            session_metrics={"avg_coherence": hiho},
            retired_labels=retired_labels,
        ))

    def get_schedule_summary(self) -> dict[str, Any]:
        """Return current scheduler state."""
        return {
            "total_retired": len(self._retired),
            "retired_labels": list(self._retired),
            "min_keeps": self.min_keeps,
            "cv_threshold": self.cv_threshold,
        }
