"""AnalystAgent — iGPU-tier semantic enrichment.

UiPath Maestro coded agent. Reads the 'plan' artifact from the case,
enriches it with semantic context from Cohezion's SemanticCache (FLUME VAE
256D embeddings), performs risk analysis, and posts 'enriched_context'.
Transitions case: PLANNING → ANALYSIS.

Inference preference: Cohezion iGPU (deepseek-r1-0528-8b-FLM, ~200ms, $0)
Fallback: Anthropic claude-sonnet-4-5
"""

import json
import os
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.uipath_client import UiPathMaestroClient
    from shared.cohezion_bridge import CohezionBridge, LemonadeClient

try:
    from uipath import activity as uipath_activity  # type: ignore[import-untyped]
except ImportError:
    def uipath_activity(f):  # type: ignore[misc]
        return f

import anthropic


_SYSTEM_PROMPT = """You are the Analyst — the second agent in a Cohezion Enterprise Code Review pipeline.

You receive a task plan and must produce a semantic enrichment that helps the Engineer implement it.

Respond ONLY with a valid JSON object:
{
  "enriched_context": "Rich context paragraph synthesizing the task and any known patterns",
  "risk_analysis": {
    "high": ["Critical risk: ...", ...],
    "medium": ["Moderate risk: ...", ...],
    "low": ["Minor risk: ...", ...]
  },
  "similar_patterns": [
    {"pattern": "Description of similar past pattern", "relevance": "Why it applies"}
  ],
  "implementation_hints": [
    "Concrete hint 1 for the engineer",
    "Concrete hint 2",
    ...
  ],
  "security_checklist": ["Item 1", "Item 2", ...]
}

For security-sensitive tasks (OAuth, auth, tokens, encryption), populate security_checklist with 4-6 items.
Similar patterns: draw on common enterprise patterns (PKCE, rate limiting, circuit breakers, etc).
Implementation hints: 3-5 actionable, specific, technical hints.
"""


class AnalystAgent:
    """Semantic enrichment agent using Cohezion iGPU tier and FLUME VAE.

    Reads plan from Maestro case, performs SemanticCache lookup for similar
    patterns from the knowledge vault, then enriches with LLM analysis.
    """

    AGENT_ID = "cohezion-analyst"

    def __init__(self, maestro: "UiPathMaestroClient", bridge: "CohezionBridge") -> None:
        self._maestro = maestro
        self._bridge = bridge
        self._client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    def run(self, case_id: str) -> dict:
        """Enrich plan with semantic context and risk analysis.

        Reads the 'plan' artifact from the Maestro case, searches the
        Cohezion knowledge vault for similar patterns via FLUME VAE embeddings,
        then produces enriched context for the Engineer.

        Args:
            case_id: Active Maestro case ID.

        Returns:
            Enriched context dict with risk_analysis, similar_patterns, etc.
        """
        plan = self._maestro.get_artifact(case_id, "plan")
        if plan is None:
            return {"error": "No 'plan' artifact found in case", "case_id": case_id}

        self._maestro.update_case_status(case_id, "ANALYSIS")

        task_summary = plan.get("task_summary", "Unknown task")
        risk_flags = plan.get("risk_flags", [])

        # SemanticCache lookup — FLUME VAE 256D embeddings
        similar_patterns = self._bridge.semantic_search(task_summary, top_k=3)
        cache_stats = self._bridge.get_cache_stats()
        flume_encoded = self._bridge.cohezion_available

        # Attempt iGPU tier first
        enriched = self._run_igpu(plan, similar_patterns)
        igpu_used = enriched is not None

        if not enriched:
            enriched = self._run_cloud(plan, similar_patterns)

        # Merge SemanticCache findings into enriched context
        if similar_patterns and not enriched.get("similar_patterns"):
            enriched["similar_patterns"] = [
                {"pattern": p["pattern"], "relevance": f"Similarity: {p['similarity']:.0%}"}
                for p in similar_patterns
            ]

        cache_hit_rate = cache_stats.get("combined_hit_rate", 0.0)

        enriched["cache_hit_rate"] = cache_hit_rate
        enriched["cohezion_flume_encoded"] = flume_encoded
        enriched["cohezion_igpu_used"] = igpu_used
        enriched["case_id"] = case_id
        enriched["agent_id"] = self.AGENT_ID
        enriched["timestamp"] = time.time()
        enriched["risk_flags_from_plan"] = risk_flags

        self._maestro.post_artifact(case_id, "enriched_context", enriched)
        return enriched

    def _run_igpu(self, plan: dict, similar_patterns: list) -> dict | None:
        """Try local inference ($0): dedicated iGPU tier, then the already-loaded OMNI
        model on the :13305 router (dedicated ports often down in the router-centric
        topology -- omni router is what actually serves; OOM-safe, already-loaded only)."""
        from shared.cohezion_bridge import CohezionBridge, LemonadeClient  # noqa: PLC0415

        patterns_text = ""
        if similar_patterns:
            patterns_text = "\n".join(
                f"- {p['pattern']} (similarity: {p.get('similarity', 0):.0%})"
                for p in similar_patterns
            )

        prompt = (
            f"Analyze this enterprise software task and produce enriched context for implementation.\n\n"
            f"Task: {plan.get('task_summary', '')}\n"
            f"Complexity: {plan.get('complexity', 'medium')}\n"
            f"Phases: {', '.join(plan.get('phases', []))}\n"
            f"Risk flags: {', '.join(plan.get('risk_flags', []))}\n"
            f"Similar patterns found:\n{patterns_text or 'None'}\n\n"
            f"Respond with JSON: {{\"enriched_context\": \"...\", \"risk_analysis\": "
            f"{{\"high\": [...], \"medium\": [...], \"low\": [...]}}, "
            f"\"similar_patterns\": [...], \"implementation_hints\": [...], "
            f"\"security_checklist\": [...]}}"
        )

        igpu = LemonadeClient("igpu")
        if igpu.is_available():
            impl = _parse_json(igpu.complete(prompt, max_tokens=1024, temperature=0.2))
            if impl:
                return impl

        text, _backend = CohezionBridge().complete_omni(prompt, max_tokens=1024, temperature=0.2)
        if text and text.strip():
            return _parse_json(text)
        return None

    def _run_cloud(self, plan: dict, similar_patterns: list) -> dict:
        """Fall back to Anthropic claude-sonnet-4-5."""
        patterns_text = ""
        if similar_patterns:
            patterns_text = "\n".join(
                f"- {p['pattern']} (similarity: {p.get('similarity', 0):.0%})"
                for p in similar_patterns
            )

        user_content = (
            f"Analyze and enrich this enterprise task:\n\n"
            f"Task summary: {plan.get('task_summary', '')}\n"
            f"Complexity: {plan.get('complexity', 'medium')}\n"
            f"Planned phases:\n" + "\n".join(f"  {p}" for p in plan.get("phases", [])) + "\n"
            f"Risk flags: {', '.join(plan.get('risk_flags', [])) or 'None identified'}\n\n"
            f"Similar patterns from Cohezion knowledge vault:\n{patterns_text or 'None (cold start)'}\n"
        )

        msg = self._client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        raw = msg.content[0].text if msg.content else "{}"
        enriched = _parse_json(raw)
        if not enriched:
            enriched = {
                "enriched_context": f"Analysis of: {plan.get('task_summary', 'task')}",
                "risk_analysis": {"high": [], "medium": [], "low": []},
                "similar_patterns": [],
                "implementation_hints": [
                    "Review existing authentication flow before modifying",
                    "Add comprehensive test coverage for edge cases",
                    "Validate against security standards checklist",
                ],
                "security_checklist": [],
            }
        return enriched


# ─── UiPath coded agent entrypoint ───────────────────────────────────────────

@uipath_activity
def run_analyst(case_id: str) -> dict:
    """UiPath Maestro coded agent entrypoint for AnalystAgent.

    Invoked by Maestro via REST after OrchestratorAgent completes.
    Input JSON: {"case_id": "..."}. Returns enriched_context dict.
    """
    from shared.uipath_client import UiPathMaestroClient  # noqa: PLC0415
    from shared.cohezion_bridge import CohezionBridge  # noqa: PLC0415
    maestro = UiPathMaestroClient()
    bridge = CohezionBridge()
    agent = AnalystAgent(maestro, bridge)
    return agent.run(case_id)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_json(text: str) -> dict | None:
    text = text.strip()
    for start, end in [("```json", "```"), ("```", "```")]:
        if text.startswith(start):
            inner = text[len(start):]
            if end in inner:
                inner = inner[:inner.rfind(end)]
            try:
                return json.loads(inner.strip())
            except (json.JSONDecodeError, ValueError):
                pass
    try:
        brace = text.find("{")
        if brace >= 0:
            return json.loads(text[brace:text.rfind("}") + 1])
    except (json.JSONDecodeError, ValueError):
        pass
    return None
