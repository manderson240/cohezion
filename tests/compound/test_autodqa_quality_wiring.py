"""AQ1-AQ6: AutoDQA output-quality evaluation wired onto the production path.

The gap this closes
-------------------
``quality_eval.evaluate`` — the type-aware output evaluator (AST-parses code,
checks uncertainty markers, length-gates per output_type) plus its
mutation-verified AG1-AG4 semantic-agreement gate — had ZERO production
consumers. Its only caller is ``AutoDQA``, and ``make_executor`` never built
one, so the whole evaluator was inert. ``dormancy_scan.py`` carried it as a
known-dormant NOTICE since 2026-08-14:

    "quality_eval.evaluate — sole consumer is AutoDQA, which is itself absent
     from make_executor, so it is dormant ON THE PRODUCTION PATH."

A knock-on effect: ``AutoDQA`` persists to the ``autodqa_results`` table, which
``model/training_data.py`` already reads (filtered ``score >= 0.45``) as a
training corpus. With no producer, that source was permanently empty.

The scale finding (why the obvious wiring is WRONG)
---------------------------------------------------
``SkillRefiner._extract_metrics`` derives ``quality_score`` by aliasing
``anomaly_score``, a telemetry-derived health signal. It is tempting to replace
that with the new measurement. Do not: the two are different quantities.
``quality_eval`` is an ESCALATION gate ("substantial enough not to escalate to a
bigger model?"), not a correctness measure — a correct ``"Yes."`` scores 0.00 and
is 'rejected' purely for being under 10 chars. Feeding that to
``DifficultyEstimator`` (``_QUALITY_FLOOR = 0.6``) would punish terse-but-correct
answers and escalate to costlier tiers. So the executor publishes it under
``output_quality_*``, and ``TestAQ6ScaleMismatch`` guards the alias against being
added later on intuition.

Per ``verification-depth.md`` every invariant below is a CONSUMPTION invariant
paired with a test that FAILS when the mechanism is neutralised — not a
``hasattr`` existence check. Mutation-verified 2026-08-30: 6/6 mutants killed,
including the plausible wrong fix (reject verdict wired into ``success``).

AQ1 (CONSUMPTION) — execute_task publishes metrics["output_quality_score"] FROM
                    THE OUTPUT TEXT. Discriminating: identical telemetry,
                    different output content => different score.
AQ2 (fail-open)   — a raising evaluator leaves the result IDENTICAL to the
                    no-evaluator control (not merely "not crashed").
AQ3 (not a gate)  — a REJECT verdict must NOT flip success to False. This is
                    telemetry; the guardrail pipeline is the gate.
AQ4 (deference)   — an execute_fn that measured its own lane keeps its value.
AQ5 (injection)   — make_executor auto-injects the evaluator (W1 precedent).
AQ6 (scale guard) — the escalation score must NOT be aliased into quality_score.
"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.executor import CompoundExecutor


# task_description "t" classifies as output_type="short_answer", whose scorer is
# ``min(1.0, len(text) / 50)`` — a continuous function of CONTENT LENGTH ONLY.
# Both outputs below are ACCEPTED, so the pair discriminates a real measurement
# from a pass/fail proxy: an impl that aliases anomaly_score returns the same
# number for both.
_TASK = "t"
_HIGH_QUALITY = "x" * 60  # -> score 1.00
_LOW_QUALITY = "x" * 15  # -> score 0.30
_REJECTED = "ok"  # -> accept=False, score 0.00 (too short)


def _run(executor: CompoundExecutor, output: str, extra_metrics: dict | None = None):
    """Drive execute_task with a stubbed logger and a fixed output."""
    with (
        patch.object(executor.logger, "get_experience_guidance", return_value={"context": "t"}),
        patch.object(executor.logger, "log_execution_start", return_value="exp_path"),
        patch.object(executor.logger, "log_execution_result"),
        patch.object(executor.logger, "extract_execution_pattern", return_value="pattern_path"),
    ):
        return executor.execute_task(
            task_description=_TASK,
            skill_name="s",
            operation_type="generate",
            execute_fn=lambda _g: (output, dict(extra_metrics or {})),
        )


@pytest.fixture
def make_exec():
    """Build a CompoundExecutor with vault logging patched out."""

    def _factory(**kwargs):
        with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
            return CompoundExecutor(MagicMock(), **kwargs)

    return _factory


@pytest.fixture
def evaluator():
    """A real AutoDQA with side effects (SurrealDB, Telegram) disabled."""
    from cohezion.compound.autodqa import AutoDQA

    return AutoDQA(persist=False, notify_on_reject=False)


# ---------------------------------------------------------------------------
# T1: structural — necessary, never sufficient
# ---------------------------------------------------------------------------


class TestAQStructural:
    def test_executor_accepts_quality_evaluator_kwarg(self):
        sig = inspect.signature(CompoundExecutor.__init__)
        assert "quality_evaluator" in sig.parameters, (
            "CompoundExecutor.__init__ must accept quality_evaluator="
        )

    def test_executor_stores_quality_evaluator(self):
        assert "_quality_evaluator" in inspect.getsource(CompoundExecutor.__init__)


# ---------------------------------------------------------------------------
# T2: AQ1 — the CONSUMPTION invariant
# ---------------------------------------------------------------------------


class TestAQ1Consumption:
    def test_DISCRIMINATING_output_content_changes_quality_score(self, make_exec, evaluator):
        """Identical telemetry, different output text => different quality_score.

        This is THE discriminating test. Both runs pass an empty metrics dict, so
        every telemetry-derived signal (duration, tokens, anomaly) is equivalent;
        the ONLY difference is the output string. An implementation that keeps
        aliasing anomaly_score, or that never wires the evaluator, produces equal
        values (or no key at all) and fails here.
        """
        high = _run(make_exec(quality_evaluator=evaluator), _HIGH_QUALITY)
        low = _run(make_exec(quality_evaluator=evaluator), _LOW_QUALITY)

        assert "output_quality_score" in high.metrics, "execute_task must publish quality_score"
        assert "output_quality_score" in low.metrics

        assert high.metrics["output_quality_score"] > low.metrics["output_quality_score"], (
            "quality_score must track OUTPUT CONTENT: "
            f"len-60 scored {high.metrics['output_quality_score']} but "
            f"len-15 scored {low.metrics['output_quality_score']}"
        )

    def test_quality_score_matches_the_evaluator_verdict(self, make_exec, evaluator):
        """The published score is the evaluator's, not an arbitrary constant."""
        from cohezion.inference.quality_eval import evaluate
        from cohezion.inference.task_classifier import classify

        expected = evaluate(_HIGH_QUALITY, classify(_TASK).output_type, _TASK).score
        result = _run(make_exec(quality_evaluator=evaluator), _HIGH_QUALITY)
        assert result.metrics["output_quality_score"] == pytest.approx(expected)

    def test_quality_band_and_reason_are_published(self, make_exec, evaluator):
        """Band + reason accompany the score so a low score is diagnosable."""
        result = _run(make_exec(quality_evaluator=evaluator), _LOW_QUALITY)
        assert result.metrics["output_quality_band"] in {
            "BELOW_HIHO",
            "HIHO_EQUILIBRIUM",
            "ABOVE_HIHO",
        }
        assert isinstance(result.metrics.get("output_quality_reason"), str)


# ---------------------------------------------------------------------------
# T2: AQ2 — fail-open must be IDENTITY, not merely "survived"
# ---------------------------------------------------------------------------


class TestAQ2FailOpen:
    def test_raising_evaluator_leaves_result_identical_to_control(self, make_exec):
        """A broken evaluator must change NOTHING — same success, same output.

        Asserting only "did not raise" would pass for an impl that silently
        corrupted the output or zeroed the score. The control comparison is what
        makes this discriminating.
        """

        class _Broken:
            def evaluate(self, output, task_description, peer_outputs=None):
                raise RuntimeError("simulated evaluator failure")

        control = _run(make_exec(), _HIGH_QUALITY)
        broken = _run(make_exec(quality_evaluator=_Broken()), _HIGH_QUALITY)

        assert broken.success == control.success
        assert broken.output == control.output
        assert "output_quality_score" not in broken.metrics, (
            "a failed evaluation must publish NO score rather than a fabricated one"
        )

    def test_no_evaluator_publishes_no_quality_score(self, make_exec):
        """Absent evaluator => absent key. Never a placeholder."""
        result = _run(make_exec(), _HIGH_QUALITY)
        assert "output_quality_score" not in result.metrics


# ---------------------------------------------------------------------------
# T2: AQ3 — a learning signal, not a gate
# ---------------------------------------------------------------------------


class TestAQ3NeverGates:
    def test_DISCRIMINATING_rejected_verdict_does_not_fail_the_task(self, make_exec, evaluator):
        """A REJECT verdict records a low score but must NOT flip success.

        Blast radius matters here: success=False suppresses pattern extraction,
        skill refinement and cache writes. The guardrail pipeline is the gate;
        AutoDQA is telemetry. An impl that wires the verdict into `success`
        fails this test.
        """
        result = _run(make_exec(quality_evaluator=evaluator), _REJECTED)

        assert result.metrics["output_quality_score"] == pytest.approx(0.0)
        assert result.success is True, (
            "a low quality score must not fail the task — it is a learning signal"
        )
        assert result.output == _REJECTED, "output must not be rewritten by the evaluator"


# ---------------------------------------------------------------------------
# T2: AQ4 — defer to a lane that measured its own quality
# ---------------------------------------------------------------------------


class TestAQ4Deference:
    def test_execute_fn_supplied_quality_score_is_not_clobbered(self, make_exec, evaluator):
        """An execute_fn that reports its own quality_score keeps it.

        Non-destructive wiring: adding this evaluator must not regress a caller
        that already produced a lane-specific signal.
        """
        result = _run(
            make_exec(quality_evaluator=evaluator),
            _HIGH_QUALITY,
            extra_metrics={"output_quality_score": 0.42},
        )
        assert result.metrics["output_quality_score"] == pytest.approx(0.42)


# ---------------------------------------------------------------------------
# T3: AQ5 — factory injection (W1 precedent)
# ---------------------------------------------------------------------------


class TestAQ5FactoryInjection:
    def test_make_executor_auto_injects_a_quality_evaluator(self):
        from cohezion.compound import make_executor

        executor = make_executor(MagicMock())
        assert getattr(executor, "_quality_evaluator", None) is not None, (
            "make_executor must auto-inject a quality evaluator (AQ5)"
        )

    def test_explicit_evaluator_takes_priority_over_auto_injection(self, evaluator):
        from cohezion.compound import make_executor

        executor = make_executor(MagicMock(), quality_evaluator=evaluator)
        assert executor._quality_evaluator is evaluator


# ---------------------------------------------------------------------------
# T4: AQ6 — the downstream consumer prefers the MEASURED value
# ---------------------------------------------------------------------------


class TestAQ7PersistIsActuallyAwaited:
    """AutoDQA._persist_result must AWAIT the async SurrealDB write.

    Found by an un-mocked end-to-end smoke run, not by any mocked test: the code
    called `client.create(...)` — an `async def` — without awaiting, which builds
    a coroutine and discards it. No row is written and NOTHING RAISES, so the
    method's own try/except never fires and it "looks wired while being dead".
    `surreal_client.run_sync`'s docstring names this exact call site as a known
    offender that had never written a row; it stayed unfixed because AutoDQA was
    dormant. Wiring AutoDQA into the executor makes it a live bug.

    Asserting "no exception" is what let this hide for months, so these tests
    assert the await itself.

    A NOTE ON THE DOUBLE, because the obvious one is useless here: patching
    ``SurrealClient`` with ``MagicMock`` makes ``create`` a plain Mock, so calling
    it produces NO coroutine and the un-awaited bug becomes invisible — the first
    version of this test passed against the genuinely broken code. The stub below
    keeps ``create`` a real ``async def``, so "was the body reached?" is the
    discriminating question: an un-awaited coroutine never runs its body.
    """

    @staticmethod
    def _async_stub():
        """A SurrealClient double whose create() is genuinely async."""
        calls: list[tuple[str, dict]] = []

        class _Client:
            async def create(self, table, data):
                calls.append((table, data))
                return {"ok": True}

        return _Client, calls

    def _run_persist(self, persist: bool):
        from cohezion.compound.autodqa import AutoDQA

        cls, calls = self._async_stub()
        with patch("cohezion.core.persistence.surreal_client.SurrealClient", cls):
            AutoDQA(persist=persist, notify_on_reject=False).evaluate(_HIGH_QUALITY, _TASK)
        return calls

    def test_DISCRIMINATING_the_write_coroutine_body_actually_runs(self):
        """The row write must EXECUTE, not just be constructed and dropped.

        Pre-fix (`client.create(...)` with no await) builds a coroutine and
        discards it: the body never runs, `calls` stays empty, nothing raises.
        Verified 2026-08-30 against the real pre-fix file — this assertion fails
        there and passes after the run_sync fix.
        """
        calls = self._run_persist(persist=True)
        assert calls, (
            "autodqa_results write never executed — the coroutine was discarded "
            "un-awaited (the 'looks wired while being dead' failure mode)"
        )
        table, data = calls[0]
        assert table == "autodqa_results"
        assert data["quality_band"] in {"BELOW_HIHO", "HIHO_EQUILIBRIUM", "ABOVE_HIHO"}

    def test_no_never_awaited_runtime_warning(self, recwarn):
        """Corroborating signal: the warning the bug emitted in the wild."""
        import gc

        self._run_persist(persist=True)
        gc.collect()  # un-awaited coroutines warn when finalized
        never_awaited = [w for w in recwarn if "never awaited" in str(w.message)]
        assert not never_awaited, [str(w.message) for w in never_awaited]

    def test_persist_false_writes_nothing(self):
        """Control: the opt-out is respected. Passes either way by design."""
        assert self._run_persist(persist=False) == []


class TestAQ6ScaleMismatch:
    """The escalation-gate score must NOT be aliased into SkillRefiner.quality_score.

    Aliasing it is the obvious-looking next move once Step 3.9 exists, and it is
    wrong. This class exists so the next person hits the evidence instead of the
    intuition. Written as an executable guard, not a comment, because a comment
    does not fail CI.
    """

    def _extract(self, metrics: dict):
        from cohezion.compound.skill_refiner import SkillRefiner

        return SkillRefiner()._extract_metrics(
            {"success": True, "metrics": metrics, "duration_seconds": 1.0, "token_metrics": {}}
        )

    def test_EVIDENCE_correct_terse_answers_score_zero_on_the_escalation_gate(self):
        """quality_eval measures ESCALATION-WORTHINESS, not correctness.

        These are correct answers. They score 0.0 and are 'rejected' purely for
        being under the 10-char short_answer floor — the gate is asking "is this
        substantial enough that I shouldn't escalate to a bigger model?", which
        is a different question from "is this right?".

        This is the measurement that decides the wiring, so it is pinned here. If
        quality_eval's calibration ever changes such that terse-correct answers
        score above the GIC floor, this test fails and the aliasing decision
        should be revisited deliberately.
        """
        from cohezion.compound.difficulty_estimator import _QUALITY_FLOOR
        from cohezion.inference.quality_eval import evaluate
        from cohezion.inference.task_classifier import classify

        for correct_answer in ("Yes.", "yes", "42"):
            verdict = evaluate(correct_answer, classify(_TASK).output_type, _TASK)
            assert verdict.score < _QUALITY_FLOOR, (
                f"{correct_answer!r} scored {verdict.score} — at or above the GIC "
                f"floor {_QUALITY_FLOOR}. The scale mismatch this guard documents "
                "may no longer hold; re-derive the wiring decision."
            )

    def test_skill_refiner_does_NOT_alias_the_output_quality_score(self):
        """A published output_quality_score must not leak into quality_score.

        Discriminating: an impl that adds
        `metrics_dict.get("output_quality_score", anomaly_score)` returns 0.2
        here and fails. That is exactly the change this guard forbids.
        """
        extracted = self._extract({"anomaly_score": 0.9, "output_quality_score": 0.2})
        assert extracted.quality_score == pytest.approx(0.9), (
            "quality_score must remain the anomaly-derived health signal until a "
            "calibration experiment justifies otherwise (see class docstring)"
        )

    def test_anomaly_alias_behaviour_is_unchanged(self):
        """The historical path is untouched — this change is purely additive."""
        assert self._extract({"anomaly_score": 0.9}).quality_score == pytest.approx(0.9)

    def test_default_when_absent(self):
        """Absent => the pre-existing 0.5 default, unchanged."""
        assert self._extract({}).quality_score == pytest.approx(0.5)
