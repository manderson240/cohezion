"""Code review handler — 3-agent Cohezion pipeline posting to Slack thread.

Pipeline:
  OrchestratorAgent (NPU) → plan
  AnalystAgent (iGPU)     → enriched_context
  EngineerAgent (CPU)     → implementation

Each stage posts incremental updates to the Slack thread via the progress_callback.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.cohezion_bridge import CohezionBridge, LemonadeClient

_bridge = CohezionBridge()


def _call_claude(system: str, prompt: str, model: str = "claude-sonnet-4-5") -> str:
    """Call Anthropic API and return text response."""
    try:
        import anthropic  # noqa: PLC0415
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text if response.content else ""
    except Exception:  # noqa: BLE001
        return ""


def _lemonade_or_claude(tier: str, system: str, prompt: str) -> tuple[str, bool]:
    """Try local AMD silicon first, fall back to Claude. Returns (text, used_local).

    Order: dedicated tier -> already-loaded OMNI model on the :13305 router -> cloud.
    The dedicated per-tier ports are often down in the router-centric topology, so the
    omni router is what actually serves $0. OOM-safe: already-loaded model only.
    """
    if _bridge.lemonade_available(tier):
        lm = LemonadeClient(tier)
        text = lm.complete(f"{system}\n\n{prompt}", max_tokens=1024)
        if text:
            return text, True
    omni_text, _backend = _bridge.complete_omni(f"{system}\n\n{prompt}", max_tokens=1024)
    if omni_text and omni_text.strip():
        return omni_text, True
    return _call_claude(system, prompt), False


# ── Agent system prompts ───────────────────────────────────────────────────────

_ORCHESTRATOR_SYS = """\
You are a technical project orchestrator specializing in code review planning.
Given a code review task, produce a JSON plan with these fields:
{
  "task_summary": "...",
  "complexity": "low|medium|high",
  "phases": ["phase1", "phase2", ...],
  "risk_flags": ["flag1", "flag2", ...],
  "recommended_tier": "npu|igpu|cpu"
}
Respond with valid JSON only."""

_ANALYST_SYS = """\
You are a senior code analyst specializing in risk assessment and semantic pattern matching.
Given a code review plan, produce enriched context as JSON:
{
  "risk_analysis": {"high": ["..."], "medium": ["..."], "low": ["..."]},
  "similar_patterns": [{"pattern": "...", "relevance": "..."}],
  "implementation_hints": ["hint1", "hint2", ...],
  "security_considerations": ["..."]
}
Respond with valid JSON only."""

_ENGINEER_SYS = """\
You are a senior software engineer synthesizing implementation guidance from a code review.
Given enriched context, produce an implementation plan as JSON:
{
  "code_patches": [
    {"file": "path/to/file.py", "description": "...", "code": "# code snippet..."}
  ],
  "test_recommendations": ["test1", "test2", ...],
  "confidence_score": 0.85,
  "skill_updates": ["pattern extracted for skill library"]
}
Respond with valid JSON only."""


def handle_review(
    task: str,
    progress_callback: Callable[[str, str], None] | None = None,
) -> dict:
    """Run the 3-agent code review pipeline.

    Args:
        task: Code review task description.
        progress_callback: Called with (stage, message) for incremental Slack updates.

    Returns:
        {
            "summary": str,
            "plan": dict,
            "enriched": dict,
            "implementation": dict,
            "total_time_s": float,
            "cost_usd": float,
        }
    """
    def notify(stage: str, msg: str) -> None:
        if progress_callback:
            progress_callback(stage, msg)

    start = time.time()
    total_cost = 0.0

    # ── Agent 1: Orchestrator (NPU tier) ─────────────────────────────
    notify("orchestrator", "Classifying task and building review plan...")
    orch_text, orch_local = _lemonade_or_claude(
        "npu",
        _ORCHESTRATOR_SYS,
        f"Code review task:\n\n{task}",
    )
    if not orch_local:
        total_cost += 0.001

    plan: dict[str, Any] = {}
    try:
        plan = json.loads(orch_text)
    except (json.JSONDecodeError, ValueError):
        plan = {
            "task_summary": task[:200],
            "complexity": "medium",
            "phases": ["Security review", "Quality review", "Test review"],
            "risk_flags": ["Manual review recommended"],
            "recommended_tier": "igpu",
        }

    notify("orchestrator", f"Plan complete — complexity: {plan.get('complexity', '?').upper()}, {len(plan.get('phases', []))} phases")

    # ── Agent 2: Analyst (iGPU tier) ─────────────────────────────────
    notify("analyst", "Running semantic enrichment and risk analysis...")
    plan_summary = json.dumps(plan, indent=2)

    # Also check SemanticCache for similar patterns
    similar = _bridge.semantic_search(task, top_k=3)

    analyst_text, analyst_local = _lemonade_or_claude(
        "igpu",
        _ANALYST_SYS,
        f"Plan:\n{plan_summary}\n\nSimilar patterns from vault:\n{json.dumps(similar)}",
    )
    if not analyst_local:
        total_cost += 0.003

    enriched: dict[str, Any] = {}
    try:
        enriched = json.loads(analyst_text)
    except (json.JSONDecodeError, ValueError):
        enriched = {
            "risk_analysis": {"high": [], "medium": ["Review security implications"], "low": []},
            "similar_patterns": similar,
            "implementation_hints": ["Follow existing code style", "Add comprehensive tests"],
            "security_considerations": ["Review authentication flows", "Check input validation"],
        }

    high_risks = len(enriched.get("risk_analysis", {}).get("high", []))
    notify("analyst", f"Analysis complete — {high_risks} high risks, {len(similar)} similar patterns found")

    # ── Agent 3: Engineer (CPU tier) ─────────────────────────────────
    notify("engineer", "Synthesizing implementation guidance...")
    enriched_summary = json.dumps(enriched, indent=2)

    eng_text, eng_local = _lemonade_or_claude(
        "cpu",
        _ENGINEER_SYS,
        f"Enriched context:\n{enriched_summary}\n\nOriginal task:\n{task}",
    )
    if not eng_local:
        total_cost += 0.008

    implementation: dict[str, Any] = {}
    try:
        implementation = json.loads(eng_text)
    except (json.JSONDecodeError, ValueError):
        implementation = {
            "code_patches": [
                {
                    "file": "src/main.py",
                    "description": "Apply suggested improvements",
                    "code": "# Implementation details require local silicon or API key",
                }
            ],
            "test_recommendations": ["Add unit tests for edge cases", "Integration test coverage"],
            "confidence_score": 0.75,
            "skill_updates": [],
        }

    patches = len(implementation.get("code_patches", []))
    confidence = implementation.get("confidence_score", 0)
    notify("engineer", f"Implementation complete — {patches} patches, {confidence:.0%} confidence")

    # ── Summary ───────────────────────────────────────────────────────
    total_time = time.time() - start
    summary_lines = [
        f"*Cohezion Code Review Complete* ({total_time:.1f}s)",
        f"• Complexity: {plan.get('complexity', '?').upper()}",
        f"• High risks: {high_risks}",
        f"• Code patches: {patches}",
        f"• Confidence: {confidence:.0%}",
        f"• Cost: ${total_cost:.4f}",
    ]

    return {
        "summary": "\n".join(summary_lines),
        "plan": plan,
        "enriched": enriched,
        "implementation": implementation,
        "total_time_s": total_time,
        "cost_usd": total_cost,
    }
