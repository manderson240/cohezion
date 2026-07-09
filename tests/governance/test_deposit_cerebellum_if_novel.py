"""Discriminating tests for recall-deduped cerebellum deposit (item 51, 2026-06-06).

`deposit_cerebellum_if_novel(records, store)` closes the gap item 36 surfaced: a STABLE fleet
re-deposits a DUPLICATE cerebellum neuron on every health snapshot. It recalls (item 29) the existing
cerebellum neuron for the detected pattern's task_class and deposits (item 24) ONLY when none exists —
procedural-memory dedup.

Each test fails a plausible wrong impl:
  - deposits a duplicate when one already exists → test_dedup_no_redeposit,
  - fails to deposit a genuinely novel stable pattern → test_novel_deposits_one,
  - deposits on a noisy/fallback corpus → test_noisy_no_deposit,
  - reads/writes the real graph when store=None under pytest → test_store_none_no_real_graph.
"""

from __future__ import annotations

from unittest.mock import patch

from cohezion.governance import knowledge_bridge as kb
from cohezion.governance.knowledge_bridge import (
    build_cerebellum_neuron,
    deposit_cerebellum_if_novel,
)


def _stable(task: str, lane: str = "igpu", n: int = 6) -> list[dict]:
    return [{"task_class": task, "lane": lane, "fell_back": False} for _ in range(n)]


def _noisy(task: str, n: int = 6) -> list[dict]:
    return [{"task_class": task, "lane": "", "fell_back": True} for _ in range(n)]


def test_dedup_no_redeposit_when_present() -> None:
    existing = build_cerebellum_neuron("RERANK", "igpu", consistency=1.0, samples=6)
    store = [existing]
    out = deposit_cerebellum_if_novel(_stable("RERANK"), store=store)
    assert out is None  # a cerebellum neuron for RERANK already exists → no duplicate
    assert len(store) == 1


def test_novel_deposits_one() -> None:
    store: list[dict] = []
    out = deposit_cerebellum_if_novel(_stable("RERANK"), store=store)
    assert out is not None
    assert out["country"] == "cerebellum"
    assert "RERANK" in out["tags"]
    assert len(store) == 1


def test_noisy_no_deposit() -> None:
    store: list[dict] = []
    assert deposit_cerebellum_if_novel(_noisy("RERANK"), store=store) is None
    assert store == []


def test_dedup_is_per_task_class() -> None:
    # An existing neuron for a DIFFERENT task must not block a novel task's deposit.
    store = [build_cerebellum_neuron("OCR_DOC", "cpu", consistency=1.0, samples=6)]
    out = deposit_cerebellum_if_novel(_stable("RERANK"), store=store)
    assert out is not None and "RERANK" in out["tags"]
    assert len(store) == 2


def test_store_none_no_real_graph() -> None:
    # store=None under pytest → no deposit AND no real-graph read/write.
    with (
        patch.object(kb, "_select_neurons_from_graph") as sel,
        patch.object(kb, "deposit_neuron_record") as dep,
    ):
        assert deposit_cerebellum_if_novel(_stable("RERANK"), store=None) is None
        sel.assert_not_called()
        dep.assert_not_called()
