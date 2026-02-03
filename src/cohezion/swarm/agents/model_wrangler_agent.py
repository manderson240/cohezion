"""
ASCENDED COHEZION - Model Wrangler Agent v2.0
Fleet Optimizer & SLM Scout with Mode Controller Integration
Manages 13-model multimodal suite with unified memory awareness.
"""

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from cohezion.reliability.monitor import ResourceMonitor
from cohezion.swarm.agents.base import AgentResponse, BaseAgent
from cohezion.swarm.mode_controller import (
    ModeController,
    SystemMode,
    GovernanceMode,
    get_mode_controller,
)

logger = logging.getLogger(__name__)

# ASCENDED COHEZION SLM Roster - 13 Models (Feb 2026 SOTA)
ASCENDED_ROSTER = {
    # Tier 1: Core Language (Always Hot)
    "routing": "phi4:mini",  # 3.8B - Ultra-fast routing
    "reasoning": "deepseek-r1-distill:8b",  # 8B - Chain-of-thought
    "coding": "qwen3-coder:30b",  # 30B - SOTA coding
    # Tier 2: Performance Language (Mode-dependent)
    "advanced_reasoning": "phi4",  # 14B - Tiny Giant
    "generalist": "llama4-scout",  # 15B - GPT-4 level
    "rag_enterprise": "mistral-small-3",  # 22B - 128K context
    # Tier 3: Specialized Language
    "ultra_light": "gemma3:1b",  # 1B - Edge speed
    "vision_language": "gemma3:4b",  # 4B - Multimodal
    "advanced_vision": "gemma3:12b",  # 12B - Complex vision
    # Tier 4: Multimodal Media
    "tts": "pocket-tts",  # 100M - Voice (CPU-based)
    "image_fast": "flux2-klein-4b",  # 4B - Fast images
    "image_quality": "flux2-klein-9b",  # 9B - Quality images
    "video": "wan-2.1-5b",  # 5B - Video generation
    "video_quality": "wan-2.1-14b",  # 14B - Quality video (on-demand)
}

# Mode-optimized priority mappings
MODE_PRIORITY_MAP = {
    SystemMode.CONSERVATIVE: {
        "critical": [
            "phi4:mini",
            "deepseek-r1-distill:8b",
            "qwen3-coder:30b",
            "pocket-tts",
        ],
        "high": [],
        "medium": ["gemma3:1b"],
        "low": [],
    },
    SystemMode.PERFORMANCE: {
        "critical": ["phi4:mini", "deepseek-r1-distill:8b", "qwen3-coder:30b"],
        "high": ["phi4", "llama4-scout", "mistral-small-3"],
        "medium": ["pocket-tts"],
        "low": [],
    },
    SystemMode.IMAGE_WORK: {
        "critical": ["phi4:mini", "qwen3-coder:30b"],
        "high": ["gemma3:4b"],
        "medium": ["flux2-klein-4b", "flux2-klein-9b", "pocket-tts"],
        "low": [],
    },
    SystemMode.VIDEO_WORK: {
        "critical": ["qwen3-coder:30b", "gemma3:4b"],
        "high": ["wan-2.1-5b"],
        "medium": ["pocket-tts"],
        "low": [],
    },
    SystemMode.FULL_MULTIMODAL: {
        "critical": ["phi4", "deepseek-r1-distill:8b", "qwen3-coder:30b"],
        "high": ["llama4-scout", "gemma3:12b"],
        "medium": ["flux2-klein-9b", "wan-2.1-5b", "pocket-tts"],
        "low": [],
    },
}


class ModelWranglerAscended(BaseAgent):
    """
    ASCENDED Model Wrangler - v2.0

    Manages 13-model multimodal suite with:
    - Mode Controller integration (5 dynamic modes)
    - Unified memory awareness (128GB Strix Halo optimized)
    - HIHO stability tracking (0.5 coherence)
    - Automatic/Advisory/Hybrid governance
    - Compound engineering principles
    """

    def __init__(self, config: Any = None, governance_mode: str = "hybrid"):
        super().__init__(
            model_name="phi4:mini",  # Always use fastest router
            config=config,
        )

        # Core components
        self.monitor = ResourceMonitor()
        self.monitor.register_coordinator(self)

        # Mode Controller integration
        self.mode_controller = get_mode_controller(governance_mode)
        self.governance_mode = governance_mode

        # ASCENDED Registry
        self.registry_path = (
            Path(os.environ.get("COHEZION_ROOT", "/home/mike-anderson/dev/cohezion"))
            / "model_registry_ascended.json"
        )

        self.model_data = self._load_ascended_registry()
        self.installed_models: Set[str] = set()
        self._refresh_installed_models()
        self.roster = self._build_ascended_roster()

        # Unified memory tracking
        self.unified_memory_total = 128  # GB - Strix Halo
        self.unified_memory_available = 112  # GB - allocatable to GPU
        self.target_buffer_gb = 20

        # State
        self.active_models: Set[str] = set()
        self.mode_switches = 0
        self._initialized = True

        logger.info("🌌 ASCENDED Model Wrangler initialized")
        logger.info(f"   Governance: {governance_mode}")
        logger.info(f"   Current Mode: {self.mode_controller.current_mode.value}")
        logger.info(f"   Registry: {len(self.model_data.get('models', {}))} models")

    def _load_ascended_registry(self) -> dict:
        """Load ASCENDED model registry"""
        try:
            if not self.registry_path.exists():
                logger.warning(f"ASCENDED registry not found: {self.registry_path}")
                return {}

            content = self.registry_path.read_text()
            lines = content.splitlines()
            clean_lines = [l for l in lines if not l.strip().startswith(("#", "//"))]
            return json.loads("\n".join(clean_lines))
        except Exception as e:
            logger.error(f"Failed to load ASCENDED registry: {e}")
            return {}

    def _build_ascended_roster(self) -> dict:
        """Build roster from ASCENDED registry with verification"""
        roster = {}

        # Get all models from registry
        all_models = {}
        if "models" in self.model_data:
            all_models.update(self.model_data["models"].get("language_models", {}))
            all_models.update(self.model_data["models"].get("multimodal_models", {}))

        # Check installed models
        self._refresh_installed_models()

        # Build role-based roster
        for model_id, model_info in all_models.items():
            specialization = model_info.get("specialization", "")

            # Map specializations to roles
            role_mapping = {
                "ultra_fast_routing": "routing",
                "reasoning": "reasoning",
                "coding": "coding",
                "reasoning_routing": "advanced_reasoning",
                "generalist": "generalist",
                "rag_enterprise": "rag_enterprise",
                "ultra_lightweight": "ultra_light",
                "vision_language": "vision_language",
                "advanced_vision_language": "advanced_vision",
                "text_to_speech": "tts",
                "fast_image_generation": "image_fast",
                "quality_image_generation": "image_quality",
                "video_generation": "video",
                "quality_video_generation": "video_quality",
            }

            role = role_mapping.get(specialization)
            if role:
                if model_id in self.installed_models:
                    roster[role] = model_id
                else:
                    logger.warning(
                        f"Model {model_id} not installed but assigned to {role}"
                    )

        return roster

    def _refresh_installed_models(self):
        """Refresh list of installed Ollama models"""
        try:
            result = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=10
            )
            self.installed_models.clear()
            for line in result.stdout.splitlines()[1:]:  # Skip header
                if line.strip():
                    model_name = line.split()[0].split(":")[0]
                    self.installed_models.add(model_name)
        except Exception as e:
            logger.error(f"Failed to refresh installed models: {e}")

    def get_unified_memory_stats(self) -> Dict[str, float]:
        """Get unified memory statistics for Strix Halo"""
        vitals = self.monitor.get_vitals()

        # AMD GPU memory
        vram_used = 0
        vram_total = 0
        try:
            total_path = Path("/sys/class/drm/card1/device/mem_info_vram_total")
            used_path = Path("/sys/class/drm/card1/device/mem_info_vram_used")
            if total_path.exists() and used_path.exists():
                vram_total = int(total_path.read_text().strip()) / (1024**3)
                vram_used = int(used_path.read_text().strip()) / (1024**3)
        except Exception:
            pass

        # System memory
        import psutil

        vm = psutil.virtual_memory()
        system_used = (vm.total - vm.available) / (1024**3)

        # Unified calculation (simplified - actual unified memory is complex)
        total_used = max(system_used, vram_used)  # Conservative estimate
        available = self.unified_memory_available - total_used

        return {
            "unified_total_gb": self.unified_memory_total,
            "unified_available_gb": self.unified_memory_available,
            "unified_used_gb": total_used,
            "unified_available_now_gb": available,
            "vram_used_gb": vram_used,
            "vram_total_gb": vram_total,
            "system_used_gb": system_used,
            "buffer_target_gb": self.target_buffer_gb,
            "can_allocate": available > self.target_buffer_gb,
        }

    async def suggest_mode_switch(self, task_description: str) -> Optional[SystemMode]:
        """Suggest optimal mode for task with unified memory check"""
        suggested_mode = await self.mode_controller.suggest_mode(task_description)

        if not suggested_mode:
            return None

        # Check if we have enough unified memory
        mem_stats = self.get_unified_memory_stats()
        mode_config = self.mode_controller.configs.get(suggested_mode)

        if not mode_config:
            return None

        if mem_stats["unified_available_now_gb"] < mode_config.buffer_gb:
            logger.warning(
                f"Mode {suggested_mode.value} requires {mode_config.buffer_gb}GB buffer, "
                f"but only {mem_stats['unified_available_now_gb']:.1f}GB available"
            )

            # Fall back to conservative mode
            if suggested_mode != SystemMode.CONSERVATIVE:
                logger.info(
                    "Falling back to CONSERVATIVE mode due to memory constraints"
                )
                return SystemMode.CONSERVATIVE

        return suggested_mode

    async def execute_mode_switch(
        self, target_mode: SystemMode, force: bool = False
    ) -> Dict[str, Any]:
        """Execute mode switch with unified memory optimization"""

        # Pre-switch unified memory check
        mem_stats = self.get_unified_memory_stats()

        logger.info(f"🔄 Mode Switch Request: {target_mode.value}")
        logger.info(
            f"   Unified Memory: {mem_stats['unified_used_gb']:.1f}/"
            f"{mem_stats['unified_available_gb']:.1f} GB used"
        )
        logger.info(f"   Available Now: {mem_stats['unified_available_now_gb']:.1f} GB")

        # Attempt switch
        success = await self.mode_controller.switch_mode(target_mode, force=force)

        if success:
            self.mode_switches += 1

            # Update active models tracking
            mode_config = self.mode_controller.configs.get(target_mode)
            if mode_config:
                self.active_models = set(mode_config.models + mode_config.multimodal)

            # Post-switch stats
            new_stats = self.get_unified_memory_stats()

            return {
                "success": True,
                "from_mode": self.mode_controller.current_mode.value,
                "to_mode": target_mode.value,
                "unified_memory_before_gb": mem_stats["unified_used_gb"],
                "unified_memory_after_gb": new_stats["unified_used_gb"],
                "active_models": list(self.active_models),
                "mode_switch_count": self.mode_switches,
                "hi_ho_coherence": self.mode_controller.target_coherence,
            }
        else:
            return {
                "success": False,
                "reason": "Switch blocked by governance or resource constraints",
                "current_mode": self.mode_controller.current_mode.value,
                "suggested_mode": target_mode.value,
            }

    async def prepare_resources_for_task(
        self, task_type: str, priority: int = 3
    ) -> Dict[str, Any]:
        """
        Prepare resources for a task with mode-aware optimization
        """
        # Detect optimal mode
        suggested_mode = await self.suggest_mode_switch(task_description=task_type)

        result = {
            "task_type": task_type,
            "suggested_mode": suggested_mode.value if suggested_mode else None,
            "current_mode": self.mode_controller.current_mode.value,
            "preparation_actions": [],
        }

        # Switch mode if needed and allowed
        if suggested_mode and suggested_mode != self.mode_controller.current_mode:
            governance = self.mode_controller.governance_mode

            if governance == GovernanceMode.AUTOMATIC:
                switch_result = await self.execute_mode_switch(suggested_mode)
                result["mode_switch"] = switch_result
                result["preparation_actions"].append("automatic_mode_switch")

            elif governance == GovernanceMode.HYBRID:
                # Auto-switch for safe modes
                if suggested_mode in [SystemMode.CONSERVATIVE, SystemMode.PERFORMANCE]:
                    switch_result = await self.execute_mode_switch(suggested_mode)
                    result["mode_switch"] = switch_result
                    result["preparation_actions"].append("hybrid_auto_switch")
                else:
                    result["preparation_actions"].append("advisory_confirmation_needed")

            elif governance == GovernanceMode.ADVISORY:
                result["preparation_actions"].append("advisory_confirmation_needed")
                result["confirmation_request"] = {
                    "message": f"Switch to {suggested_mode.value}?",
                    "reason": f"Optimal for {task_type}",
                    "memory_required": self.mode_controller.configs[
                        suggested_mode
                    ].memory_budget_gb,
                }

        # Check unified memory
        mem_stats = self.get_unified_memory_stats()
        if not mem_stats["can_allocate"]:
            result["warnings"].append("Low unified memory - may need to evict models")
            # Trigger proactive eviction if critical
            if priority <= 2:
                await self._proactive_eviction()
                result["preparation_actions"].append("proactive_model_eviction")

        return result

    async def _proactive_eviction(self):
        """Proactively evict non-essential models when memory is tight"""
        mem_stats = self.get_unified_memory_stats()

        if mem_stats["unified_available_now_gb"] > self.target_buffer_gb * 2:
            return  # Plenty of memory

        logger.warning("🧹 Proactive model eviction triggered")

        # Get current mode priority
        current_mode = self.mode_controller.current_mode
        priority_map = MODE_PRIORITY_MAP.get(current_mode, {})

        critical_models = set(priority_map.get("critical", []))

        # Evict non-critical models
        for model in list(self.active_models):
            if model not in critical_models:
                logger.info(f"Evicting non-critical model: {model}")
                await self.mode_controller._unload_model(model)
                self.active_models.discard(model)

    async def get_fleet_status(self) -> Dict[str, Any]:
        """Get comprehensive fleet status with unified memory"""
        mode_info = self.mode_controller.get_mode_info()
        mem_stats = self.get_unified_memory_stats()

        return {
            "mode": mode_info,
            "unified_memory": mem_stats,
            "models": {
                "installed": list(self.installed_models),
                "active": list(self.active_models),
                "roster": self.roster,
            },
            "governance": self.governance_mode,
            "hi_ho": {
                "target_coherence": self.mode_controller.target_coherence,
                "acceptable_range": self.mode_controller.coherence_range,
            },
            "ascended_metrics": {
                "mode_switches": self.mode_switches,
                "total_models_in_registry": len(
                    self.model_data.get("models", {}).get("language_models", {})
                )
                + len(self.model_data.get("models", {}).get("multimodal_models", {})),
                "multimodal_ready": True,
            },
        }

    async def scout_ascended_models(self) -> str:
        """Scout for new SOTA models for ASCENDED roster"""
        prompt = """
        ACT as an ASCENDED AI Research Scout.
        
        OBJECTIVE: Identify SOTA models for the ASCENDED COHEZION multimodal suite:
        - Text-to-Speech (tiny, CPU-based)
        - Image Generation (efficient, quality)
        - Video Generation (emerging SOTA)
        - Vision-Language (multimodal understanding)
        - Small Language Models (under 20B, exceptional performance)
        
        CRITERIA:
        1. Must fit within 128GB unified memory (Strix Halo)
        2. Apache 2.0 or MIT license preferred
        3. "Tip of the Spear" - best in class for specific use
        4. Available via Ollama or easy local deployment
        
        FORMAT: model_name, size, specialty, why_it's_SOTA
        """

        response = await self._call_ollama(prompt)
        return response

    async def process(self, context: str, **kwargs: Any) -> AgentResponse:
        """
        Process Model Wrangler requests with ASCENDED capabilities
        """
        context_lower = context.lower()

        # Mode management
        if "switch mode" in context_lower or "change mode" in context_lower:
            # Parse target mode from context
            for mode in SystemMode:
                if mode.value in context_lower:
                    force = "force" in context_lower
                    result = await self.execute_mode_switch(mode, force=force)
                    return AgentResponse(
                        json.dumps(result, indent=2), action="mode_switch"
                    )

            return AgentResponse(
                "Available modes: conservative, performance, image_work, video_work, full_multimodal",
                action="mode_list",
            )

        elif "current mode" in context_lower or "mode status" in context_lower:
            status = await self.get_fleet_status()
            return AgentResponse(
                json.dumps(status, indent=2, default=str), action="mode_status"
            )

        elif "unified memory" in context_lower or "memory stats" in context_lower:
            stats = self.get_unified_memory_stats()
            return AgentResponse(json.dumps(stats, indent=2), action="memory_status")

        elif "prepare for" in context_lower or "optimize for" in context_lower:
            # Extract task type
            task_type = (
                context_lower.replace("prepare for", "")
                .replace("optimize for", "")
                .strip()
            )
            priority = kwargs.get("priority", 3)
            result = await self.prepare_resources_for_task(task_type, priority)
            return AgentResponse(
                json.dumps(result, indent=2), action="resource_preparation"
            )

        elif "roster" in context_lower or "deploy" in context_lower:
            self._refresh_installed_models()
            return AgentResponse(
                f"ASCENDED Roster ({len(self.roster)} roles):\n"
                + json.dumps(self.roster, indent=2),
                action="roster_check",
            )

        elif "scout" in context_lower or "new models" in context_lower:
            scout_report = await self.scout_ascended_models()
            return AgentResponse(scout_report, action="slm_scouting")

        elif "evict" in context_lower or "unload" in context_lower:
            await self._proactive_eviction()
            return AgentResponse(
                "Proactive eviction completed", action="proactive_eviction"
            )

        # Default: comprehensive status
        status = await self.get_fleet_status()
        return AgentResponse(
            f"🌌 ASCENDED Model Wrangler Active\n"
            f"Mode: {status['mode']['current_mode']}\n"
            f"Governance: {status['governance']}\n"
            f"Memory: {status['unified_memory']['unified_used_gb']:.1f}/"
            f"{status['unified_memory']['unified_available_gb']:.1f} GB\n"
            f"Active Models: {len(status['models']['active'])}\n"
            f"HIHO Coherence: {status['hi_ho']['target_coherence']}",
            status="active",
        )


# Legacy compatibility
ModelWrangler = ModelWranglerAscended
