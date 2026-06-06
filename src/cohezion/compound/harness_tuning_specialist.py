"""Harness-Tuning Specialist — the self-improvement-from-experiments role (item 35, thread E).

Composes the autonomous RHO chain into ONE report-only call:
  routing corpus → `generate_harness_candidates` (item 33, from item-9 `propose_tuning`)
                 → `SkillRefiner.propose_rho_update` (item 27 → item-22 RHO self-preference)
                 → the winning harness-update proposal.

It PROPOSES a harness update; it never writes a skill file (propose_rho_update is report-only).
A fallback-heavy corpus yields ONE RHO-selected proposal targeting the worst-fallback class; a
healthy or empty corpus yields None (UNPROVEN — never a fabricated proposal). The SkillRefiner is
injectable so the RHO gate (rho_enabled) and the decision are deterministic and testable.
"""

from __future__ import annotations

from typing import Any

from cohezion.compound.skill_refiner import SkillRefiner
from cohezion.models.rho_selector import generate_harness_candidates


class HarnessTuningSpecialist:
    """Corpus → candidates → RHO self-preference → the winning harness-update proposal (report-only)."""

    def __init__(self, *, refiner: SkillRefiner | None = None) -> None:
        # The specialist's whole job is to RUN RHO, so the default refiner has the gate ON. An
        # injected refiner (e.g. rho_enabled=False) lets a test prove the RHO path is really used.
        self._refiner = refiner if refiner is not None else SkillRefiner(rho_enabled=True)

    def propose_harness_tuning(
        self,
        records: list[dict[str, Any]],
        *,
        min_samples: int = 5,
        fallback_threshold: float = 0.5,
    ) -> Any | None:
        """Return the RHO-selected harness update for the corpus, or None (UNPROVEN). Report-only.

        Derives candidates autonomously from the corpus (item 33), then runs them through the
        SkillRefiner's RHO self-preference path (item 27 → item 22). No chronically-fallback class
        (healthy/empty corpus) → no candidates → None. A winner emerges only when the RHO
        tournament endorses one; otherwise None. Never writes a skill.
        """
        candidates = generate_harness_candidates(
            records, min_samples=min_samples, fallback_threshold=fallback_threshold
        )
        if not candidates:
            return None  # healthy/empty corpus → UNPROVEN
        return self._refiner.propose_rho_update(
            records,
            candidates,
            min_samples=min_samples,
            fallback_threshold=fallback_threshold,
        )
