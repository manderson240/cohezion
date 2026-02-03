import os
import asyncio
import logging
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

class LocalExpertRouter:
    """
    Routes routine tasks to local SLMs (Ollama) for token efficiency.
    Supports Qwen-32B (Coding/Reasoning) and DeepSeek-R1 (Logic).
    """

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.client = httpx.AsyncClient(timeout=300.0)
        
        # ASCENDED ROSTER (256k Optimized)
        self.role_map = {
            "routing": "phi4-256k:latest",
            "reasoning": "phi4-256k:latest",
            "coding": "qwen3-coder-256k:latest",
            "general": "gpt-oss-256k:latest",
            "vision": "gemma3-4b-256k:latest",
        }
        self.default_model = "phi4-256k:latest"

        # Task-specific context caps (Prevent overkill)
        self.task_caps = {
            "routing": 8192,
            "general": 32768,
            "vision": 32768,
            "coding": 256000,
            "reasoning": 256000
        }

    async def route_task(self, task_type: str, prompt: str, context: Optional[Dict] = None) -> str:
        """
        Route a task to the optimal local model based on type and context.
        Implements dynamic context window scaling to prevent system OOM.
        """
        context = context or {}
        model = self.role_map.get(task_type, self.default_model)
        
        # 1. Get Mode-Aware Context (From Ascended Registry)
        from cohezion.swarm.mode_controller import get_mode_controller
        from cohezion.reliability.monitor import get_resource_monitor
        
        mode_ctrl = get_mode_controller()
        monitor = get_resource_monitor()
        
        # Base context recommended by current system mode
        recommended_ctx = mode_ctrl.get_recommended_context(model)
        
        # 2. Apply Task-Specific Cap
        task_cap = self.task_caps.get(task_type, 32768)
        final_ctx = min(recommended_ctx, task_cap)
        
        # 3. Apply VRAM Pressure Scaling (Dilation)
        dilation = monitor.get_dilation_factor()
        if dilation < 1.0:
            original_ctx = final_ctx
            final_ctx = int(final_ctx * dilation)
            logger.warning(f"📉 Dilation Active ({dilation:.2f}): Scaling context {original_ctx} -> {final_ctx}")
        
        # Minimum safety floor
        final_ctx = max(final_ctx, 4096)

        logger.info(f"🚀 [ASCENDED] Routing {task_type} task to {model} (num_ctx: {final_ctx})")
        
        options = {"num_ctx": final_ctx}
        if "options" in context:
            options.update(context["options"])

        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": options
            }
            if "system" in context and context["system"]:
                payload["system"] = context["system"]
            
            response = await self.client.post(f"{self.ollama_url}/api/generate", json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            logger.error(f"❌ Ascended routing failed for {model}: {e}")
            return f"Error: {e}"

    async def close(self):
        await self.client.aclose()

# Global instance
LOCAL_ROUTER = LocalExpertRouter()
