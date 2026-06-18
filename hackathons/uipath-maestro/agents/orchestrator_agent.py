"""OrchestratorAgent — NPU-tier task classification and planning.

UiPath Maestro coded agent. Receives a task, classifies complexity,
decomposes into phases, flags risks, and posts a typed 'plan' artifact
to the Maestro case. Transitions case status: OPEN → PLANNING.

Inference preference: Cohezion NPU (llama3.2-1b-FLM, 42 TPS, $0)
Fallback: Anthropic claude-haiku-4-5
"""

import json
import os
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.uipath_client import UiPathMaestroClient
    from shared.cohezion_bridge import CohezionBridge, LemonadeClient

# Graceful UiPath activity decorator — no-op when uipath package not installed
try:
    from uipath import activity as uipath_activity  # type: ignore[import-untyped]
except ImportError:
    def uipath_activity(f):  # type: ignore[misc]
        return f

import anthropic


_SYSTEM_PROMPT = """You are the Orchestrator — the first agent in a Cohezion Enterprise Code Review pipeline.

Your role: receive a user task, classify its complexity, decompose it into actionable phases, and identify risk flags.

Respond ONLY with a valid JSON object. No prose, no markdown fences. The JSON must have exactly these keys:
{
  "task_summary": "One-sentence summary of the task",
  "complexity": "low" | "medium" | "high",
  "phases": ["Phase 1: ...", "Phase 2: ...", ...],
  "risk_flags": ["Risk: ...", ...],
  "recommended_tier": "npu" | "igpu" | "cpu",
  "estimated_effort": "X hours"
}

Guidelines:
- complexity "high" when: security-sensitive, architectural, >500 LOC changed, multi-service
- complexity "medium" when: feature addition, 100-500 LOC, clear scope
- complexity "low" when: bug fix, docs, config, <100 LOC
- phases: 3-6 concrete steps, each starting with a verb
- risk_flags: security, performance, compatibility, compliance concerns only — omit if none
- recommended_tier: "npu" for classification tasks, "igpu" for generation, "cpu" for reasoning
"""


class OrchestratorAgent:
    """Plans and classifies user tasks using Cohezion NPU tier.

    Runs first in the pipeline. Posts 'plan' artifact to the Maestro case
    so downstream agents can read it.
    """

    AGENT_ID = "cohezion-orchestrator"

    def __init__(self, maestro: "UiPathMaestroClient", bridge: "CohezionBridge") -> None:
        self._maestro = maestro
        self._bridge = bridge
        self._client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    def run(self, case_id: str, user_task: str) -> dict:
        """Classify task, build plan, post to Maestro case.

        Args:
            case_id: Active Maestro case ID.
            user_task: Free-text task description.

        Returns:
            Plan dict with complexity, phases, risk_flags, etc.
        """
        self._maestro.update_case_status(case_id, "PLANNING")

        # Attempt NPU tier first (Cohezion LemonadeClient)
        plan = self._run_npu(user_task)
        npu_used = plan is not None

        if not plan:
            plan = self._run_cloud(user_task)

        plan["cohezion_npu_used"] = npu_used
        plan["case_id"] = case_id
        plan["agent_id"] = self.AGENT_ID
        plan["timestamp"] = time.time()

        self._maestro.post_artifact(case_id, "plan", plan)
        return plan

    def _run_npu(self, task: str) -> dict | None:
        """Try local inference ($0): dedicated NPU tier, then the already-loaded OMNI
        model on the :13305 router (OOM-safe, already-loaded only, never auto-loads)."""
        from shared.cohezion_bridge import CohezionBridge, LemonadeClient  # noqa: PLC0415

        prompt = (
            f"You are an enterprise task orchestrator. Analyze this task and respond with JSON only.\n\n"
            f"Task: {task}\n\n"
            f"Respond with JSON: {{\"task_summary\": \"...\", \"complexity\": \"low|medium|high\", "
            f"\"phases\": [...], \"risk_flags\": [...], \"recommended_tier\": \"npu|igpu|cpu\", "
            f"\"estimated_effort\": \"X hours\"}}"
        )

        npu = LemonadeClient("npu")
        if npu.is_available():
            impl = _parse_json(npu.complete(prompt, max_tokens=512, temperature=0.1))
            if impl:
                return impl

        text, _backend = CohezionBridge().complete_omni(prompt, max_tokens=512, temperature=0.1)
        if text and text.strip():
            return _parse_json(text)
        return None

    def _run_cloud(self, task: str) -> dict:
        """Fall back to Anthropic claude-haiku-4-5."""
        msg = self._client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Task to analyze:\n\n{task}"}],
        )
        raw = msg.content[0].text if msg.content else "{}"
        plan = _parse_json(raw)
        if not plan:
            # Structured fallback
            plan = {
                "task_summary": task[:200],
                "complexity": "medium",
                "phases": [
                    "Phase 1: Analyze requirements and scope",
                    "Phase 2: Review existing implementation",
                    "Phase 3: Identify risks and dependencies",
                    "Phase 4: Synthesize recommendations",
                ],
                "risk_flags": [],
                "recommended_tier": "igpu",
                "estimated_effort": "2-4 hours",
            }
        return plan


# ─── UiPath coded agent entrypoint ───────────────────────────────────────────

@uipath_activity
def run_orchestrator(task: str, case_id: str) -> dict:
    """UiPath Maestro coded agent entrypoint for OrchestratorAgent.

    Invoked by Maestro via REST. Input JSON: {"task": "...", "case_id": "..."}.
    Returns plan dict posted to the case.
    """
    from shared.uipath_client import UiPathMaestroClient  # noqa: PLC0415
    from shared.cohezion_bridge import CohezionBridge  # noqa: PLC0415
    maestro = UiPathMaestroClient()
    bridge = CohezionBridge()
    agent = OrchestratorAgent(maestro, bridge)
    return agent.run(case_id, task)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_json(text: str) -> dict | None:
    """Extract JSON from model output, handling markdown fences."""
    text = text.strip()
    for start, end in [("```json", "```"), ("```", "```"), ("{", None)]:
        if text.startswith(start):
            inner = text[len(start):]
            if end:
                inner = inner[:inner.rfind(end)] if end in inner else inner
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
