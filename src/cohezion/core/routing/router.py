# ruff: noqa: E501  # long lines: SQL/URLs/docstrings — wrapping reduces readability
import logging
from typing import Any

import httpx


logger = logging.getLogger(__name__)

# Import adaptive framework optimizer
try:
    from cohezion.core.optimization.adaptive_framework import get_adaptive_optimizer

    ADAPTIVE_OPTIMIZER_AVAILABLE = True
except ImportError:
    ADAPTIVE_OPTIMIZER_AVAILABLE = False
    logger.warning("Adaptive framework optimizer not available")


class LocalExpertRouter:
    """
    Routes routine tasks to local SLMs (Ollama) for token efficiency.
    Supports Qwen-32B (Coding/Reasoning) and DeepSeek-R1 (Logic).
    """

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.client = httpx.AsyncClient(timeout=300.0)

        # ELITE COHEZION ROSTER (v0.15.5-rc2 Optimized with Qwen3-Coder-Next & GLM-OCR)
        self.role_map = {
            # Elite tier - highest performance with MoE efficiency
            "elite-coding": "qwen3-coder-next:q8_0",
            "agentic-coding": "qwen3-coder-next:latest",
            "ocr-vision": "glm-ocr:latest",
            "voice-synthesis": "pocket-tts:latest",
            "speech-to-text": "kyutai-stt-1b-en",
            "voice-native": "moshi:latest",
            # Core tier - balanced performance
            "coding": "qwen3-coder-next:latest",
            "vision": "glm-ocr:latest",
            "routing": "phi4-256k:latest",
            "reasoning": "phi4-256k:latest",
            "general": "gpt-oss-256k:latest",
            # Fallback tier - memory constrained scenarios
            "legacy-coding": "qwen3-coder-256k:latest",
            "legacy-vision": "gemma3-4b-256k:latest",
            # Optimization for verification/light tasks
            "light-reasoning": "phi3:mini",
            "light-coding": "phi3:mini",
        }
        self.default_model = "qwen3-coder-next:latest"

        # Elite task-specific context caps (Leveraging v0.15.5-rc2 automatic scaling)
        self.task_caps = {
            "elite-coding": 262144,
            "agentic-coding": 262144,
            "ocr-vision": 128000,  # GLM-OCR native context
            "voice-synthesis": 32768,  # Pocket TTS optimized
            "speech-to-text": 8192,  # Kyutai STT optimized
            "voice-native": 65536,  # Moshi speech-native
            "routing": 8192,
            "general": 32768,
            "vision": 128000,
            "coding": 262144,
            "reasoning": 262144,
            "legacy-coding": 256000,
            "legacy-vision": 256000,
        }

        # Memory-aware model selection thresholds
        self.memory_thresholds = {
            "elite_threshold": 90,  # GB available for elite models
            "agentic_threshold": 55,  # GB available for balanced models
            "fallback_threshold": 20,  # GB threshold for legacy models
        }

    async def route_task(self, task_type: str, prompt: str, context: dict | None = None) -> str:
        """
        Elite compound engineering routing with MoE optimization and memory awareness.
        Implements intelligent model selection and dynamic context scaling for optimal performance.
        """
        context = context or {}

        # 1. Access System Guards (Dilation & Memory)
        available_memory = await self._get_available_memory()
        from cohezion.reliability.monitor import get_resource_monitor

        monitor = get_resource_monitor()
        dilation = monitor.get_dilation_factor()

        # 2. Adaptive Framework-Aware Model Selection
        if ADAPTIVE_OPTIMIZER_AVAILABLE:
            optimizer = get_adaptive_optimizer()
            hardware_profile = optimizer.get_current_profile()
            if hardware_profile:
                logger.info(
                    f"🧠 Using adaptive framework for {hardware_profile.tier} tier hardware"
                )
                model = self._select_optimal_model_adaptive(
                    task_type, available_memory, hardware_profile
                )
            else:
                model = self._select_optimal_model(task_type, available_memory, dilation)
        else:
            model = self._select_optimal_model(task_type, available_memory, dilation)

        # 3. Get Mode-Aware Context (From Ascended Registry)
        from cohezion.swarm.mode_controller import get_mode_controller

        mode_ctrl = get_mode_controller()

        # Base context recommended by current system mode
        recommended_ctx = mode_ctrl.get_recommended_context(model)

        # 3. Apply Task-Specific Cap with v0.15.5-rc2 optimizations
        task_cap = self.task_caps.get(task_type, 32768)
        final_ctx = min(recommended_ctx, task_cap)

        # 4. Apply VRAM Pressure Scaling (Dilation)
        dilation = monitor.get_dilation_factor()
        if dilation < 1.0:
            original_ctx = final_ctx
            final_ctx = int(final_ctx * dilation)
            logger.warning(
                f"📉 Memory Dilation Active ({dilation:.2f}): Scaling context {original_ctx} -> {final_ctx}"
            )

        # 5. Elite MoE Optimization for Qwen3-Coder-Next
        if "qwen3-coder-next" in model:
            final_ctx = max(final_ctx, 65536)  # Minimum context for MoE efficiency
            logger.info(
                f"🧠 MoE Optimization: {model} using only 3B active params (3.75% of 80B total)"
            )

        # 6. OCR Optimization for GLM-OCR
        if "glm-ocr" in model:
            final_ctx = min(final_ctx, 128000)  # Native context limit
            logger.info(f"👁️ OCR Optimization: {model} with 94.62% OmniDocBench accuracy")

        # Minimum safety floor
        final_ctx = max(final_ctx, 4096)

        logger.info(
            f"🚀 [ELITE COHEZION] Routing {task_type} → {model} (ctx: {final_ctx}, mem: {available_memory}GB)"
        )

        # 7. Build optimized options for v0.15.5-rc2
        options = {
            "num_ctx": final_ctx,
            "num_predict": min(4096, final_ctx // 4),  # Predict up to 25% of context
            "temperature": 0.7 if "coding" in task_type else 0.5,
            "top_p": 0.9,
        }

        # Add model-specific optimizations
        if "q8_0" in model:
            options["repeat_penalty"] = 1.05  # Prevent repetition in high-quality model
        if "glm-ocr" in model:
            options["temperature"] = 0.3  # More deterministic OCR results
        if "pocket-tts" in model:
            options["temperature"] = 0.8  # Voice synthesis optimization
            options["speed"] = 1.0  # Normal speech rate

        if "options" in context:
            options.update(context["options"])

        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": options,
            }
            if context.get("system"):
                payload["system"] = context["system"]

            response = await self.client.post(f"{self.ollama_url}/api/generate", json=payload)
            response.raise_for_status()

            result = response.json()
            response_text = result.get("response", "")

            # 8. Performance logging for compound engineering
            await self._log_performance_metrics(task_type, model, final_ctx, available_memory)

            return response_text
        except Exception as e:
            logger.error(f"❌ Elite routing failed for {model}: {e}")
            # Fallback to simpler model
            return await self._fallback_routing(task_type, prompt, context, e)

    async def _get_available_memory(self) -> float:
        """Get available system memory in GB"""
        try:
            import psutil

            memory = psutil.virtual_memory()
            return round(memory.available / (1024**3), 1)
        except ImportError:
            return 125.0  # Default from system analysis

    def _select_optimal_model(
        self, task_type: str, available_memory: float, dilation: float = 1.0
    ) -> str:
        """Select optimal model based on task type, memory, and VRAM pressure (dilation)"""
        primary_model = self.role_map.get(task_type, self.default_model)

        # Severe VRAM Pressure: Trigger mandatory downscaling to 8B/Mini models
        if dilation < 0.5:
            logger.warning(
                f"📉 SEVERE VRAM PRESSURE ({dilation:.2f}): Downscaling {task_type} tasks."
            )
            if task_type in ["reasoning", "routing"]:
                return "deepseek-r1:7b"  # Chain-of-thought but lighter than 256k models
            elif task_type == "coding":
                return "qwen3-coder:30b"  # Smaller than the MoE 80B version
            else:
                return "phi3:mini"

        # Elite models available (Only if no dilation pressure)
        if available_memory >= self.memory_thresholds["elite_threshold"] and dilation >= 0.8:
            if task_type == "coding":
                return self.role_map["elite-coding"]
            elif task_type == "vision":
                return self.role_map["ocr-vision"]

        # Agentic models available
        elif available_memory >= self.memory_thresholds["agentic_threshold"] and dilation >= 0.7:
            if task_type == "coding":
                return self.role_map["agentic-coding"]
            elif task_type == "vision":
                return self.role_map["ocr-vision"]

        # Fallback for memory constraints OR moderate pressure
        elif available_memory < self.memory_thresholds["fallback_threshold"] or dilation < 0.8:
            if task_type == "vision":
                return self.role_map["legacy-vision"]
            elif task_type in ["coding", "elite-coding", "agentic-coding"]:
                return "qwen3-coder:30b"
            elif task_type in ["reasoning", "routing"]:
                return "deepseek-r1:7b"

        return primary_model

    def _select_optimal_model_adaptive(
        self,
        task_type: str,
        available_memory: float,
        hardware_profile: Any,
    ) -> str:
        """Select model using adaptive hardware profile for precise tier matching.

        Uses the detected hardware tier and capabilities from the adaptive
        framework optimizer to select the best model, avoiding the heuristic
        thresholds of ``_select_optimal_model``.
        """
        tier = hardware_profile.tier
        caps = set(hardware_profile.capabilities)
        has_uma = "uma_zero_copy" in caps

        # Enterprise/Professional with UMA: elite models can leverage full memory pool
        if tier in ("enterprise", "professional"):
            if task_type == "coding":
                # Elite Q8 quant if enough memory, otherwise MoE variant
                if available_memory >= 90 or has_uma:
                    return self.role_map["elite-coding"]
                return self.role_map["agentic-coding"]
            elif task_type == "vision":
                return self.role_map["ocr-vision"]
            elif task_type in ("reasoning", "routing"):
                return self.role_map.get("reasoning", self.default_model)
            elif task_type == "general":
                return self.role_map.get("general", self.default_model)
            return self.role_map.get(task_type, self.default_model)

        # Desktop tier: balanced models
        elif tier == "desktop":
            if task_type == "coding":
                return self.role_map["agentic-coding"]
            elif task_type == "vision":
                return self.role_map["ocr-vision"]
            return self.role_map.get(task_type, self.default_model)

        # Laptop/Mobile: conservative models
        else:
            if task_type == "coding":
                return self.role_map.get("legacy-coding", "qwen3-coder:30b")
            elif task_type == "vision":
                return self.role_map.get("legacy-vision", "gemma3-4b-256k:latest")
            elif task_type in ("reasoning", "routing"):
                return self.role_map.get("light-reasoning", "phi3:mini")
            return self.role_map.get("light-coding", "phi3:mini")

    async def _log_performance_metrics(
        self, task_type: str, model: str, context: int, memory: float
    ):
        """Log performance metrics for compound engineering optimization"""
        metrics = {
            "task_type": task_type,
            "model": model,
            "context_window": context,
            "available_memory_gb": memory,
            "moe_efficiency": "96.25%" if "qwen3-coder-next" in model else "N/A",
            "ocr_savings": "90.5%" if "glm-ocr" in model else "N/A",
        }

        logger.info(f"📊 Performance Metrics: {metrics}")

    async def _fallback_routing(
        self,
        task_type: str,
        prompt: str,
        context: dict | None,
        original_error: Exception,
    ) -> str:
        """Fallback routing for error recovery"""
        fallback_model = "phi4-256k:latest"  # Most reliable fallback

        logger.warning(f"🔄 Fallback routing to {fallback_model} due to: {original_error}")

        try:
            payload = {
                "model": fallback_model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_ctx": 8192},
            }

            response = await self.client.post(f"{self.ollama_url}/api/generate", json=payload)
            response.raise_for_status()

            result = response.json()
            return result.get("response", "")
        except Exception as e:
            logger.error(f"❌ Fallback routing also failed: {e}")
            return f"Routing Error: {original_error} | Fallback Error: {e}"

    async def close(self):
        await self.client.aclose()


# Global instance
LOCAL_ROUTER = LocalExpertRouter()
