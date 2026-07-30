"""The REFLECT step must actually be present in a live executor (2026-07-29).

THE LOOP IS: execute -> reflect -> refine. `executor.py` genuinely consumes the reflect step
(`analyze_execution_result()` gates `should_refine`), but a live executor was getting
`_retrospection_engine = None`, so production ran execute -> refine with nothing analysing
whether the execution justified the skill update.

TWO INDEPENDENT DEFECTS caused it:

 1. `compound/__init__.make_executor` BYPASSES `ExecutorFactory.create()` and hand-duplicates
    the auto-wiring. Its own comment says so. It re-implements jepa_gate (W1) and
    degradation_detector (CB5) but silently omits retrospection_engine.
 2. `executor_factory.make_executor` — the path that DOES wire retrospection — could not be
    called at all: it forwards `inference_provider=` to `ExecutorFactory.create()`, which does
    not accept it (TypeError).

So the correct wiring existed in a function nobody could call, and the callable function had
incomplete wiring. Duplicated wiring diverges; that is the lesson, not the individual omission.

Both tests below FAIL against the pre-fix code.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class TestReflectPresent:
    def test_init_make_executor_wires_retrospection(self):
        """DISCRIMINATING: returned None pre-fix -> reflect silently absent from the loop."""
        from cohezion.compound import make_executor

        engine = getattr(make_executor(MagicMock()), "_retrospection_engine", None)
        assert engine is not None, "reflect step missing: executor got retrospection_engine=None"
        assert hasattr(engine, "analyze_execution_result"), (
            "wired object must expose the method executor.py actually calls"
        )

    def test_factory_make_executor_is_callable(self):
        """DISCRIMINATING: raised TypeError pre-fix (inference_provider not accepted by create)."""
        from cohezion.compound.executor_factory import make_executor

        engine = getattr(make_executor(MagicMock()), "_retrospection_engine", None)
        assert engine is not None

    def test_both_paths_agree(self):
        """The two factories must not diverge again — that divergence IS the defect."""
        from cohezion.compound import make_executor as init_make
        from cohezion.compound.executor_factory import make_executor as fact_make

        a = getattr(init_make(MagicMock()), "_retrospection_engine", None)
        b = getattr(fact_make(MagicMock()), "_retrospection_engine", None)
        assert (a is None) == (b is None), "factory paths disagree on reflect wiring"

    def test_explicit_injection_still_wins(self):
        """Auto-create must not clobber a caller-supplied engine (CB5 convention)."""
        from cohezion.compound import make_executor

        sentinel = MagicMock()
        e = make_executor(MagicMock(), retrospection_engine=sentinel)
        assert e._retrospection_engine is sentinel


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
