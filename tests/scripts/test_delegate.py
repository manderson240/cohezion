"""Unit tests for scripts/delegate.py.

The script's live path (actually calling fleet.route() against Lemonade) is
integration-tested by running the wrapper. Here we cover the pure CLI surface:
stdin handling, argparse wiring, output format switching (plain vs JSON), and
the per-session DelegationBudget gate (L367 / ARC Lesson 3).

Network and fleet calls are patched out. Budget state paths are redirected to
tmp_path so tests don't touch ~/.cohezion-engine/.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import patch


_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import delegate  # noqa: E402


# ---------------------------------------------------------------------------
# Prompt reading + basic CLI surface
# ---------------------------------------------------------------------------


def test_read_prompt_from_argument() -> None:
    assert delegate._read_prompt("hello world") == "hello world"


def test_read_prompt_dash_reads_stdin(monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("piped input  \n"))
    assert delegate._read_prompt("-") == "piped input"


def test_read_prompt_none_reads_stdin(monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("fallback stdin"))
    assert delegate._read_prompt(None) == "fallback stdin"


def test_main_rejects_empty_prompt(capsys, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    monkeypatch.setattr(delegate, "_budget_state_path", lambda _sid: tmp_path / "b.json")
    rc = delegate.main(["-"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "empty prompt" in captured.err


def test_main_plain_output_writes_text_to_stdout_and_meta_to_stderr(
    capsys, monkeypatch, tmp_path
) -> None:
    """When --json is not passed, stdout gets the text body and stderr gets
    a one-line [delegate] metadata summary."""
    monkeypatch.setattr(delegate, "_budget_state_path", lambda _sid: tmp_path / "b.json")

    async def fake_dispatch(*_args, **_kwargs):
        return {
            "text": "the answer is 42",
            "model": "phi4:latest",
            "lane": "cpu",
            "latency_ms": 123.4,
            "total_ms": 200.0,
            "ttft_ms": None,
            "tokens_per_sec": None,
            "cost_usd": 0.0,
            "escalated_to_cloud": False,
            "attempts": ["phi4:latest"],
            "error": None,
        }

    with patch.object(delegate, "_dispatch", fake_dispatch):
        rc = delegate.main(["test prompt"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "the answer is 42" in captured.out
    assert "[delegate]" in captured.err
    assert "model=phi4:latest" in captured.err
    assert "escalated=False" in captured.err
    assert "budget_remaining=" in captured.err


def test_main_json_output_writes_full_envelope_to_stdout(capsys, monkeypatch, tmp_path) -> None:
    """--json mode emits a parseable JSON envelope with all metadata."""
    monkeypatch.setattr(delegate, "_budget_state_path", lambda _sid: tmp_path / "b.json")

    async def fake_dispatch(*_args, **_kwargs):
        return {
            "text": "hi",
            "model": "Gemma-4-E4B-it-GGUF",
            "lane": "igpu_rocwmma",
            "latency_ms": 99.0,
            "total_ms": 100.0,
            "ttft_ms": 12.0,
            "tokens_per_sec": 50.0,
            "cost_usd": 0.0,
            "escalated_to_cloud": False,
            "attempts": ["Gemma-4-E4B-it-GGUF"],
            "error": None,
        }

    with patch.object(delegate, "_dispatch", fake_dispatch):
        rc = delegate.main(["--json", "test prompt"])
    assert rc == 0
    captured = capsys.readouterr()
    envelope = json.loads(captured.out)
    assert envelope["text"] == "hi"
    assert envelope["model"] == "Gemma-4-E4B-it-GGUF"
    assert envelope["escalated_to_cloud"] is False
    assert envelope["forced_local"] is False
    assert "budget_remaining" in envelope


def test_main_returns_1_when_text_empty_or_error(capsys, monkeypatch, tmp_path) -> None:
    """Exit 1 on empty text OR on explicit error from the dispatcher."""
    monkeypatch.setattr(delegate, "_budget_state_path", lambda _sid: tmp_path / "b.json")

    async def empty_text(*_args, **_kwargs):
        return {
            "text": "",
            "model": "",
            "lane": "",
            "latency_ms": 0.0,
            "total_ms": 0.0,
            "ttft_ms": None,
            "tokens_per_sec": None,
            "cost_usd": 0.0,
            "escalated_to_cloud": False,
            "attempts": [],
            "error": "all candidates exhausted",
        }

    with patch.object(delegate, "_dispatch", empty_text):
        rc = delegate.main(["test prompt"])
    assert rc == 1


# ---------------------------------------------------------------------------
# DelegationBudget — per-session cloud quota
# ---------------------------------------------------------------------------


def test_estimate_tokens_coarse_4_chars_per_token() -> None:
    assert delegate._estimate_tokens("a" * 40) == 10
    # Minimum of 1 so empty-string doesn't allow unlimited calls
    assert delegate._estimate_tokens("") == 1


def test_load_budget_state_returns_defaults_for_missing_file(tmp_path) -> None:
    state = delegate._load_budget_state(tmp_path / "nonexistent.json")
    assert state["cloud_tokens_used"] == 0
    assert state["local_tokens_used"] == 0
    assert state["calls_total"] == 0


def test_load_budget_state_returns_defaults_for_corrupt_file(tmp_path) -> None:
    path = tmp_path / "corrupt.json"
    path.write_text("{not valid json")
    state = delegate._load_budget_state(path)
    assert state["cloud_tokens_used"] == 0  # Graceful recovery


def test_save_and_load_roundtrip(tmp_path) -> None:
    path = tmp_path / "state.json"
    state = {
        "cloud_tokens_used": 1234,
        "local_tokens_used": 5678,
        "calls_total": 3,
        "calls_escalated": 1,
        "calls_forced_local": 0,
        "last_call_ts": 1234567890.0,
    }
    delegate._save_budget_state(path, state)
    loaded = delegate._load_budget_state(path)
    assert loaded == state


def test_cloud_escalation_allowed_when_under_cap() -> None:
    state = {"cloud_tokens_used": 100, "local_tokens_used": 0, "calls_total": 1}
    allowed, remaining = delegate._cloud_escalation_allowed(
        state, max_tokens=500, cloud_budget=1000
    )
    assert allowed is True
    assert remaining == 900


def test_cloud_escalation_denied_when_over_cap() -> None:
    state = {"cloud_tokens_used": 800, "local_tokens_used": 0, "calls_total": 5}
    allowed, remaining = delegate._cloud_escalation_allowed(
        state, max_tokens=500, cloud_budget=1000
    )
    # Cumulative would be 1300 > 1000 budget — deny
    assert allowed is False
    assert remaining == 200


def test_record_call_credits_cloud_tokens_on_escalation() -> None:
    state = delegate._load_budget_state(Path("/nonexistent"))  # defaults
    updated = delegate._record_call(state, tokens=150, escalated=True, forced_local=False)
    assert updated["cloud_tokens_used"] == 150
    assert updated["local_tokens_used"] == 0
    assert updated["calls_escalated"] == 1


def test_record_call_credits_local_tokens_when_not_escalated() -> None:
    state = delegate._load_budget_state(Path("/nonexistent"))
    updated = delegate._record_call(state, tokens=80, escalated=False, forced_local=False)
    assert updated["cloud_tokens_used"] == 0
    assert updated["local_tokens_used"] == 80
    assert updated["calls_escalated"] == 0


def test_record_call_increments_forced_local_counter() -> None:
    state = delegate._load_budget_state(Path("/nonexistent"))
    updated = delegate._record_call(state, tokens=50, escalated=False, forced_local=True)
    assert updated["calls_forced_local"] == 1


def test_show_budget_prints_summary_and_exits_0(capsys, monkeypatch, tmp_path) -> None:
    state_path = tmp_path / "b.json"
    state_path.write_text(
        json.dumps(
            {
                "cloud_tokens_used": 2500,
                "local_tokens_used": 1000,
                "calls_total": 10,
                "calls_escalated": 2,
                "calls_forced_local": 0,
                "last_call_ts": None,
            }
        )
    )
    monkeypatch.setattr(delegate, "_budget_state_path", lambda _sid: state_path)
    rc = delegate.main(["--show-budget"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "cloud_used=2500" in out
    assert "cloud_budget=10000" in out
    assert "remaining=7500" in out


def test_reset_budget_removes_state_file(capsys, monkeypatch, tmp_path) -> None:
    state_path = tmp_path / "b.json"
    state_path.write_text("{}")
    monkeypatch.setattr(delegate, "_budget_state_path", lambda _sid: state_path)
    rc = delegate.main(["--reset-budget"])
    assert rc == 0
    assert not state_path.exists()
    assert "budget reset" in capsys.readouterr().out


def test_main_forces_local_when_budget_would_be_exhausted(capsys, monkeypatch, tmp_path) -> None:
    """When cumulative cloud tokens + max_tokens exceeds --cloud-budget, the
    hook forces --local-only and notes the forced demotion in the envelope."""
    state_path = tmp_path / "b.json"
    state_path.write_text(
        json.dumps(
            {
                "cloud_tokens_used": 9800,  # near cap
                "local_tokens_used": 0,
                "calls_total": 5,
                "calls_escalated": 5,
                "calls_forced_local": 0,
                "last_call_ts": None,
            }
        )
    )
    monkeypatch.setattr(delegate, "_budget_state_path", lambda _sid: state_path)

    observed_local_only: list[bool] = []

    async def recording_dispatch(*_args, **kwargs):
        observed_local_only.append(kwargs["local_only"])
        return {
            "text": "local response",
            "model": "Gemma-4-E4B-it-GGUF",
            "lane": "igpu_rocwmma",
            "latency_ms": 50.0,
            "total_ms": 60.0,
            "ttft_ms": None,
            "tokens_per_sec": None,
            "cost_usd": 0.0,
            "escalated_to_cloud": False,
            "attempts": ["Gemma-4-E4B-it-GGUF"],
            "error": None,
        }

    # Default max_tokens=512, budget=10000, already-used=9800 → would-be 10312 > 10000
    with patch.object(delegate, "_dispatch", recording_dispatch):
        rc = delegate.main(["--json", "test prompt"])
    assert rc == 0
    # Hook observed local_only=True even though caller didn't pass --local-only
    assert observed_local_only == [True]
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["forced_local"] is True


def test_main_returns_3_when_forced_local_also_fails(monkeypatch, tmp_path) -> None:
    """Budget-driven forced-local + local failure = exit 3 (distinguishes from
    generic fleet exhaustion which is exit 1)."""
    state_path = tmp_path / "b.json"
    state_path.write_text(
        json.dumps(
            {
                "cloud_tokens_used": 9800,
                "local_tokens_used": 0,
                "calls_total": 5,
                "calls_escalated": 5,
                "calls_forced_local": 0,
                "last_call_ts": None,
            }
        )
    )
    monkeypatch.setattr(delegate, "_budget_state_path", lambda _sid: state_path)

    async def empty_text(*_args, **_kwargs):
        return {
            "text": "",
            "model": "",
            "lane": "",
            "latency_ms": 0.0,
            "total_ms": 0.0,
            "ttft_ms": None,
            "tokens_per_sec": None,
            "cost_usd": 0.0,
            "escalated_to_cloud": False,
            "attempts": [],
            "error": None,
        }

    with patch.object(delegate, "_dispatch", empty_text):
        rc = delegate.main(["test prompt"])
    assert rc == 3


def test_main_does_not_force_local_when_budget_ample(monkeypatch, tmp_path) -> None:
    state_path = tmp_path / "b.json"
    monkeypatch.setattr(delegate, "_budget_state_path", lambda _sid: state_path)

    observed_local_only: list[bool] = []

    async def recording_dispatch(*_args, **kwargs):
        observed_local_only.append(kwargs["local_only"])
        return {
            "text": "ok",
            "model": "claude-sonnet-4-6",
            "lane": "cloud_claude",
            "latency_ms": 400.0,
            "total_ms": 500.0,
            "ttft_ms": None,
            "tokens_per_sec": None,
            "cost_usd": 0.002,
            "escalated_to_cloud": True,
            "attempts": ["Gemma-4-E4B-it-GGUF", "claude-sonnet-4-6"],
            "error": None,
        }

    with patch.object(delegate, "_dispatch", recording_dispatch):
        rc = delegate.main(["--json", "test"])
    assert rc == 0
    # No budget pressure; caller's local_only=False preserved
    assert observed_local_only == [False]


def test_main_explicit_local_only_bypasses_budget_logic(monkeypatch, tmp_path) -> None:
    """--local-only means the budget check is moot — no escalation would
    happen anyway. Cumulative tokens still tracked for local use."""
    state_path = tmp_path / "b.json"
    state_path.write_text(
        json.dumps(
            {
                "cloud_tokens_used": 9999,  # over budget
                "local_tokens_used": 0,
                "calls_total": 0,
                "calls_escalated": 0,
                "calls_forced_local": 0,
                "last_call_ts": None,
            }
        )
    )
    monkeypatch.setattr(delegate, "_budget_state_path", lambda _sid: state_path)

    async def fake(*_args, **_kwargs):
        return {
            "text": "local response",
            "model": "m",
            "lane": "l",
            "latency_ms": 1.0,
            "total_ms": 1.0,
            "ttft_ms": None,
            "tokens_per_sec": None,
            "cost_usd": 0.0,
            "escalated_to_cloud": False,
            "attempts": ["m"],
            "error": None,
        }

    with patch.object(delegate, "_dispatch", fake):
        rc = delegate.main(["--local-only", "--json", "test"])
    assert rc == 0
    # forced_local is False because the caller asked for local explicitly,
    # not because we downgraded them
    out_state = delegate._load_budget_state(state_path)
    assert out_state["calls_forced_local"] == 0
    assert out_state["local_tokens_used"] > 0
