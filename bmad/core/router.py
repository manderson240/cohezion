"""
HRM Router Module
"""

from dataclasses import dataclass
from enum import Enum


class ModelTier(Enum):
    LOCAL = 1
    FAST = 2
    STRONG = 3
    REASONING = 4

@dataclass
class RoutingDecision:
    tier: ModelTier
    reasoning: str
    suggested_agent: str = "Generic Agent"

def assess_complexity(task_description: str) -> int:
    """
    Assess the complexity of a task on a scale of 1-10.
    
    Args:
        task_description: The text description of the task.
        
    Returns:
        int: Complexity score (1-10).
    """
    # Heuristic-based assessment for now
    score = 1

    keywords_high = ["architect", "design", "strategy", "complex", "reasoning", "critical"]
    keywords_medium = ["implement", "code", "debug", "refactor", "analyze"]
    keywords_low = ["format", "classify", "summarize", "list"]

    desc_lower = task_description.lower()

    for word in keywords_high:
        if word in desc_lower:
            score += 3

    for word in keywords_medium:
        if word in desc_lower:
            score += 2

    if len(desc_lower) > 500: # Long context
        score += 2

    return min(score, 10)

def route_task(task_description: str) -> RoutingDecision:
    """
    Route a task to the appropriate model tier.
    
    Args:
        task_description: The text description of the task.
        
    Returns:
        RoutingDecision: The assigned tier and reasoning.
    """
    score = assess_complexity(task_description)

    if score >= 8:
        return RoutingDecision(ModelTier.REASONING, f"High complexity score ({score}). Requires deep reasoning.")
    elif score >= 5:
        return RoutingDecision(ModelTier.STRONG, f"Medium complexity score ({score}). Requires strong model.")
    elif score >= 3:
        return RoutingDecision(ModelTier.FAST, f"Low-Medium complexity score ({score}). Fast model sufficient.")
    else:
        return RoutingDecision(ModelTier.LOCAL, f"Low complexity score ({score}). Local model sufficient.")
