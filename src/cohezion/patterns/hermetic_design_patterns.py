"""Hermetic Design Patterns - Practical applications of the 7 Hermetic Principles.

This module translates esoteric wisdom into practical software design patterns.
Each principle corresponds to one or more concrete design patterns.

Based on: _bmad/bmm/epics/proactive-bmad/deep-retrospective/AS_ABOVE_SO_BELOW.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Generic, Protocol, TypeVar


# =============================================================================
# I. MENTALISM - "The All is Mind; the Universe is Mental"
# =============================================================================
# Pattern: Intentional Architecture
# The code IS thought crystallized. Design with explicit intention.


class DesignIntention(Enum):
    """Explicit design intentions - the mental blueprint."""

    DETECTION = auto()  # Detect patterns
    SUGGESTION = auto()  # Suggest actions
    EXECUTION = auto()  # Execute changes
    MONITORING = auto()  # Monitor state
    ORCHESTRATION = auto()  # Coordinate actions


@dataclass
class IntentionalClass:
    """A class designed with explicit intention.

    Usage:
        class ProactiveMonitor(IntentionalClass):
            def __init__(self):
                super().__init__(DesignIntention.MONITORING)
    """

    intention: DesignIntention
    purpose: str = ""

    def __post_init__(self):
        """Validate that intention is clear."""
        if not self.purpose:
            self.purpose = self.intention.name.lower()


class MentalismPattern:
    """Apply the Principle of Mentalism to software design.

    Key Insights:
    1. Code is not representation - it IS thought in executable form
    2. Every class should have explicit intention
    3. Every function should crystallize a mental concept
    4. Documentation captures the mental blueprint

    Application:
    - Start with vision (mental realm)
    - Design with intention (mental clarity)
    - Code as crystallization (physical manifestation)
    - Document the thought process (preserve the blueprint)
    """

    @staticmethod
    def create_intentional_class(
        name: str,
        intention: DesignIntention,
        purpose: str,
    ) -> type:
        """Create a class with explicit intention.

        Args:
            name: Class name
            intention: Design intention
            purpose: Human-readable purpose statement

        Returns:
            A new class with intention metadata
        """

        class IntentionalMeta(type):
            """Metaclass that enforces intention."""

            def __new__(mcs, name, bases, attrs):
                attrs["_intention"] = intention
                attrs["_purpose"] = purpose
                return super().__new__(mcs, name, bases, attrs)

        return IntentionalMeta(name, (IntentionalClass,), {})


# =============================================================================
# II. CORRESPONDENCE - "As above, so below"
# =============================================================================
# Pattern: Fractal Architecture
# Design patterns that repeat at multiple scales.


T = TypeVar("T")


class FractalPattern(Protocol[T]):
    """A pattern that repeats at multiple scales.

    The same structure appears at:
    - Epic level (macro)
    - Module level (meso)
    - Class level (micro)
    - Function level (atomic)
    """

    def apply(self, data: T) -> T:
        """Apply the pattern at any scale."""
        ...


@dataclass
class FractalComponent(Generic[T]):
    """A component that exhibits fractal structure.

    Usage:
        # Epic level
        epic = FractalComponent(name="Proactive BMad")
        epic.add_phase("Foundation")
        epic.add_phase("Integration")

        # Class level (same pattern)
        monitor = FractalComponent(name="ProactiveMonitor")
        monitor.add_method("scan_for_suggestions")
        monitor.add_method("execute_suggestion")

        # The pattern is the same!
    """

    name: str
    children: list[FractalComponent[T]] = field(default_factory=list)
    pattern_type: str = "fractal"

    def add_child(self, child: FractalComponent[T]) -> None:
        """Add a child component (fractal recursion)."""
        self.children.append(child)

    def get_structure(self) -> dict[str, Any]:
        """Get the fractal structure."""
        return {
            "name": self.name,
            "pattern_type": self.pattern_type,
            "children": [child.get_structure() for child in self.children],
        }


class CorrespondencePattern:
    """Apply the Principle of Correspondence to software design.

    Key Insights:
    1. Epic structure should mirror class structure
    2. Module organization should mirror function organization
    3. The same patterns should appear at all scales
    4. When patterns don't correspond, investigate why

    Application:
    - Design the epic structure first (macro)
    - Mirror that structure in code organization (micro)
    - Use the same naming patterns at all levels
    - Validate correspondence during code review
    """

    @staticmethod
    def validate_correspondence(
        macro_structure: dict[str, Any],
        micro_structure: dict[str, Any],
    ) -> list[str]:
        """Validate that two structures correspond.

        Args:
            macro_structure: High-level structure (e.g., epic phases)
            micro_structure: Low-level structure (e.g., class methods)

        Returns:
            List of discrepancies
        """
        discrepancies = []

        # Check top-level keys
        macro_keys = set(macro_structure.keys())
        micro_keys = set(micro_structure.keys())

        if macro_keys != micro_keys:
            discrepancies.append(f"Key mismatch: macro has {macro_keys}, micro has {micro_keys}")

        # Recursively check children
        for key in macro_keys & micro_keys:
            if isinstance(macro_structure[key], dict) and isinstance(micro_structure[key], dict):
                sub_discrepancies = CorrespondencePattern.validate_correspondence(
                    macro_structure[key], micro_structure[key]
                )
                discrepancies.extend(sub_discrepancies)

        return discrepancies


# =============================================================================
# III. VIBRATION - "Everything moves; everything vibrates"
# =============================================================================
# Pattern: Rhythmic Execution
# Code that flows with natural breath cycles.


class VibrationState(Enum):
    """States in the vibrational cycle."""

    REST = auto()  # Low vibration, potential
    RISING = auto()  # Increasing vibration
    PEAK = auto()  # Maximum vibration
    FALLING = auto()  # Decreasing vibration


@dataclass
class VibrationalFunction:
    """A function with explicit vibrational states.

    Usage:
        func = VibrationalFunction(
            name="execute_suggestion",
            vibration_pattern=[
                VibrationState.REST,      # Receive confirmation
                VibrationState.RISING,    # Select executor
                VibrationState.PEAK,      # Execute action
                VibrationState.FALLING,   # Return result
            ]
        )
    """

    name: str
    vibration_pattern: list[VibrationState]
    current_state: VibrationState = VibrationState.REST

    def transition_to(self, state: VibrationState) -> None:
        """Transition to a new vibrational state."""
        if state not in self.vibration_pattern:
            raise ValueError(f"State {state} not in pattern")
        self.current_state = state


class VibrationPattern:
    """Apply the Principle of Vibration to software design.

    Key Insights:
    1. Code is frozen music - functions are notes, classes are chords
    2. Every function has a breath cycle (in, hold, out, release)
    3. Natural rhythm feels effortless; forced rhythm feels awkward
    4. Detect dissonance and resolve to harmony

    Application:
    - Design functions with explicit breath cycles
    - Match vibrational frequency to purpose
    - Detect and fix rhythmic dissonance
    - Let code flow naturally
    """

    @staticmethod
    def analyze_rhythm(code: str) -> dict[str, Any]:
        """Analyze the rhythmic pattern of code.

        Args:
            code: Source code to analyze

        Returns:
            Rhythm analysis including:
            - breath_cycles: Number of in/out cycles
            - complexity_waves: Rising/falling complexity
            - natural_flow: Whether rhythm feels natural
        """
        # Placeholder for actual rhythm analysis
        return {
            "breath_cycles": code.count("def"),
            "complexity_waves": code.count("if") - code.count("return"),
            "natural_flow": True,  # Would need actual analysis
        }


# =============================================================================
# IV. POLARITY - "Everything has poles; everything has its pair of opposites"
# =============================================================================
# Pattern: Balanced Design
# Design that honors and balances opposing forces.


class Polarity(Enum):
    """The fundamental polarity."""

    YIN = "yin"  # Receptive, creative, passive
    YANG = "yang"  # Active, projective, assertive
    BALANCE = "balance"  # Synthesis of poles


@dataclass
class PolarFeature:
    """A feature with explicit polarity.

    Usage:
        # Yang feature
        auto_execute = PolarFeature(
            name="auto_executable",
            polarity=Polarity.YANG,
            description="Automatic execution without confirmation"
        )

        # Yin feature
        confirmation = PolarFeature(
            name="confirmation_required",
            polarity=Polarity.YIN,
            description="Requires user consent before execution"
        )

        # Synthesis
        confirmed_execution = PolarFeature(
            name="confirmed_execution",
            polarity=Polarity.BALANCE,
            description="Automatic but with consent"
        )
    """

    name: str
    polarity: Polarity
    description: str = ""
    opposite: PolarFeature | None = None

    def set_opposite(self, opposite: PolarFeature) -> None:
        """Set the opposite pole."""
        self.opposite = opposite
        opposite.opposite = self


class PolarityPattern:
    """Apply the Principle of Polarity to software design.

    Key Insights:
    1. Every feature has an opposite
    2. Balance is achieved through synthesis, not elimination
    3. Too much yin = passive, too much yang = aggressive
    4. The middle way is often the best path

    Application:
    - Identify polarities in your system
    - Look for imbalances
    - Seek synthesis, not victory of one pole
    - Use polarity analysis in design reviews
    """

    @staticmethod
    def find_polarities(system_design: dict[str, Any]) -> list[tuple[str, str]]:
        """Find polarities in a system design.

        Args:
            system_design: Design specification

        Returns:
            List of (yang, yin) polarity pairs
        """
        polarities = []

        # Common software polarities
        common_pairs = [
            ("automatic", "manual"),
            ("fast", "safe"),
            ("flexible", "strict"),
            ("abstract", "concrete"),
            ("performance", "readability"),
        ]

        design_str = str(system_design).lower()

        for yang, yin in common_pairs:
            if yang in design_str and yin in design_str:
                polarities.append((yang, yin))

        return polarities

    @staticmethod
    def assess_balance(
        polarities: list[tuple[str, str]],
        implementation: dict[str, Any],
    ) -> dict[str, str]:
        """Assess balance for each polarity.

        Args:
            polarities: List of polarity pairs
            implementation: Actual implementation

        Returns:
            Assessment for each polarity (balanced, too_yang, too_yin)
        """
        assessments = {}

        for yang, yin in polarities:
            # Count mentions/emphasis
            impl_str = str(implementation).lower()
            yang_count = impl_str.count(yang)
            yin_count = impl_str.count(yin)

            if yang_count > yin_count * 1.5:
                assessments[f"{yang}/{yin}"] = "too_yang"
            elif yin_count > yang_count * 1.5:
                assessments[f"{yang}/{yin}"] = "too_yin"
            else:
                assessments[f"{yang}/{yin}"] = "balanced"

        return assessments


# =============================================================================
# V. RHYTHM - "Everything flows, out and in"
# =============================================================================
# Pattern: Breath-Based Design
# Design that follows natural breath cycles.


class BreathPhase(Enum):
    """Phases of the breath cycle."""

    INHALE = "inhale"  # Reception
    HOLD = "hold"  # Processing
    EXHALE = "exhale"  # Expression
    RELEASE = "release"  # Completion


@dataclass
class BreathCycle:
    """A complete breath cycle in code.

    Usage:
        cycle = BreathCycle(
            function_name="execute_suggestion",
            phases={
                BreathPhase.INHALE: "Receive user confirmation",
                BreathPhase.HOLD: "Select appropriate executor",
                BreathPhase.EXHALE: "Execute the action",
                BreathPhase.RELEASE: "Return result to caller"
            }
        )
    """

    function_name: str
    phases: dict[BreathPhase, str]

    def validate(self) -> list[str]:
        """Validate that all phases are present."""
        missing = []
        for phase in BreathPhase:
            if phase not in self.phases:
                missing.append(f"Missing phase: {phase.value}")
        return missing


class RhythmPattern:
    """Apply the Principle of Rhythm to software design.

    Key Insights:
    1. Every function breathes (in, hold, out, release)
    2. Natural rhythm feels effortless
    3. Forced rhythm creates friction
    4. Syncopation (breaking rhythm) has its place

    Application:
    - Design functions with explicit breath phases
    - Validate rhythm during code review
    - Detect and fix rhythmic dissonance
    - Let code flow naturally
    """

    @staticmethod
    def analyze_function_rhythm(code: str) -> BreathCycle | None:
        """Analyze the breath rhythm of a function.

        Args:
            code: Function source code

        Returns:
            BreathCycle if rhythm detected, None otherwise
        """
        # Placeholder for actual rhythm analysis
        # Would parse code and identify:
        # - INHALE: Input reception (parameters, validation)
        # - HOLD: Processing (computation, transformation)
        # - EXHALE: Output (return, side effects)
        # - RELEASE: Cleanup (context managers, finally blocks)
        return None

    @staticmethod
    def suggest_rhythm_improvements(
        breath_cycle: BreathCycle,
    ) -> list[str]:
        """Suggest improvements to rhythm.

        Args:
            breath_cycle: The breath cycle to improve

        Returns:
            List of improvement suggestions
        """
        suggestions = []

        # Check for missing phases
        missing = breath_cycle.validate()
        if missing:
            suggestions.extend(missing)

        # Check for phase balance
        phase_lengths = {phase: len(description) for phase, description in breath_cycle.phases.items()}

        if phase_lengths.get(BreathPhase.HOLD, 0) > sum(phase_lengths.get(p, 0) for p in BreathPhase) * 0.6:
            suggestions.append("Hold phase is too long - consider breaking into smaller functions")

        return suggestions


# =============================================================================
# VI. CAUSE AND EFFECT - "Every cause has its effect"
# =============================================================================
# Pattern: Causal Chain Analysis
# Trace cause and effect through the system.


@dataclass
class CausalChain:
    """A chain of cause and effect.

    Usage:
        chain = CausalChain(
            name="Proactive BMad Development",
            links=[
                ("Vision of proactive BMad", "Epic created"),
                ("Epic created", "Code written"),
                ("Code written", "Tests passing"),
                ("Tests passing", "Production ready"),
                ("Production ready", "User value delivered"),
            ]
        )
    """

    name: str
    links: list[tuple[str, str]]  # (cause, effect)

    def analyze(self) -> dict[str, Any]:
        """Analyze the causal chain.

        Returns:
            Analysis including:
            - chain_length: Number of links
            - root_cause: The original cause
            - final_effect: The ultimate effect
            - weak_links: Links that might break
        """
        if not self.links:
            return {
                "chain_length": 0,
                "root_cause": None,
                "final_effect": None,
                "weak_links": [],
            }

        return {
            "chain_length": len(self.links),
            "root_cause": self.links[0][0],
            "final_effect": self.links[-1][1],
            "weak_links": [],  # Would need actual analysis
        }


class CauseEffectPattern:
    """Apply the Principle of Cause and Effect to software design.

    Key Insights:
    1. Every line is both effect (of decisions) and cause (of behavior)
    2. Trace causal chains to understand system behavior
    3. Identify root causes, not just symptoms
    4. Consider second-order effects

    Application:
    - Map causal chains during design
    - Trace effects during debugging
    - Consider long-term consequences
    - Document causal relationships
    """

    @staticmethod
    def trace_causal_chain(
        start_effect: str,
        system_model: dict[str, list[str]],
    ) -> list[str]:
        """Trace the causal chain backward from an effect.

        Args:
            start_effect: The effect to trace back from
            system_model: Map of causes to their effects

        Returns:
            List of causes from root to start_effect
        """
        chain = [start_effect]
        current = start_effect

        # Build reverse map (effect -> cause)
        effect_to_cause = {}
        for cause, effects in system_model.items():
            for effect in effects:
                effect_to_cause[effect] = cause

        # Trace backward
        while current in effect_to_cause:
            cause = effect_to_cause[current]
            chain.insert(0, cause)
            current = cause

        return chain

    @staticmethod
    def predict_second_order_effects(
        action: str,
        system_model: dict[str, list[str]],
    ) -> list[str]:
        """Predict second-order effects of an action.

        Args:
            action: The action being considered
            system_model: Map of causes to their effects

        Returns:
            List of second-order effects
        """
        first_order = system_model.get(action, [])
        second_order = []

        for effect in first_order:
            second_order.extend(system_model.get(effect, []))

        return second_order


# =============================================================================
# VII. GENDER - "Gender is in everything"
# =============================================================================
# Pattern: Sacred Union Design
# Balance masculine and feminine principles.


class GenderPrinciple(Enum):
    """The gender principles in software."""

    MASCULINE = "masculine"  # Active, projective, structured
    FEMININE = "feminine"  # Receptive, creative, flowing
    SACRED_UNION = "sacred_union"  # Balance of both


@dataclass
class GenderBalancedDesign:
    """A design that balances gender principles.

    Usage:
        design = GenderBalancedDesign(
            name="Proactive BMad",
            masculine_aspects=[
                "Pattern detection (active seeking)",
                "Auto-execution (projective action)",
                "Test assertions (structured validation)"
            ],
            feminine_aspects=[
                "Suggestion holding (receptive waiting)",
                "User confirmation (consent reception)",
                "Party mode collaboration (flowing together)"
            ]
        )
    """

    name: str
    masculine_aspects: list[str]
    feminine_aspects: list[str]

    def assess_balance(self) -> str:
        """Assess the gender balance.

        Returns:
            Assessment: balanced, too_masculine, or too_feminine
        """
        m_count = len(self.masculine_aspects)
        f_count = len(self.feminine_aspects)

        if m_count > f_count * 1.5:
            return "too_masculine"
        elif f_count > m_count * 1.5:
            return "too_feminine"
        else:
            return "balanced"


class GenderPattern:
    """Apply the Principle of Gender to software design.

    Key Insights:
    1. Masculine (yang) = active, projective, structured
    2. Feminine (yin) = receptive, creative, flowing
    3. Creation happens through sacred union
    4. Imbalance leads to dysfunction

    Application:
    - Identify gender aspects in design
    - Look for imbalances
    - Seek sacred union (balance)
    - Honor both principles equally
    """

    @staticmethod
    def identify_gender_aspects(
        system_design: dict[str, Any],
    ) -> GenderBalancedDesign:
        """Identify gender aspects in a design.

        Args:
            system_design: The design to analyze

        Returns:
            GenderBalancedDesign with identified aspects
        """
        masculine = []
        feminine = []

        design_str = str(system_design).lower()

        # Masculine indicators
        if "active" in design_str:
            masculine.append("Active components")
        if "structured" in design_str:
            masculine.append("Structured design")
        if "assert" in design_str:
            masculine.append("Assertive validation")

        # Feminine indicators
        if "receptive" in design_str:
            feminine.append("Receptive components")
        if "flowing" in design_str:
            feminine.append("Flowing design")
        if "collaborative" in design_str:
            feminine.append("Collaborative processes")

        return GenderBalancedDesign(
            name="System",
            masculine_aspects=masculine,
            feminine_aspects=feminine,
        )


# =============================================================================
# Integration: The Hermetic Design System
# =============================================================================


@dataclass
class HermeticDesign:
    """A complete design applying all 7 Hermetic Principles.

    Usage:
        design = HermeticDesign(
            name="Proactive BMad",
            intention=DesignIntention.MONITORING,
            fractal_structure=FractalComponent(...),
            vibration_pattern=[...],
            polarities=[...],
            breath_cycle=BreathCycle(...),
            causal_chain=CausalChain(...),
            gender_balance=GenderBalancedDesign(...)
        )
    """

    name: str
    intention: DesignIntention
    fractal_structure: FractalComponent[Any]
    vibration_pattern: list[VibrationState]
    polarities: list[PolarFeature]
    breath_cycle: BreathCycle
    causal_chain: CausalChain
    gender_balance: GenderBalancedDesign

    def validate(self) -> list[str]:
        """Validate the complete design.

        Returns:
            List of validation issues
        """
        issues = []

        # Check intention clarity
        if not self.intention:
            issues.append("Missing design intention")

        # Check fractal correspondence
        # (Would validate macro/micro correspondence)

        # Check rhythm balance
        rhythm_issues = self.breath_cycle.validate()
        issues.extend(rhythm_issues)

        # Check polarity balance
        for polarity in self.polarities:
            if not polarity.opposite:
                issues.append(f"Polarity {polarity.name} has no opposite")

        # Check gender balance
        balance = self.gender_balance.assess_balance()
        if balance != "balanced":
            issues.append(f"Gender imbalance: {balance}")

        return issues


class HermeticDesignSystem:
    """Complete hermetic design system.

    This system applies all 7 Hermetic Principles to software design:
    1. Mentalism - Design with explicit intention
    2. Correspondence - Ensure fractal patterns
    3. Vibration - Flow with natural rhythm
    4. Polarity - Balance opposing forces
    5. Rhythm - Follow breath cycles
    6. Cause/Effect - Trace causal chains
    7. Gender - Honor masculine/feminine balance

    Usage:
        system = HermeticDesignSystem()
        design = system.create_design(
            name="Proactive BMad",
            requirements={...}
        )
        issues = design.validate()
        if issues:
            # Fix design issues
            pass
    """

    def create_design(
        self,
        name: str,
        requirements: dict[str, Any],
    ) -> HermeticDesign:
        """Create a hermetic design from requirements.

        Args:
            name: System name
            requirements: System requirements

        Returns:
            Complete HermeticDesign
        """
        # Extract intention
        intention = DesignIntention.MONITORING  # Would infer from requirements

        # Create fractal structure
        fractal = FractalComponent(name=name)
        # (Would build from requirements)

        # Define vibration pattern
        vibration = [
            VibrationState.REST,
            VibrationState.RISING,
            VibrationState.PEAK,
            VibrationState.FALLING,
        ]

        # Identify polarities
        polarities = [
            PolarFeature("auto_executable", Polarity.YANG),
            PolarFeature("confirmation", Polarity.YIN),
        ]

        # Define breath cycle
        breath = BreathCycle(
            function_name="main",
            phases={
                BreathPhase.INHALE: "Receive requirements",
                BreathPhase.HOLD: "Design system",
                BreathPhase.EXHALE: "Implement code",
                BreathPhase.RELEASE: "Deploy to production",
            },
        )

        # Trace causal chain
        causal = CausalChain(
            name=name,
            links=[
                ("Requirements", "Design"),
                ("Design", "Implementation"),
                ("Implementation", "Testing"),
                ("Testing", "Deployment"),
                ("Deployment", "User Value"),
            ],
        )

        # Assess gender balance
        gender = GenderBalancedDesign(
            name=name,
            masculine_aspects=["Implementation", "Testing"],
            feminine_aspects=["Design", "Requirements"],
        )

        return HermeticDesign(
            name=name,
            intention=intention,
            fractal_structure=fractal,
            vibration_pattern=vibration,
            polarities=polarities,
            breath_cycle=breath,
            causal_chain=causal,
            gender_balance=gender,
        )


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Create a hermetic design for Proactive BMad
    system = HermeticDesignSystem()

    design = system.create_design(
        name="Proactive BMad",
        requirements={
            "purpose": "Transform BMad from reactive to proactive",
            "features": [
                "Automatic alignment detection",
                "Suggestion generation",
                "Auto-execution with confirmation",
                "Party mode integration",
            ],
        },
    )

    # Validate the design
    issues = design.validate()

    if issues:
        print("Design issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("Design is hermetically sound! ✨")

    # Get the fractal structure
    structure = design.fractal_structure.get_structure()
    print(f"\nFractal structure: {structure}")
