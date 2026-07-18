"""Discriminating tests for session_digest — the LLM judgment layer over salvaged sessions.

The deterministic half (session_salvage) is tested separately. These tests cover the two
things that actually break in practice with local thinking-models:
  1. Gemma-4 puts the answer in `reasoning_content` and leaves `content` empty.
  2. It wraps structured output in ``` fences.
Both are silent-empty-output failures, so each has a test that fails without the fix.
"""

from __future__ import annotations

import pytest

from cohezion.observability import session_digest
from cohezion.observability.session_digest import (
    build_digest_prompt,
    digest_session,
    parse_chat_response,
)
from cohezion.observability.session_salvage import FileWrite, SessionArtifacts


def _art(**kw) -> SessionArtifacts:
    base = {
        "session_id": "s1",
        "cwd": "/repo",
        "first_ts": "2026-07-18T09:00:00Z",
        "last_ts": "2026-07-18T10:00:00Z",
        "user_prompts": ["fix the parser"],
        "file_writes": [FileWrite("/repo/a.py", "Write", "x=1")],
        "bash_commands": ["pytest -q"],
        "commands_invoked": [],
    }
    base.update(kw)
    return SessionArtifacts(**base)


class TestParseChatResponse:
    def test_plain_content_returned(self):
        payload = {"choices": [{"message": {"content": "a summary"}}]}
        assert parse_chat_response(payload) == "a summary"

    def test_reasoning_content_used_when_content_empty(self):
        """Discriminating: Gemma-4 thinking-mode returns content="" with the real answer
        in reasoning_content. An impl reading only `content` yields "" — a silent no-op
        that looks like the model declined."""
        payload = {
            "choices": [{"message": {"content": "", "reasoning_content": "the real summary"}}]
        }
        assert parse_chat_response(payload) == "the real summary"

    def test_content_wins_when_both_present(self):
        payload = {"choices": [{"message": {"content": "answer", "reasoning_content": "think"}}]}
        assert parse_chat_response(payload) == "answer"

    def test_markdown_fences_stripped(self):
        """Discriminating: an impl that returns raw text leaves the fences, which breaks
        any downstream parse and pollutes the vault note."""
        payload = {"choices": [{"message": {"content": '```json\n{"a": 1}\n```'}}]}
        assert parse_chat_response(payload) == '{"a": 1}'

    def test_malformed_payload_returns_empty_not_raises(self):
        for bad in ({}, {"choices": []}, {"choices": [{}]}, {"choices": [{"message": {}}]}):
            assert parse_chat_response(bad) == ""


class TestBuildDigestPrompt:
    def test_prompt_includes_the_evidence(self):
        p = build_digest_prompt(_art())
        assert "fix the parser" in p
        assert "/repo/a.py" in p
        assert "pytest -q" in p

    def test_prompt_is_bounded_for_huge_sessions(self):
        """Discriminating: an impl that inlines everything sends a 300-file session
        straight past the context window. Cheap local tokens are not infinite context."""
        big = _art(
            user_prompts=[f"prompt {i}" for i in range(500)],
            file_writes=[FileWrite(f"/repo/f{i}.py", "Write", "z") for i in range(500)],
            bash_commands=[f"cmd-{i}" for i in range(500)],
        )
        p = build_digest_prompt(big)
        assert len(p) < 12000, f"prompt not bounded: {len(p)} chars"
        assert "500" in p or "more" in p.lower(), "truncation should be disclosed"

    def test_empty_session_still_produces_a_prompt(self):
        p = build_digest_prompt(_art(user_prompts=[], file_writes=[], bash_commands=[]))
        assert isinstance(p, str) and p.strip()


class TestDigestSession:
    def test_chat_fn_receives_prompt_and_result_is_parsed(self):
        seen = {}

        def fake_chat(prompt: str) -> dict:
            seen["prompt"] = prompt
            return {"choices": [{"message": {"content": "", "reasoning_content": "S"}}]}

        out = digest_session(_art(), fake_chat)
        assert out == "S"
        assert "fix the parser" in seen["prompt"]

    def test_chat_failure_returns_empty_not_raises(self):
        """Fail-open: one unreachable model must not abort a 221-session batch."""

        def boom(prompt: str) -> dict:
            raise OSError("connection refused")

        assert digest_session(_art(), boom) == ""


class TestEndpointSchemePinning:
    def test_non_http_endpoint_is_refused(self, monkeypatch):
        """Discriminating: OMNIROUTER is module-level and rebindable. Without the scheme
        check, urlopen honours file:// and the 'local inference call' becomes an arbitrary
        file read. An impl that trusts the constant reaches urlopen and does NOT raise."""
        monkeypatch.setattr(session_digest, "OMNIROUTER", "file:///etc/passwd")
        with pytest.raises(ValueError, match="non-HTTP inference endpoint"):
            session_digest.lemonade_chat("hi")

    def test_http_endpoint_passes_the_guard(self, monkeypatch):
        """The guard must not reject the legitimate endpoint — it fails past the scheme
        check on connection, not on validation."""
        monkeypatch.setattr(session_digest, "OMNIROUTER", "http://127.0.0.1:9/none")
        with pytest.raises(OSError):
            session_digest.lemonade_chat("hi", timeout=1.0)
