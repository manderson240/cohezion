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
    is_well_formed,
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
        """Two independent caps bound this: _MAX_ITEMS (count) and _MAX_CHARS (per line).

        The original version of this test used ~10-char items and asserted `< 12000`,
        which pinned only the item cap: raising _MAX_CHARS 200->4000, or deleting the
        per-line truncation outright, both left it green. The 12000 encoded the author's
        fixture, not the code's guarantee — the real bound is ~25.5k and the largest real
        session already emits 18.2k. Items below are at the truncation boundary so BOTH
        caps are load-bearing, and the bound is derived from the constants, not guessed.
        """
        long_item = "x" * (session_digest._MAX_CHARS * 10)
        n = session_digest._MAX_ITEMS * 10
        big = _art(
            user_prompts=[long_item] * n,
            file_writes=[FileWrite(f"/repo/{long_item}{i}.py", "Write", "z") for i in range(n)],
            bash_commands=[long_item] * n,
        )
        p = build_digest_prompt(big)
        cap = 3 * session_digest._MAX_ITEMS * (session_digest._MAX_CHARS + 8) + 4000
        assert len(p) < cap, f"prompt not bounded: {len(p)} chars (cap {cap})"
        assert long_item not in p, "per-line truncation did not fire"
        assert "more" in p.lower(), "truncation should be disclosed"

    def test_empty_session_still_produces_a_prompt(self):
        p = build_digest_prompt(_art(user_prompts=[], file_writes=[], bash_commands=[]))
        assert isinstance(p, str) and p.strip()


WELL_FORMED = "GOAL: g\nOUTCOME: o\nDECISIONS: none visible\nOPEN: none visible"
# Taken from a REAL failed digest (53ddf60c..., 9782 bytes) on the first live run.
#
# The critical property: it contains "GOAL:" and "OPEN:" *inside its prose*, just never at
# line start. An earlier hand-invented fixture omitted them, so a substring-based gate
# passed this test while still letting the real 9KB dumps through — a placebo test that
# certified a gate which was not working. Do not "simplify" this fixture.
SCRATCHPAD = (
    "*   Goal: Summarize an AI coding session for an engineering knowledge vault.\n"
    "    *   Format: Four sections (GOAL, OUTCOME, DECISIONS, OPEN) in plain prose.\n"
    "    *   Constraint: GOAL: one sentence. OUTCOME: one or two sentences.\n"
    "    *   DECISIONS: one per line. OPEN: anything left unfinished.\n"
    "*   Working Directory: `/home/mike-anderson/dev/cohezion`\n"
)


def _reply(text: str) -> dict:
    return {"choices": [{"message": {"content": "", "reasoning_content": text}}]}


class TestDigestSession:
    def test_chat_fn_receives_prompt_and_result_is_parsed(self):
        seen = {}

        def fake_chat(prompt: str, max_tokens: int) -> dict:
            seen["prompt"] = prompt
            return _reply(WELL_FORMED)

        assert digest_session(_art(), fake_chat) == WELL_FORMED
        assert "fix the parser" in seen["prompt"]

    def test_chat_failure_returns_empty_not_raises(self):
        """Fail-open: one unreachable model must not abort a 221-session batch."""

        def boom(prompt: str, max_tokens: int) -> dict:
            raise OSError("connection refused")

        assert digest_session(_art(), boom) == ""


class TestWellFormedGate:
    """The gate that separates an ANSWER from a thinking-mode SCRATCHPAD.
    8% of the first live run (3/37) failed this way and was persisted as if valid."""

    def test_scratchpad_is_not_well_formed(self):
        assert not is_well_formed(SCRATCHPAD)

    def test_complete_digest_is_well_formed(self):
        assert is_well_formed(WELL_FORMED)

    def test_truncated_digest_is_not_well_formed(self):
        """Mode B: cut off before OPEN. Looks fine until you check for the last section."""
        assert not is_well_formed("GOAL: g\nOUTCOME: o\nDECISIONS: d")

    def test_scratchpad_reply_is_discarded_not_returned(self):
        """Discriminating: an impl without the gate returns the 9KB reasoning dump, which
        the batch then writes to the vault as a legitimate digest."""

        def always_scratchpad(prompt: str, max_tokens: int) -> dict:
            return _reply(SCRATCHPAD)

        assert digest_session(_art(), always_scratchpad, retries=1) == ""

    def test_retry_doubles_the_token_budget(self):
        """Discriminating: an impl that retries with the SAME budget just repeats the
        truncation. The budget must grow, because running out of room IS the failure."""
        budgets = []

        def fails_then_succeeds(prompt: str, max_tokens: int) -> dict:
            budgets.append(max_tokens)
            return _reply(SCRATCHPAD if len(budgets) == 1 else WELL_FORMED)

        assert digest_session(_art(), fails_then_succeeds, max_tokens=100) == WELL_FORMED
        assert budgets == [100, 200], f"budget did not double: {budgets}"


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


class TestOOMPreflight:
    """A chat request naming an unloaded model makes the router LOAD it, so this is a
    model-load path. It previously bypassed oom_guard entirely — the box hard-froze on
    2026-07-18 with heavy local inference running, which is what this gate exists to stop.
    """

    def _force_risk(self, monkeypatch, *, safe: bool):
        from cohezion.compound import oom_guard

        risk = oom_guard.OOMRisk(safe, "M", 2.0, 40.0, "insufficient RAM: need 48.0GB")
        monkeypatch.setattr(oom_guard, "check_oom_risk", lambda *a, **k: risk)

    def test_unsafe_memory_refuses_before_any_request(self, monkeypatch):
        """Discriminating: an unwired impl reaches urlopen and errors on CONNECTION
        (OSError) rather than refusing on MEMORY, so asserting MemoryError specifically
        is what proves the gate ran."""
        self._force_risk(monkeypatch, safe=False)
        monkeypatch.setattr(session_digest, "OMNIROUTER", "http://127.0.0.1:9/none")
        with pytest.raises(MemoryError, match="protect the box"):
            session_digest.lemonade_chat("hi", timeout=1.0)

    def test_safe_memory_proceeds_to_the_request(self, monkeypatch):
        """Mirror case: the gate must not block when memory is fine — it should get past
        the check and fail on connection instead."""
        self._force_risk(monkeypatch, safe=True)
        monkeypatch.setattr(session_digest, "OMNIROUTER", "http://127.0.0.1:9/none")
        with pytest.raises(OSError):
            session_digest.lemonade_chat("hi", timeout=1.0)
