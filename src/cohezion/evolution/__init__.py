"""Autogenesis-inspired self-evolution for Cohezion skills.

Provides SEPL (Self Evolution Protocol Layer): propose → assess → commit
improvement loop for PRIME skill definitions, using local Lemonade inference.

Based on: Autogenesis (Zhang et al., 2026) https://arxiv.org/abs/2604.15034
"""

from cohezion.evolution.reflection_optimizer import OptimizationResult, ReflectionOptimizer
from cohezion.evolution.skill_optimizer import SkillOptimizer
from cohezion.evolution.variable import Variable


__all__ = ["OptimizationResult", "ReflectionOptimizer", "SkillOptimizer", "Variable"]
