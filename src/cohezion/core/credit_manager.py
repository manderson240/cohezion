# long lines: SQL/URLs/docstrings — wrapping reduces readability
"""
Credit Manager for Recursive Sovereignty (Gateway 12).

Manages agent credit balances for model routing.
Premium models cost more credits; agents earn credits from NodeVerification yield.
"""

import logging


logger = logging.getLogger(__name__)

# Model Cost Table (Credits per call)
MODEL_COSTS: dict[str, int] = {
    # Antigravity IDE Models
    "gemini-3-pro": 10,
    "gemini-3-flash": 1,
    "claude-sonnet-4.5": 15,
    "claude-opus-4.5": 20,
    "gpt-oss": 2,
    # Local Ollama Models (Simulated Energy Cost)
    "phi3:mini": 1,
    "gemma3:4b": 2,
    "mistral:7b": 3,
    "qwen3-coder:32b": 8,
    "deepseek-r1:70b": 15,
    "moondream:latest": 2,
}

# Fallback model when credits insufficient
FALLBACK_MODEL = "phi3:mini"


class CreditManager:
    """
    Singleton manager for agent credit balances.
    """

    def __init__(self, default_credits: int = 100):
        self._balances: dict[str, int] = {}
        self._default = default_credits

    def get_balance(self, agent_id: str) -> int:
        """Get agent's current credit balance."""
        return self._balances.get(agent_id, self._default)

    def deduct(self, agent_id: str, amount: int) -> bool:
        """
        Attempt to deduct credits from agent.
        Returns True if successful, False if insufficient funds.
        """
        balance = self.get_balance(agent_id)

        if balance >= amount:
            self._balances[agent_id] = balance - amount
            logger.debug(
                f"Agent {agent_id}: Deducted {amount} credits. New balance: {self._balances[agent_id]}"
            )
            return True

        logger.warning(f"Agent {agent_id}: Insufficient credits ({balance} < {amount})")
        return False

    def credit(self, agent_id: str, amount: int) -> None:
        """Add credits to an agent's balance."""
        balance = self.get_balance(agent_id)
        self._balances[agent_id] = balance + amount
        logger.info(f"Agent {agent_id}: Credited {amount}. New balance: {self._balances[agent_id]}")

    def can_afford(self, agent_id: str, model: str) -> bool:
        """Check if agent can afford the specified model."""
        return self.get_balance(agent_id) >= self.get_model_cost(model)

    def get_model_cost(self, model: str) -> int:
        """Get the credit cost for a specific model."""
        return MODEL_COSTS.get(model, 5)  # Default baseline

    def get_best_affordable_model(self, agent_id: str, preferred: str) -> str:
        """
        Get the best model the agent can afford.
        Falls back to cheaper models if preferred is too expensive.
        """
        cost = MODEL_COSTS.get(preferred, 5)
        balance = self.get_balance(agent_id)

        if balance >= cost:
            return preferred

        # Find cheapest affordable LOCAL model
        local_models = [
            "phi3:mini",
            "gemma3:4b",
            "mistral:7b",
            "moondream:latest",
            "qwen3-coder:32b",
            "deepseek-r1:70b",
        ]
        affordable_locals = [
            m for m in local_models if m in MODEL_COSTS and balance >= MODEL_COSTS[m]
        ]

        if affordable_locals:
            # Sort by cost descending (best affordable local)
            sorted_locals = sorted(affordable_locals, key=lambda x: MODEL_COSTS[x], reverse=True)
            return sorted_locals[0]

        return FALLBACK_MODEL


# Singleton instance
_INSTANCE = None


def get_credit_manager() -> CreditManager:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = CreditManager()
    return _INSTANCE
