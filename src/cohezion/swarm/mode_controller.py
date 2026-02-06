"""
ASCENDED COHEZION - Mode Controller
Manages 5 system modes with HIHO stability and automatic/advisory/hybrid switching.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import psutil

logger = logging.getLogger(__name__)


class SystemMode(Enum):
    """ASCENDED COHEZION System Modes"""

    CONSERVATIVE = "conservative"  # 24/7 background
    PERFORMANCE = "performance"  # Heavy LLM work
    IMAGE_WORK = "image_work"  # Visual generation
    VIDEO_WORK = "video_work"  # Video generation
    FULL_MULTIMODAL = "full_multimodal"  # All modalities


class GovernanceMode(Enum):
    """Mode switching governance policies"""

    AUTOMATIC = "automatic"
    ADVISORY = "advisory"
    HYBRID = "hybrid"


@dataclass
class ModeConfiguration:
    """Configuration for a system mode"""

    mode: SystemMode
    description: str
    trigger: str
    memory_budget_gb: int
    target_coherence: float
    models: list[str]
    multimodal: list[str]
    context_tier: int
    max_context: int
    auto_scale: bool
    human_gate: str
    buffer_gb: int
    purpose: str


@dataclass
class ModelInfo:
    """Model metadata from registry"""

    name: str
    parameters: str
    context: int
    memory_gb: float
    quantization: str
    specialization: str
    priority: int
    tier: int
    always_hot: bool
    available_modes: list[str]
    multimodal: bool = False
    device: str = "gpu"


@dataclass
class SystemVitals:
    """Current system state"""

    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    memory_total_gb: float
    vram_percent: float
    vram_used_gb: float
    vram_total_gb: float
    unified_memory_percent: float
    active_models: int
    coherence: float = 0.5
    timestamp: float = field(default_factory=time.time)


class ModeController:
    """
    ASCENDED COHEZION Mode Controller

    Manages 5 system modes with:
    - HIHO stability (0.5 coherence targeting)
    - Dynamic mode switching
    - Trinity governance (Automatic/Advisory/Hybrid)
    - Unified memory optimization
    - Compound engineering principles
    """

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, governance_mode: GovernanceMode = GovernanceMode.HYBRID):
        if self._initialized:
            return

        self.governance_mode = governance_mode
        self.current_mode = SystemMode.CONSERVATIVE
        self.target_coherence = 0.5
        self.coherence_range = (0.45, 0.55)

        # Load configurations
        self.configs = self._load_mode_configs()
        self.models = self._load_model_registry()

        # State tracking
        self.active_models: set[str] = set()
        self.mode_history: list[dict[str, Any]] = []
        self.switch_in_progress = False

        # Monitoring
        self.last_vitals = None
        self.mode_switch_count = 0
        self.last_switch_time = 0

        self._initialized = True
        logger.info("🌌 ASCENDED Mode Controller initialized")
        logger.info(f"   Governance: {governance_mode.value}")
        logger.info(f"   Initial Mode: {self.current_mode.value}")
        logger.info(f"   HIHO Target: {self.target_coherence}")

    @staticmethod
    def _load_json_with_comments(path: Path) -> dict:
        """Load a JSON file, stripping leading comment lines (lines starting with #)."""
        text = path.read_text()
        lines = text.split("\n")
        cleaned = "\n".join(line for line in lines if not line.lstrip().startswith("#"))
        return json.loads(cleaned)

    def _load_mode_configs(self) -> dict[SystemMode, ModeConfiguration]:
        """Load mode configurations from registry"""
        registry_path = Path(
            "/home/mike-anderson/dev/cohezion/model_registry_ascended.json"
        )

        try:
            data = self._load_json_with_comments(registry_path)

            configs = {}
            for mode_name, mode_data in data["system_modes"].items():
                mode = SystemMode(mode_name)
                configs[mode] = ModeConfiguration(
                    mode=mode,
                    description=mode_data["description"],
                    trigger=mode_data["trigger"],
                    memory_budget_gb=mode_data["memory_budget_gb"],
                    target_coherence=mode_data["target_coherence"],
                    models=mode_data["models"],
                    multimodal=mode_data.get("multimodal", []),
                    context_tier=mode_data["context_tier"],
                    max_context=mode_data["max_context"],
                    auto_scale=mode_data["auto_scale"],
                    human_gate=mode_data["human_gate"],
                    buffer_gb=mode_data["buffer_gb"],
                    purpose=mode_data["purpose"],
                )

            return configs
        except Exception as e:
            logger.error(f"Failed to load mode configs: {e}")
            return {}

    def _load_model_registry(self) -> dict[str, ModelInfo]:
        """Load model information from registry"""
        registry_path = Path(
            "/home/mike-anderson/dev/cohezion/model_registry_ascended.json"
        )

        try:
            data = self._load_json_with_comments(registry_path)

            models = {}

            # Load language models
            for name, info in data["models"]["language_models"].items():
                models[name] = ModelInfo(
                    name=name,
                    parameters=info["parameters"],
                    context=info["context"],
                    memory_gb=info["memory_gb"],
                    quantization=info["quantization"],
                    specialization=info["specialization"],
                    priority=info["priority"],
                    tier=info["tier"],
                    always_hot=info["always_hot"],
                    available_modes=info["available_modes"],
                    multimodal=info.get("multimodal", False),
                    device="gpu",
                )

            # Load multimodal models
            for name, info in data["models"]["multimodal_models"].items():
                models[name] = ModelInfo(
                    name=name,
                    parameters=info["parameters"],
                    context=0,  # Multimodal models don't use context
                    memory_gb=info["memory_gb"],
                    quantization=info.get("quantization", "N/A"),
                    specialization=info["specialization"],
                    priority=info["priority"],
                    tier=info["tier"],
                    always_hot=info["always_hot"],
                    available_modes=info["available_modes"],
                    multimodal=True,
                    device=info.get("device", "gpu"),
                )

            return models
        except Exception as e:
            logger.error(f"Failed to load model registry: {e}")
            return {}

    def get_vitals(self) -> SystemVitals:
        """Get current system vitals including unified memory"""
        vm = psutil.virtual_memory()

        # Get AMD GPU stats
        vram_total = 0
        vram_used = 0
        try:
            total_path = Path("/sys/class/drm/card1/device/mem_info_vram_total")
            used_path = Path("/sys/class/drm/card1/device/mem_info_vram_used")
            if total_path.exists() and used_path.exists():
                vram_total = int(total_path.read_text().strip()) / (1024**3)
                vram_used = int(used_path.read_text().strip()) / (1024**3)
        except Exception:
            pass

        # Unified memory calculation
        total_memory = vm.total / (1024**3)
        available_memory = vm.available / (1024**3)
        unified_percent = 100 - ((available_memory / total_memory) * 100)

        vitals = SystemVitals(
            cpu_percent=psutil.cpu_percent(),
            memory_percent=vm.percent,
            memory_available_gb=available_memory,
            memory_total_gb=total_memory,
            vram_percent=(vram_used / vram_total * 100) if vram_total > 0 else 0,
            vram_used_gb=vram_used,
            vram_total_gb=vram_total,
            unified_memory_percent=unified_percent,
            active_models=len(self.active_models),
            coherence=self.target_coherence,
        )

        self.last_vitals = vitals
        return vitals

    def detect_workload(self, task_queue: list[dict[str, Any]]) -> SystemMode | None:
        """
        Analyze task queue and recommend optimal mode
        Returns None if current mode is optimal
        """
        if not task_queue:
            return None

        # Count task types
        image_tasks = sum(
            1
            for t in task_queue
            if t.get("type") in ["image_gen", "image_edit", "visual_design"]
        )
        video_tasks = sum(
            1
            for t in task_queue
            if t.get("type") in ["video_gen", "animation", "motion_design"]
        )
        coding_tasks = sum(
            1
            for t in task_queue
            if t.get("type") in ["coding", "refactoring", "architecture"]
        )
        analysis_tasks = sum(
            1
            for t in task_queue
            if t.get("type") in ["analysis", "planning", "research"]
        )

        # Decision logic
        if video_tasks > 0:
            return SystemMode.VIDEO_WORK
        elif image_tasks > 2:
            return SystemMode.IMAGE_WORK
        elif coding_tasks > 5 or analysis_tasks > 3:
            return SystemMode.PERFORMANCE
        elif image_tasks > 0 or video_tasks > 0:
            # Mixed multimodal
            return SystemMode.FULL_MULTIMODAL

        return None

    def can_switch_mode(self, target_mode: SystemMode) -> tuple[bool, str]:
        """
        Check if mode switch is allowed under current governance
        Returns (allowed, reason)
        """
        vitals = self.get_vitals()
        config = self.configs.get(target_mode)

        if not config:
            return False, "Unknown mode"

        # Check memory availability
        if vitals.memory_available_gb < config.buffer_gb:
            return (
                False,
                f"Insufficient memory: {vitals.memory_available_gb:.1f}GB < {config.buffer_gb}GB required",
            )

        # Check coherence stability
        if vitals.coherence < 0.3:
            return (
                False,
                f"Coherence too low: {vitals.coherence:.2f} (emergency threshold 0.3)",
            )

        # Governance checks
        if self.governance_mode == GovernanceMode.AUTOMATIC:
            # Allow if basic checks pass
            return True, "Automatic mode - checks passed"

        elif self.governance_mode == GovernanceMode.ADVISORY:
            # Always require confirmation for non-conservative modes
            if target_mode != SystemMode.CONSERVATIVE:
                return (
                    False,
                    f"Advisory mode - {target_mode.value} requires human confirmation",
                )
            return True, "Advisory mode - conservative mode allowed"

        elif self.governance_mode == GovernanceMode.HYBRID:
            # Hybrid logic
            auto_allowed = [SystemMode.CONSERVATIVE, SystemMode.PERFORMANCE]

            if target_mode in auto_allowed and vitals.memory_available_gb > 50:
                return True, "Hybrid mode - auto-allowed for safe conditions"
            elif target_mode in [SystemMode.IMAGE_WORK, SystemMode.VIDEO_WORK]:
                return False, f"Hybrid mode - {target_mode.value} requires confirmation"
            elif target_mode == SystemMode.FULL_MULTIMODAL:
                return (
                    False,
                    "Hybrid mode - full_multimodal always requires confirmation",
                )
            else:
                return True, "Hybrid mode - approved"

        return False, "Unknown governance mode"

    async def switch_mode(self, target_mode: SystemMode, force: bool = False) -> bool:
        """
        Execute mode switch with HIHO stability verification
        """
        if self.switch_in_progress:
            logger.warning("Mode switch already in progress")
            return False

        if target_mode == self.current_mode:
            return True

        # Check if allowed
        if not force:
            allowed, reason = self.can_switch_mode(target_mode)
            if not allowed:
                logger.warning(f"Mode switch blocked: {reason}")
                return False

        self.switch_in_progress = True
        start_time = time.time()

        try:
            logger.info(
                f"🔄 Switching mode: {self.current_mode.value} → {target_mode.value}"
            )

            # Log the switch
            self.mode_history.append(
                {
                    "from": self.current_mode.value,
                    "to": target_mode.value,
                    "timestamp": time.time(),
                    "vitals_before": self.get_vitals().__dict__,
                    "governance": self.governance_mode.value,
                }
            )

            # Verify HIHO coherence
            vitals = self.get_vitals()
            if not (0.45 <= vitals.coherence <= 0.55):
                logger.warning(
                    f"Coherence {vitals.coherence:.2f} outside HIHO range (0.45-0.55)"
                )

            # Unload models not in target mode
            target_config = self.configs[target_mode]
            target_models = set(target_config.models + target_config.multimodal)

            models_to_unload = self.active_models - target_models
            for model in models_to_unload:
                await self._unload_model(model)

            # Load required models
            models_to_load = target_models - self.active_models
            for model in models_to_load:
                await self._load_model(model)

            # Update state
            old_mode = self.current_mode
            self.current_mode = target_mode
            self.mode_switch_count += 1
            self.last_switch_time = time.time()

            switch_duration = time.time() - start_time

            # Narration (Constitutional requirement)
            logger.info(
                f"✅ Mode switch complete: {old_mode.value} → {target_mode.value}"
            )
            logger.info(f"   Duration: {switch_duration:.2f}s")
            logger.info(f"   Unloaded: {len(models_to_unload)} models")
            logger.info(f"   Loaded: {len(models_to_load)} models")
            logger.info(f"   Active: {len(self.active_models)} models")
            logger.info(f"   HIHO Coherence: {self.target_coherence}")

            return True

        except Exception as e:
            logger.error(f"Mode switch failed: {e}")
            return False
        finally:
            self.switch_in_progress = False

    async def _unload_model(self, model_name: str):
        """Unload a model via Ollama API"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "curl",
                "-s",
                "-X",
                "POST",
                "http://localhost:11434/api/generate",
                "-d",
                json.dumps({"model": model_name, "keep_alive": 0}),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            self.active_models.discard(model_name)
            logger.debug(f"Unloaded model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to unload {model_name}: {e}")

    async def _load_model(self, model_name: str):
        """Load a model via Ollama API"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "curl",
                "-s",
                "-X",
                "POST",
                "http://localhost:11434/api/pull",
                "-d",
                json.dumps({"name": model_name}),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            self.active_models.add(model_name)
            logger.debug(f"Loaded model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load {model_name}: {e}")

    def get_mode_info(self) -> dict[str, Any]:
        """Get current mode information"""
        config = self.configs.get(self.current_mode)
        vitals = self.get_vitals()

        return {
            "current_mode": self.current_mode.value,
            "governance": self.governance_mode.value,
            "description": config.description if config else "Unknown",
            "purpose": config.purpose if config else "Unknown",
            "active_models": list(self.active_models),
            "memory_budget": config.memory_budget_gb if config else 0,
            "vitals": {
                "memory_available_gb": vitals.memory_available_gb,
                "unified_memory_percent": vitals.unified_memory_percent,
                "coherence": vitals.coherence,
            },
            "switch_count": self.mode_switch_count,
            "last_switch": self.last_switch_time,
        }

    async def suggest_mode(self, task_description: str) -> SystemMode | None:
        """
        Suggest optimal mode for a given task
        """
        task_lower = task_description.lower()

        # Video keywords
        if any(kw in task_lower for kw in ["video", "animation", "motion", "temporal"]):
            return SystemMode.VIDEO_WORK

        # Image keywords
        if any(
            kw in task_lower
            for kw in ["image", "visual", "design", "asset", "ui", "graphic"]
        ):
            if "multiple" in task_lower or "batch" in task_lower:
                return SystemMode.IMAGE_WORK
            return SystemMode.FULL_MULTIMODAL

        # Complex coding/analysis
        if any(
            kw in task_lower
            for kw in [
                "architecture",
                "system design",
                "complex",
                "multi-file",
                "refactor",
            ]
        ):
            return SystemMode.PERFORMANCE

        # Default
        return SystemMode.CONSERVATIVE

    def get_recommended_context(self, model_name: str) -> int:
        """Get recommended context window for model in current mode"""
        config = self.configs.get(self.current_mode)
        if not config:
            return 32768

        model_info = self.models.get(model_name)
        if not model_info:
            return config.max_context

        # Use mode-specific context tier
        if hasattr(model_info, "context_tiers"):
            return model_info.context_tiers.get(
                self.current_mode.value, config.max_context
            )

        return min(model_info.context, config.max_context)


# Singleton accessor
def get_mode_controller(governance_mode: str = "hybrid") -> ModeController:
    """Get or create the Mode Controller singleton"""
    mode_map = {
        "automatic": GovernanceMode.AUTOMATIC,
        "advisory": GovernanceMode.ADVISORY,
        "hybrid": GovernanceMode.HYBRID,
    }

    return ModeController(mode_map.get(governance_mode, GovernanceMode.HYBRID))


# Legacy compatibility
ModeSwitcher = ModeController
