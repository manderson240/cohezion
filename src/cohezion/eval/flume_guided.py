"""FLUME-guided code generation using journey metrics.

Uses phi_score and coherence to steer generation toward more successful outcomes.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GenerationGuidance:
    """Guidance for FLUME-guided generation."""

    target_phi_range: tuple[float, float] = (0.4, 0.7)
    target_coherence: float = 0.5
    preferred_patterns: list[str] | None = None
    avoid_patterns: list[str] | None = None


class FLUMEGuidedGenerator:
    """Generate code guided by FLUME journey metrics.

    Uses phi_score and coherence to steer generation toward
    patterns that have historically led to success.
    """

    def __init__(self, base_generator):
        """Initialize with base generator.

        Args:
            base_generator: Any generator with `generate(prompt) -> str`
        """
        self.base_generator = base_generator
        self.guidance = GenerationGuidance()
        self.success_patterns: list[dict[str, Any]] = []

    def set_guidance(self, guidance: GenerationGuidance) -> None:
        """Set generation guidance."""
        self.guidance = guidance

    def add_success_pattern(self, pattern: dict[str, Any]) -> None:
        """Add a successful pattern to learn from."""
        self.success_patterns.append(pattern)

    def generate(
        self,
        prompt: str,
        use_patterns: bool = True,
    ) -> str:
        """Generate with FLUME guidance.

        Args:
            prompt: Input prompt
            use_patterns: Whether to incorporate success patterns

        Returns:
            Generated code
        """
        # Build enhanced prompt with pattern context
        if use_patterns and self.success_patterns:
            prompt = self._enhance_prompt(prompt)

        # Generate
        result = self.base_generator.generate(prompt)

        # Post-process based on guidance
        result = self._apply_guidance(result)

        return result

    def _enhance_prompt(self, prompt: str) -> str:
        """Enhance prompt with success pattern context."""
        context = "\n\n".join(
            [
                f"Example successful solution:\n{p['completion'][:500]}"
                for p in self.success_patterns[:3]
            ]
        )

        return f"""{prompt}

参考以下成功模式:
{context}

生成类似风格的解决方案。"""

    def _apply_guidance(self, code: str) -> str:
        """Apply guidance filters to generated code."""
        # Simple heuristics based on guidance
        lines = code.split("\n")

        # Check for problematic patterns
        if self.guidance.avoid_patterns:
            for pattern in self.guidance.avoid_patterns:
                if pattern.lower() in code.lower():
                    logger.warning(f"Pattern '{pattern}' found in output")

        return code

    def learn_from_results(
        self,
        attempts: list[dict[str, Any]],
    ) -> None:
        """Learn from benchmark attempts to improve guidance.

        Args:
            attempts: List of {completion, success, phi_score, coherence}
        """
        successful = [a for a in attempts if a.get("success", False)]

        if successful:
            # Update patterns
            self.success_patterns = sorted(
                successful,
                key=lambda x: x.get("phi_score", 0),
                reverse=True,
            )[:10]

            # Analyze phi_score range for successes
            phi_scores = [s.get("phi_score", 0.5) for s in successful]
            if phi_scores:
                self.guidance.target_phi_range = (
                    min(phi_scores) * 0.8,
                    max(phi_scores) * 1.2,
                )

            logger.info(
                f"Learned from {len(successful)} successful attempts. "
                f"Phi range: {self.guidance.target_phi_range}"
            )


def create_flume_guided_runner(
    generator, phi_coherence_data: list[dict]
) -> FLUMEGuidedGenerator:
    """Create FLUME-guided runner from phi/coherence data.

    Args:
        generator: Base code generator
        phi_coherence_data: List of {completion, success, phi_score, coherence}

    Returns:
        Configured FLUMEGuidedGenerator
    """
    flume_gen = FLUMEGuidedGenerator(generator)
    flume_gen.learn_from_results(phi_coherence_data)
    return flume_gen
