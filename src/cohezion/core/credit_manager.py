"""
Credit Manager for Recursive Sovereignty (Gateway 12).

Manages agent credit balances for model routing.
Premium models cost more credits; agents earn credits from NodeVerification yield.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Model Cost Table (Credits per call)
MODEL_COSTS: Dict[str, int] = {
    # Antigravity IDE Models
    "gemini-3-pro": 10,
    "gemini-3-flash": 1,
    "claude-sonnet-4.5": 15,
    "claude-opus-4.5": 20,
    "gpt-oss": 2,
    
    # Local Ollama Models (Free)
    "phi3:mini": 0,
    "mistral:7b": 0,
    "qwen3-coder:32b": 0,
    "deepseek-r1:70b": 0,
}

# Fallback model when credits insufficient
FALLBACK_MODEL = "phi3:mini"


class CreditManager:
    """
    Singleton manager for agent credit balances.
    """
    
    def __init__(self, default_credits: int = 100):
        self._balances: Dict[str, int] = {}
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
            logger.debug(f"Agent {agent_id}: Deducted {amount} credits. New balance: {self._balances[agent_id]}")
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
        cost = MODEL_COSTS.get(model, 5)  # Default cost if unknown
        return self.get_balance(agent_id) >= cost
        
    def get_best_affordable_model(self, agent_id: str, preferred: str) -> str:
        """
        Get the best model the agent can afford.
        Falls back to cheaper models if preferred is too expensive.
        """
        cost = MODEL_COSTS.get(preferred, 5)
        balance = self.get_balance(agent_id)
        
        if balance >= cost:
            return preferred
            
        # Find cheapest affordable model
        for model, model_cost in sorted(MODEL_COSTS.items(), key=lambda x: x[1]):
            if balance >= model_cost:
                logger.info(f"Agent {agent_id}: Downgraded from {preferred} to {model} (credits: {balance})")
                return model
                
        return FALLBACK_MODEL


# Singleton instance
_INSTANCE = None

def get_credit_manager() -> CreditManager:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = CreditManager()
    return _INSTANCE
