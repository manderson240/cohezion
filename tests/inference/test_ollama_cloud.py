"""Autoharness for the blessed Ollama Cloud client (no network)."""

from __future__ import annotations

import json

import cohezion.inference.ollama_cloud as oc


class TestExtractJson:
    def test_plain_object(self):
        assert oc.extract_json('{"a": 1}') == {"a": 1}

    def test_fenced_json(self):
        assert oc.extract_json('Sure:\n```json\n{"a": 1}\n```\ndone') == {"a": 1}

    def test_think_wrapped(self):
        assert oc.extract_json('<think>{"decoy": 0} hmm</think>{"a": 1}') == {"a": 1}

    def test_garbage_returns_none_not_coerced(self):
        # Discriminating (Minerva outcome discipline): unparseable must be None,
        # never a silently-guessed object.
        assert oc.extract_json("Thinking...\nWe are asked to extract") is None
        assert oc.extract_json("") is None

    def test_non_object_json_rejected(self):
        assert oc.extract_json("[1, 2, 3]") is None


class TestCloudChatContract:
    def test_never_raises_and_logs_on_transport_error(self, monkeypatch, tmp_path):
        # Point the API at a dead port and the ledger at tmp — the call must
        # return "" (fail-soft contract) AND record the failure for budget audit.
        monkeypatch.setattr(oc, "OLLAMA_API", "http://127.0.0.1:9/api/chat")
        monkeypatch.setattr(oc, "USAGE_LEDGER", tmp_path / "usage.jsonl")
        out = oc.cloud_chat("hi", timeout_s=1.0, purpose="harness-test")
        assert out == ""
        rows = [json.loads(x) for x in (tmp_path / "usage.jsonl").read_text().splitlines()]
        assert rows and rows[0]["purpose"] == "harness-test" and rows[0]["error"]

    def test_think_defaults_off(self):
        # Structural: the metered lane defaults to no-think (doctrine + #1511 contrast).
        import inspect

        sig = inspect.signature(oc.cloud_chat)
        assert sig.parameters["think"].default is False
        assert sig.parameters["purpose"].default == "unspecified"
