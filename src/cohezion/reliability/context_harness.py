"""
Context Harness for Local SLM Optimization.
Prunes, summaryzes, and anchors context for smaller local models.
"""

from cohezion.reliability.monitor import get_resource_monitor
from cohezion.reliability.resolver import HallucinationResolver


class ContextHarness:
    def __init__(self, target_model: str = "phi4"):
        self.target_model = target_model
        self.resolver = HallucinationResolver()
        # Max context target in characters (approximate)
        self.context_limits = {
            "phi4": 16000,
            "phi3:mini": 8000,
            "qwen3-coder-256k": 64000,
            "default": 16000,
        }

    def harness_prompt(self, prompt: str, system_prompt: str | None = None) -> dict[str, str]:
        """Prepare optimized prompt and system prompt for local SLM."""

        # 1. Start with Truth Anchors
        truth_anchors = self.resolver.get_truth_anchors()

        # 2. Prune context if it exceeds dynamic model limits
        limit = self._get_dynamic_limit(self.target_model)
        pruned_prompt = self._prune_text(prompt, limit)

        # 3. Add instruction specialization
        specialized_system = self._get_specialized_system(system_prompt)

        # Final Assembly
        final_system = f"{truth_anchors}\n\n{specialized_system}"

        return {"prompt": pruned_prompt, "system": final_system}

    def _get_dynamic_limit(self, model: str) -> int:
        """Calculate dynamic context limit based on available system memory."""
        monitor = get_resource_monitor()
        stats = monitor.get_vitals()
        avail = stats["memory_available_gb"]

        # Base limits (characters)
        base_limit = self.context_limits.get(model, self.context_limits["default"])

        # 1. RAH Emergency Mitigation (Maxwellian Relaxation signal)
        if getattr(monitor, "pressure_mitigation_active", False):
            # Aggressively prune if autonomic healing requested it
            base_limit = int(base_limit * 0.5)

        # 2. Scaling logic for 128GB RAM substrate
        # If RAM is plenty (>64GB available), allow expansion
        if avail > 64:
            return base_limit * 4  # Aggressive expansion for Strix Halo
        # If RAM is low (<20GB available), throttle back
        elif avail < 20:
            return int(base_limit * 0.5)

        return base_limit

    def _prune_text(self, text: str, limit: int) -> str:
        """Intelligently prune text to fit limits."""
        if len(text) <= limit:
            return text

        # Keep the beginning and end, summarize the 'mantle'
        # High-Fidelity head (first 25% of limit)
        head_len = int(limit * 0.25)
        # High-Fidelity tail (last 50% of limit)
        tail_len = int(limit * 0.50)

        head = text[:head_len]
        tail = text[-tail_len:]

        return f"{head}\n\n[... CONTEXT PRUNED FOR EFFICIENCY ...]\n\n{tail}"

    def _get_specialized_system(self, system_prompt: str | None) -> str:
        """Add instruction following wrappers for high-fidelity SLM response."""
        base = system_prompt or "You are a helpful co-developer assistant."

        if "phi4" in self.target_model:
            wrapper = "Be extremadamente concise. Prioritize concrete facts and code over conversational filler."
        elif "qwen" in self.target_model:
            wrapper = "You are a coding specialist. Ensure all code blocks are complete and syntactically correct."
        else:
            wrapper = "Focus on accuracy and structural coherence."

        return f"{base}\n\n{wrapper}"


if __name__ == "__main__":
    harness = ContextHarness("phi4-mini")
    result = harness.harness_prompt(
        "This is a very long task about building a universe simulation logic...",
        "System instructions.",
    )
    print("--- HARNESSED SYSTEM ---")
    print(result["system"])
    print("\n--- HARNESSED PROMPT ---")
    print(result["prompt"])
