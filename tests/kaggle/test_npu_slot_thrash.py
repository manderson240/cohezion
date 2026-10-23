"""The NPU holds ONE FLM model; every model change evicts and reloads it and holds lemond's lock.

Measured 2026-10-23: this worker caused 37 NPU slot evictions in 30 min (tracks interleaved
deepseek/qwen, and qwen-track repairs hard-coded deepseek), which blocked lemond /health.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

from cohezion.kaggle import stateless_npu_agent as npu


ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "npu_worker", ROOT / "scripts/kaggle/stateless_npu_ascension_worker.py"
)
worker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(worker)

D, Q = "deepseek-r1-0528-8b-FLM", "qwen3.5-4b-FLM"
TRACKS = [
    {"slug": "a", "model": D},
    {"slug": "b", "model": Q},
    {"slug": "c", "model": D},
    {"slug": "d", "model": Q},
]


def _swaps(models: list[str]) -> int:
    return sum(1 for a, b in zip(models, models[1:]) if a != b)


def test_dispatch_order_swaps_the_slot_at_most_once_per_epoch() -> None:
    epochs = 6
    seq = [t["model"] for e in range(1, epochs + 1) for t in worker.dispatch_order(TRACKS, e, Q)]
    assert sorted(seq) == sorted([t["model"] for t in TRACKS] * epochs)  # nothing dropped
    assert _swaps(seq) <= epochs  # was 4 per epoch with the declared order
    assert _swaps([t["model"] for t in TRACKS] * epochs) == 4 * epochs - 1  # control: old order


class _FakeClient:
    def __init__(self) -> None:
        self.models: list[str] = []

    async def query_stateless(
        self, prompt, system_prompt="", model="", max_tokens=0, temperature=0.0
    ):
        self.models.append(model)
        return "```python\ndef f(x):\n    return x\n```", {}


def test_repair_reuses_the_resident_model_when_told_to() -> None:
    client = _FakeClient()
    agent = npu.StatelessNPUAgent(client=client, model=Q)
    assert agent.repair_model == npu.REASONING_NPU_MODEL  # default unchanged for other callers
    agent.repair_model = Q
    state = npu.StatelessState(
        task_id="t",
        domain=list(npu.InvariantDomain)[0],
        hypothesis="h",
        current_code="def f(x):\n    return x\n",
        target_invariant="i",
    )
    asyncio.run(
        agent.execute_turn(state, lambda code: (0.0, "fail", True))
    )  # force the repair path
    assert len(client.models) == 2  # generation + repair
    assert set(client.models) == {Q}  # no swap to deepseek inside a qwen track
