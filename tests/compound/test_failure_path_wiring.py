"""Discriminating test: the FAPO failure-attribution keystone must be reachable
from CompoundExecutor.execute_task() on a REAL production failure, not only
from a hand-built call to SkillRefiner.refine().

Claim under test: on ``not success``, ``execute_task()`` must
  (a) invoke ``FailureAttributor.classify()``,
  (b) call ``skill_refiner.refine(..., failure_attribution=<non-None>)``, and
  (c) the failure-conditioned memory (``FailureConditionedMemory``) participates
      end-to-end — a pre-seeded analogous fix is retrieved and cited in the PRIME
      skill file — when driven purely through ``execute_task()``.

The wrong (CURRENT, pre-fix) implementation gates BOTH ``refine()`` call sites on
``if success and self.skill_refiner and should_refine:`` — so on a failure,
``FailureAttributor`` is never instantiated and ``refine()`` never sees
``failure_attribution``. Every test below MUST fail against that implementation
(classify not called / refine not called with a non-None failure_attribution /
prime_file left untouched) and MUST pass once the failure branch is wired.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.failure_attributor import FailureAttribution, FailureAttributor
from cohezion.compound.failure_memory import FailureConditionedMemory
from cohezion.compound.skill_refiner import SkillRefiner


class _FakeEmbed:
    """Deterministic embed: analogous 'malformed json'/'unparseable' failures cluster."""

    def __call__(self, text: str) -> np.ndarray:
        key = text.lower()
        if "malformed json" in key or "unparseable" in key:
            return np.array([1.0, 0.0, 0.0], dtype=np.float32)
        return np.array([0.0, 1.0, 0.0], dtype=np.float32)


def _make_executor(skill_refiner) -> CompoundExecutor:
    """Minimal executor: guardrails/alignment off so the failure reaches Step 7 directly."""
    executor = CompoundExecutor(
        mcp_client=MagicMock(),
        skill_refiner=skill_refiner,
        enable_guardrails=False,
        enable_alignment_analysis=False,
    )
    executor.logger = MagicMock()
    executor.logger.get_experience_guidance.return_value = {}
    return executor


def _failing_execute_fn(guidance):  # matches _call_execute_fn's 1-arg contract
    raise RuntimeError("tool X returned malformed JSON while parsing the response body")


class TestFailurePathWiringExecutor:
    """(a) classify() invoked, (b) refine(failure_attribution=...) called — from execute_task()."""

    def test_failure_invokes_attribution_and_refine_with_attribution(self):
        mock_refiner = MagicMock()
        executor = _make_executor(mock_refiner)

        stub_attribution = FailureAttribution(
            category="reasoning", escalation_level="L1", evidence="stub evidence"
        )
        with patch.object(
            FailureAttributor, "classify", return_value=stub_attribution
        ) as mock_classify:
            result = executor.execute_task(
                task_description="Test failing task",
                skill_name="test-skill",
                operation_type="generate",
                execute_fn=_failing_execute_fn,
            )

        assert result.success is False

        # (a) FailureAttributor.classify was invoked on THIS production failure —
        # with the real output/metrics/decision_paths the pipeline computed.
        mock_classify.assert_called_once()
        _, call_kwargs = mock_classify.call_args
        assert "malformed JSON" in call_kwargs["output"]
        assert isinstance(call_kwargs["metrics"], dict)
        assert isinstance(call_kwargs["decision_paths"], list)

        # (b) refine() was called WITH the non-None attribution and success=False in the
        # execution_result — the current `if success:`-gated call never fires for a failure.
        mock_refiner.refine.assert_called_once()
        _, refine_kwargs = mock_refiner.refine.call_args
        assert refine_kwargs.get("failure_attribution") is stub_attribution
        assert refine_kwargs.get("execution_result", {}).get("success") is False

    def test_success_path_unchanged_no_failure_attribution(self):
        """Non-regression: a SUCCESSFUL execution must NOT go through the failure branch."""
        mock_refiner = MagicMock()
        executor = _make_executor(mock_refiner)

        with patch.object(FailureAttributor, "classify") as mock_classify:
            result = executor.execute_task(
                task_description="Test succeeding task",
                skill_name="test-skill",
                operation_type="generate",
                execute_fn=lambda guidance: ("ok output", {"tokens": 10}),
            )

        assert result.success is True
        mock_classify.assert_not_called()
        mock_refiner.refine.assert_called_once()
        _, refine_kwargs = mock_refiner.refine.call_args
        assert refine_kwargs.get("failure_attribution") is None


class TestFailureMemoryEndToEndThroughExecutor:
    """(c) FailureConditionedMemory participates when driven through execute_task()."""

    def test_analogous_failure_via_execute_task_retrieves_preseeded_fix(
        self, tmp_path, monkeypatch
    ):
        memory = FailureConditionedMemory(embed_fn=_FakeEmbed(), similarity_threshold=0.5)
        memory.record(
            failure_text="tool X returned malformed JSON",
            fix_text="add schema validation before parse",
            skill_name="other-skill",
            category="format",
        )
        refiner = SkillRefiner(failure_memory=memory)
        prime_file = tmp_path / "TEST_SKILL_PRIME.md"
        prime_file.write_text("# Test Skill\n\n## Version: 1.0.0\n\n## Keywords: test\n")
        monkeypatch.setattr(refiner, "_find_prime_file", lambda _skill: prime_file)

        executor = _make_executor(refiner)
        stub_attribution = FailureAttribution(
            category="format",
            escalation_level="L1",
            evidence="tool Y emitted unparseable output",
        )
        with patch.object(FailureAttributor, "classify", return_value=stub_attribution):
            result = executor.execute_task(
                task_description="failing task",
                skill_name="test-skill",
                operation_type="analyze",
                execute_fn=_failing_execute_fn,
            )

        assert result.success is False
        content = prime_file.read_text()
        # The PRE-SEEDED analogous fix was retrieved and cited verbatim — proving
        # failure_memory is reachable end-to-end from execute_task(), not merely from
        # a hand-built refiner.refine(failure_attribution=...) call in isolation.
        assert "add schema validation before parse" in content
        assert "Add structured-output format examples" not in content
        # And the NEW failure was itself recorded for the next analogous failure.
        assert len(refiner._failure_memory._records) == 2

    def test_unmocked_real_classifier_records_a_live_failure(self, tmp_path, monkeypatch):
        """Un-mocked boundary smoke (verification-depth.md corrective #3): the REAL
        ``FailureAttributor`` — no patching at all — classifies a real ``execute_task``
        failure and the real ``SkillRefiner`` records it into failure_memory. Proves the
        wiring holds with the actual deterministic classifier, not just a stubbed one.
        """
        memory = FailureConditionedMemory(embed_fn=_FakeEmbed(), similarity_threshold=0.5)
        refiner = SkillRefiner(failure_memory=memory)
        prime_file = tmp_path / "TEST_SKILL_PRIME.md"
        prime_file.write_text("# Test Skill\n\n## Version: 1.0.0\n\n## Keywords: test\n")
        monkeypatch.setattr(refiner, "_find_prime_file", lambda _skill: prime_file)

        executor = _make_executor(refiner)
        result = executor.execute_task(
            task_description="failing task, no mocks on the attribution boundary",
            skill_name="test-skill",
            operation_type="analyze",
            execute_fn=_failing_execute_fn,
        )

        assert result.success is False
        # The real (deterministic, no-LLM) FailureAttributor classified this failure into
        # one of its four categories, and refine() acted on it — either an L1 PRIME edit
        # (prime_file changed + a memory record) or an L2/L3 proof_obligation (no PRIME
        # edit, by design — see FailureAttributor's escalation map). Either outcome proves
        # the boundary is reachable; a dormant implementation produces NEITHER.
        content = prime_file.read_text()
        prime_edited = content != "# Test Skill\n\n## Version: 1.0.0\n\n## Keywords: test\n"
        memory_recorded = len(refiner._failure_memory._records) > 0
        assert prime_edited or memory_recorded, (
            "neither the PRIME file nor failure_memory changed — the real "
            "FailureAttributor -> refine() boundary is still dormant"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
