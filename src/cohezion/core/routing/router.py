import logging
from typing import TYPE_CHECKING, Any

import httpx


if TYPE_CHECKING:
    from cohezion.core.optimization.adaptive_framework import HardwareProfile

logger = logging.getLogger(__name__)

try:
    from cohezion.compound.telemetry import get_tracker

    _telemetry_available = True
except ImportError:
    _telemetry_available = False
    logger.warning("TokenEfficiencyTracker not available")

try:
    from cohezion.core.optimization.adaptive_framework import get_adaptive_optimizer

    _adaptive_optimizer_available = True
except ImportError:
    _adaptive_optimizer_available = False
    logger.warning("Adaptive framework optimizer not available")


class LocalExpertRouter:
    """
    Routes routine tasks to local SLMs (Ollama) for token efficiency.
    Supports Qwen-32B (Coding/Reasoning) and DeepSeek-R1 (Logic).
    """

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.client = httpx.AsyncClient(timeout=300.0)

        self.role_map = {
            "elite-coding": "qwen3-coder-next:q8_0",
            "agentic-coding": "qwen3-coder-next:latest",
            "ocr-vision": "glm-ocr:latest",
            "voice-synthesis": "pocket-tts:latest",
            "speech-to-text": "kyutai-stt-1b-en",
            "voice-native": "moshi:latest",
            "coding": "qwen3-coder-next:latest",
            "vision": "glm-ocr:latest",
            "routing": "phi4-256k:latest",
            "reasoning": "phi4-256k:latest",
            "general": "gpt-oss-256k:latest",
            "legacy-coding": "qwen3-coder-256k:latest",
            "legacy-vision": "gemma3-4b-256k:latest",
            "light-reasoning": "phi3:mini",
            "light-coding": "phi3:mini",
        }
        self.default_model = "qwen3-coder-next:latest"

        self.task_caps = {
            "elite-coding": 262144,
            "agentic-coding": 262144,
            "ocr-vision": 128000,
            "voice-synthesis": 32768,
            "speech-to-text": 8192,
            "voice-native": 65536,
            "routing": 8192,
            "general": 32768,
            "vision": 128000,
            "coding": 262144,
            "reasoning": 262144,
            "legacy-coding": 256000,
            "legacy-vision": 256000,
        }

        self.memory_thresholds = {
            "elite_threshold": 90,
            "agentic_threshold": 55,
            "fallback_threshold": 20,
        }

    async def route_task(
        self, task_type: str, prompt: str, context: dict | None = None
    ) -> str:
        """
        Elite compound engineering routing with MoE optimization and memory awareness.
        Implements intelligent model selection and dynamic context scaling for optimal performance.
        """
        context = context or {}

        available_memory = await self._get_available_memory()
        from cohezion.reliability.monitor import get_resource_monitor

        monitor = get_resource_monitor()
        dilation = monitor.get_dilation_factor()

        if _adaptive_optimizer_available:
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
                model = self._select_optimal_model(
                    task_type, available_memory, dilation
                )
        else:
            model = self._select_optimal_model(task_type, available_memory, dilation)

        from cohezion.swarm.mode_controller import get_mode_controller

        mode_ctrl = get_mode_controller()

        recommended_ctx = mode_ctrl.get_recommended_context(model)

        task_cap = self.task_caps.get(task_type, 32768)
        final_ctx = min(recommended_ctx, task_cap)

        dilation = monitor.get_dilation_factor()
        if dilation < 1.0:
            original_ctx = final_ctx
            final_ctx = int(final_ctx * dilation)
            logger.warning(
                f"📉 Memory Dilation Active ({dilation:.2f}): Scaling context {original_ctx} -> {final_ctx}"
            )

        if "qwen3-coder-next" in model:
            final_ctx = max(final_ctx, 65536)
            logger.info(
                f"🧠 MoE Optimization: {model} using only 3B active params (3.75% of 80B total)"
            )

        if "glm-ocr" in model:
            final_ctx = min(final_ctx, 128000)
            logger.info(
                f"👁️ OCR Optimization: {model} with 94.62% OmniDocBench accuracy"
            )

        final_ctx = max(final_ctx, 4096)

        logger.info(
            f"🚀 [ELITE COHEZION] Routing {task_type} → {model} (ctx: {final_ctx}, mem: {available_memory}GB)"
        )

        options = {
            "num_ctx": final_ctx,
            "num_predict": min(4096, final_ctx // 4),
            "temperature": 0.7 if "coding" in task_type else 0.5,
            "top_p": 0.9,
        }

        if "q8_0" in model:
            options["repeat_penalty"] = 1.05
        if "glm-ocr" in model:
            options["temperature"] = 0.3
        if "pocket-tts" in model:
            options["temperature"] = 0.8
            options["speed"] = 1.0

        if "options" in context:
            options.update(context["options"])

        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": options,
            }
            if "system" in context and context["system"]:
                payload["system"] = context["system"]

            response = await self.client.post(
                f"{self.ollama_url}/api/generate", json=payload
            )
            response.raise_for_status()

            result = response.json()
            response_text = result.get("response", "")

            # Capture token usage from Ollama
            input_tokens = result.get("prompt_eval_count", 0)
            output_tokens = result.get("eval_count", 0)

            await self._log_performance_metrics(
                task_type,
                model,
                final_ctx,
                available_memory,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

            return response_text
        except Exception as e:
            logger.error(f"❌ Elite routing failed for {model}: {e}")
            return await self._fallback_routing(task_type, prompt, context, e)

    async def _get_available_memory(self) -> float:
        """Get available system memory in GB"""
        try:
            import psutil

            memory = psutil.virtual_memory()
            return round(memory.available / (1024**3), 1)
        except ImportError:
            return 125.0

    def _select_optimal_model(
        self, task_type: str, available_memory: float, dilation: float = 1.0
    ) -> str:
        """Select optimal model based on task type, memory, and VRAM pressure (dilation)"""
        primary_model = self.role_map.get(task_type, self.default_model)

        if dilation < 0.5:
            logger.warning(
                f"📉 SEVERE VRAM PRESSURE ({dilation:.2f}): Downscaling {task_type} tasks."
            )
            if task_type in ["reasoning", "routing"]:
                return "deepseek-r1:7b"
            elif task_type == "coding":
                return "qwen3-coder:30b"
            else:
                return "phi3:mini"

        if (
            available_memory >= self.memory_thresholds["elite_threshold"]
            and dilation >= 0.8
        ):
            if task_type == "coding":
                return self.role_map["elite-coding"]
            elif task_type == "vision":
                return self.role_map["ocr-vision"]

        elif (
            available_memory >= self.memory_thresholds["agentic_threshold"]
            and dilation >= 0.7
        ):
            if task_type == "coding":
                return self.role_map["agentic-coding"]
            elif task_type == "vision":
                return self.role_map["ocr-vision"]

        elif (
            available_memory < self.memory_thresholds["fallback_threshold"]
            or dilation < 0.8
        ):
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
        hardware_profile: "HardwareProfile",
    ) -> str:
        """Select model using adaptive hardware profile for precise tier matching.

        Uses the detected hardware tier and capabilities from the adaptive
        framework optimizer to select the best model, avoiding the heuristic
        thresholds of ``_select_optimal_model``.
        """
        tier = hardware_profile.tier
        caps = set(hardware_profile.capabilities)
        has_uma = "uma_zero_copy" in caps

        if tier in ("enterprise", "professional"):
            if task_type == "coding":
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

        elif tier == "desktop":
            if task_type == "coding":
                return self.role_map["agentic-coding"]
            elif task_type == "vision":
                return self.role_map["ocr-vision"]
            return self.role_map.get(task_type, self.default_model)

        else:
            if task_type == "coding":
                return self.role_map.get("legacy-coding", "qwen3-coder:30b")
            elif task_type == "vision":
                return self.role_map.get("legacy-vision", "gemma3-4b-256k:latest")
            elif task_type in ("reasoning", "routing"):
                return self.role_map.get("light-reasoning", "phi3:mini")
            return self.role_map.get("light-coding", "phi3:mini")

    async def _log_performance_metrics(
        self,
        task_type: str,
        model: str,
        context: int,
        memory: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ):
        """Log performance metrics for compound engineering optimization"""
        metrics = {
            "task_type": task_type,
            "model": model,
            "context_window": context,
            "available_memory_gb": memory,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "moe_efficiency": "96.25%" if "qwen3-coder-next" in model else "N/A",
            "ocr_savings": "90.5%" if "glm-ocr" in model else "N/A",
        }

        logger.info(f"📊 Performance Metrics: {metrics}")

        if _telemetry_available:
            get_tracker().record_call(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                task_type=task_type,
            )

    async def _fallback_routing(
        self,
        task_type: str,
        prompt: str,
        context: dict | None,
        original_error: Exception,
    ) -> str:
        """Fallback routing for error recovery"""
        fallback_model = "phi4-256k:latest"

        logger.warning(
            f"🔄 Fallback routing to {fallback_model} due to: {original_error}"
        )

        try:
            payload = {
                "model": fallback_model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_ctx": 8192},
            }

            response = await self.client.post(
                f"{self.ollama_url}/api/generate", json=payload
            )
            response.raise_for_status()

            result = response.json()
            return result.get("response", "")
        except Exception as e:
            logger.error(f"❌ Fallback routing also failed: {e}")
            return f"Routing Error: {original_error} | Fallback Error: {e}"

    async def close(self):
        await self.client.aclose()


LOCAL_ROUTER = LocalExpertRouter()
