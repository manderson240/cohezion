"""
Compound Logic Engine (CLE).
Orchestrates the "Feature Nexus" where every feature makes future features easier.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from cohezion.registry.capability_registry import CapabilityRegistry, Capability

logger = logging.getLogger(__name__)

class CompoundLogicEngine:
    """
    The engine that enforces "Compound Engineering" laws.
    Identifies existing hooks that can simplify the current task.
    """
    
    def __init__(self, registry: Optional[CapabilityRegistry] = None):
        self.registry = registry or CapabilityRegistry()
        
    def analyze_task_for_compounding(self, task_intent: str) -> List[Dict[str, Any]]:
        """
        Analyze a task and find existing capabilities with relevant 'Future Hooks'.
        """
        logger.info(f"🧩 [CLE] Analyzing task for compound opportunities: {task_intent[:50]}...")
        
        # 1. Find relevant capabilities
        candidates = self.registry.find(task_intent, top_k=5)
        
        compounds = []
        for cap in candidates:
            if cap.future_proofing_hooks:
                compounds.append({
                    "name": cap.name,
                    "type": cap.type,
                    "hooks": cap.future_proofing_hooks,
                    "impact_score": cap.compound_impact_score,
                    "relevance": cap.score
                })
        
        if compounds:
            logger.info(f"✨ Found {len(compounds)} compound hooks to accelerate this task.")
            
        return compounds

    def validate_future_proofing(self, content: str) -> bool:
        """
        Verify that a new feature contains the mandatory 'FUTURE HOOKS' section.
        """
        if "## FUTURE HOOKS" in content.upper():
            # Check for at least one bullet point
            lines = content.split("\n")
            in_section = False
            for line in lines:
                if "## FUTURE HOOKS" in line.upper():
                    in_section = True
                    continue
                if in_section and line.strip().startswith("- "):
                    return True
                if in_section and line.startswith("#") and "FUTURE HOOKS" not in line.upper():
                    break
        
        return False

    def record_compound_impact(self, name: str, impact_delta: float = 0.1):
        """
        Record that a specific capability helped another feature.
        """
        for cap in self.registry.capabilities:
            if cap.name == name:
                cap.compound_impact_score += impact_delta
                logger.info(f"🚀 Increased compound impact for {name}: {cap.compound_impact_score:.2f}")
                # Note: Registry persistence happens via increment_usage or manual trigger
                break

CLE = CompoundLogicEngine()
