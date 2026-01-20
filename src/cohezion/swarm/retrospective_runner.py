"""
Retrospective Runner - Automated learning extraction and skill generation.

Runs after simulation batches to:
1. Extract patterns from results
2. Store learnings to SurrealDB
3. Generate skills from patterns ≥0.85 confidence
4. Propose GEMINI.md updates

Part of the R-Zero self-improvement loop.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """An extracted pattern from experience."""
    
    name: str
    description: str
    confidence: float
    occurrences: int = 1
    examples: list[str] = field(default_factory=list)
    is_anti_pattern: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "confidence": self.confidence,
            "occurrences": self.occurrences,
            "examples": self.examples[:3],  # Limit examples
            "is_anti_pattern": self.is_anti_pattern,
        }


@dataclass
class RetrospectiveResult:
    """Result from a retrospective run."""
    
    session_id: str
    patterns_found: list[Pattern] = field(default_factory=list)
    skills_generated: list[str] = field(default_factory=list)
    learnings_stored: int = 0
    gemini_updates_proposed: int = 0
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class RetrospectiveRunner:
    """
    Automated retrospective after simulation batches.
    
    Implements the self-improvement loop:
    measure → extract → store → generate → update
    """
    
    def __init__(self, skills_dir: Path | None = None):
        self.skills_dir = skills_dir or Path(
            "/home/mike-anderson/dev/cohezion/src/cohezion/skills"
        )
        self.pattern_registry: dict[str, Pattern] = {}
        self._surreal_mcp = None
    
    async def _get_surreal(self):
        """Lazy-load SurrealDB MCP."""
        if self._surreal_mcp is None:
            from cohezion.mcp.surreal_server import get_server
            self._surreal_mcp = get_server()
        return self._surreal_mcp
    
    async def run_retrospective(
        self,
        session_id: str,
        metrics: dict[str, Any],
        issues: list[str] | None = None,
    ) -> RetrospectiveResult:
        """
        Run a full retrospective on a session.
        
        Args:
            session_id: Unique session identifier
            metrics: Session metrics (scores, coherence, etc.)
            issues: Any issues encountered
            
        Returns:
            RetrospectiveResult with patterns, skills, and learnings
        """
        import time
        start = time.monotonic()
        
        result = RetrospectiveResult(session_id=session_id)
        issues = issues or []
        
        # 1. Extract patterns from metrics
        patterns = await self._extract_patterns(metrics, issues)
        result.patterns_found = patterns
        
        # 2. Store learnings to SurrealDB
        surreal = await self._get_surreal()
        for pattern in patterns:
            try:
                await surreal.store_learning(
                    learning_id=f"auto_{session_id}_{pattern.name[:20]}",
                    title=pattern.name,
                    content=pattern.description,
                    pattern="anti_pattern" if pattern.is_anti_pattern else "pattern",
                    score=pattern.confidence,
                )
                result.learnings_stored += 1
            except Exception as e:
                logger.error(f"Failed to store learning: {e}")
        
        # 3. Generate skills from high-confidence patterns
        for pattern in patterns:
            if pattern.confidence >= 0.85 and pattern.occurrences >= 3:
                skill_name = await self._generate_skill(pattern)
                if skill_name:
                    result.skills_generated.append(skill_name)
        
        # 4. Propose GEMINI.md updates for top patterns
        for pattern in patterns:
            if pattern.confidence >= 0.85 and not pattern.is_anti_pattern:
                proposed = await self._propose_gemini_update(pattern)
                if proposed:
                    result.gemini_updates_proposed += 1
        
        result.duration_ms = (time.monotonic() - start) * 1000
        
        logger.info(
            f"Retrospective {session_id}: "
            f"{len(patterns)} patterns, "
            f"{result.learnings_stored} learnings, "
            f"{len(result.skills_generated)} skills"
        )
        
        return result
    
    async def _extract_patterns(
        self,
        metrics: dict[str, Any],
        issues: list[str],
    ) -> list[Pattern]:
        """Extract patterns from metrics and issues."""
        patterns = []
        
        # Pattern: High coherence
        avg_coherence = metrics.get("avg_coherence", 0)
        if avg_coherence >= 0.85:
            patterns.append(Pattern(
                name="High Coherence Achievement",
                description=f"System achieved {avg_coherence:.1%} coherence",
                confidence=avg_coherence,
            ))
        
        # Pattern: Pragmatist scoring
        avg_score = metrics.get("avg_score", 0)
        if avg_score >= 0.85:
            patterns.append(Pattern(
                name="Pragmatist Quality Pass",
                description=f"Pragmatist scored {avg_score:.1%} average",
                confidence=avg_score,
            ))
        
        # Anti-pattern: Low scores
        if avg_score < 0.3:
            patterns.append(Pattern(
                name="Quality Degradation",
                description=f"Low scoring detected: {avg_score:.1%}",
                confidence=1.0 - avg_score,
                is_anti_pattern=True,
                examples=issues[:3],
            ))
        
        # Pattern: Self-healing success
        heal_rate = metrics.get("self_heal_rate", 0)
        if heal_rate >= 0.9:
            patterns.append(Pattern(
                name="Self-Healing Active",
                description=f"Recovery rate: {heal_rate:.1%}",
                confidence=heal_rate,
            ))
        
        # Anti-pattern detection from issues
        for issue in issues:
            if "error" in issue.lower() or "failed" in issue.lower():
                # Check if we've seen this pattern before
                key = issue[:50]
                if key in self.pattern_registry:
                    self.pattern_registry[key].occurrences += 1
                else:
                    self.pattern_registry[key] = Pattern(
                        name=f"Issue: {issue[:30]}",
                        description=issue,
                        confidence=0.6,
                        is_anti_pattern=True,
                    )
        
        # Add recurring patterns from registry
        for pattern in self.pattern_registry.values():
            if pattern.occurrences >= 3:
                patterns.append(pattern)
        
        return patterns
    
    async def _generate_skill(self, pattern: Pattern) -> str | None:
        """Generate a skill from a pattern."""
        if pattern.is_anti_pattern:
            return None  # Don't generate skills from anti-patterns
        
        skill_name = pattern.name.upper().replace(" ", "_") + "_PRIME"
        skill_path = self.skills_dir / f"{skill_name}.md"
        
        if skill_path.exists():
            logger.info(f"Skill already exists: {skill_name}")
            return None
        
        skill_content = f"""# SKILL: {skill_name}

## DOMAIN EXPERTISE
Auto-generated skill from pattern: {pattern.name}

## KEY TEXTS & CONCEPTS
- Pattern confidence: {pattern.confidence:.1%}
- Occurrences: {pattern.occurrences}

## INSTRUCTION
{pattern.description}

## EXAMPLES
{chr(10).join(f"- {ex}" for ex in pattern.examples[:3]) or "- See pattern documentation"}

## VERSION
v0.1 (auto-generated)

## SEE ALSO
- RETROSPECTIVE_SKILL.md
- R_ZERO_CHALLENGER_PRIME.md
"""
        
        try:
            skill_path.write_text(skill_content)
            logger.info(f"Generated skill: {skill_name}")
            return skill_name
        except Exception as e:
            logger.error(f"Failed to generate skill: {e}")
            return None
    
    async def _propose_gemini_update(self, pattern: Pattern) -> bool:
        """Propose an update to GEMINI.md based on pattern."""
        proposals_path = Path(
            "/home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/gemini_proposals.md"
        )
        
        proposal = f"""
## Proposed Update: {pattern.name}
**Date:** {datetime.now().isoformat()}
**Confidence:** {pattern.confidence:.1%}
**Occurrences:** {pattern.occurrences}

### Description
{pattern.description}

### Suggested Addition
```markdown
| Pattern | Application |
|---------|-------------|
| {pattern.name} | {pattern.description[:50]}... |
```

---
"""
        
        try:
            mode = "a" if proposals_path.exists() else "w"
            with open(proposals_path, mode) as f:
                if mode == "w":
                    f.write("# GEMINI.md Update Proposals\n\n")
                f.write(proposal)
            return True
        except Exception as e:
            logger.error(f"Failed to propose GEMINI update: {e}")
            return False
    
    async def save_retrospective_markdown(
        self,
        result: RetrospectiveResult,
        output_dir: Path | None = None,
    ) -> Path:
        """Save retrospective as markdown document."""
        output_dir = output_dir or Path(
            "/home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/retrospectives"
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = result.timestamp.strftime("%Y%m%d_%H%M%S")
        path = output_dir / f"auto_retrospective_{timestamp}.md"
        
        content = f"""# Retrospective: {result.session_id}

**Generated:** {result.timestamp.isoformat()}
**Duration:** {result.duration_ms:.0f}ms

## Summary
- **Patterns Found:** {len(result.patterns_found)}
- **Learnings Stored:** {result.learnings_stored}
- **Skills Generated:** {len(result.skills_generated)}
- **GEMINI Updates Proposed:** {result.gemini_updates_proposed}

## Patterns

| Name | Confidence | Type |
|------|------------|------|
"""
        
        for p in result.patterns_found:
            ptype = "❌ Anti-Pattern" if p.is_anti_pattern else "✅ Pattern"
            content += f"| {p.name} | {p.confidence:.1%} | {ptype} |\n"
        
        if result.skills_generated:
            content += "\n## Generated Skills\n"
            for skill in result.skills_generated:
                content += f"- `{skill}`\n"
        
        content += "\n---\n*Auto-generated by RetrospectiveRunner*\n"
        
        path.write_text(content)
        logger.info(f"Saved retrospective: {path}")
        return path


# Singleton
_runner: RetrospectiveRunner | None = None


def get_retrospective_runner() -> RetrospectiveRunner:
    """Get or create the singleton RetrospectiveRunner."""
    global _runner
    if _runner is None:
        _runner = RetrospectiveRunner()
    return _runner
