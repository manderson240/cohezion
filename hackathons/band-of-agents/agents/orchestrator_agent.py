"""OrchestratorAgent — Task classification and structured planning.

Inference tier: NPU (fast, $0, 42 TPS via llama3.2-1b-FLM)
Band role: entry point — reads user task, posts structured plan artifact.

The Orchestrator uses claude-haiku-4-5 (mirrors Cohezion's NPU-tier routing
for classification tasks: short_categorical output, sub-500µs on-device).
"""

import json
import os
import sys
import uuid
from pathlib import Path

from anthropic import Anthropic

# Ensure shared/ and Cohezion src are importable
_HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_HERE))

from shared.band_client import BandClient  # noqa: E402
from shared.cohezion_bridge import CohezionBridge  # noqa: E402


_PROMPT_FILE = _HERE / "prompts" / "orchestrator.md"


class OrchestratorAgent:
    """Task classifier and plan generator.

    Reads a user task description, classifies its complexity using Cohezion's
    NPU-tier task classifier (when available), then uses claude-haiku-4-5 to
    decompose it into a structured plan artifact that it posts to Band.

    Args:
        band: BandClient instance (shared with other agents).
        bridge: Optional CohezionBridge for local inference integration.
    """

    AGENT_ID = "cohezion-orchestrator"
    MODEL = "claude-haiku-4-5"  # Fast model — NPU tier equivalent

    def __init__(self, band: BandClient, bridge: CohezionBridge | None = None):
        self.band = band
        self.bridge = bridge or CohezionBridge()
        self.client = Anthropic()
        self._system_prompt = self._load_system_prompt()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, user_task: str) -> dict:
        """Process a user task: classify, plan, post to Band.

        Args:
            user_task: Free-text task description from the user.

        Returns:
            The plan dict that was posted to Band.
        """
        print(f"\n[Orchestrator] Processing task: {user_task[:80]}...")

        # Step 1: Try Cohezion NPU classification first
        cohezion_class = self.bridge.classify_task(user_task)
        if cohezion_class:
            print(
                f"[Orchestrator] Cohezion NPU classification: "
                f"node={cohezion_class['node']}, "
                f"output_type={cohezion_class['output_type']}"
            )

        # Step 2: Generate structured plan via LLM
        plan = self._generate_plan(user_task, cohezion_class)

        # Step 3: Post plan to Band — this is the coordination moment
        success = self.band.post_artifact(self.AGENT_ID, "plan", plan)
        if not success:
            print("[Orchestrator] WARNING: Band post failed")

        print(
            f"[Orchestrator] Plan posted to Band — "
            f"complexity={plan['complexity']}, "
            f"phases={len(plan['phases'])}, "
            f"risk_flags={len(plan.get('risk_flags', []))}"
        )
        return plan

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _generate_plan(self, user_task: str, cohezion_class: dict | None) -> dict:
        """Call the LLM to generate a structured plan."""
        context_note = ""
        if cohezion_class:
            context_note = (
                f"\n\nCohezion NPU pre-classification: "
                f"routing_tier={cohezion_class['node']}, "
                f"confidence={cohezion_class.get('confidence', 0):.2f}"
            )

        user_message = (
            f"Analyze and create a structured plan for this task:\n\n"
            f"TASK: {user_task}"
            f"{context_note}"
            f"\n\nRespond with ONLY valid JSON matching the schema in your system prompt."
        )

        raw = self._generate(self._system_prompt, user_message, 1024).strip()

        # Extract JSON (handle markdown code fences)
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        try:
            plan = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: construct minimal plan
            plan = self._fallback_plan(user_task)

        # Ensure task_id is set
        plan.setdefault("task_id", str(uuid.uuid4())[:8])
        plan.setdefault("cohezion_npu_used", cohezion_class is not None)
        return plan

    def _fallback_plan(self, user_task: str) -> dict:
        """Minimal plan when JSON parsing fails."""
        return {
            "task_id": str(uuid.uuid4())[:8],
            "complexity": "medium",
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Analysis",
                    "description": f"Analyze requirements: {user_task[:100]}",
                    "files_affected": [],
                    "dependencies": [],
                    "priority": "critical",
                }
            ],
            "estimated_files": [],
            "risk_flags": ["plan generation degraded — review manually"],
            "confidence": 0.5,
            "cohezion_npu_used": False,
        }

    def _generate(self, system: str, user_message: str, max_tokens: int) -> str:
        """Generate local-first ($0 AMD silicon) with cloud fallback.

        COHEZION_LOCAL_FIRST=1 routes to the already-loaded OMNI model (via :13305,
        OOM-safe); empty local output escalates to cloud. Records the serving backend
        in self._last_backend for honest provenance.
        """
        if os.getenv("COHEZION_LOCAL_FIRST", "0") == "1":
            text, backend = self.bridge.complete_omni(
                f"{system}\n\n{user_message}", max_tokens=max_tokens, temperature=0.1,
            )
            if text and text.strip():
                self._last_backend = backend
                return text
        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        self._last_backend = "anthropic-cloud"
        return response.content[0].text

    def _load_system_prompt(self) -> str:
        """Load the orchestrator role prompt from file."""
        if _PROMPT_FILE.exists():
            return _PROMPT_FILE.read_text()
        return (
            "You are an expert systems architect. Analyze the task and produce "
            "a JSON plan with task_id, complexity (low/medium/high), phases (list), "
            "estimated_files (list), risk_flags (list), and confidence (float)."
        )
