"""
TensorBeam Journey Graph - Persist to SurrealDB
================================================
Store the conceptual journey from Nothing to Particle as a queryable knowledge graph.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConceptNode:
    """A concept in the TensorBeam framework."""

    id: str
    name: str
    type: str  # "principle", "fabric", "field", "operation", "particle"
    description: str
    chapter: int
    mathematical_form: str | None = None
    prerequisite_concepts: list[str] = None


@dataclass
class JourneyEdge:
    """A conceptual relationship/dependency."""

    from_concept: str
    to_concept: str
    relationship: str  # "creates", "operates_on", "emerges_from", "stabilizes_at"
    weight: float = 1.0


# Define the complete conceptual graph
CONCEPTS = [
    # Chapter 0: Prelude
    ConceptNode(
        id="void",
        name="Nothing-At-All",
        type="principle",
        description="The primordial state. Not empty space, but the ABSENCE of differentiation. Reality exists (from 0 to ∞), but it is FORMLESS.",
        chapter=0,
    ),
    ConceptNode(
        id="awareness",
        name="Awareness",
        type="principle",
        description="The PRIMARY parameter. Awareness doesn't create Reality, but PERCEIVES and ORGANIZES it through the Quadrature Concept.",
        chapter=0,
    ),
    ConceptNode(
        id="quadrature",
        name="Quadrature Concept",
        type="operation",
        description="The fundamental operation: creating perpendicular relationships. √-1 in physics. The 'broadside' operation that unfolds dimensions.",
        chapter=0,
        mathematical_form="Q(X) → X_perp",
    ),
    # Chapter 1: Space Fabric
    ConceptNode(
        id="space_point",
        name="Point",
        type="fabric",
        description="0-dimensional. The first fixation of Reality.",
        chapter=1,
    ),
    ConceptNode(
        id="space_line",
        name="Line",
        type="fabric",
        description="1-dimensional. Point stretched by Quadrature.",
        chapter=1,
    ),
    ConceptNode(
        id="space_area",
        name="Area",
        type="fabric",
        description="2-dimensional. Line pulled perpendicular.",
        chapter=1,
    ),
    ConceptNode(
        id="space_volume",
        name="Volume (3D Space)",
        type="fabric",
        description="3-dimensional. Area extended perpendicular. Our familiar space.",
        chapter=1,
    ),
    # Chapter 2: Field Fabric
    ConceptNode(
        id="field_tempic",
        name="Tempic Field (∇)",
        type="field",
        description="The gradient of Reality density in Space. NOT time, but that which PRODUCES change. Time is its reciprocal derivative.",
        chapter=2,
        mathematical_form="J = ∇ρ (gradient of reality density)",
    ),
    ConceptNode(
        id="field_electric",
        name="Electric Field (∇·)",
        type="field",
        description="The divergence of the Tempic field. Sources and sinks of Reality.",
        chapter=2,
        mathematical_form="E = ∇·J (divergence)",
    ),
    ConceptNode(
        id="field_magnetic",
        name="Magnetic Field (∇×)",
        type="field",
        description="The curl of the Electric field. Whirling, circulating Reality.",
        chapter=2,
        mathematical_form="B = ∇×E (curl)",
    ),
    # Chapter 3: Toroidal Particle
    ConceptNode(
        id="toroidal_closure",
        name="Toroidal Closure",
        type="particle",
        description="When fields self-interact, they must close on themselves. The only stable configuration is a TORUS - a smoke ring of reality.",
        chapter=3,
    ),
    ConceptNode(
        id="skew_motion",
        name="Skew Condition (1,1,1)",
        type="particle",
        description="The real motion is in the vector (1,1,1) direction - midway among all three field axes. This creates BOTH rotation and precession.",
        chapter=3,
        mathematical_form="v_real = (v_tempic + v_electric + v_magnetic)/√3",
    ),
    ConceptNode(
        id="spin_rotation",
        name="Rotation",
        type="particle",
        description="The toroid SPINS. Can be right-handed or left-handed.",
        chapter=3,
    ),
    ConceptNode(
        id="spin_precession",
        name="Precession",
        type="particle",
        description="The toroid also PRECESSES (like a wobbling top). Can be right or left-handed. Smaller than rotation.",
        chapter=3,
    ),
    ConceptNode(
        id="charge",
        name="Charge Polarity",
        type="particle",
        description="The RESULTANT of rotation + precession fields. Four states: ++, +-, -+, --. Two positive, two negative.",
        chapter=3,
        mathematical_form="Q = sign(rotation) + 0.3×sign(precession)",
    ),
    # Chapter 4: HIHO & Precipitation
    ConceptNode(
        id="hiho_principle",
        name="Half-In-Half-Out (HIHO)",
        type="principle",
        description="Stability occurs at EXACTLY 50% reality overlap. >50% = coherent matter. <50% = incoherent radiation/thought.",
        chapter=4,
        mathematical_form="Stability = 1 - 2|overlap - 0.5|",
    ),
    ConceptNode(
        id="precipitation",
        name="Precipitation",
        type="principle",
        description="When coherence >0.5, Reality PRECIPITATES into discrete, observable particles. The transition from potential to actual.",
        chapter=4,
    ),
]

EDGES = [
    JourneyEdge("awareness", "quadrature", "uses"),
    JourneyEdge("quadrature", "space_point", "creates"),
    JourneyEdge("space_point", "space_line", "stretches_to"),
    JourneyEdge("space_line", "space_area", "extends_to"),
    JourneyEdge("space_area", "space_volume", "expands_to"),
    JourneyEdge("space_volume", "field_tempic", "supports"),
    JourneyEdge("field_tempic", "field_electric", "differentiates_to"),
    JourneyEdge("field_electric", "field_magnetic", "curls_to"),
    JourneyEdge("field_electric", "toroidal_closure", "self_interacts_forming"),
    JourneyEdge("field_magnetic", "toroidal_closure", "sustains"),
    JourneyEdge("toroidal_closure", "skew_motion", "manifests_as"),
    JourneyEdge("skew_motion", "spin_rotation", "creates"),
    JourneyEdge("skew_motion", "spin_precession", "creates"),
    JourneyEdge("spin_rotation", "charge", "contributes_to"),
    JourneyEdge("spin_precession", "charge", "contributes_to"),
    JourneyEdge("charge", "hiho_principle", "obeys"),
    JourneyEdge("hiho_principle", "precipitation", "enables"),
]


async def persist_to_surreal():
    """Persist the journey graph to SurrealDB."""
    try:
        from surrealdb import Surreal

        async with Surreal("ws://localhost:8000/rpc") as db:
            await db.signin({"user": "root", "pass": "root"})
            await db.use("cohezion", "tensorbeam")

            # Store concepts
            for concept in CONCEPTS:
                await db.create(
                    "concept",
                    {
                        "id": concept.id,
                        "name": concept.name,
                        "type": concept.type,
                        "description": concept.description,
                        "chapter": concept.chapter,
                        "math": concept.mathematical_form,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

            # Store relationships
            for edge in EDGES:
                await db.query(f"""
                    RELATE concept:{edge.from_concept}->{edge.relationship}->concept:{edge.to_concept}
                    SET weight = {edge.weight}
                """)

            print("✅ TensorBeam journey graph persisted to SurrealDB!")
            print(f"   Concepts: {len(CONCEPTS)}")
            print(f"   Relationships: {len(EDGES)}")

    except Exception as e:
        print(f"⚠️ SurrealDB not available: {e}")
        print("   Continuing without persistence...")


if __name__ == "__main__":
    # Print journey summary
    print("🌌 TENSORBEAM CONCEPTUAL JOURNEY\n")
    print("=" * 80)

    for chapter in range(5):
        chapter_concepts = [c for c in CONCEPTS if c.chapter == chapter]
        if chapter_concepts:
            chapter_names = {
                0: "PRELUDE: The Void",
                1: "CHAPTER 1: Space Unfolds",
                2: "CHAPTER 2: Fields Emerge",
                3: "CHAPTER 3: The Toroidal Dance",
                4: "CHAPTER 4: The HIHO Moment",
            }
            print(f"\n{chapter_names[chapter]}")
            print("-" * 80)
            for concept in chapter_concepts:
                print(f"  • {concept.name}: {concept.description[:80]}...")

    # Persist to SurrealDB
    asyncio.run(persist_to_surreal())
