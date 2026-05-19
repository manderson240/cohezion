"""Textgrad-style Variable for Cohezion skill evolution.

Adapted from Autogenesis (Zhang et al., 2026) — simplified for skill prompt
optimization without graphviz/cloud-model dependencies. Supports text gradient
backpropagation through prompt composition graphs.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Variable:
    """A prompt or skill component that can be improved via text gradients.

    A Variable wraps a string value (skill section, prompt template, instruction)
    and tracks feedback (text gradients) that indicate what to improve.
    Setting require_grad=True marks it as trainable by the optimizer.
    """

    name: str
    value: str
    description: str = ""
    require_grad: bool = False

    # Text gradients: natural language feedback about what to improve
    gradients: list[str] = field(default_factory=list)
    # Optimization history for memory-augmented refinement
    history: list[dict[str, str]] = field(default_factory=list)

    def add_gradient(self, feedback: str) -> None:
        """Add a text gradient (feedback signal) to this variable."""
        if feedback and feedback not in self.gradients:
            self.gradients.append(feedback)

    def get_gradient_text(self) -> str:
        """Aggregate all gradients into a single feedback string."""
        return "\n".join(f"- {g}" for g in self.gradients)

    def reset_gradients(self) -> None:
        self.gradients.clear()

    def record_update(self, old_value: str, new_value: str, reasoning: str) -> None:
        """Record an optimization step in history."""
        self.history.append(
            {
                "old": old_value,
                "new": new_value,
                "reasoning": reasoning,
            }
        )

    def __repr__(self) -> str:
        grad_count = len(self.gradients)
        return (
            f"Variable(name={self.name!r}, len={len(self.value)}, "
            f"grad={self.require_grad}, gradients={grad_count})"
        )

    def __str__(self) -> str:
        return self.value


def from_prime_section(section_name: str, content: str, require_grad: bool = True) -> Variable:
    """Wrap a PRIME skill section as a trainable Variable."""
    return Variable(
        name=section_name,
        value=content,
        description=f"PRIME skill section: {section_name}",
        require_grad=require_grad,
    )
