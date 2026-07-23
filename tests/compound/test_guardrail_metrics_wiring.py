"""Discriminating test: guardrail actions in execute_task feed UnifiedMetrics.

Producer-consumer gap (2026-07-12 audit): the executor produced
`output_blocked_by_guardrails` in its metrics dict, but `UnifiedMetricsCollector.
record_guardrail_action` (the producer of the `guardrail_blocks` counter the
/guardrails analytics reads) had ZERO callers -> the security dashboard silently
reported 0 blocks forever. This test fails if that wiring is removed.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from cohezion.compound.executor import CompoundExecutor
from cohezion.observability.unified_metrics import get_metrics_collector
from cohezion.security.guardrail_pipeline import GuardrailAction


class _Pipeline:
    """Guardrail pipeline stub: input ALLOW, output BLOCK."""

    async def check_input(self, text, ctx):  # noqa: ARG002
        return SimpleNamespace(action=GuardrailAction.ALLOW, reason="", modified_input=None)

    async def check_output(self, text, ctx):  # noqa: ARG002
        return SimpleNamespace(
            action=GuardrailAction.BLOCK, reason="test block", modified_input=None
        )


def test_guardrail_block_feeds_unified_metrics_counter():
    collector = get_metrics_collector()
    blocks_before = collector.current_metrics.guardrail_blocks
    checks_before = collector.current_metrics.guardrail_checks

    ex = CompoundExecutor(MagicMock(), guardrail_pipeline=_Pipeline(), enable_guardrails=True)
    ex.execute_task(
        task_description="hello world",
        skill_name="test_skill",
        operation_type="generate",
        execute_fn=lambda guidance: ("some output", {}),  # noqa: ARG005
    )

    # input ALLOW (+1 check) + output BLOCK (+1 check, +1 block)
    assert collector.current_metrics.guardrail_blocks == blocks_before + 1, (
        "output BLOCK not recorded"
    )
    assert collector.current_metrics.guardrail_checks == checks_before + 2, (
        "guardrail checks not recorded"
    )
