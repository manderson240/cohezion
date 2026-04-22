"""Unit tests for scripts/delegate.py.

The script's live path (actually calling fleet.route() against Lemonade) is
integration-tested by running the wrapper. Here we cover the pure CLI surface:
stdin handling, argparse wiring, output format switching (plain vs JSON).
Network and fleet calls are patched out.
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


def test_read_prompt_from_argument() -> None:
    assert delegate._read_prompt("hello world") == "hello world"


def test_read_prompt_dash_reads_stdin(monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("piped input  \n"))
    assert delegate._read_prompt("-") == "piped input"


def test_read_prompt_none_reads_stdin(monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("fallback stdin"))
    assert delegate._read_prompt(None) == "fallback stdin"


def test_main_rejects_empty_prompt(capsys, monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    rc = delegate.main(["-"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "empty prompt" in captured.err


def test_main_plain_output_writes_text_to_stdout_and_meta_to_stderr(capsys, monkeypatch) -> None:
    """When --json is not passed, stdout gets the text body and stderr gets
    a one-line [delegate] metadata summary."""

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


def test_main_json_output_writes_full_envelope_to_stdout(capsys) -> None:
    """--json mode emits a parseable JSON envelope with all metadata."""

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


def test_main_returns_1_when_text_empty_or_error(capsys) -> None:
    """Exit 1 on empty text OR on explicit error from the dispatcher."""

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
