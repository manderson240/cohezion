"""Tests for the AutoHarness <-> GAIA SDK bridge (2026-09-15).

Parser cases include the exact live failure strings observed with
Gemma-4-31B on 2026-09-15 (nested tool_args + <|tool_call|> suffix;
fenced-JSON treated as final answer). Gate tests use a stub registry; the
full GAIA integration test runs only when the gaia package is installed.
"""

from __future__ import annotations

from typing import Any

import pytest

from cohezion.agi.gaia_autoharness_bridge import (
    GAIA_AVAILABLE,
    extract_tool_call,
)


# --- parser (dependency-free, always runs) --------------------------------


class TestExtractToolCall:
    def test_plain_json(self) -> None:
        out = extract_tool_call('{"tool":"run_bash","tool_args":{"cmd":"ls"}}')
        assert out == {"tool": "run_bash", "tool_args": {"cmd": "ls"}}

    def test_plain_json_missing_tool_args(self) -> None:
        out = extract_tool_call('{"tool":"read_charter"}')
        assert out == {"tool": "read_charter", "tool_args": {}}

    def test_fenced_json(self) -> None:
        out = extract_tool_call(
            'Here is my action:\n```json\n{"tool":"run_bash","tool_args":{"cmd":"ls"}}\n```\n'
        )
        assert out is not None
        assert out["tool"] == "run_bash"

    def test_nested_args_with_suffix(self) -> None:
        """The exact live 2026-09-15 failure: nested tool_args + <|tool_call|>."""
        live = (
            "{\"thought\": \"The change in '.pi/git/' is adding '-dirty'\", "
            '"tool": "append_log", '
            '"tool_args": {"entry": "[DECISION] File: .pi | Classification: Daemon"}}'
            "<|tool_call|>"
        )
        out = extract_tool_call(live)
        assert out is not None
        assert out["tool"] == "append_log"
        entry = out["tool_args"]["entry"]
        assert "Daemon" in entry

    def test_preamble_then_call(self) -> None:
        out = extract_tool_call(
            'Let me check the file. {"tool":"run_bash","tool_args":{"cmd":"ls"}}'
        )
        assert out is not None
        assert out["tool"] == "run_bash"

    def test_last_call_wins(self) -> None:
        out = extract_tool_call('{"tool":"first_call"} later {"tool":"second_call"}')
        assert out is not None
        assert out["tool"] == "second_call"

    def test_braces_inside_strings(self) -> None:
        out = extract_tool_call('{"tool":"run_bash","tool_args":{"cmd":"echo \'{\\"a\\":1}\'"}}')
        assert out is not None
        assert out["tool"] == "run_bash"

    def test_true_final_answer_is_none(self) -> None:
        assert (
            extract_tool_call("I have completed the task. Everything is done and verified.") is None
        )

    def test_empty_and_whitespace(self) -> None:
        assert extract_tool_call("") is None
        assert extract_tool_call("   ") is None

    def test_malformed_json_near_tool_key(self) -> None:
        assert extract_tool_call('{"tool": broken') is None


# --- gate (needs gaia; skips otherwise) -----------------------------------


@pytest.mark.skipif(not GAIA_AVAILABLE, reason="gaia package not installed")
class TestAutoHarnessGaiaBridge:
    def _make_agent(self) -> Any:
        from gaia.agents.base.agent import Agent

        from cohezion.agi.gaia_autoharness_bridge import AutoHarnessGaiaBridge

        class Runner(AutoHarnessGaiaBridge, Agent):
            def _register_tools(self) -> None:
                pass

        # skip_lemonade=True: keep tests offline — no lemonade startup ping.
        return Runner(skip_lemonade=True)

    def test_parse_delegates_to_extract(self, monkeypatch: pytest.MonkeyPatch) -> None:
        agent = self._make_agent()
        out = agent._parse_llm_response('preamble {"tool":"run_bash","tool_args":{"cmd":"ls"}}')
        assert out["tool"] == "run_bash"
        assert agent.harness_stats["deterministic_reparses"] == 1

    def test_parse_final_answer_passthrough(self) -> None:
        agent = self._make_agent()
        out = agent._parse_llm_response("All done, nothing left to do.")
        assert out["answer"].startswith("All done")

    def test_gate_blocks_hallucinated_tool(self) -> None:
        agent = self._make_agent()
        # _tools_registry is a read-only property; the sanctioned per-instance
        # override is the _snapshot_tools() mechanism (_instance_tools).
        agent.__dict__["_instance_tools"] = {"read_charter": object()}
        out = agent._execute_tool("nonexistent_tool", {})
        assert out["status"] == "error"
        assert "does not exist" in out["error"]
        assert agent.harness_stats["policy_blocks"] == 1

    def test_gate_allows_registered_tool(self) -> None:
        from gaia.agents.base.agent import Agent as agent_cls

        agent = self._make_agent()
        agent.__dict__["_instance_tools"] = {"read_charter": object()}
        seen: dict[str, str] = {}

        def fake_execute(self: Any, tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any]:
            seen["name"] = tool_name
            return {"status": "success"}

        orig = getattr(agent_cls, "_execute_tool", None)
        agent_cls._execute_tool = fake_execute
        try:
            out = agent._execute_tool("read_charter", {})
        finally:
            if orig is not None:
                agent_cls._execute_tool = orig
            else:
                delattr(agent_cls, "_execute_tool")
        assert out == {"status": "success"}
        assert seen["name"] == "read_charter"
        assert agent.harness_stats["gated_tool_calls"] == 1

    def test_memory_safe_block(self) -> None:
        agent = self._make_agent()
        agent.__dict__["_instance_tools"] = {"read_charter": object()}
        agent.__dict__["_harness_available_gb"] = 10.0  # below the 20 GiB floor
        out = agent._execute_tool("read_charter", {})
        assert out["status"] == "error"
        assert "policy block" in out["error"]

    def test_import_guard_flag(self) -> None:
        assert GAIA_AVAILABLE is True  # in this venv gaia is installed


# --- mix-in without a gaia Agent base fails closed ------------------------


@pytest.mark.skipif(not GAIA_AVAILABLE, reason="gaia package not installed")
def test_fail_closed_without_gaia_base() -> None:
    """Bridge composed without an Agent base must refuse, not drop the call."""
    from cohezion.agi.gaia_autoharness_bridge import AutoHarnessGaiaBridge

    class Bare(AutoHarnessGaiaBridge):  # no Agent base
        # Provide the registry attribute the gate looks up, so the name check
        # passes and execution reaches the missing-parent branch.
        _tools_registry = {"read_charter": object()}  # type: ignore

        def _register_tools(self) -> None:
            pass

    agent = Bare()
    out = agent._execute_tool("read_charter", {})
    assert out["status"] == "error"
    assert "requires a gaia Agent base" in out["error"]
