"""AutoHarness <-> GAIA SDK bridge: deterministic seams for GAIA agents.

Fixes GAIA 0.23.0's LLM-fragile parse/dispatch seams with AutoHarness
code-as-action checks — zero LLM calls, sub-millisecond, deterministic:

1. ``_parse_llm_response`` override — deterministic fence-aware tool-call
   extraction, superseding GAIA's heuristic ``_extract_embedded_tool_call``
   whose ambiguity→None path mis-classes wrapped tool JSON as a FINAL
   ANSWER (observed live 2026-09-15: ``read_charter`` ×4 infinite-turn
   failure with zero work done).
2. Nested-call extraction — models terminate turns with a complete tool
   call embedded in narrative (``{"tool_args": {...}}`` nested braces,
   ``<|tool_call|>`` suffix). Naive ``[^{}]*`` regexes miss nested
   objects → premature "final answer". Fixed with a string-aware
   brace-depth scanner (no regex on JSON structure).
3. ``_execute_tool`` gate — pre-execution ``AutoHarness.evaluate_policy()``
   on tool-name validity (against the live registry) plus the registered
   ``memory_safe`` state policy, so a hallucinated tool name fail-closes
   deterministically instead of surfacing as an LLM-side error round-trip.

Live validation (2026-09-15, Gemma-4-31B via Lemonade iGPU): with the
bridge, a GAIA dirt-triage agent executed 15 consecutive tool calls with
per-file decision logs and an honest max-steps termination report; the
same task without the bridge produced 4 identical turns and zero work.

The parser functions are dependency-free (stdlib only) and always
importable; the agent mix-in requires the ``gaia`` package and is gated
behind ``GAIA_AVAILABLE`` so CI environments without GAIA still run the
parser test suite.
"""

from __future__ import annotations

import json
import re
from typing import Any

from cohezion.agi.autoharness_policy import AutoHarnessPolicy


try:  # pragma: no cover - import guard verified by tests
    from gaia.agents.base.agent import Agent

    GAIA_AVAILABLE = True
except ImportError:  # pragma: no cover
    Agent = object  # type: ignore[assignment, misc]
    GAIA_AVAILABLE = False


# --- deterministic fence-aware parser -------------------------------------

_TOOL_KEY_RE = re.compile(r'"tool"\s*:')
_FENCE_RE = re.compile(r"```[a-zA-Z0-9_-]*\n(.*?)```", re.DOTALL)


def _top_level_json_objects(text: str) -> list[str]:
    """Scan for balanced top-level JSON objects with a string-aware
    brace-depth counter (handles nesting like ``{"tool_args": {...}}`` and
    braces inside string values correctly — no regex on structure)."""
    objects: list[str] = []
    depth = 0
    start = -1
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if esc:
            esc = False
            continue
        if in_str:
            if ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                objects.append(text[start : i + 1])
                start = -1
    return objects


def extract_tool_call(response: str) -> dict[str, Any] | None:
    """Deterministically extract a GAIA tool-call dict from an LLM response.

    Order (all zero-cost, no LLM):
      1. direct ``json.loads`` of the whole response
      2. balanced top-level objects containing a ``"tool"`` key, LAST first
         (models append the call after a narrative preamble; the final
         candidate is the actionable one — covers the nested ``tool_args`` /
         ``<|tool_call|>``-suffix failure observed live)
      3. fenced blocks with a ``"tool"`` key, last first

    Returns ``None`` only when genuinely no tool call exists — callers then
    treat the text as a final answer. This removes GAIA's ambiguous-
    fenced-candidates → None → false-final-answer failure mode.
    """
    if not response or not response.strip():
        return None

    # 1. Whole-response JSON
    try:
        obj = json.loads(response)
        if isinstance(obj, dict) and "tool" in obj:
            obj.setdefault("tool_args", {})
            return obj
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. Balanced candidates (unfenced), scan from the last backwards
    candidates = [s for s in _top_level_json_objects(response) if _TOOL_KEY_RE.search(s)]
    for s in reversed(candidates):
        try:
            obj = json.loads(s)
            if isinstance(obj, dict) and "tool" in obj:
                obj.setdefault("tool_args", {})
                return obj
        except json.JSONDecodeError:
            continue

    # 3. Fenced blocks, last first
    for m in reversed(list(_FENCE_RE.finditer(response))):
        block = m.group(1)
        if _TOOL_KEY_RE.search(block):
            try:
                obj = json.loads(block)
                if isinstance(obj, dict) and "tool" in obj:
                    obj.setdefault("tool_args", {})
                    return obj
            except json.JSONDecodeError:
                continue
    return None


if GAIA_AVAILABLE:

    class AutoHarnessGaiaBridge:
        """Mix-in for a ``gaia`` Agent subclass: deterministic parse + gate.

        Usage::

            class Runner(AutoHarnessGaiaBridge, Agent):
                def _register_tools(self) -> None:
                    pass  # module-level @tool decorators auto-register

        Set ``_harness_available_gb`` (int/float) on the instance to feed
        the ``memory_safe`` policy from a live probe instead of the 64 GiB
        default.
        """

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.autoharness = AutoHarnessPolicy("gaia_agent_gate")
            self.harness_stats = {
                "deterministic_reparses": 0,
                "gated_tool_calls": 0,
                "policy_blocks": 0,
            }

        # --- Seam 1: deterministic response parsing -----------------------
        def _parse_llm_response(self, response: str) -> dict[str, Any]:
            # Fast path: GAIA's own direct-JSON success case is kept
            # (identical behaviour, zero regression).
            try:
                obj = json.loads(response)
                if isinstance(obj, dict):
                    if "tool" in obj:
                        obj.setdefault("tool_args", {})
                    return obj
            except (json.JSONDecodeError, ValueError):
                pass

            # Deterministic fence-aware extraction (the fix for the
            # fenced-JSON-treated-as-final-answer failure mode).
            tool_call = extract_tool_call(response)
            if tool_call is not None:
                self.harness_stats["deterministic_reparses"] += 1
                return tool_call

            # Genuinely no tool call anywhere → final answer (GAIA contract).
            return {"thought": "", "goal": "", "answer": response}

        # --- Seam 2: pre-execution deterministic gate ---------------------
        def _execute_tool(self, tool_name: str, tool_args: dict[str, Any]) -> Any:
            registry = getattr(self, "_tools_registry", {}) or {}
            normalized = (tool_name or "").removesuffix("()").replace("-", "_")

            if normalized and normalized not in registry:
                # Deterministic fail-close: no LLM round-trip on
                # hallucinated tool names; the error text steers the model
                # to the valid set.
                self.harness_stats["policy_blocks"] += 1
                return {
                    "status": "error",
                    "error": (
                        f"AutoHarness gate: tool '{normalized}' does not exist. "
                        f"Valid tools: {sorted(registry.keys())}"
                    ),
                    "error_displayed": True,
                }

            state = {
                "tool": normalized,
                "available_gb": getattr(self, "_harness_available_gb", None) or 64.0,
            }
            result = self.autoharness.evaluate_policy(action_type="memory_safe", state=state)
            if not result.allowed:
                self.harness_stats["policy_blocks"] += 1
                return {
                    "status": "error",
                    "error": f"AutoHarness policy block: {result.reason}",
                    "error_displayed": True,
                }

            self.harness_stats["gated_tool_calls"] += 1
            parent_execute = getattr(super(), "_execute_tool", None)
            if parent_execute is None:
                # Mix-in used without a gaia Agent base — fail closed rather
                # than silently dropping the call.
                return {
                    "status": "error",
                    "error": (
                        "AutoHarnessGaiaBridge requires a gaia Agent base "
                        "class (class Runner(AutoHarnessGaiaBridge, Agent))"
                    ),
                    "error_displayed": True,
                }
            return parent_execute(normalized, tool_args)
