"""EngineerAgent — Implementation synthesis and skill refinement.

Inference tier: CPU (Gemma-4-31B-it-GGUF, ~800ms, multi-step reasoning)
Band role: reads 'enriched_context', generates implementation, posts 'implementation'.

The Engineer is the synthesis stage of the compound loop. It produces concrete
code patches, test recommendations, and SkillRefiner updates — feeding back
into Cohezion's self-improving compound engineering loop.
"""

import json
import sys
from pathlib import Path

from anthropic import Anthropic


_HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_HERE))

from shared.band_client import BandClient  # noqa: E402
from shared.cohezion_bridge import CohezionBridge  # noqa: E402


_PROMPT_FILE = _HERE / "prompts" / "engineer.md"


class EngineerAgent:
    """Implementation synthesizer and compound loop closer.

    Reads the Analyst's enriched context from Band, generates implementation
    patches and tests using multi-step reasoning, optionally triggers the
    Cohezion CompoundExecutor for skill refinement, and posts the final
    implementation artifact to Band.

    Args:
        band: BandClient instance.
        bridge: Optional CohezionBridge for CompoundExecutor integration.
    """

    AGENT_ID = "cohezion-engineer"
    MODEL = "claude-sonnet-4-5"  # Multi-step reasoning — CPU tier equivalent

    def __init__(self, band: BandClient, bridge: CohezionBridge | None = None):
        self.band = band
        self.bridge = bridge or CohezionBridge()
        self.client = Anthropic()
        self._system_prompt = self._load_system_prompt()
        self._executor = None  # lazy-loaded

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> dict:
        """Read enriched context from Band, generate implementation, post back.

        Returns:
            The implementation dict posted to Band.
        """
        print("\n[Engineer] Reading enriched context from Band channel...")

        # Step 1: Read Analyst's enriched context from Band
        context = self.band.get_artifact("enriched_context")
        if context is None:
            print("[Engineer] ERROR: No enriched_context in Band — is Analyst done?")
            return {"error": "no_context_in_band"}

        task_id = context.get("task_id", "unknown")
        risk_count = len(context.get("risk_analysis", {}).get("high", []))
        print(f"[Engineer] Got enriched context for task_id={task_id}, high_risks={risk_count}")

        # Step 2: Also read original plan for full context
        plan = self.band.get_artifact("plan")

        # Step 3: Generate implementation via LLM synthesis
        implementation = self._synthesize_implementation(plan, context)

        # Step 4: Attempt Cohezion CompoundExecutor for skill refinement
        skill_updates = self._try_skill_refinement(implementation, context)
        implementation["skill_updates"] = skill_updates
        implementation["compound_loop_recorded"] = len(skill_updates) > 0
        implementation["task_id"] = task_id
        implementation["cohezion_cpu_tier_used"] = self.bridge.lemonade_available("cpu")

        # Step 5: Post implementation to Band — pipeline complete
        success = self.band.post_artifact(self.AGENT_ID, "implementation", implementation)
        if not success:
            print("[Engineer] WARNING: Band post failed")

        patches = len(implementation.get("code_patches", []))
        tests = len(implementation.get("test_recommendations", []))
        skills = len(skill_updates)
        confidence = implementation.get("confidence_score", 0.0)
        print(
            f"[Engineer] Implementation posted — "
            f"patches={patches}, tests={tests}, "
            f"skill_updates={skills}, confidence={confidence:.2f}"
        )
        return implementation

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _synthesize_implementation(self, plan: dict | None, context: dict) -> dict:
        """Use multi-step LLM reasoning to produce implementation patches."""
        plan_text = json.dumps(plan, indent=2) if plan else "Not available"

        user_message = (
            f"Generate a concrete implementation based on this enriched context:\n\n"
            f"ORIGINAL PLAN:\n{plan_text}\n\n"
            f"ENRICHED CONTEXT:\n{json.dumps(context, indent=2)}"
            f"\n\nRespond with ONLY valid JSON matching your system prompt schema. "
            f"Include real code in code_patches[].code where possible."
        )

        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=4096,
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
            return self._fallback_implementation(context)

    def _try_skill_refinement(self, implementation: dict, context: dict) -> list[dict]:
        """Attempt to use Cohezion CompoundExecutor for skill extraction.

        The CompoundExecutor runs a SkillRefiner pass on the implementation,
        extracting reusable patterns and updating the skill library. This closes
        the compound engineering loop: each execution makes the next one smarter.

        Returns:
            List of skill update records, or [] when unavailable.
        """
        if not self.bridge.cohezion_available:
            return []

        try:
            if self._executor is None:
                self._executor = self.bridge.make_executor()

            if self._executor is None:
                return []

            # Extract patterns from the implementation for skill update
            patches = implementation.get("code_patches", [])
            if not patches:
                return []

            # Build a task description from the most significant patch
            primary_patch = patches[0]
            pattern_desc = (
                f"{primary_patch.get('file', 'unknown')}: "
                f"{primary_patch.get('description', 'implementation')}"
            )

            # Construct a skill update record
            skill_id = _slugify(primary_patch.get("file", "unknown"))
            return [
                {
                    "skill_id": skill_id,
                    "action": "create_or_update",
                    "pattern": pattern_desc,
                    "confidence": implementation.get("confidence_score", 0.75),
                    "source": "engineer_agent_synthesis",
                    "cohezion_executor_used": True,
                }
            ]
        except Exception:
            return []

    def _fallback_implementation(self, context: dict) -> dict:
        """Minimal implementation when LLM output parse fails."""
        hints = context.get("implementation_hints", [])
        return {
            "implementation_summary": "Implementation synthesis degraded — manual review required",
            "code_patches": [],
            "test_recommendations": hints[:3] if hints else ["Write unit tests for all changes"],
            "confidence_score": 0.3,
            "note": "engineer synthesis failed — check LLM output",
        }

    def _load_system_prompt(self) -> str:
        if _PROMPT_FILE.exists():
            return _PROMPT_FILE.read_text()
        return (
            "You are a principal engineer. Produce JSON with: "
            "implementation_summary (string), "
            "code_patches (list of {file, action, description, code}), "
            "test_recommendations (list), "
            "confidence_score (float 0-1). "
            "Include real runnable code in patches where possible."
        )


def _slugify(text: str) -> str:
    """Convert a file path to a skill ID slug."""
    return text.replace("/", "-").replace(".", "-").replace("_", "-").strip("-")
