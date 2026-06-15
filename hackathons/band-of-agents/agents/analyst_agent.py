"""AnalystAgent — Semantic analysis and context enrichment.

Inference tier: iGPU (RDNA 3.5 / ROCWMMA, ~200ms, deepseek-r1-0528-8b-FLM)
Band role: reads 'plan' artifact, enriches it, posts 'enriched_context' artifact.

The Analyst uses Cohezion's SemanticCache (FLUME VAE 256D embeddings, L1/L2/L3)
to surface similar past patterns from the knowledge vault, then uses claude-sonnet
to synthesize risk analysis and implementation hints.
"""

import json
import sys
from pathlib import Path

from anthropic import Anthropic


_HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_HERE))

from shared.band_client import BandClient  # noqa: E402
from shared.cohezion_bridge import CohezionBridge  # noqa: E402


_PROMPT_FILE = _HERE / "prompts" / "analyst.md"


class AnalystAgent:
    """Semantic analyst and context enricher.

    Reads the Orchestrator's plan from Band, runs it through Cohezion's
    SemanticCache to find similar patterns in the knowledge vault, performs
    risk analysis, and posts enriched context back to Band for the Engineer.

    Args:
        band: BandClient instance.
        bridge: Optional CohezionBridge for semantic cache and FLUME integration.
    """

    AGENT_ID = "cohezion-analyst"
    MODEL = "claude-sonnet-4-5"  # Semantic reasoning — iGPU tier equivalent

    def __init__(self, band: BandClient, bridge: CohezionBridge | None = None):
        self.band = band
        self.bridge = bridge or CohezionBridge()
        self.client = Anthropic()
        self._system_prompt = self._load_system_prompt()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> dict:
        """Read plan from Band, enrich with semantic context, post back.

        Returns:
            The enriched_context dict posted to Band, or an error dict.
        """
        print("\n[Analyst] Reading plan from Band channel...")

        # Step 1: Read Orchestrator's plan from Band
        plan = self.band.get_artifact("plan")
        if plan is None:
            print("[Analyst] ERROR: No plan found in Band channel — is Orchestrator done?")
            return {"error": "no_plan_in_band"}

        task_id = plan.get("task_id", "unknown")
        print(f"[Analyst] Got plan for task_id={task_id}, complexity={plan.get('complexity')}")

        # Step 2: Semantic similarity search via Cohezion SemanticCache
        similar_patterns = self._semantic_search(plan)
        cache_stats = self.bridge.get_cache_stats()

        # Step 3: LLM-powered risk analysis and enrichment
        enriched = self._enrich(plan, similar_patterns)

        # Step 4: Add Cohezion metadata
        enriched["task_id"] = task_id
        enriched["similar_patterns"] = similar_patterns
        enriched["cache_hit_rate"] = cache_stats.get("combined_hit_rate", 0.0)
        enriched["semantic_cache_used"] = self.bridge.cohezion_available
        enriched["cohezion_flume_encoded"] = self.bridge.cohezion_available
        enriched["cohezion_status"] = self.bridge.get_status()

        # Step 5: Post enriched context to Band
        success = self.band.post_artifact(self.AGENT_ID, "enriched_context", enriched)
        if not success:
            print("[Analyst] WARNING: Band post failed")

        high_risks = len(enriched.get("risk_analysis", {}).get("high", []))
        hints = len(enriched.get("implementation_hints", []))
        patterns = len(similar_patterns)
        print(
            f"[Analyst] Enriched context posted — "
            f"patterns={patterns}, high_risks={high_risks}, hints={hints}, "
            f"flume_encoded={enriched['cohezion_flume_encoded']}"
        )
        return enriched

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _semantic_search(self, plan: dict) -> list[dict]:
        """Search Cohezion vault for similar patterns.

        Builds a natural language query from the plan and runs it through
        SemanticCache (FLUME VAE 256D, L2 cosine, threshold=0.58).
        """
        if not self.bridge.cohezion_available:
            print("[Analyst] Cohezion SemanticCache unavailable — skipping vault search")
            return []

        # Build search query from plan content
        query_parts = []
        for phase in plan.get("phases", []):
            query_parts.append(phase.get("description", ""))
        query_parts.extend(plan.get("risk_flags", []))
        query = " ".join(query_parts[:3])  # keep query focused

        if not query.strip():
            query = f"enterprise code review: {plan.get('complexity', 'medium')} complexity"

        patterns = self.bridge.semantic_search(query, top_k=3)
        if patterns:
            print(f"[Analyst] SemanticCache: found {len(patterns)} similar patterns")
        else:
            print("[Analyst] SemanticCache: no similar patterns found (cache may be cold)")
        return patterns

    def _enrich(self, plan: dict, similar_patterns: list[dict]) -> dict:
        """Run LLM enrichment pass."""
        patterns_text = ""
        if similar_patterns:
            patterns_text = "\n\nSimilar patterns from Cohezion vault:\n" + "\n".join(
                f"- [{p['similarity']:.2f}] {p['pattern']}" for p in similar_patterns
            )

        user_message = (
            f"Analyze this implementation plan and provide enriched context:\n\n"
            f"PLAN:\n{json.dumps(plan, indent=2)}"
            f"{patterns_text}"
            f"\n\nRespond with ONLY valid JSON matching your system prompt schema."
        )

        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=2048,
            system=self._system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return self._fallback_enrichment(plan)

    def _fallback_enrichment(self, plan: dict) -> dict:
        """Minimal enrichment when LLM output can't be parsed."""
        return {
            "risk_analysis": {
                "high": plan.get("risk_flags", []),
                "medium": [],
                "low": [],
            },
            "implementation_hints": [
                "Review plan phases carefully before implementation",
                "Consider writing tests first (TDD approach)",
            ],
            "note": "enrichment degraded — LLM output parse failure",
        }

    def _load_system_prompt(self) -> str:
        if _PROMPT_FILE.exists():
            return _PROMPT_FILE.read_text()
        return (
            "You are a senior staff engineer. Analyze the implementation plan and return JSON with: "
            "risk_analysis (dict with high/medium/low lists), "
            "implementation_hints (list of strings). "
            "Be specific — name libraries, version constraints, and edge cases."
        )
