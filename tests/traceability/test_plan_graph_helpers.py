"""Discriminating tests for traceability.plan_graph pure helpers (V-model audit, 2026-06-05).

`traceability` was a no-test module. PlanGraph itself is SurrealDB-backed, but its pure
helpers parse the SurrealDB HTTP response shape and build record ids — silent-wrong-data
risks worth pinning. Each test fails a plausible wrong impl:
  - _path_to_id that only replaces '/' (not '.' / '-') or forgets to strip,
  - _first_result that returns on the FIRST envelope even when its result list is empty,
  - _all_results that mishandles a missing/dict result.
"""

from __future__ import annotations

from cohezion.traceability.plan_graph import _all_results, _first_result, _path_to_id


def test_path_to_id_replaces_slash_dot_dash_and_strips() -> None:
    assert _path_to_id("src/cohezion/foo.py") == "src_cohezion_foo_py"
    assert _path_to_id("a-b.c") == "a_b_c"  # dashes too, not just slashes
    assert _path_to_id("./foo") == "foo"  # leading separators stripped
    assert _path_to_id("/x/") == "x"


def test_first_result_skips_empty_result_list_finds_next_envelope() -> None:
    # Discriminates a "return on first envelope" impl: the first result list is empty,
    # so it must continue to the second envelope and return its first record.
    resp = [{"result": []}, {"result": [{"b": 2}]}]
    assert _first_result(resp) == {"b": 2}


def test_first_result_returns_first_of_list_and_handles_dict() -> None:
    assert _first_result([{"result": [{"a": 1}, {"a": 2}]}]) == {"a": 1}
    assert _first_result([{"result": {"a": 1}}]) == {"a": 1}  # dict result returned as-is


def test_first_result_none_when_no_records() -> None:
    assert _first_result([{"result": []}]) is None
    assert _first_result([]) is None


def test_all_results_returns_list_and_empty_on_missing_or_dict() -> None:
    assert _all_results([{"result": [{"a": 1}, {"a": 2}]}]) == [{"a": 1}, {"a": 2}]
    assert _all_results([{"result": []}]) == []
    assert _all_results([{"status": "ERR"}]) == []  # no 'result' key -> []
