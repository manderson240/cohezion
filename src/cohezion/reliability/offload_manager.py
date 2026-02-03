"""
Offload Manager for Cohezion.
Classifies tasks as menial (offloadable) or critical (cortex-only).
"""

import re
from typing import List, Dict, Any

class OffloadManager:
    def __init__(self):
        # Keywords that suggest a task is "menial" (low-complexity, documentation, formatting)
        self.menial_keywords = [
            "documentation", "docstring", "comment", "format", "lint", 
            "summarize", "rephrase", "typo", "readme", "changelog",
            "boilerplate", "rename", "organize imports", "todo"
        ]
        
        # Keywords that suggest a task is "critical" (logic, architecture, security)
        self.critical_keywords = [
            "logic", "algorithm", "architecture", "security", "vulnerability",
            "refactor core", "protocol", "quantum", "physics", "simulation",
            "database schema", "regression", "auth", "encryption"
        ]

    def is_offloadable(self, query: str) -> bool:
        """Determines if a task query is suitable for a local SLM offload."""
        q = query.lower()
        
        # If it's explicitly critical, don't offload
        if any(kw in q for kw in self.critical_keywords):
            return False
            
        # If it contains menial keywords or is short/simple, it's offloadable
        if any(kw in q for kw in self.menial_keywords):
            return True
            
        # Heuristic: shorter queries about updates/writing are often menial
        if len(q) < 150 and any(kw in q for kw in ["write", "update", "create", "list"]):
             return True
             
        return False

    def get_offload_recommendation(self, query: str) -> Dict[str, Any]:
        """Provides a recommendation on whether to offload and which model to use."""
        offloadable = self.is_offloadable(query)
        
        if not offloadable:
            return {"offload": False, "target": "gemini-3-pro"}
            
        # Determine specific local target
        q = query.lower()
        if "code" in q or "python" in q:
            target = "qwen3-coder-256k"
        else:
            target = "phi4"
            
        return {
            "offload": True,
            "target": target,
            "reason": "Task identified as menial/supportive."
        }
