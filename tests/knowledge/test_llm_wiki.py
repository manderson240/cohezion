"""Discriminating tests for knowledge.LLMWiki (V-model audit, 2026-06-05).

`knowledge` was a no-test module. LLMWiki is a JSON-backed key-value store; its load-bearing
contract is the persist→reload ROUND TRIP (`_persist` dumps `v.__dict__`, `_load` rebuilds
`WikiEntry(**v)`). Each test fails a plausible wrong impl:
  - query that raises (instead of None) on a missing key,
  - a round trip that drops a WikiEntry field (only the value survives),
  - update that doesn't overwrite an existing key,
  - a missing wiki dir that crashes instead of degrading to empty.
"""

from __future__ import annotations

from cohezion.knowledge.llm_wiki import LLMWiki, WikiEntry


def _entry(key: str = "npu_tps") -> WikiEntry:
    return WikiEntry(
        key=key,
        value=42,
        source="benchmark-2026",
        timestamp="2026-06-05T00:00:00Z",
        metadata={"backend": "xdna2", "unit": "tokens/s"},
    )


def test_query_missing_key_returns_none(tmp_path) -> None:
    w = LLMWiki(wiki_path=tmp_path)
    assert w.query("does_not_exist") is None


def test_update_then_query_in_memory(tmp_path) -> None:
    (tmp_path / "d").mkdir()
    w = LLMWiki(wiki_path=tmp_path / "d")
    e = _entry()
    w.update(e)
    assert w.query("npu_tps") is e


def test_persist_reload_round_trip_preserves_all_fields(tmp_path) -> None:
    # THE discriminating test: write on instance A, read on a fresh instance B (same path).
    # A round trip that drops any of the 5 fields, or mangles the metadata dict, fails here.
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    a = LLMWiki(wiki_path=wiki_dir)
    a.update(_entry())

    b = LLMWiki(wiki_path=wiki_dir)  # re-loads from wiki.json written by a.update()
    got = b.query("npu_tps")
    assert got is not None
    assert got == _entry()  # dataclass __eq__ over all 5 fields incl metadata dict


def test_update_overwrites_existing_key(tmp_path) -> None:
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    w = LLMWiki(wiki_path=wiki_dir)
    w.update(_entry())
    w.update(WikiEntry("npu_tps", 99, "s2", "t2", {}))
    assert w.query("npu_tps").value == 99
    assert len(w.get_all_entries()) == 1  # overwrite, not append


def test_missing_wiki_dir_degrades_to_empty_not_crash(tmp_path) -> None:
    w = LLMWiki(wiki_path=tmp_path / "nonexistent")
    assert w.get_all_entries() == {}
