"""Tests for GapMiner — V-model invariants GM1–GM5.

GM1: structural — endorsed field exists on DataProduct (safe default False)
GM2: mine() groups by (domain, action) and applies the threshold
GM3: discriminating — an ENDORSED domain's gap outranks a same-count gap (priority high)
GM4: run_once() files only NEW gaps (state dedupe across runs)
GM5: fail-open — SurrealDB unreachable → mine() returns [] (no crash)
"""

from __future__ import annotations

import dataclasses
import json
from unittest.mock import patch

from cohezion.data_mesh.data_product import DataProduct
from cohezion.data_mesh.gap_miner import GapMiner


def _events(rows):
    """Patch target helper: rows as GapMiner._fetch_events would return them."""
    return [
        {"source": f"GaiaDataAgent/{d}", "payload": {"domain": d, "action": a}, "timestamp": 1.0}
        for d, a in rows
    ]


def _product(domain: str, endorsed: bool) -> DataProduct:
    return DataProduct(
        product_id=f"p-{domain}",
        name=domain,
        description="t",
        owner_domain=domain,
        endorsed=endorsed,
    )


# ── GM1 ───────────────────────────────────────────────────────────────────────


def test_gm1_endorsed_field_defaults_false():
    fields = {f.name: f for f in dataclasses.fields(DataProduct)}
    assert "endorsed" in fields
    assert fields["endorsed"].default is False


# ── GM2 ───────────────────────────────────────────────────────────────────────


def test_gm2_mine_groups_and_thresholds(tmp_path):
    miner = GapMiner(threshold=3, state_file=tmp_path / "s.json")
    rows = _events([("inference", "HEAL")] * 3 + [("skills", "ALERT")] * 2)
    with patch.object(GapMiner, "_fetch_events", return_value=rows):
        gaps = miner.mine()
    assert len(gaps) == 1
    assert gaps[0]["domain"] == "inference" and gaps[0]["action"] == "HEAL"
    assert gaps[0]["count"] == 3


# ── GM3: endorsement consumption (discriminating) ─────────────────────────────


def test_gm3_endorsed_domain_gap_gets_high_priority(tmp_path):
    products = {"a": _product("inference", endorsed=True), "b": _product("skills", endorsed=False)}
    miner = GapMiner(products=products, threshold=3, state_file=tmp_path / "s.json")
    rows = _events([("inference", "HEAL")] * 3 + [("skills", "HEAL")] * 3)
    with patch.object(GapMiner, "_fetch_events", return_value=rows):
        gaps = {g["domain"]: g for g in miner.mine()}
    # An impl that never reads DataProduct.endorsed gives both "normal" and fails here.
    assert gaps["inference"]["priority"] == "high"
    assert gaps["skills"]["priority"] == "normal"


# ── GM4: idempotent filing ────────────────────────────────────────────────────


def test_gm4_run_once_files_only_new_gaps(tmp_path):
    miner = GapMiner(threshold=3, state_file=tmp_path / "s.json")
    rows = _events([("inference", "HEAL")] * 3)
    pushed: list[dict] = []
    with (
        patch.object(GapMiner, "_fetch_events", return_value=rows),
        patch.object(GapMiner, "_push", side_effect=lambda item: pushed.append(item) or True),
    ):
        first = miner.run_once()
        second = miner.run_once()
    assert first == {"gaps_found": 1, "filed": 1}
    assert second == {"gaps_found": 1, "filed": 0}  # deduped by state
    assert len(pushed) == 1
    state = json.loads((tmp_path / "s.json").read_text())
    assert state["filed"] == ["gap-inference-heal"]


def test_gm4_failed_push_not_marked_filed(tmp_path):
    miner = GapMiner(threshold=3, state_file=tmp_path / "s.json")
    rows = _events([("inference", "HEAL")] * 3)
    with (
        patch.object(GapMiner, "_fetch_events", return_value=rows),
        patch.object(GapMiner, "_push", return_value=False),
    ):
        result = miner.run_once()
    assert result["filed"] == 0
    assert json.loads((tmp_path / "s.json").read_text())["filed"] == []


# ── GM5: fail-open ────────────────────────────────────────────────────────────


def test_gm5_mine_empty_when_surreal_unreachable(tmp_path):
    miner = GapMiner(threshold=1, state_file=tmp_path / "s.json")
    with patch(
        "cohezion.data_mesh.gap_miner.urllib.request.urlopen",
        side_effect=OSError("connection refused"),
    ):
        assert miner.mine() == []
