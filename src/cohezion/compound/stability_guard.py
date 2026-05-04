"""HIHO Stability Guard for the EcoResilience loop.
Ensures that synthesized strategies adhere to 12D manifold stability thresholds.
If coherence < 0.5, it triggers a refinement loop via the Compound Executor.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from cohezion.flume.manifolds.translator import ManifoldProjection


logger = logging.getLogger(__name__)


class StabilityCheckResult(BaseModel):
    """Result of a HIHO stability verification."""

    is_stable: bool
    coherence: float
    suggestion: str | None = None


class _AwaitableStabilityCheckResult:
    """Wrapper that exposes a :class:`StabilityCheckResult` synchronously
    while also being awaitable.

    Allows :meth:`HIHOStabilityGuard.verify` to support both
    ``result = guard.verify(...)`` and ``result = await guard.verify(...)``
    call styles. Synchronous attribute access proxies to the underlying
    result; ``await`` returns the same underlying result.
    """

    __slots__ = ("_result",)

    def __init__(self, result: StabilityCheckResult):
        self._result = result

    def __await__(self):
        if False:
            yield  # pragma: no cover - turns this into a generator
        return self._result

    def __getattr__(self, name: str):
        return getattr(self._result, name)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"_AwaitableStabilityCheckResult({self._result!r})"


class HIHOStabilityGuard:
    """
    Guardrail that validates the output of the EcoResilience synthesis.
    Criterium: Coherence must be >= 0.5.
    """

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

    def verify(
        self, projection: ManifoldProjection, response: str
    ) -> _AwaitableStabilityCheckResult:
        """
        Verify the coherence of the projection and the logical consistency
        of the response relative to that coherence.

        Returns a dual-mode result that callers can use either synchronously
        (attribute access works directly) or via ``await``. Existing
        ``await guard.verify(...)`` callers continue to work.
        """
        # 1. Primary check: The projection's own coherence
        if projection.coherence < self.threshold:
            result = StabilityCheckResult(
                is_stable=False,
                coherence=projection.coherence,
                suggestion="The 12D manifold project is unstable. Re-evaluate the TEK inputs and manifold coordinates.",
            )
        else:
            # 2. Secondary check: Does the response acknowledge the
            # stability? (In a real scenario, we would use a small model to
            # check for contradictions.) For now, we rely on the projection's
            # mathematical coherence.
            result = StabilityCheckResult(
                is_stable=True, coherence=projection.coherence, suggestion=None
            )

        return _AwaitableStabilityCheckResult(result)

    def should_refine(self, result: StabilityCheckResult) -> bool:
        """Returns True if the result fails the stability threshold."""
        return not result.is_stable
