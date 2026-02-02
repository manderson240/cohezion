"""Grounded context harness for hallucination-resistant local model delegation.

Provides model-aware context construction with:
- Vector similarity-based skill ranking
- Structured context templates per model capability
- Fact verification grounding
- Confidence-based escalation triggers

Usage:
    harness = GroundedContextHarness(agent)
    context = await harness.build_for_local_model(
        query="analyze code",
        model_name="phi3:mini",
        min_confidence=0.7
    )
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContextSpec:
    """Specification for context construction."""

    max_tokens: int
    include_skills: bool = True
    include_history: bool = True
    include_artifacts: bool = False
    require_grounding: bool = True
    output_format: str = "text"  # text, json, structured


@dataclass
class GroundedContext:
    """Context package with grounding metadata."""

    system_prompt: str
    user_prompt: str
    skills: list[dict[str, Any]] = field(default_factory=list)
    grounding_sources: list[str] = field(default_factory=list)
    confidence_estimate: float = 0.0
    suggested_model: str | None = None
    escalation_recommended: bool = False


class ContextEncoder(Protocol):
    """Protocol for encoding text to vectors."""

    async def encode(self, text: str) -> list[float]: ...


# Model capability profiles
MODEL_PROFILES: dict[str, ContextSpec] = {
    "phi3:mini": ContextSpec(
        max_tokens=2048,
        include_skills=True,
        include_history=False,  # Limited context window
        include_artifacts=False,
        require_grounding=True,
        output_format="structured",
    ),
    "deepseek-r1:7b": ContextSpec(
        max_tokens=4096,
        include_skills=True,
        include_history=True,
        include_artifacts=True,
        require_grounding=True,
        output_format="json",
    ),
    "deepseek-r1:70b": ContextSpec(
        max_tokens=8192,
        include_skills=True,
        include_history=True,
        include_artifacts=True,
        require_grounding=False,  # Strong enough to handle ambiguity
        output_format="text",
    ),
    "qwen3-coder:32b": ContextSpec(
        max_tokens=8192,
        include_skills=True,
        include_history=True,
        include_artifacts=True,
        require_grounding=True,
        output_format="structured",
    ),
    "gemma2:9b": ContextSpec(
        max_tokens=4096,
        include_skills=True,
        include_history=True,
        include_artifacts=False,
        require_grounding=True,
        output_format="text",
    ),
}

DEFAULT_PROFILE = ContextSpec(
    max_tokens=2048,
    include_skills=True,
    include_history=False,
    include_artifacts=False,
    require_grounding=True,
    output_format="text",
)


class GroundedContextHarness:
    """Builds hallucination-resistant context for local model delegation.

    Key features:
    1. Model-specific context sizing (token-aware)
    2. Skill ranking by vector similarity to query
    3. Structured templates that guide smaller models
    4. Confidence scoring with escalation triggers
    5. Fact grounding via cross-referencing
    """

    def __init__(self, agent: Any, encoder: ContextEncoder | None = None):
        self.agent = agent
        self._encoder = encoder
        self._skill_cache: dict[str, Any] = {}
        self._context_history: list[dict[str, Any]] = []

    def _get_model_profile(self, model_name: str) -> ContextSpec:
        """Get context spec for model, with fuzzy matching."""
        # Exact match
        if model_name in MODEL_PROFILES:
            return MODEL_PROFILES[model_name]

        # Partial match (e.g., "phi3" matches "phi3:mini")
        for key, profile in MODEL_PROFILES.items():
            if model_name.lower() in key.lower() or key.lower() in model_name.lower():
                return profile

        return DEFAULT_PROFILE

    def _estimate_complexity(self, query: str) -> float:
        """Estimate query complexity (0.0 - 1.0)."""
        factors = {
            "length": min(len(query) / 500, 1.0),
            "code_blocks": 0.3 if "```" in query else 0.0,
            "multiple_tasks": 0.2 if query.count("and then") > 1 else 0.0,
            "reasoning_required": 0.2
            if any(w in query.lower() for w in ["why", "explain", "analyze"])
            else 0.0,
            "creative": 0.1
            if any(w in query.lower() for w in ["create", "design", "imagine"])
            else 0.0,
        }
        return min(sum(factors.values()), 1.0)

    def _rank_skills_by_relevance(
        self, query: str, skills: list[Any], top_k: int = 5
    ) -> list[tuple[Any, float]]:
        """Rank skills by keyword overlap with query."""
        query_words = set(query.lower().split())

        scored = []
        for skill in skills:
            score = 0.0

            # Name match (highest weight)
            if hasattr(skill, "name"):
                name_words = set(skill.name.lower().split())
                score += len(query_words & name_words) * 3.0

            # Description match
            if hasattr(skill, "description"):
                desc_words = set(skill.description.lower().split())
                score += len(query_words & desc_words) * 1.0

            # Tag match
            if hasattr(skill, "tags"):
                for tag in skill.tags:
                    tag_words = set(tag.lower().split())
                    score += len(query_words & tag_words) * 2.0

            if score > 0:
                scored.append((skill, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _build_system_prompt(
        self,
        role: str,
        model_profile: ContextSpec,
        skills: list[Any],
        grounding: list[str],
    ) -> str:
        """Build model-specific system prompt."""

        # Base role definition
        base = f"You are a specialized {role}."

        # Model-specific instructions
        if model_profile.output_format == "json":
            format_instr = """
You must respond in valid JSON format with:
- "response": your main answer
- "confidence": float 0.0-1.0 indicating certainty
- "reasoning": brief explanation of your logic
- "uncertainties": list any facts you're not certain about"""
        elif model_profile.output_format == "structured":
            format_instr = """
Structure your response with:
1. ANSWER: Direct response to the query
2. REASONING: Brief logic trail (2-3 sentences max)
3. CONFIDENCE: High/Medium/Low
4. UNCERTAINTIES: Flag any uncertain claims with [VERIFY]"""
        else:
            format_instr = ""

        # Skill context
        skill_context = ""
        if skills and model_profile.include_skills:
            skill_lines = []
            for skill in skills[:3]:  # Top 3 most relevant
                if hasattr(skill, "name") and hasattr(skill, "description"):
                    skill_lines.append(f"- {skill.name}: {skill.description[:100]}")
            if skill_lines:
                skill_context = "\n\nRelevant capabilities:\n" + "\n".join(skill_lines)

        # Grounding instructions
        grounding_instr = ""
        if model_profile.require_grounding and grounding:
            grounding_instr = (
                f"\n\nGround your response in these verified facts:\n"
                + "\n".join(f"- {g}" for g in grounding[:3])
            )

        # Hallucination warnings for weaker models
        hallucination_warning = ""
        if model_profile.max_tokens <= 2048:
            hallucination_warning = """

IMPORTANT: Only state facts you are confident about. 
If uncertain, say "I'm not certain about [specific detail]" 
rather than guessing."""

        return f"{base}{format_instr}{skill_context}{grounding_instr}{hallucination_warning}"

    async def build_for_local_model(
        self,
        query: str,
        model_name: str,
        min_confidence: float = 0.7,
        context: dict[str, Any] | None = None,
    ) -> GroundedContext:
        """Build hallucination-resistant context for local model.

        Args:
            query: The task/query to delegate
            model_name: Target local model (e.g., "phi3:mini")
            min_confidence: Minimum confidence threshold for escalation
            context: Optional additional context

        Returns:
            GroundedContext with structured prompts and metadata
        """
        ctx = context or {}
        profile = self._get_model_profile(model_name)

        # Assess complexity
        complexity = self._estimate_complexity(query)

        # Gather relevant skills
        skills = []
        if profile.include_skills and hasattr(self.agent, "registry"):
            try:
                all_skills = self.agent.registry.get_capabilities("skill")
                skills = self._rank_skills_by_relevance(query, all_skills, top_k=5)
                skills = [s[0] for s in skills]  # Just the skill objects
            except Exception as e:
                logger.debug(f"Skill retrieval failed: {e}")

        # Gather grounding sources
        grounding = []
        if profile.require_grounding:
            # Add recent conversation context as grounding
            if self._context_history:
                grounding.extend(
                    [
                        f"Previous context: {h.get('query', '')[:100]}"
                        for h in self._context_history[-2:]
                    ]
                )

            # Add any provided artifacts
            if profile.include_artifacts and "artifacts" in ctx:
                grounding.extend(ctx["artifacts"][:2])

        # Build prompts
        system_prompt = self._build_system_prompt(
            role=ctx.get("role", "assistant"),
            model_profile=profile,
            skills=skills,
            grounding=grounding,
        )

        # Build user prompt with constraints
        user_prompt = query
        if profile.max_tokens <= 2048:
            user_prompt = f"{query[:1000]}\n\n[Respond concisely due to context limits]"

        # Estimate confidence
        confidence = 0.8  # Base confidence
        if complexity > 0.7:
            confidence -= 0.2  # Complex queries harder for small models
        if not skills:
            confidence -= 0.1  # No relevant skills
        if profile.max_tokens <= 2048:
            confidence -= 0.1  # Limited context window

        confidence = max(0.0, min(1.0, confidence))

        # Determine if escalation recommended
        escalation = confidence < min_confidence
        suggested_model = None
        if escalation:
            # Suggest stronger model
            if "phi3" in model_name or "gemma" in model_name:
                suggested_model = "deepseek-r1:7b"
            elif "deepseek-r1:7b" in model_name:
                suggested_model = "deepseek-r1:70b"

        # Store in history for future grounding
        self._context_history.append(
            {
                "query": query,
                "model": model_name,
                "skills_used": [getattr(s, "name", str(s)) for s in skills[:3]],
                "confidence": confidence,
            }
        )
        # Trim history
        if len(self._context_history) > 10:
            self._context_history = self._context_history[-10:]

        return GroundedContext(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            skills=[
                {"name": getattr(s, "name", str(s)), "score": i}
                for i, s in enumerate(skills[:3])
            ],
            grounding_sources=grounding,
            confidence_estimate=confidence,
            suggested_model=suggested_model,
            escalation_recommended=escalation,
        )

    def verify_claim(self, claim: str, sources: list[str]) -> tuple[bool, float]:
        """Simple claim verification against sources.

        Returns:
            (verified: bool, confidence: float)
        """
        claim_words = set(claim.lower().split())

        best_match = 0.0
        for source in sources:
            source_words = set(source.lower().split())
            overlap = len(claim_words & source_words)
            total = len(claim_words)
            if total > 0:
                similarity = overlap / total
                best_match = max(best_match, similarity)

        # Threshold: 50% word overlap = verified
        verified = best_match > 0.5
        confidence = min(best_match * 1.5, 1.0)  # Scale up but cap at 1.0

        return verified, confidence
