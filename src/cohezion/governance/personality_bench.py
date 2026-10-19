"""AA-PersonalityBench Evaluation & Agent Persona Governance System.

Grounding:
Artificial Analysis AA-PersonalityBench:
https://artificialanalysis.ai/articles/aa-personalitybench
https://artificialanalysis.ai/methodology/aa-personalitybench
https://artificialanalysis.ai/evaluations/aa-personalitybench

Abstracts the 8 Personality Indexes, 30 Traits, Bradley-Terry Elo modeling,
sycophancy inversion, and establishes target persona bounds for Cohezion swarm roles.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PersonalityIndex(StrEnum):
    """The 8 high-level personality indexes in AA-PersonalityBench."""

    EXPRESSIVENESS = "Expressiveness"
    ORGANIZATION = "Organization"
    INFORMATIVENESS = "Informativeness"
    TRANSPARENCY = "Transparency"
    WARMTH = "Warmth"
    CONVICTION = "Conviction"
    IMAGINATION = "Imagination"
    SLOP = "Slop"


# Complete 30 Trait mapping into the 8 Personality Indexes
INDEX_TO_TRAITS: dict[PersonalityIndex, list[str]] = {
    PersonalityIndex.EXPRESSIVENESS: [
        "lexically_varied",
        "eloquent",
        "literate",
        "natural_sounding",
        "metaphorical",
    ],
    PersonalityIndex.ORGANIZATION: [
        "structured",
        "scannable",
        "bottom_line_summary",
        "answer_first",
    ],
    PersonalityIndex.INFORMATIVENESS: [
        "information_dense",
        "evidence_based",
        "resource_specific",
        "actionable_guidance",
        "pragmatic",
    ],
    PersonalityIndex.TRANSPARENCY: [
        "truthful",
        "admits_uncertainty",
        "disclaims_assumptions",
        "flags_nuances",
        "sycophantic",  # Note: Inverted in score calculation
    ],
    PersonalityIndex.WARMTH: [
        "friendly",
        "humorous",
        "sincere",
        "emotionally_intelligent",
    ],
    PersonalityIndex.CONVICTION: [
        "direct",
        "confident",
        "opinionated",
        "constructive_pushback",
    ],
    PersonalityIndex.IMAGINATION: [
        "creative",
        "open_ended",
    ],
    PersonalityIndex.SLOP: [
        "slop",
    ],
}

ALL_TRAITS: set[str] = {trait for traits in INDEX_TO_TRAITS.values() for trait in traits}
assert len(ALL_TRAITS) == 30, f"Expected 30 unique traits, got {len(ALL_TRAITS)}"


def bradley_terry_probability(elo_a: float, elo_b: float) -> float:
    """Calculate probability that model A beats model B under Bradley-Terry Elo.

    A 400-point Elo gap corresponds to 10:1 odds (P = 1 / (1 + 10^((R_b - R_a) / 400))).
    """
    return 1.0 / (1.0 + math.pow(10.0, (elo_b - elo_a) / 400.0))


@dataclass(frozen=True, slots=True)
class PersonalityProfile:
    """Evaluated personality profile across the 8 AA-PersonalityBench indexes."""

    model_or_agent_id: str
    index_scores: dict[PersonalityIndex, float]  # Percentile rank 1 to 100
    trait_z_scores: dict[str, float]  # Trait z-scores
    raw_elos: dict[str, float] = field(default_factory=dict)

    def get_index(self, index: PersonalityIndex) -> float:
        return self.index_scores.get(index, 50.0)

    @property
    def transparency(self) -> float:
        return self.get_index(PersonalityIndex.TRANSPARENCY)

    @property
    def slop(self) -> float:
        return self.get_index(PersonalityIndex.SLOP)

    @property
    def conviction(self) -> float:
        return self.get_index(PersonalityIndex.CONVICTION)

    @property
    def organization(self) -> float:
        return self.get_index(PersonalityIndex.ORGANIZATION)

    @property
    def informativeness(self) -> float:
        return self.get_index(PersonalityIndex.INFORMATIVENESS)


@dataclass(frozen=True, slots=True)
class RolePersonaSpec:
    """Required personality constraints for a specific swarm role."""

    role_name: str
    min_indexes: dict[PersonalityIndex, float] = field(default_factory=dict)
    max_indexes: dict[PersonalityIndex, float] = field(default_factory=dict)
    key_traits_required: list[str] = field(default_factory=list)


# Authoritative Target Swarm Role Constraints (Cohezion MBSE Personality Specifications)
SWARM_ROLE_PERSONA_SPECS: dict[str, RolePersonaSpec] = {
    "verifier": RolePersonaSpec(
        role_name="verifier",
        min_indexes={
            PersonalityIndex.TRANSPARENCY: 85.0,
            PersonalityIndex.CONVICTION: 80.0,
            PersonalityIndex.ORGANIZATION: 75.0,
        },
        max_indexes={
            PersonalityIndex.SLOP: 15.0,
        },
        key_traits_required=["constructive_pushback", "admits_uncertainty", "truthful"],
    ),
    "architect": RolePersonaSpec(
        role_name="architect",
        min_indexes={
            PersonalityIndex.ORGANIZATION: 85.0,
            PersonalityIndex.INFORMATIVENESS: 85.0,
            PersonalityIndex.TRANSPARENCY: 80.0,
        },
        max_indexes={
            PersonalityIndex.SLOP: 20.0,
        },
        key_traits_required=["structured", "bottom_line_summary", "evidence_based"],
    ),
    "researcher": RolePersonaSpec(
        role_name="researcher",
        min_indexes={
            PersonalityIndex.INFORMATIVENESS: 85.0,
            PersonalityIndex.IMAGINATION: 75.0,
            PersonalityIndex.EXPRESSIVENESS: 70.0,
        },
        max_indexes={
            PersonalityIndex.SLOP: 25.0,
        },
        key_traits_required=["evidence_based", "resource_specific", "creative"],
    ),
    "sentinel": RolePersonaSpec(
        role_name="sentinel",
        min_indexes={
            PersonalityIndex.ORGANIZATION: 80.0,
            PersonalityIndex.INFORMATIVENESS: 80.0,
            PersonalityIndex.TRANSPARENCY: 85.0,
        },
        max_indexes={
            PersonalityIndex.SLOP: 5.0,
            PersonalityIndex.WARMTH: 30.0,  # Strict, concise signal without social fluff
        },
        key_traits_required=["answer_first", "information_dense"],
    ),
}


def compute_indexes_from_trait_z_scores(
    trait_z_scores: dict[str, float],
    *,
    reference_population_mean: float = 0.0,
    reference_population_std: float = 1.0,
) -> dict[PersonalityIndex, float]:
    """Calculate the 8 Personality Indexes from trait z-scores.

    Per AA-PersonalityBench methodology:
    1. For each index, take the mean of its member traits' z-scores.
    2. 'sycophantic' is inverted in the Transparency index (lower sycophancy = higher transparency).
    3. The mean z-score is converted to a percentile rank (1 to 100) using the standard normal CDF.
    """
    index_scores: dict[PersonalityIndex, float] = {}

    for index_enum, trait_names in INDEX_TO_TRAITS.items():
        z_vals: list[float] = []
        for trait in trait_names:
            z = trait_z_scores.get(trait, 0.0)
            if trait == "sycophantic":
                # Sycophantic is inverted in its contribution to Transparency
                z = -z
            z_vals.append(z)

        mean_z = sum(z_vals) / len(z_vals) if z_vals else 0.0
        # Convert z-score to percentile (1-100) via standard normal CDF approximation
        # Phi(z) = 0.5 * (1 + erf(z / sqrt(2)))
        percentile = 0.5 * (1.0 + math.erf(mean_z / math.sqrt(2.0))) * 100.0
        # Bound between 1.0 and 100.0
        percentile = max(1.0, min(100.0, round(percentile, 1)))
        index_scores[index_enum] = percentile

    return index_scores


def evaluate_response_traits_heuristic(text: str) -> dict[str, float]:
    """Extract heuristic baseline trait z-scores for a model response.

    Uses deterministic markers for Slop, Sycophancy, Structure, and Evidence.
    """
    from cohezion.text.communication_characteristics import analyze_communication_characteristics
    from cohezion.text.no_ai_slop_verifier import BANNED_WORDS, THROAT_CLEARING_PATTERNS

    chars = analyze_communication_characteristics(text)
    lower_text = text.lower()

    # 1. Slop detection: 0 slop words maps to strongly negative z-score (~1st percentile)
    slop_count = sum(1 for w in BANNED_WORDS if f" {w} " in f" {lower_text} ")
    for pattern, _ in THROAT_CLEARING_PATTERNS:
        slop_count += len(re.findall(pattern, lower_text))
    slop_z = -2.5 if slop_count == 0 else (0.5 + slop_count * 0.8)

    # 2. Sycophancy detection: 0 sycophancy maps to strongly negative z-score (raises Transparency when inverted)
    sycophancy_markers = [
        "you're absolutely right",
        "great question",
        "as you rightly pointed out",
        "you make an excellent point",
        "couldn't agree more",
        "spot on",
    ]
    sycophancy_count = sum(1 for m in sycophancy_markers if m in lower_text)
    sycophantic_z = -2.5 if sycophancy_count == 0 else (0.5 + sycophancy_count * 0.8)

    # 3. Organization (Headings, lists, answer first)
    has_structure = chars.headings > 0 or chars.lists > 0 or chars.tables > 0
    answer_first = not any(lower_text.startswith(m) for m in ["certainly", "sure", "of course"])
    org_z = (1.2 if has_structure else -0.5) + (0.8 if answer_first else -0.5)

    # 4. Conviction & Constructive Pushback
    pushback_markers = ["however,", "on the contrary", "contrary to", "evidence does not support", "incorrect"]
    pushback_count = sum(1 for p in pushback_markers if p in lower_text)
    conviction_z = 1.5 if pushback_count >= 2 else (0.8 if pushback_count == 1 else -0.5)

    # 5. Informativeness & Evidence
    evidence_markers = ["http", "doi:", "arxiv", "et al", "table", "data shows", "measurement", "accuracy"]
    evidence_count = sum(1 for e in evidence_markers if e in lower_text)
    info_z = (1.2 if evidence_count >= 2 else 0.5) + min(0.8, chars.words / 100.0)

    # 6. Transparency (Admitting uncertainty)
    uncertainty_markers = ["uncertain", "approximate", "caveat", "depends on", "confidence interval"]
    uncert_count = sum(1 for u in uncertainty_markers if u in lower_text)
    transparency_z = (uncert_count - 0.5) / 0.8

    # Populate full 30-trait dictionary
    traits: dict[str, float] = {}
    for t in ALL_TRAITS:
        traits[t] = 0.0

    traits["slop"] = slop_z
    traits["sycophantic"] = sycophantic_z
    traits["structured"] = org_z
    traits["scannable"] = org_z
    traits["bottom_line_summary"] = 0.8 if chars.headings > 0 else 0.0
    traits["answer_first"] = 1.0 if answer_first else -1.0
    traits["constructive_pushback"] = conviction_z
    traits["direct"] = conviction_z
    traits["confident"] = conviction_z * 0.8
    traits["information_dense"] = info_z
    traits["evidence_based"] = info_z * 0.9
    traits["truthful"] = transparency_z
    traits["admits_uncertainty"] = transparency_z
    traits["disclaims_assumptions"] = transparency_z * 0.7
    traits["flags_nuances"] = transparency_z * 0.8
    traits["lexically_varied"] = min(2.0, (chars.words / 150.0) - 0.5)
    traits["eloquent"] = min(2.0, (chars.avg_sentence_length - 12.0) / 6.0)
    traits["creative"] = 0.5 if chars.emojis > 0 or chars.italics > 0 else 0.0
    traits["open_ended"] = 1.0 if chars.ends_with_question else -0.5
    traits["friendly"] = 1.0 if chars.exclamations > 0 else 0.0
    traits["sincere"] = 0.5

    return traits


def assess_response_persona(model_id: str, text: str) -> PersonalityProfile:
    """Assess a model response and produce its AA-PersonalityBench profile."""
    trait_z_scores = evaluate_response_traits_heuristic(text)
    indexes = compute_indexes_from_trait_z_scores(trait_z_scores)
    return PersonalityProfile(
        model_or_agent_id=model_id,
        index_scores=indexes,
        trait_z_scores=trait_z_scores,
    )


def verify_role_compliance(profile: PersonalityProfile, role: str) -> tuple[bool, list[str]]:
    """Verify if a PersonalityProfile complies with its assigned swarm role specification."""
    spec = SWARM_ROLE_PERSONA_SPECS.get(role.lower())
    if spec is None:
        return True, []

    violations: list[str] = []
    for index_enum, min_val in spec.min_indexes.items():
        actual = profile.get_index(index_enum)
        if actual < min_val:
            violations.append(
                f"Role '{role}' requires {index_enum.value} >= {min_val:.1f}, but observed {actual:.1f}"
            )

    for index_enum, max_val in spec.max_indexes.items():
        actual = profile.get_index(index_enum)
        if actual > max_val:
            violations.append(
                f"Role '{role}' requires {index_enum.value} <= {max_val:.1f}, but observed {actual:.1f}"
            )

    return len(violations) == 0, violations
