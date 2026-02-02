
import logging
import random
from typing import Dict, Any

logger = logging.getLogger("KnowledgeMapper")

class KnowledgeMapper:
    """
    Bridges the gap between Abstract Knowledge (Research) and Concrete Simulation (Physics).
    """
    
    def __init__(self):
        self.mappings = {
            "astronomy": {"mass_modifier": 2.0, "gravity": "high", "color": "#FF00FF"}, # Purple/High Mass
            "black hole": {"mass_modifier": 100.0, "gravity": "extreme", "singularity": True, "color": "#000000"},
            "quantum": {"mass_modifier": 0.1, "volatility": 0.9, "entangled": True, "color": "#00FFFF"}, # Cyan/Jittery
            "consciousness": {"complexity": 1.0, "coherence_threshold": 0.8, "color": "#FFFFFF"},
            "biology": {"growth_rate": 0.5, "replication": True, "color": "#00FF00"},
            "history": {"temporal_drag": 0.8, "mass_modifier": 1.0, "color": "#A52A2A"} # Brown/Slow
        }
        
    def map_research_to_physics(self, topic: str, grade: float) -> Dict[str, Any]:
        """
        Converts a Research Topic + Grade into Simulation Parameters.
        """
        base_topic = topic.lower()
        
        # Default Physics
        physics = {
            "mass": 1.0,
            "velocity": [random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)],
            "spin": random.random(),
            "color": "#808080", # Grey
            "lifespan": 1000 + (grade * 1000) # Better research lasts longer
        }
        
        # Apply Mapping logic
        found_key = None
        for key in self.mappings:
            if key in base_topic:
                found_key = key
                props = self.mappings[key]
                physics.update(props)
                
                # Grade multipliers
                if "mass_modifier" in props:
                    physics["mass"] *= props["mass_modifier"]
                    if grade > 0.9 and key == "black hole":
                        physics["mass"] *= 2.0 # Supermassive
                        
                break
                
        logger.debug(f"Mapped '{topic}' (Grade {grade}) -> {found_key or 'Standard'} Physics")
        return physics
