"""Work-queue actioner engine tests (design v2 §6 + review correction #2).

Everything is injected (fake API, fake executor, fake chat) — no HTTP, no
inference, no real files outside tmp_path.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from cohezion.actioner.engine import (
    WorkQueueAPI,
    load_actioned_ids,
    run_batch,
    triage,
)


# ── fakes ─────────────────────────────────────────────────────────────────────
class FakeAPI(WorkQueueAPI):
    def __init__(self, items):
        super().__init__("http://fake")
        self._items = items
        self.patched: list[tuple[str, str]] = []

    def eligible_items(self):
        return list(self._items)

    def mark_actioned(self, item_id, note):
        self.patched.append((item_id, note))
        return {"id": item_id, "status": "actioned"}


class FakeExecutor:
    """Runs execute_fn for real (so artifacts get produced) and reports success."""

    def __init__(self, succeed=True):
        self.succeed = succeed
        self.calls = 0

    def execute_task(self, task_description, skill_name, operation_type, execute_fn):
        self.calls += 1
        if self.succeed:
            output, metrics = execute_fn("guidance")
            return SimpleNamespace(success=True, output=output, metrics=metrics)
        return SimpleNamespace(success=False, error="quality gate failed")


def _item(i, title="prompt caching for agent tools", **kw):
    return {
        "id": f"item{i:03d}",
        "title": title,
        "abstract": kw.pop("abstract", ""),
        "domain": kw.pop("domain", "cs.AI"),
        "relevance": "APPLY",
        "status": "reviewed",
        "url": f"https://arxiv.org/abs/26{i:02d}.00001",
        **kw,
    }


def _chat(prompt):
    return json.dumps({"proposal": "wire X into Y", "falsifiable_step": "measure Z drops"})


# ── tests ─────────────────────────────────────────────────────────────────────
def test_triage_routing():
    # Route B (methodology) keywords win, and are checked before Route A
    assert triage(_item(1, title="SFT curriculum for reward models")) == "experiment"
    # Route A (tooling/config/prompt-pattern)
    assert triage(_item(2, title="prompt caching for agent tools")) == "implement"
    # B-before-A precedence when both match
    assert triage(_item(3, title="prompt tuning improves eval benchmarks")) == "experiment"
    # No match -> None (item left untouched, never guessed)
    assert (
        triage(_item(4, title="quantum entanglement in superconductors", domain="quant-ph")) is None
    )


def test_route_a_idempotency_dedup_skips_rework(tmp_path):
    proposals = tmp_path / "props.jsonl"
    proposals.write_text(json.dumps({"item_id": "item001", "proposal": "old"}) + "\n")
    assert load_actioned_ids(proposals) == {"item001"}

    api = FakeAPI([_item(1)])
    ex = FakeExecutor()
    summary = run_batch(ex, api, _chat, proposals_path=proposals, vault_dir=tmp_path / "v")
    # No new inference cycle ran, no duplicate artifact appended...
    assert ex.calls == 0
    assert len(proposals.read_text().splitlines()) == 1
    assert summary["deduped"] == ["item001"]
    # ...but the crash-replay item still gets its PATCH (at-least-once completion).
    assert [p[0] for p in api.patched] == ["item001"]


def test_patch_only_after_successful_artifact(tmp_path):
    proposals = tmp_path / "props.jsonl"
    api = FakeAPI([_item(1)])
    summary = run_batch(
        FakeExecutor(), api, _chat, proposals_path=proposals, vault_dir=tmp_path / "v"
    )
    assert summary["actioned"] == [{"id": "item001", "route": "implement"}]
    entry = json.loads(proposals.read_text().splitlines()[0])
    assert entry["item_id"] == "item001"
    assert entry["verdict"] == "PROPOSED"  # honesty: never a claimed result
    assert [p[0] for p in api.patched] == ["item001"]


def test_failed_item_not_patched_and_batch_continues(tmp_path):
    """Review correction #2: a failed item stays `reviewed` (no PATCH) and the
    NEXT item still processes."""
    proposals = tmp_path / "props.jsonl"
    items = [_item(1), _item(2, title="tool sandbox config")]
    api = FakeAPI(items)

    class FlakyExecutor(FakeExecutor):
        def execute_task(self, *a, **kw):
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("inference stalled")
            return super().execute_task(*a, **kw)

    summary = run_batch(
        FlakyExecutor(), api, _chat, proposals_path=proposals, vault_dir=tmp_path / "v"
    )
    assert "item001" in summary["failed"]
    assert [a["id"] for a in summary["actioned"]] == ["item002"]
    assert [p[0] for p in api.patched] == ["item002"]  # failed item NOT patched


def test_batch_limit_strictly_enforced(tmp_path):
    api = FakeAPI([_item(i) for i in range(60)])
    ex = FakeExecutor()
    summary = run_batch(
        ex,
        api,
        _chat,
        batch_size=50,
        proposals_path=tmp_path / "p.jsonl",
        vault_dir=tmp_path / "v",
    )
    assert len(api.patched) == 50  # exactly batch_size ATTEMPTED items


def test_unmatched_head_items_do_not_starve_batch(tmp_path):
    """Found live 2026-07-10: no-match items at the oldest-first queue head
    consumed every batch slot, so matchable items behind them never ran."""
    unmatched = [_item(i, title="quantum entanglement", domain="quant-ph") for i in range(3)]
    matchable = [_item(10, title="prompt caching for agent tools")]
    api = FakeAPI(unmatched + matchable)
    summary = run_batch(
        FakeExecutor(),
        api,
        _chat,
        batch_size=3,
        proposals_path=tmp_path / "p.jsonl",
        vault_dir=tmp_path / "v",
    )
    assert len(summary["skipped_no_match"]) == 3
    assert [a["id"] for a in summary["actioned"]] == ["item010"]


def test_experiment_route_writes_vault_note(tmp_path):
    proposals = tmp_path / "props.jsonl"
    vault = tmp_path / "vault"
    api = FakeAPI([_item(1, title="DPO fine-tuning benchmark study")])
    summary = run_batch(FakeExecutor(), api, _chat, proposals_path=proposals, vault_dir=vault)
    assert summary["actioned"][0]["route"] == "experiment"
    notes = list(vault.glob("*.md"))
    assert len(notes) == 1
    body = notes[0].read_text()
    assert "PROPOSED — not run" in body and "Falsifiable step" in body


def test_dry_run_writes_nothing(tmp_path):
    proposals = tmp_path / "props.jsonl"
    api = FakeAPI([_item(1)])
    ex = FakeExecutor()
    summary = run_batch(
        ex, api, _chat, dry_run=True, proposals_path=proposals, vault_dir=tmp_path / "v"
    )
    assert summary["actioned"] == [{"id": "item001", "route": "implement", "dry_run": True}]
    assert ex.calls == 0 and api.patched == [] and not proposals.exists()


@pytest.mark.parametrize(
    "raw", ['{"proposal": "do X", "falsifiable_step": "check Y"}', "just prose"]
)
def test_parse_proposal_structured_and_fallback(raw):
    from cohezion.actioner.engine import _parse_proposal

    parsed = _parse_proposal(raw)
    assert parsed["proposal"]
    assert parsed["falsifiable_step"]
