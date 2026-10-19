"""Stylometric & PersonalityBench Feature Extractor for Kaggle Competitions.

Integrates Artificial Analysis AA-PersonalityBench (8 index vectors: Expressiveness,
Organization, Informativeness, Transparency, Warmth, Conviction, Imagination, Slop)
and the 21 deterministic communication characteristics into competitive feature
extractors for:
1. Name That LLM: Multi-class and pairwise LLM model attribution.
2. Gemma-4 Developer Agent: Pre-submission anti-slop & high-transparency gating.
3. ARC Prize (ARC-AGI-2 & ARC-AGI-3): De-biasing prompt search & hypothesis drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np

from cohezion.governance.personality_bench import (
    PersonalityIndex,
    PersonalityProfile,
    assess_response_persona,
    verify_role_compliance,
)
from cohezion.text.communication_characteristics import (
    CommunicationCharacteristics,
    analyze_communication_characteristics,
)


@dataclass(frozen=True)
class StylometricPersonalityFeatureVector:
    """Combined 29-dimensional feature representation."""

    # 21 communication characteristics
    characters: float
    words: float
    sentences: float
    paragraphs: float
    avg_sentence_length: float
    lists: float
    headings: float
    tables: float
    em_dashes: float
    contractions: float
    exclamations: float
    questions: float
    parentheses: float
    quotes: float
    colons: float
    ellipses: float
    bold: float
    italics: float
    emojis: float
    acronyms: float
    ends_with_question: float

    # 8 PersonalityBench index scores
    expressiveness: float
    organization: float
    informativeness: float
    transparency: float
    warmth: float
    conviction: float
    imagination: float
    slop: float

    def to_numpy(self) -> np.ndarray:
        """Export as a 1D float32 numpy array of length 29."""
        return np.array(
            [
                self.characters,
                self.words,
                self.sentences,
                self.paragraphs,
                self.avg_sentence_length,
                self.lists,
                self.headings,
                self.tables,
                self.em_dashes,
                self.contractions,
                self.exclamations,
                self.questions,
                self.parentheses,
                self.quotes,
                self.colons,
                self.ellipses,
                self.bold,
                self.italics,
                self.emojis,
                self.acronyms,
                self.ends_with_question,
                self.expressiveness,
                self.organization,
                self.informativeness,
                self.transparency,
                self.warmth,
                self.conviction,
                self.imagination,
                self.slop,
            ],
            dtype=np.float32,
        )

    @classmethod
    def feature_names(cls) -> List[str]:
        """Ordered list of feature names."""
        return [
            "characters",
            "words",
            "sentences",
            "paragraphs",
            "avg_sentence_length",
            "lists",
            "headings",
            "tables",
            "em_dashes",
            "contractions",
            "exclamations",
            "questions",
            "parentheses",
            "quotes",
            "colons",
            "ellipses",
            "bold",
            "italics",
            "emojis",
            "acronyms",
            "ends_with_question",
            "pb_expressiveness",
            "pb_organization",
            "pb_informativeness",
            "pb_transparency",
            "pb_warmth",
            "pb_conviction",
            "pb_imagination",
            "pb_slop",
        ]


class StylometricPersonalityExtractor:
    """Extracts zero-overhead stylometric and personality features from raw model text."""

    def extract_features(
        self, text: str, model_id: str = "candidate"
    ) -> StylometricPersonalityFeatureVector:
        """Extract all 29 features from input text."""
        comm: CommunicationCharacteristics = analyze_communication_characteristics(text)
        profile: PersonalityProfile = assess_response_persona(model_id, text)

        return StylometricPersonalityFeatureVector(
            characters=float(comm.characters),
            words=float(comm.words),
            sentences=float(comm.sentences),
            paragraphs=float(comm.paragraphs),
            avg_sentence_length=float(comm.avg_sentence_length),
            lists=float(comm.lists),
            headings=float(comm.headings),
            tables=float(comm.tables),
            em_dashes=float(comm.em_dashes),
            contractions=float(comm.contractions),
            exclamations=float(comm.exclamations),
            questions=float(comm.questions),
            parentheses=float(comm.parentheses),
            quotes=float(comm.quotes),
            colons=float(comm.colons),
            ellipses=float(comm.ellipses),
            bold=float(comm.bold),
            italics=float(comm.italics),
            emojis=float(comm.emojis),
            acronyms=float(comm.acronyms),
            ends_with_question=1.0 if comm.ends_with_question else 0.0,
            expressiveness=profile.get_index(PersonalityIndex.EXPRESSIVENESS),
            organization=profile.get_index(PersonalityIndex.ORGANIZATION),
            informativeness=profile.get_index(PersonalityIndex.INFORMATIVENESS),
            transparency=profile.get_index(PersonalityIndex.TRANSPARENCY),
            warmth=profile.get_index(PersonalityIndex.WARMTH),
            conviction=profile.get_index(PersonalityIndex.CONVICTION),
            imagination=profile.get_index(PersonalityIndex.IMAGINATION),
            slop=profile.get_index(PersonalityIndex.SLOP),
        )

    def extract_pairwise_diff(
        self, text_a: str, text_b: str
    ) -> Dict[str, np.ndarray]:
        """Extract individual and differential features for paired comparison (e.g. Chatbot Arena / Name That LLM).

        Returns:
            dict containing:
            - 'vec_a': shape (29,)
            - 'vec_b': shape (29,)
            - 'diff': shape (29,) (vec_a - vec_b)
            - 'abs_diff': shape (29,) |vec_a - vec_b|
            - 'combined': shape (87,) [vec_a, vec_b, diff]
        """
        vec_a = self.extract_features(text_a, model_id="response_a").to_numpy()
        vec_b = self.extract_features(text_b, model_id="response_b").to_numpy()
        diff = vec_a - vec_b
        abs_diff = np.abs(diff)
        combined = np.concatenate([vec_a, vec_b, diff], axis=0)

        return {
            "vec_a": vec_a,
            "vec_b": vec_b,
            "diff": diff,
            "abs_diff": abs_diff,
            "combined": combined,
        }

    def evaluate_gemma4_agent_compliance(
        self, code_explanation: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Validate developer agent output for code evaluation benchmarks.

        Enforces:
        - slop <= 25.0 (no excessive conversational filler)
        - organization >= 50.0 (structured reasoning)
        - transparency >= 50.0 (grounded in evidence)
        """
        features = self.extract_features(code_explanation, model_id="gemma4_agent")
        passed = (
            features.slop <= 25.0
            and features.organization >= 50.0
            and features.transparency >= 50.0
        )
        return passed, {
            "slop": features.slop,
            "organization": features.organization,
            "transparency": features.transparency,
            "passed": passed,
        }
