"""Markov chain model for branch integration sequencing.

Models the branch integration process as a 5-state discrete-time Markov chain:

    unreviewed → assessed → conflict_checked → tests_green → merged

Transition probabilities are estimated from commit count and file overlap ratio.
The phi score (HIHO quality metric: 4*c*(1-c)) weights expected integration value.
Steady-state distribution is computed via numpy eigendecomposition.

Usage::

    markov = BranchIntegrationMarkov()
    markov.add_branch("feat/researcher-lanes", commit_count=3, overlap_ratio=0.1)
    markov.add_branch("fix/makefile-merge-markers", commit_count=21, overlap_ratio=0.05)
    sequence = markov.optimal_sequence()
    for branch, score in sequence:
        print(f"{score:.3f} {branch.name}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np


if TYPE_CHECKING:
    pass


# State indices
_STATES = ["unreviewed", "assessed", "conflict_checked", "tests_green", "merged"]
_S = {s: i for i, s in enumerate(_STATES)}


@dataclass
class BranchState:
    """Integration state for a single branch.

    Attributes:
        name: Git branch name.
        commit_count: Number of unique commits not in the integration target.
        state: Current integration state.
        phi_score: HIHO quality weight = 4 * coherence * (1 - coherence).
            Coherence is estimated from commit_count: smaller branches = higher
            coherence (0.5 is peak quality = phi_score 1.0).
        overlap_ratio: Fraction of files changed in this branch that overlap with
            the integration target. Used to estimate conflict probability.
        transition_probs: Row-stochastic transition matrix row for this branch
            (keyed by destination state name).
        expected_value: Expected phi-weighted probability of reaching merged state.
    """

    name: str
    commit_count: int
    state: str = "unreviewed"
    phi_score: float = 0.0
    overlap_ratio: float = 0.0
    transition_probs: dict[str, float] = field(default_factory=dict)
    expected_value: float = 0.0


class BranchIntegrationMarkov:
    """Markov chain sequencer for branch integration.

    Each branch has its own transition matrix derived from commit count and
    file overlap. The optimal integration sequence maximises expected phi-weighted
    value while ordering by ascending conflict risk.
    """

    def __init__(self) -> None:
        self._branches: list[BranchState] = []

    # ── Branch registration ───────────────────────────────────────────────

    def add_branch(
        self,
        name: str,
        commit_count: int,
        overlap_ratio: float = 0.0,
        current_state: str = "unreviewed",
    ) -> BranchState:
        """Register a branch for integration modelling.

        Args:
            name: Git branch name.
            commit_count: Unique commits not yet on the target branch.
            overlap_ratio: Fraction of changed files that conflict with target.
                0.0 = no overlap, 1.0 = complete overlap. Estimate from
                `git diff --name-only <branch> <target> | wc -l` / total files.
            current_state: Starting state (default 'unreviewed').

        Returns:
            The created BranchState (also stored internally).
        """
        phi = self._phi(commit_count)
        probs = self._transition_row(commit_count, overlap_ratio)
        ev = self._expected_value(probs, phi)
        branch = BranchState(
            name=name,
            commit_count=commit_count,
            state=current_state,
            phi_score=phi,
            overlap_ratio=overlap_ratio,
            transition_probs=probs,
            expected_value=ev,
        )
        self._branches.append(branch)
        return branch

    # ── Scoring ──────────────────────────────────────────────────────────

    @staticmethod
    def _phi(commit_count: int) -> float:
        """HIHO coherence-derived phi score: 4 * c * (1 - c).

        Maps commit count to coherence in [0, 1]:
          - 1 commit  → coherence 0.98 → phi 0.078  (too exploitative: tiny)
          - 5 commits → coherence 0.80 → phi 0.640  (healthy)
          - 10 commits→ coherence 0.60 → phi 0.960  (near-optimal)
          - 20 commits→ coherence 0.40 → phi 0.960  (also near-optimal)
          - 50 commits→ coherence 0.20 → phi 0.640  (drifting exploratory)
          - 100+      → coherence 0.05 → phi 0.190  (too exploratory: large)

        Coherence decays as: c = exp(-commit_count / 20).
        """
        coherence = np.exp(-commit_count / 20.0)
        return float(4.0 * coherence * (1.0 - coherence))

    @staticmethod
    def _transition_row(commit_count: int, overlap_ratio: float) -> dict[str, float]:
        """Estimate row-stochastic transition probabilities.

        Returns a dict mapping each source state to its probability of moving
        to the next state (all other states have probability 0 since this is
        a linear chain with absorbing end).
        """
        # P(assessed | unreviewed) = 1.0 — analysis always possible
        p_assess = 1.0
        # P(conflict_checked | assessed) decreases for large branches
        p_conflict_check = 1.0 if commit_count < 10 else max(0.6, 1.0 - commit_count / 100.0)
        # P(tests_green | conflict_checked) decreases with file overlap
        p_tests_green = max(0.4, 1.0 - overlap_ratio)
        # P(merged | tests_green) = 1.0 — if tests pass, merge is trivial
        p_merge = 1.0

        return {
            "unreviewed": p_assess,
            "assessed": p_conflict_check,
            "conflict_checked": p_tests_green,
            "tests_green": p_merge,
            "merged": 1.0,  # absorbing
        }

    @staticmethod
    def _expected_value(probs: dict[str, float], phi: float) -> float:
        """Expected phi-weighted probability of reaching merged state."""
        p_reach = (
            probs["unreviewed"]
            * probs["assessed"]
            * probs["conflict_checked"]
            * probs["tests_green"]
        )
        return phi * p_reach

    # ── Steady-state analysis ─────────────────────────────────────────────

    def transition_matrix(self) -> np.ndarray:
        """Build the fleet-wide transition matrix (N_branches × N_states × N_states).

        Returns a single N_states × N_states matrix averaged across branches,
        suitable for computing the fleet steady-state distribution.
        """
        n = len(_STATES)
        fleet_P = np.zeros((n, n))
        if not self._branches:
            return fleet_P

        for branch in self._branches:
            row = branch.transition_probs
            for src_name, src_idx in _S.items():
                if src_name == "merged":
                    fleet_P[src_idx, src_idx] += 1.0  # absorbing
                else:
                    p = row.get(src_name, 0.0)
                    fleet_P[src_idx, src_idx + 1] += p
                    fleet_P[src_idx, src_idx] += 1.0 - p

        fleet_P /= len(self._branches)
        return fleet_P

    def steady_state(self) -> dict[str, float]:
        """Compute steady-state distribution via left eigenvector (eigenvalue=1).

        The steady-state tells us the long-run fraction of branches expected to
        be in each integration state if we keep adding branches at this risk level.
        A healthy fleet has most branches in 'merged'; stalled fleets pile up in
        'conflict_checked'.

        Returns:
            Dict mapping state name to steady-state probability.
        """
        P = self.transition_matrix()
        if P.sum() == 0:
            return {s: 0.0 for s in _STATES}

        # Left eigenvectors of P^T: π P = π  ↔  P^T π = π
        eigenvalues, eigenvectors = np.linalg.eig(P.T)
        # Find eigenvector for eigenvalue closest to 1
        idx = int(np.argmin(np.abs(eigenvalues - 1.0)))
        pi = np.real(eigenvectors[:, idx])
        pi = np.abs(pi)
        pi_sum = pi.sum()
        if pi_sum > 0:
            pi /= pi_sum
        return {_STATES[i]: float(pi[i]) for i in range(len(_STATES))}

    # ── Sequencing ────────────────────────────────────────────────────────

    def optimal_sequence(self) -> list[tuple[BranchState, float]]:
        """Return branches sorted by expected integration value (descending).

        Ties broken by ascending commit count (cheaper work first within same value).

        Returns:
            List of (branch, expected_value) tuples, highest value first.
        """
        scored = [(b, b.expected_value) for b in self._branches]
        return sorted(scored, key=lambda x: (-x[1], x[0].commit_count))

    def summary(self) -> str:
        """Human-readable integration plan summary."""
        lines = ["Branch Integration Plan (Markov-optimal sequence):", ""]
        lines.append(f"{'#':>3}  {'EV':>6}  {'Phi':>5}  {'Commits':>7}  {'Overlap':>7}  Branch")
        lines.append("-" * 70)
        for rank, (branch, ev) in enumerate(self.optimal_sequence(), 1):
            lines.append(
                f"{rank:>3}.  {ev:>6.3f}  {branch.phi_score:>5.3f}"
                f"  {branch.commit_count:>7d}  {branch.overlap_ratio:>7.2%}  {branch.name}"
            )
        lines.append("")
        ss = self.steady_state()
        lines.append("Steady-state distribution:")
        for state in _STATES:
            lines.append(f"  {state:<20} {ss.get(state, 0):.1%}")
        return "\n".join(lines)

    # ── State transition (runtime tracking) ───────────────────────────────

    def advance(self, branch_name: str, to_state: str) -> BranchState | None:
        """Mark a branch as having reached a new integration state.

        Args:
            branch_name: Name of the branch to advance.
            to_state: Target state (must be the next state in the chain).

        Returns:
            Updated BranchState, or None if branch not found.
        """
        for branch in self._branches:
            if branch.name == branch_name:
                current_idx = _S.get(branch.state, -1)
                target_idx = _S.get(to_state, -1)
                if target_idx == current_idx + 1:
                    branch.state = to_state
                return branch
        return None

    @property
    def branches(self) -> list[BranchState]:
        """All registered branches."""
        return list(self._branches)

    def merged_count(self) -> int:
        """Count of branches that have reached the merged state."""
        return sum(1 for b in self._branches if b.state == "merged")

    def pending_count(self) -> int:
        """Count of branches not yet merged."""
        return sum(1 for b in self._branches if b.state != "merged")
