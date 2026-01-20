"""
GEMINI.md Refiner - Automated rule updates from learnings.

Watches for high-confidence patterns (≥0.85, 3+ occurrences)
and proposes updates to GEMINI.md to improve agent behavior.

Part of the Gateway 5: Autonomous Evolution system.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProposedUpdate:
    """A proposed update to GEMINI.md."""
    
    section: str  # Which section to update
    update_type: str  # "add_pattern", "add_anti_pattern", "add_model", "modify"
    content: str
    confidence: float
    source_learning_id: str
    status: str = "pending"  # pending, approved, rejected
    
    def to_markdown(self) -> str:
        return f"""
### Proposed: {self.update_type}
**Section:** {self.section}
**Confidence:** {self.confidence:.1%}
**Source:** {self.source_learning_id}

```markdown
{self.content}
```
"""


class GeminiRefiner:
    """
    Automatically propose and apply updates to GEMINI.md.
    
    Triggers:
    - Pattern achieves ≥0.85 confidence
    - Same pattern observed 3+ times
    - Anti-pattern detected repeatedly
    """
    
    GEMINI_PATH = Path("/home/mike-anderson/.gemini/GEMINI.md")
    PROPOSALS_PATH = Path(
        "/home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/gemini_proposals.md"
    )
    
    # Section markers in GEMINI.md
    SECTIONS = {
        "anti_patterns": "## Anti-Patterns to Avoid",
        "model_routing": "### Model Routing",
        "local_models": "#### Local Ollama Roster",
        "skills": "## Skill Structure",
        "security": "## Security",
    }
    
    def __init__(self):
        self.pending_updates: list[ProposedUpdate] = []
        self.applied_count = 0
    
    async def propose_update(
        self,
        learning: dict[str, Any],
    ) -> ProposedUpdate | None:
        """
        Propose a GEMINI.md update based on a learning.
        
        Args:
            learning: Learning dict with id, title, pattern, score
            
        Returns:
            ProposedUpdate if proposal created, None otherwise
        """
        score = learning.get("score", 0)
        pattern = learning.get("pattern", "")
        title = learning.get("title", "")
        content = learning.get("content", "")
        
        if score < 0.85:
            logger.debug(f"Learning {learning.get('learning_id')} score too low: {score}")
            return None
        
        # Determine section and update type
        if pattern == "anti_pattern":
            section = "anti_patterns"
            update_type = "add_anti_pattern"
            formatted = self._format_anti_pattern(title, content)
        else:
            section = "skills"  # Default to skills section
            update_type = "add_pattern"
            formatted = self._format_pattern(title, content)
        
        update = ProposedUpdate(
            section=section,
            update_type=update_type,
            content=formatted,
            confidence=score,
            source_learning_id=learning.get("learning_id", "unknown"),
        )
        
        self.pending_updates.append(update)
        await self._save_proposal(update)
        
        logger.info(f"Proposed GEMINI update: {update_type} in {section}")
        return update
    
    def _format_anti_pattern(self, title: str, content: str) -> str:
        """Format an anti-pattern for GEMINI.md."""
        short_content = content[:50] + "..." if len(content) > 50 else content
        return f"| {title} | {short_content} | See learnings |"
    
    def _format_pattern(self, title: str, content: str) -> str:
        """Format a pattern for GEMINI.md."""
        return f"- **{title}**: {content[:100]}"
    
    async def _save_proposal(self, update: ProposedUpdate) -> None:
        """Save proposal to proposals file."""
        self.PROPOSALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        mode = "a" if self.PROPOSALS_PATH.exists() else "w"
        with open(self.PROPOSALS_PATH, mode) as f:
            if mode == "w":
                f.write("# GEMINI.md Update Proposals\n\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n\n---\n")
            f.write(update.to_markdown())
            f.write("\n---\n")
    
    async def apply_approved_updates(self, auto_approve: bool = False) -> int:
        """
        Apply approved updates to GEMINI.md.
        
        Args:
            auto_approve: If True, automatically approve high-confidence updates
            
        Returns:
            Number of updates applied
        """
        if not self.GEMINI_PATH.exists():
            logger.error(f"GEMINI.md not found at {self.GEMINI_PATH}")
            return 0
        
        content = self.GEMINI_PATH.read_text()
        applied = 0
        
        for update in self.pending_updates:
            if update.status == "pending":
                if auto_approve and update.confidence >= 0.90:
                    update.status = "approved"
            
            if update.status == "approved":
                # Find the section and append
                section_marker = self.SECTIONS.get(update.section)
                if section_marker and section_marker in content:
                    # Find end of section (next ## or end of file)
                    idx = content.index(section_marker)
                    next_section = content.find("\n## ", idx + 1)
                    
                    if next_section == -1:
                        # Append at end
                        content += f"\n{update.content}\n"
                    else:
                        # Insert before next section
                        content = (
                            content[:next_section] +
                            f"\n{update.content}\n" +
                            content[next_section:]
                        )
                    
                    applied += 1
                    update.status = "applied"
                    logger.info(f"Applied update: {update.update_type}")
        
        if applied > 0:
            # Backup current GEMINI.md
            backup_path = self.GEMINI_PATH.with_suffix(".md.bak")
            backup_path.write_text(self.GEMINI_PATH.read_text())
            
            # Write updated content
            self.GEMINI_PATH.write_text(content)
            self.applied_count += applied
            logger.info(f"Updated GEMINI.md with {applied} changes")
        
        return applied
    
    def get_status(self) -> dict[str, Any]:
        """Get refiner status."""
        return {
            "pending_updates": len([u for u in self.pending_updates if u.status == "pending"]),
            "approved_updates": len([u for u in self.pending_updates if u.status == "approved"]),
            "applied_total": self.applied_count,
            "proposals_file": str(self.PROPOSALS_PATH),
        }


# Singleton
_refiner: GeminiRefiner | None = None


def get_gemini_refiner() -> GeminiRefiner:
    """Get or create the singleton GeminiRefiner."""
    global _refiner
    if _refiner is None:
        _refiner = GeminiRefiner()
    return _refiner
