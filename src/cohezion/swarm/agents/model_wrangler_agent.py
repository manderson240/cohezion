"""
Model Wrangler Specialist Agent.
 Fleet Optimizer & SLM Scout for the Cohezion local environment.
 Orchestrates model rosters, VRAM budgeting, and SOTA scouting.
"""

import asyncio
import json
import logging
import subprocess
from typing import Any

from cohezion.reliability.monitor import ResourceMonitor
from cohezion.swarm.agents.base import AgentResponse, BaseAgent

logger = logging.getLogger(__name__)

# 2026 Compatible "Tip of the Spear" SLM Roster (12GB VRAM optimized)
SLM_ROSTER = {
    "reasoning": "deepseek-r1:8b",  # Complex logic, chain-of-thought
    "coding": "qwen2.5-coder:7b",  # SOTA coding specialist
    "routing": "phi4:mini",  # 3.8B - Fast instruction following & routing
    "creative": "mistral-nemo:12b",  # Nuance (if VRAM permits, else falls back)
    "vision": "minicpm-v:latest",  # Multimodal capability
}

# Hierarchical Urgency (1=Critical, 4=Low)
PRIORITY_MAP = {
    "critical": 1,  # Strategist, Controller (cannot be stalled)
    "high": 2,  # Workflow specific agents
    "medium": 3,  # Standard analysts (Default)
    "low": 4,  # Background tasks, Scouts
}


class ModelWrangler(BaseAgent):
    """
    Expert agent for Ollama model roster management.
    Implements VRAM-aware scheduling, role-based model serving,
    and proactively scouts for cost-effective SLMs.
    """

    def __init__(self, config: Any = None):
        super().__init__(
            model_name=SLM_ROSTER["routing"],  # Default to the fast router
            config=config,
        )
        self.monitor = ResourceMonitor()
        self.monitor.register_coordinator(self)
        self.quantization_target = "Q5_K_M"
        self.roster = SLM_ROSTER
        self.priority_map = PRIORITY_MAP
        self._initialized = True

    async def prepare_resources_for_priority(self, priority: int):
        """
        Proactively evict lower-priority models if VRAM is tight.
        Used before launching high-priority reasoning tasks.
        """
        vitals = self.monitor.get_vitals()
        vram = vitals.get("vram_percent", 0.0)

        # Thresholds for proactive eviction
        # If we are a High/Critical task (Priority <= 2) and VRAM > 75%
        if priority <= 2 and vram > 75:
            logger.warning(
                f"Proactive VRAM Recovery starting (Priority: {priority}, VRAM: {vram:.1f}%)"
            )

            # Use Ollama API to find models to evict
            try:
                process = await asyncio.create_subprocess_exec(
                    "curl",
                    "-s",
                    "http://localhost:11434/api/ps",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await process.communicate()
                if stdout:
                    data = json.loads(stdout)
                    running_models = data.get("models", [])

                    for model in running_models:
                        name = model.get("name")
                        # Don't evict the router or itself unless desperate
                        if name in [SLM_ROSTER["routing"], self.model_name]:
                            continue

                        # In a more advanced version, we'd check the running agent's priority.
                        # For now, we evict non-essential models to make space for the priority call.
                        logger.info(f"Evicting model to make space: {name}")
                        await self.monitor.unload_model(name)
            except Exception as e:
                logger.error(f"Failed during proactive VRAM recovery: {e}")

    async def get_fleet_recommendation(self) -> dict[str, Any]:
        """
        Analyze current resource vitals and suggest model unloading or bit-depth reductions.
        """
        vitals = self.monitor.get_vitals()
        vram = vitals.get("vram_percent", 0.0)

        if vram > 90:
            return {
                "action": "unload_large_models",
                "reason": f"VRAM pressure critical: {vram}%",
                "target_bit_depth": "4-bit",
                "recommendation": "Switch to phi4:mini for all non-critical tasks",
            }

        return {"action": "maintain_current", "vram": vram}

    async def deploy_roster(self) -> dict[str, str]:
        """
        Check which models from the roster are missing and attempt to pull them.
        Returns a status report.
        """
        report = {}
        try:
            # list existing models
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            existing_output = result.stdout.lower()

            for role, model in self.roster.items():
                # Clean tag for flexible matching (e.g. "deepseek-r1:8b" -> "deepseek-r1")
                model_base = model.split(":")[0]

                if model_base in existing_output or model in existing_output:
                    report[role] = "Available"
                else:
                    logger.info(f"Pulling missing model for {role}: {model}")
                    # Note: In a real agentic loop, we might want to spawn a background proc
                    # For now, we flag it.
                    # subprocess.Popen(["ollama", "pull", model])
                    report[role] = "Missing - Pull Requested"

        except Exception as e:
            logger.error(f"Failed to check model roster: {e}")
            return {"error": str(e)}

        return report

    def get_model_for_role(self, role: str) -> str:
        """
        Returns the best available model for a specific cognitive role.
        """
        return self.roster.get(role, self.roster["routing"])

    async def scout_sota_slms(self) -> str:
        """
        Delegate a research task to identify high-performing small models.
        """
        # Updated prompt for 2026 context
        prompt = """
        ACT as an AI Research Scout.
        OBJECTIVE: Identify the top 3 SOTA Small Language Models (SLMs) under 10B parameters released in late 2025/2026.
        CRITERIA:
        1. Must run on <12GB VRAM (optimally Q5_K_M).
        2. Excel in either 'Reasoning' (Chain of Thought) or 'Python Coding'.
        3. 'Punch above their weight' compared to 70B+ models.

        FORMAT: specific model tags (e.g., 'deepseek-r1:8b'), parameter count, and primary strength.
        """
        response = await self._call_ollama(prompt)
        return response

    async def process(self, context: str, **kwargs: Any) -> AgentResponse:
        """
        Process Model Wrangler requests: optimize fleet, scout SLMs, check roster, or assign roles.
        """
        context_lower = context.lower()

        if "optimize" in context_lower or "vram" in context_lower:
            recommendation = await self.get_fleet_recommendation()
            return AgentResponse(str(recommendation), action="fleet_optimization")

        elif "roster" in context_lower or "deploy" in context_lower:
            status = await self.deploy_roster()
            return AgentResponse(
                f"Roster Status: {json.dumps(status, indent=2)}", action="roster_check"
            )

        elif "scout" in context_lower or "new models" in context_lower:
            scout_report = await self.scout_sota_slms()
            return AgentResponse(scout_report, action="slm_scouting")

        elif "role" in context_lower:
            # extracting requested role strictly would require parsing,
            # simplest approach is to dump the roster map
            return AgentResponse(
                f"Active Roster Mapping: {json.dumps(self.roster, indent=2)}",
                action="role_lookup",
            )

        return AgentResponse("Model Wrangler Monitoring Active", status="active")
