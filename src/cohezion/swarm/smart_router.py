"""
Smart Agent Router - Intelligent routing of tasks to appropriate models.

Features:
- Task classification
- Model capability matching
- Load balancing
- Fallback chains
- Action logging for knowledge base
"""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

import httpx


logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of tasks for routing."""

    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    CREATIVE = "creative"
    CODING = "coding"
    FACTUAL = "factual"
    DEBATE = "debate"
    SUMMARY = "summary"


class ModelCapability(Enum):
    """Model capabilities for matching."""

    FAST = "fast"
    ACCURATE = "accurate"
    CREATIVE = "creative"
    LARGE_CONTEXT = "large_context"
    CODING = "coding"


@dataclass
class ModelProfile:
    """Profile of an available model."""

    name: str
    capabilities: list[ModelCapability]
    context_length: int
    speed_tier: int  # 1=fastest, 5=slowest
    quality_tier: int  # 1=basic, 5=best

    @property
    def efficiency_score(self) -> float:
        """Score balancing speed and quality."""
        return self.quality_tier / self.speed_tier


# Define available local models (aligned with installed Ollama roster)
LOCAL_MODELS = {
    "qwen3-coder-next:q8_0": ModelProfile(
        name="qwen3-coder-next:q8_0",
        capabilities=[
            ModelCapability.ACCURATE,
            ModelCapability.CODING,
            ModelCapability.LARGE_CONTEXT,
        ],
        context_length=262144,
        speed_tier=5,
        quality_tier=5,
    ),
    "qwen3-coder-next:latest": ModelProfile(
        name="qwen3-coder-next:latest",
        capabilities=[
            ModelCapability.ACCURATE,
            ModelCapability.CODING,
            ModelCapability.LARGE_CONTEXT,
        ],
        context_length=262144,
        speed_tier=4,
        quality_tier=5,
    ),
    "qwen3-coder:30b": ModelProfile(
        name="qwen3-coder:30b",
        capabilities=[
            ModelCapability.ACCURATE,
            ModelCapability.CODING,
            ModelCapability.LARGE_CONTEXT,
        ],
        context_length=65536,
        speed_tier=3,
        quality_tier=4,
    ),
    "qwen3-coder-256k:latest": ModelProfile(
        name="qwen3-coder-256k:latest",
        capabilities=[ModelCapability.CODING, ModelCapability.LARGE_CONTEXT],
        context_length=256000,
        speed_tier=3,
        quality_tier=4,
    ),
    "qwen2.5-coder-14b-256k:latest": ModelProfile(
        name="qwen2.5-coder-14b-256k:latest",
        capabilities=[ModelCapability.CODING, ModelCapability.LARGE_CONTEXT],
        context_length=256000,
        speed_tier=2,
        quality_tier=4,
    ),
    "qwen2.5-coder:14b": ModelProfile(
        name="qwen2.5-coder:14b",
        capabilities=[ModelCapability.CODING, ModelCapability.ACCURATE],
        context_length=32768,
        speed_tier=2,
        quality_tier=4,
    ),
    "qwen2.5-coder:7b": ModelProfile(
        name="qwen2.5-coder:7b",
        capabilities=[ModelCapability.FAST, ModelCapability.CODING],
        context_length=32768,
        speed_tier=1,
        quality_tier=3,
    ),
    "phi4-256k:latest": ModelProfile(
        name="phi4-256k:latest",
        capabilities=[
            ModelCapability.ACCURATE,
            ModelCapability.LARGE_CONTEXT,
            ModelCapability.CREATIVE,
        ],
        context_length=256000,
        speed_tier=2,
        quality_tier=4,
    ),
    "phi4:latest": ModelProfile(
        name="phi4:latest",
        capabilities=[ModelCapability.ACCURATE, ModelCapability.CREATIVE],
        context_length=128000,
        speed_tier=2,
        quality_tier=4,
    ),
    "gpt-oss-256k:latest": ModelProfile(
        name="gpt-oss-256k:latest",
        capabilities=[ModelCapability.ACCURATE, ModelCapability.LARGE_CONTEXT],
        context_length=256000,
        speed_tier=3,
        quality_tier=4,
    ),
    "deepseek-r1:7b": ModelProfile(
        name="deepseek-r1:7b",
        capabilities=[ModelCapability.ACCURATE, ModelCapability.CREATIVE],
        context_length=32768,
        speed_tier=1,
        quality_tier=3,
    ),
    "qwen3:8b": ModelProfile(
        name="qwen3:8b",
        capabilities=[ModelCapability.FAST, ModelCapability.CODING],
        context_length=64000,
        speed_tier=1,
        quality_tier=3,
    ),
    "gemma3:4b": ModelProfile(
        name="gemma3:4b",
        capabilities=[ModelCapability.FAST, ModelCapability.CODING],
        context_length=8192,
        speed_tier=1,
        quality_tier=3,
    ),
    "gemma3-4b-256k:latest": ModelProfile(
        name="gemma3-4b-256k:latest",
        capabilities=[ModelCapability.FAST, ModelCapability.LARGE_CONTEXT],
        context_length=256000,
        speed_tier=1,
        quality_tier=3,
    ),
    "phi3:mini": ModelProfile(
        name="phi3:mini",
        capabilities=[ModelCapability.FAST, ModelCapability.CREATIVE],
        context_length=4096,
        speed_tier=1,
        quality_tier=2,
    ),
    "glm-ocr:latest": ModelProfile(
        name="glm-ocr:latest",
        capabilities=[ModelCapability.FAST, ModelCapability.ACCURATE],
        context_length=128000,
        speed_tier=1,
        quality_tier=3,
    ),
    "minicpm-v:8b-2.6-fp16": ModelProfile(
        name="minicpm-v:8b-2.6-fp16",
        capabilities=[ModelCapability.ACCURATE, ModelCapability.CREATIVE],
        context_length=8192,
        speed_tier=2,
        quality_tier=4,
    ),
}


# Task to capability mapping
TASK_REQUIREMENTS = {
    TaskType.ANALYSIS: [ModelCapability.ACCURATE],
    TaskType.SYNTHESIS: [ModelCapability.ACCURATE, ModelCapability.LARGE_CONTEXT],
    TaskType.CREATIVE: [ModelCapability.CREATIVE],
    TaskType.CODING: [ModelCapability.CODING],
    TaskType.FACTUAL: [ModelCapability.ACCURATE],
    TaskType.DEBATE: [ModelCapability.ACCURATE, ModelCapability.LARGE_CONTEXT],
    TaskType.SUMMARY: [ModelCapability.FAST],
}


@dataclass
class RoutingDecision:
    """Result of routing decision."""

    task_type: TaskType
    selected_model: str
    reasoning: str
    fallback_models: list[str]
    confidence: float


@dataclass
class AgentAction:
    """Record of an agent action for knowledge base."""

    timestamp: str
    agent_type: str
    model: str
    task_type: str
    input_tokens: int
    output_tokens: int
    duration_ms: float
    success: bool
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class SmartRouter:
    """
    Routes tasks to optimal models based on requirements and availability.

    Strategies:
    - Efficiency: Balance speed and quality
    - Quality: Prioritize best results
    - Speed: Prioritize fastest response
    """

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        strategy: str = "efficiency",
        log_actions: bool = True,
    ):
        self.ollama_host = ollama_host
        self.strategy = strategy
        self.log_actions = log_actions
        self.action_log: list[AgentAction] = []
        self.client = httpx.AsyncClient(timeout=60.0)

        # Track model availability
        self.available_models: dict[str, ModelProfile] = {}

        # Action log persistence — anchored to module location, not CWD
        _module_root = Path(__file__).resolve().parent.parent
        self.action_log_dir = _module_root / "knowledge_graph/universe_nodes/actions"
        self.action_log_dir.mkdir(parents=True, exist_ok=True)

    async def refresh_models(self):
        """Check which models are available."""
        try:
            resp = await self.client.get(f"{self.ollama_host}/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                for m in models:
                    name = m["name"]
                    if name in LOCAL_MODELS:
                        self.available_models[name] = LOCAL_MODELS[name]
                logger.info(f"Available models: {list(self.available_models.keys())}")
        except Exception as e:
            logger.warning(f"Could not refresh models: {e}")

    def classify_task(self, prompt: str) -> TaskType:
        """Classify the task type from the prompt."""
        prompt_lower = prompt.lower()

        if any(kw in prompt_lower for kw in ["analyze", "examine", "evaluate"]):
            return TaskType.ANALYSIS
        elif any(kw in prompt_lower for kw in ["synthesize", "integrate", "combine"]):
            return TaskType.SYNTHESIS
        elif any(kw in prompt_lower for kw in ["create", "imagine", "story", "poem"]):
            return TaskType.CREATIVE
        elif any(kw in prompt_lower for kw in ["code", "function", "implement", "debug"]):
            return TaskType.CODING
        elif any(kw in prompt_lower for kw in ["fact", "true", "verify"]):
            return TaskType.FACTUAL
        elif any(kw in prompt_lower for kw in ["debate", "perspective", "argue"]):
            return TaskType.DEBATE
        elif any(kw in prompt_lower for kw in ["summarize", "brief", "tldr"]):
            return TaskType.SUMMARY
        else:
            return TaskType.ANALYSIS  # Default

    def route(self, task_type: TaskType) -> RoutingDecision:
        """Route a task to the optimal model."""
        requirements = TASK_REQUIREMENTS.get(task_type, [])

        # Score each available model
        scored_models = []
        for name, profile in self.available_models.items():
            # Check capability match
            match_score = sum(1 for r in requirements if r in profile.capabilities)

            # Apply strategy
            if self.strategy == "efficiency":
                total_score = match_score * 2 + profile.efficiency_score
            elif self.strategy == "quality":
                total_score = match_score * 2 + profile.quality_tier
            elif self.strategy == "speed":
                total_score = match_score * 2 + (6 - profile.speed_tier)
            else:
                total_score = match_score

            scored_models.append((name, total_score, profile))

        if not scored_models:
            # Fallback to first available
            if self.available_models:
                best = next(iter(self.available_models.keys()))
            else:
                best = "gemma3:4b"  # Ultimate fallback
            return RoutingDecision(
                task_type=task_type,
                selected_model=best,
                reasoning="No models matched; using fallback",
                fallback_models=[],
                confidence=0.5,
            )

        # Sort by score (descending)
        scored_models.sort(key=lambda x: x[1], reverse=True)

        best = scored_models[0]
        fallbacks = [m[0] for m in scored_models[1:3]]

        return RoutingDecision(
            task_type=task_type,
            selected_model=best[0],
            reasoning=f"Best match for {task_type.value} with {self.strategy} strategy",
            fallback_models=fallbacks,
            confidence=min(1.0, best[1] / 5),
        )

    async def execute(
        self,
        prompt: str,
        system_prompt: str = "",
        agent_type: str = "generic",
        **kwargs,
    ) -> tuple[str, AgentAction]:
        """Execute a task with smart routing."""
        # Classify and route
        task_type = self.classify_task(prompt)
        decision = self.route(task_type)

        start_time = time.time()
        success = False
        response = ""

        # Try selected model, then fallbacks
        models_to_try = [decision.selected_model, *decision.fallback_models]

        for model in models_to_try:
            try:
                # Construct standard Ollama messages
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                clean_host = self.ollama_host.rstrip("/")
                if clean_host.endswith("/api"):
                    clean_host = clean_host[:-4]
                if clean_host.endswith("/v1"):
                    clean_host = clean_host[:-3]

                resp = await self.client.post(
                    f"{clean_host}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "system": system_prompt,
                        "stream": False,
                    },
                )
                resp.raise_for_status()

                data = await resp.json()
                response = data.get("response", "")
                tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
                success = True
                break

            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
                continue

        # Log action
        action = AgentAction(
            timestamp=datetime.now(UTC).isoformat(),
            agent_type=agent_type,
            model=decision.selected_model,
            task_type=task_type.value,
            input_tokens=len(prompt.split()),  # Approximate
            output_tokens=len(response.split()),
            duration_ms=(time.time() - start_time) * 1000,
            success=success,
            metadata={
                "routing_confidence": decision.confidence,
                "fallbacks_tried": len(models_to_try) - 1 if not success else 0,
            },
        )

        if self.log_actions:
            self.action_log.append(action)

        return response, action

    async def save_action_log(self):
        """Save action log to knowledge base."""
        if not self.action_log:
            return

        log_file = self.action_log_dir / f"actions_{int(time.time())}.json"
        with open(log_file, "w") as f:
            json.dump([a.to_dict() for a in self.action_log], f, indent=2)

        logger.info(f"Saved {len(self.action_log)} actions to {log_file}")

    async def close(self):
        """Clean up resources."""
        await self.save_action_log()
        await self.client.aclose()


# Singleton router
_router: SmartRouter | None = None


async def get_router() -> SmartRouter:
    """Get or create the smart router."""
    global _router
    if _router is None:
        _router = SmartRouter()
        await _router.refresh_models()
    return _router


async def smart_execute(
    prompt: str,
    agent_type: str = "generic",
    **kwargs,
) -> str:
    """Execute a prompt with smart routing."""
    router = await get_router()
    response, _action = await router.execute(prompt, agent_type=agent_type, **kwargs)
    return response


if __name__ == "__main__":

    async def test():
        router = SmartRouter()
        await router.refresh_models()

        prompts = [
            "Analyze the performance of CALM vs LLM",
            "Synthesize findings from multiple experiments",
            "Create a story about AI agents collaborating",
            "Implement a function to calculate coherence",
            "Summarize the key findings in one paragraph",
        ]

        for prompt in prompts:
            task_type = router.classify_task(prompt)
            decision = router.route(task_type)
            print(f"{prompt[:40]}... -> {decision.selected_model} ({task_type.value})")

        await router.close()

    logging.basicConfig(level=logging.INFO)
    asyncio.run(test())
