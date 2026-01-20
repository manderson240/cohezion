"""
Resource Monitor Service.

Ensures Cohezion development (Agentic Work) always takes precedence over 
background 'renting' tasks (Node Verification).
"""

import logging
import psutil
from typing import Dict

logger = logging.getLogger(__name__)

class ResourceMonitor:
    def __init__(self, 
                 cpu_threshold: float = 60.0, 
                 memory_threshold: float = 70.0):
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        
    def get_stats(self) -> Dict[str, float]:
        """Return current system stats."""
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "available_memory_gb": psutil.virtual_memory().available / (1024**3)
        }
        
    def should_rent(self) -> bool:
        """
        Determine if resources are sufficient to run background 'renting' tasks.
        Returns True ONLY if system load is below thresholds.
        """
        stats = self.get_stats()
        
        cpu_ok = stats["cpu_percent"] < self.cpu_threshold
        mem_ok = stats["memory_percent"] < self.memory_threshold
        
        if not cpu_ok:
            logger.debug(f"Rent paused: High CPU ({stats['cpu_percent']}%)")
            
        if not mem_ok:
            logger.debug(f"Rent paused: High Memory ({stats['memory_percent']}%)")
            
        return cpu_ok and mem_ok

# Singleton
_INSTANCE = None

def get_resource_monitor() -> ResourceMonitor:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = ResourceMonitor()
    return _INSTANCE
