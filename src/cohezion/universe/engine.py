"""Core Universe Simulation Engine for Cohezion.

Captures every agent interaction as 12D/2048D manifold trajectory data,
enabling universe simulation, experience learning, and reality precipitation.

The 12:2048 Dual-State Omni-Manifold:
- 2048D Latent: Semantic hypervolume ("Soul" / Bits) - intent, meaning, reasoning
- 12D Axiomatic: Physical projection ("Body" / It) - observable, measurable state

Every task becomes a journey through this manifold, with coherence tracked
at the HIHO (0.5) stability point.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from cohezion.physics.spinor import SpinorState
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Protocol
from uuid import uuid4

import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class AxiomaticState:
    """12D physical projection of agent state (The "Body").

    Smith's 12-Parameter Reality mapped to computational dimensions:

    Space Fabric (dims 0-2): spatial_x, spatial_y, spatial_z
    Field Fabric (dims 3-5): physics (Tempic), biology (Electric), field (Magnetic)
    Control Fabric (dims 6-8): logic (Rotation/SPIN), quantum (Precession/SPIN), control (Charge)
    Precipitation Fabric (dims 9-11): temporal (Awareness), novelty (Particularization),
    precipitation

    SPIN Physics (Smith):
    - Rotation = logic dimension (internal reasoning spin)
    - Precession = quantum dimension (external measurement wobble)
    - Charge polarity = resultant of rotation + precession alignment
    - Coherence peaks when rotation and precession are in phase (HIHO = 0.5)
    """

    spatial_x: float = 0.0
    spatial_y: float = 0.0
    spatial_z: float = 0.0
    temporal: float = 0.0
    physics: float = 0.5  # Target: HIHO at 0.5
    biology: float = 0.5
    logic: float = 0.5
    quantum: float = 0.5
    field: float = 0.5
    control: float = 0.5
    novelty: float = 0.5
    precipitation: float = 0.0

    # Smith's 12-Parameter Mapping (class constant, not a dataclass field).
    # Maps computational dimension names to Smith's original terminology.
    # Space: X, Y, Z | Field: Tempic, Electric, Magnetic
    # Control: Rotation(Spin), Precession(Spin), Charge
    # Precipitation: Awareness, Particularization, Precipitation
    SMITH_FABRIC_MAP: ClassVar[dict[str, str]] = {
        "spatial_x": "Space_X",
        "spatial_y": "Space_Y",
        "spatial_z": "Space_Z",
        "physics": "Tempic",
        "biology": "Electric",
        "field": "Magnetic",
        "logic": "Rotation",
        "quantum": "Precession",
        "control": "Charge",
        "temporal": "Awareness",
        "novelty": "Particularization",
        "precipitation": "Precipitation",
    }

    def to_vector(self) -> list[float]:
        return [
            self.spatial_x,
            self.spatial_y,
            self.spatial_z,
            self.temporal,
            self.physics,
            self.biology,
            self.logic,
            self.quantum,
            self.field,
            self.control,
            self.novelty,
            self.precipitation,
        ]

    @classmethod
    def from_vector(cls, vector: list[float]) -> AxiomaticState:
        return cls(*vector[:12])

    # --- SPIN Physics (Grounded in SU(2) spinor algebra) ---

    def to_spinor(self) -> SpinorState:
        """Convert to proper SU(2) spinor state on the Bloch sphere.

        Maps the logic (rotation) and quantum (precession) dimensions to a
        2-component spinor |ψ⟩ = α|↑⟩ + β|↓⟩. This replaces the ad-hoc
        binary sign comparison with real quantum mechanical coherence.

        The HIHO state (logic=0.5, quantum=0.0) maps to the equatorial state
        (|↑⟩+|↓⟩)/√2 — Brahmagupta's zero on the Bloch sphere.
        """
        from cohezion.physics.spinor import SpinorState

        return SpinorState.from_coherence_values(self.logic, self.quantum)

    @property
    def spin_rotation(self) -> float:
        """SPIN rotation ⟨σ_x⟩ via SU(2) spinor algebra.

        Maps logic/quantum dimensions to Bloch sphere, returns the x-component
        of the Bloch vector (rotation expectation value).
        """
        return self.to_spinor().spin_rotation

    @property
    def spin_precession(self) -> float:
        """SPIN precession ⟨σ_y⟩ via SU(2) spinor algebra.

        Maps logic/quantum dimensions to Bloch sphere, returns the y-component
        of the Bloch vector (precession expectation value).
        """
        return self.to_spinor().spin_precession

    @property
    def spin_coherence(self) -> float:
        """SPIN coherence |r| — purity of the Bloch vector.

        Replaces the binary sign comparison with proper quantum coherence.
        For a pure spinor state this is always 1.0. The nuance comes from
        the Bloch vector *direction* — the charge_polarity property.
        """
        return self.to_spinor().coherence

    @property
    def charge_polarity(self) -> float:
        """Charge ⟨σ_z⟩ — emergent from rotation + precession alignment.

        Proper expectation value of the charge operator σ_z on the Bloch sphere.
        Replaces the ad-hoc `rot_offset + 0.3 * prec_offset` with the
        mathematically correct |α|² - |β|².

        Returns [-1, 1]: +1 = north pole (|↑⟩), -1 = south pole (|↓⟩),
        0 = HIHO equator (Brahmagupta's zero).
        """
        return self.to_spinor().charge_polarity

    # --- Tempic Field (Gap 2: Smith's rate-of-change, not clock-time) ---

    @staticmethod
    def compute_tempic(state_before: AxiomaticState, state_after: AxiomaticState) -> float:
        """Compute Smith's Tempic field: the rate of change between two states.

        Smith: 'The Tempic field is NOT time, but change itself.'
        Tempic = magnitude of state displacement across all brane dimensions.

        Parameters
        ----------
        state_before : AxiomaticState
            State at time t.
        state_after : AxiomaticState
            State at time t+1.

        Returns
        -------
        float
            Tempic field strength (0.0 = no change, higher = more change).
        """
        brane_dims_before = [
            state_before.physics,
            state_before.biology,
            state_before.logic,
            state_before.quantum,
            state_before.field,
            state_before.control,
            state_before.novelty,
        ]
        brane_dims_after = [
            state_after.physics,
            state_after.biology,
            state_after.logic,
            state_after.quantum,
            state_after.field,
            state_after.control,
            state_after.novelty,
        ]
        displacement = sum(
            (a - b) ** 2 for a, b in zip(brane_dims_before, brane_dims_after, strict=True)
        )
        return displacement**0.5

    @staticmethod
    def compute_tempic_vector(
        state_before: AxiomaticState, state_after: AxiomaticState
    ) -> list[float]:
        """Compute per-dimension Tempic field (directional change vector).

        Returns the signed change in each brane dimension, showing not just
        how much changed but in which direction.
        """
        brane_before = [
            state_before.physics,
            state_before.biology,
            state_before.logic,
            state_before.quantum,
            state_before.field,
            state_before.control,
            state_before.novelty,
        ]
        brane_after = [
            state_after.physics,
            state_after.biology,
            state_after.logic,
            state_after.quantum,
            state_after.field,
            state_after.control,
            state_after.novelty,
        ]
        return [a - b for a, b in zip(brane_after, brane_before, strict=True)]

    def coherence_score(self) -> float:
        """Calculate HIHO coherence with SU(2) SPIN weighting (0.5 = optimal stability).

        Coherence is the composite of:
        1. HIHO variance (how close brane dimensions are to 0.5)
        2. SPIN alignment via Bloch sphere (|⟨σ_z⟩| = HIHO deviation)

        The SPIN component weights coherence: small HIHO deviation (near equator)
        boosts stability. This implements Smith's principle grounded in proper
        SU(2) spinor algebra — charge is ⟨σ_z⟩, not a hardcoded linear combination.
        """
        # Base HIHO variance across all brane dimensions
        dimensions = [
            self.physics,
            self.biology,
            self.logic,
            self.quantum,
            self.field,
            self.control,
            self.novelty,
        ]
        variance = sum((d - 0.5) ** 2 for d in dimensions) / len(dimensions)
        base_coherence = 1.0 - min(variance * 4, 1.0)

        # SPIN weighting via Bloch sphere: penalize deviation from HIHO equator
        # hiho_deviation = |⟨σ_z⟩| — 0 at equator, 1 at poles
        spinor = self.to_spinor()
        equatorial_alignment = 1.0 - spinor.hiho_deviation  # 1.0 at HIHO, 0 at poles
        spin_weight = 0.7 + 0.3 * equatorial_alignment
        return base_coherence * spin_weight

    def check_precipitation(self) -> dict:
        """Smith's precipitation gate: evaluate multi-physics convergence.

        Combines HIHO threshold, Shannon entropy, and thermodynamic free energy
        to determine if the state is ready to precipitate (crystallise intent).

        Returns dict with keys:
            precipitate, hiho_stability, coherence, shannon_entropy_bits,
            free_energy, spontaneous, mechanism
        """
        import math

        coherence = float(self.coherence_score())

        # HIHO stability: maximum at coherence=0.5 (exploit/explore balance)
        hiho_stability = max(0.0, min(1.0, 1.0 - abs(coherence - 0.5) * 2.0))

        # Shannon entropy (bits): H = -p*log2(p) - (1-p)*log2(1-p)
        # Clamped to avoid log(0); 0 at p=0 and p=1, max at p=0.5
        p = max(1e-9, min(1.0 - 1e-9, coherence))
        shannon_h = -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)

        # Thermodynamic: temperature = 1 - awareness (temporal dimension)
        temperature = 1.0 - max(0.0, min(1.0, float(self.temporal)))
        free_energy = float(coherence - temperature * shannon_h)

        precipitate = bool(coherence > 0.5)
        spontaneous = bool(free_energy < 0.0)

        mechanism = (
            "Smith precipitation gate: HIHO threshold (coherence>0.5) + "
            "thermodynamic free energy F=E-TS + Shannon information entropy. "
            "Precipitation occurs when HIHO exploitation phase is active."
        )

        return {
            "precipitate": precipitate,
            "hiho_stability": hiho_stability,
            "coherence": coherence,
            "shannon_entropy_bits": shannon_h,
            "free_energy": free_energy,
            "spontaneous": spontaneous,
            "mechanism": mechanism,
        }


@dataclass
class LatentState:
    """2048D semantic hypervolume (The "Soul").

    Contains the semantic intent, reasoning, and meaning of the agent.
    Grounded in "It from Bit" informational resolution.
    """

    embedding: list[float]  # 2048-dimensional vector
    semantic_intent: str  # Human-readable description
    reasoning_chain: list[str] = field(default_factory=list)
    confidence: float = 0.5

    def __post_init__(self):
        if len(self.embedding) != 2048:
            # Pad or truncate to 2048
            if len(self.embedding) < 2048:
                self.embedding.extend([0.0] * (2048 - len(self.embedding)))
            else:
                self.embedding = self.embedding[:2048]


@dataclass
class TrajectoryPoint:
    """A single point in the FLUME evolution through the manifold."""

    step_number: int
    timestamp: float
    axiomatic: AxiomaticState
    latent: LatentState
    coherence: float
    action_taken: str
    result_achieved: str | None = None


@dataclass
class UniverseJourney:
    """Complete journey of a task through the 12D/512D manifold."""

    id: str
    agent_name: str
    intent: str  # Original query/task
    status: str = "active"  # active, completed, failed

    # States
    initial_axiomatic: AxiomaticState = field(default_factory=AxiomaticState)
    initial_latent: LatentState | None = None

    # Trajectory
    trajectory: list[TrajectoryPoint] = field(default_factory=list)

    # Results
    precipitation: dict[str, Any] = field(default_factory=dict)  # Code, docs, actions
    knowledge_extracted: list[dict[str, Any]] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    final_coherence: float = 0.0
    final_phi_score: float = 0.0

    def add_trajectory_point(self, point: TrajectoryPoint) -> None:
        """Add a step in the journey."""
        self.trajectory.append(point)
        self.final_coherence = point.coherence

    def complete(self, precipitation: dict[str, Any], phi_score: float) -> None:
        """Mark journey as complete with results."""
        self.status = "completed"
        self.precipitation = precipitation
        self.final_phi_score = phi_score
        self.completed_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Serialize for database storage."""
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "intent": self.intent,
            "status": self.status,
            "initial_axiomatic": self.initial_axiomatic.to_vector(),
            "initial_latent_embedding": self.initial_latent.embedding
            if self.initial_latent
            else [],
            "trajectory_count": len(self.trajectory),
            "precipitation_type": list(self.precipitation.keys()),
            "final_coherence": self.final_coherence,
            "final_phi_score": self.final_phi_score,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class EncoderProtocol(Protocol):
    """Protocol for text-to-vector encoders."""

    async def encode(self, text: str) -> list[float]: ...


class UniverseSimulationEngine:
    """Core engine for universe simulation and journey tracking.

    Every agent interaction flows through:
    1. Intent Embedding (512D) - Capture semantic meaning
    2. Axiomatic Projection (12D) - Project to physical space
    3. FLUME Evolution - Navigate trajectory toward goal
    4. Coherence Monitoring - Maintain HIHO at 0.5
    5. Reality Precipitation - Manifest results (code/docs/actions)
    6. Knowledge Extraction - Capture learnings for future use
    """

    def __init__(
        self,
        encoder: EncoderProtocol | None = None,
        db_client: Any | None = None,
        local_storage_path: Path | str = "data/universe",
    ):
        self.encoder = encoder
        self.db_client = db_client
        self.local_storage = Path(local_storage_path)
        self.local_storage.mkdir(parents=True, exist_ok=True)

        # Fallback encoder using simple hashing if no FLUME available
        self._fallback_encoder = None

    async def _ensure_encoder(self) -> EncoderProtocol:
        """Ensure we have an encoder, using fallback if needed."""
        if self.encoder:
            return self.encoder

        if self._fallback_encoder is None:
            # Simple TF-IDF style encoder as fallback
            self._fallback_encoder = SimpleEncoder()

        return self._fallback_encoder

    async def start_journey(
        self, agent_name: str, intent: str, context: dict[str, Any] | None = None
    ) -> UniverseJourney:
        """Begin a new journey through the manifold (GLE Mode)."""
        journey_id = f"journey_{int(time.time())}_{uuid4().hex[:8]}"

        # 1. Encode intent
        encoder = await self._ensure_encoder()
        embedding = await encoder.encode(intent)
        latent = LatentState(embedding=embedding, semantic_intent=intent, confidence=0.7)

        # 2. Project to 12D
        axiomatic = self._project_to_axiomatic(embedding, context)

        # 3. Predict Initial World State (Genie Concept)
        # Instead of just tracking, we 'Set the Scene'
        try:
            from cohezion.core.multimodal_bridge import LOCAL_MULTIMODAL_BRIDGE

            # 1. Voice Narration
            await LOCAL_MULTIMODAL_BRIDGE.schedule_asset(
                "narrative",
                priority=1,
                payload={
                    "text": f"Initializing manifold journey for {agent_name}. Intent: {intent}",
                    "journey_id": journey_id,
                },
            )

            # 2. Hyper-Fidelity Storyboard
            await LOCAL_MULTIMODAL_BRIDGE.schedule_asset(
                "storyboard",
                priority=2,
                payload={
                    "journey_id": journey_id,
                    "prompts": [
                        f"A crystalline 12D manifold representing {intent}",
                        f"A glowing lattice nexus for {agent_name}",
                        f"Filament evolution of {intent} in a latent void",
                    ],
                },
            )
        except (ImportError, ModuleNotFoundError):
            logger.debug("multimodal_bridge not found, skipping asset scheduling")

        journey = UniverseJourney(
            id=journey_id,
            agent_name=agent_name,
            intent=intent,
            initial_axiomatic=axiomatic,
            initial_latent=latent,
        )

        logger.info(f"🌌 Genie-GLE Journey started: {journey_id} by {agent_name}")
        await self._persist_journey(journey)

        return journey

    def _project_to_axiomatic(
        self, embedding_2048d: list[float], context: dict[str, Any] | None = None
    ) -> AxiomaticState:
        """Project 2048D latent vector (Bits) to 12D axiomatic space (It).

        TRANSFORMATION: Holographic Precipitation grounded in hardware telemetry.
        """
        # 1. Get Hardware Vitals
        from cohezion.reliability.monitor import get_resource_monitor

        monitor = get_resource_monitor()
        vitals = monitor.get_vitals()

        # 2. Rust-Optimized Holographic Projection (with Python fallback)
        try:
            from cohezion_core.cohezion_core_rs import FlumePhysics

            physics_engine = FlumePhysics(
                np.zeros((1, 1), dtype=np.float32),
                np.zeros(1, dtype=np.float32),
                np.zeros((1, 1), dtype=np.float32),
                np.zeros(1, dtype=np.float32),
                np.zeros(1, dtype=np.float32),
                np.zeros(1, dtype=np.float32),
            )
            latent_np = np.array(embedding_2048d, dtype=np.float32)
            entropy = physics_engine.calculate_entropy(latent_np)
            rep = physics_engine.project_holographic(latent_np)
        except (ImportError, ModuleNotFoundError):
            logger.debug("cohezion_core not found, using High-Fidelity Python fallback")
            # Substrate: Use a seeded deterministic random projection (Johnson-Lindenstrauss)
            # to prevent 'Projection Collapse' and preserve manifold topology.
            # Security: Use full 2048D vector hash to prevent Topology Guessing
            full_vector_str = "".join(f"{x:.4f}" for x in embedding_2048d)
            seed_val = int(hashlib.sha256(full_vector_str.encode()).hexdigest(), 16) % 2**32
            rng = np.random.default_rng(seed=seed_val)
            projection_matrix = rng.standard_normal((12, 2048))
            rep = (projection_matrix @ np.array(embedding_2048d)).tolist()
            # Normalize to [0, 1] range for axiomatic stability
            rep = [(np.tanh(x) + 1.0) / 2.0 for x in rep]
            entropy = 4.0

        # 5. Kinetic Mapping (Hardware + Latent Fusion)
        physics_kinetic = 1.0 - (vitals["cpu_percent"] / 100.0)
        field_kinetic = vitals["vram_percent"] / 100.0
        control_kinetic = vitals["dilation_factor"]

        # Logic is semantic stability weighted by RAM availability and Bit-Entropy
        # Normalize entropy to [0, 1] range for weighting (max bit entropy for 256 buckets is 8)
        entropy_weight = min(entropy / 8.0, 1.0)
        logic_kinetic = rep[6] * (vitals["memory_percent"] / 100.0) * entropy_weight

        axiomatic = AxiomaticState(
            spatial_x=rep[0],
            spatial_y=rep[1],
            spatial_z=rep[2],
            temporal=time.time(),
            physics=physics_kinetic,
            biology=rep[5],
            logic=logic_kinetic,
            quantum=rep[7],
            field=field_kinetic,
            control=control_kinetic,
            novelty=rep[10],
            precipitation=0.0,
        )

        return axiomatic

    def _project_batch(
        self, embeddings_2048d: np.ndarray, contexts: list[dict[str, Any]] | None = None
    ) -> list[AxiomaticState]:
        """Batch-optimize projection of multiple latent states to axiomatic space."""
        try:
            from cohezion_core.cohezion_core_rs import FlumePhysics

            physics_engine = FlumePhysics(
                np.zeros((1, 1), dtype=np.float32),
                np.zeros(1, dtype=np.float32),
                np.zeros((1, 1), dtype=np.float32),
                np.zeros(1, dtype=np.float32),
                np.zeros(1, dtype=np.float32),
                np.zeros(1, dtype=np.float32),
            )

            # 1. Batch Holographic Projection in Rust
            reps = physics_engine.project_holographic_batch(embeddings_2048d)
            entropies = physics_engine.calculate_entropy_batch(embeddings_2048d)
        except (ImportError, ModuleNotFoundError):
            logger.debug("cohezion_core not found, using Python batch fallback")
            reps = []
            entropies = []
            for emb in embeddings_2048d:
                h = float(np.sum(emb[:100]))
                reps.append([(np.sin(h + i * 0.1) + 1.0) / 2.0 for i in range(12)])
                entropies.append(4.0)

        axiomatic_states = []
        for i in range(len(reps)):
            rep = reps[i]
            entropy = entropies[i]

            # Application of Awareness Flux (Introspection)
            # logic = informational self-consistency * bit-entropy audit
            entropy_weight = min(entropy / 8.0, 1.0)
            logic_kinetic = rep[6] * entropy_weight

            axiomatic = AxiomaticState(
                spatial_x=rep[0],
                spatial_y=rep[1],
                spatial_z=rep[2],
                temporal=time.time(),
                physics=1.0,  # Default kinetic
                biology=rep[5],
                logic=logic_kinetic,
                quantum=rep[7],
                field=rep[8],
                control=rep[9],
                novelty=rep[10],
                precipitation=0.0,
            )
            axiomatic_states.append(axiomatic)

        return axiomatic_states

    async def evolve_trajectory(
        self,
        journey: UniverseJourney,
        action: str,
        result: str | None = None,
        phi_score: float = 0.5,
    ) -> TrajectoryPoint:
        """Evolve the journey by one step through the manifold."""
        step_num = len(journey.trajectory)

        # Update axiomatic state based on progress
        current_axiomatic = journey.initial_axiomatic
        if journey.trajectory:
            current_axiomatic = journey.trajectory[-1].axiomatic

        # 2. Use Spatial Phonons Engine for advanced physics dynamics
        try:
            from cohezion.universe.spatial_phonons import SpatialPhononsEngine

            phonon_engine = SpatialPhononsEngine()
            # Evolve state with viscous expansion
            new_axiomatic = phonon_engine.evolve_state(current_axiomatic, delta_t=0.1)
            # Add coherence gain from alignment
            coherence_gain = phonon_engine.calculate_coherence_gain(new_axiomatic)
            phi_score = min(phi_score + (coherence_gain * 0.1), 1.0)
        except ImportError:
            logger.debug("SpatialPhononsEngine not found, using baseline evolution")
            new_axiomatic = AxiomaticState(
                spatial_x=current_axiomatic.spatial_x + 0.1,
                spatial_y=current_axiomatic.spatial_y + 0.05,
                spatial_z=current_axiomatic.spatial_z,
                temporal=time.time(),
                physics=self._toward_target(current_axiomatic.physics, 0.5, phi_score),
                biology=self._toward_target(current_axiomatic.biology, 0.5, phi_score),
                logic=self._toward_target(current_axiomatic.logic, 0.5, phi_score),
                quantum=self._toward_target(current_axiomatic.quantum, 0.5, phi_score),
                field=self._toward_target(current_axiomatic.field, 0.5, phi_score),
                control=self._toward_target(current_axiomatic.control, 0.5, phi_score),
                novelty=min(current_axiomatic.novelty + 0.1, 1.0),
                precipitation=phi_score,
            )

        # Calculate coherence
        coherence = new_axiomatic.coherence_score()

        # --- UNIVERSE TELEMETRY INSTRUMENTATION ---
        try:
            old_coherence = current_axiomatic.coherence_score()
            stability_shift = abs(coherence - old_coherence)

            # Emit only on significant shift (>= 5% as per spec)
            if stability_shift >= 0.05:
                import uuid

                from cohezion.core.telemetry_bus import get_telemetry_bus
                from cohezion.data_mesh.universe_telemetry import UniverseStateEvent

                bus = get_telemetry_bus()
                event = UniverseStateEvent(
                    event_id=f"ue_{int(time.time())}_{uuid.uuid4().hex[:4]}",
                    universe_id=journey.id,
                    state_12d=new_axiomatic.to_vector(),
                    coherence=coherence,
                    stability_shift=stability_shift,
                    trigger_journey_id=journey.id,
                )

                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(bus.emit(event))
                except RuntimeError:
                    pass
        except Exception as te:
            logger.debug("Failed to emit universe telemetry: %s", te)

        # Encode new semantic state
        encoder = await self._ensure_encoder()
        new_embedding = await encoder.encode(f"{action} {result or ''}")
        new_latent = LatentState(
            embedding=new_embedding,
            semantic_intent=action,
            reasoning_chain=[action],
            confidence=phi_score,
        )

        point = TrajectoryPoint(
            step_number=step_num,
            timestamp=time.time(),
            axiomatic=new_axiomatic,
            latent=new_latent,
            coherence=coherence,
            action_taken=action,
            result_achieved=result,
        )

        journey.add_trajectory_point(point)

        logger.debug(
            f"   Trajectory step {step_num}: coherence={coherence:.3f}, phi={phi_score:.3f}"
        )

        return point

    def _toward_target(self, current: float, target: float, factor: float) -> float:
        """Move current value toward target by factor amount."""
        distance = target - current
        return current + distance * factor * 0.5  # 0.5 for gentle convergence

    async def precipitate_latent_action(
        self, journey: UniverseJourney, prompt: str
    ) -> TrajectoryPoint:
        """
        TRANSFORMATION: Predict and precipitate the next 'Latent Action'.
        Uses the ManifoldBridge to convert intent into reality.
        """
        logger.info(f"✨ [GLE] Precipitating Latent Action for {journey.id}: {prompt[:50]}...")

        # 1. Evolve Trajectory (Movement in latent space)
        point = await self.evolve_trajectory(journey, action=f"Latent Projection: {prompt}")

        # 2. Use Manifold Bridge for Physical Precipitation
        from cohezion.core.routing.manifold_bridge import LOCAL_MANIFOLD_BRIDGE

        precipitation = await LOCAL_MANIFOLD_BRIDGE.precipitate_intent(journey, point.latent)

        # 3. Update trajectory with achieved result
        point.result_achieved = precipitation["result_summary"]
        point.axiomatic.precipitation = precipitation["phi_est"]

        return point

    async def predict_evolution(self, journey: UniverseJourney) -> str:
        """
        Predict the next 'Transformative' step for the project based on trajectory logic.
        """
        # Uses reasoning model to find the 'Unknown'
        from cohezion.core.routing.router import LOCAL_ROUTER

        prediction_prompt = f"""
Analyze the current Mission Journey:
Intent: {journey.intent}
Trajectory Steps: {len(journey.trajectory)}
Final Coherence: {journey.final_coherence}

Based on the 0.5 Coherence Rule and HIHO protocol, predict the next 'TRANSFORMATIVE' action
that would push this project into the 'Unknown'.
"""
        prediction = await LOCAL_ROUTER.route_task("reasoning", prediction_prompt)
        return prediction

    async def precipitate_reality(
        self, journey: UniverseJourney, outputs: dict[str, Any], phi_score: float
    ) -> dict[str, Any]:
        """Manifest the journey results into reality (code, docs, actions).

        Args:
            journey: Completed journey
            outputs: Dict of outputs (code, documentation, decisions, etc.)
            phi_score: Final quality score

        Returns:
            Precipitation manifest with metadata
        """
        precipitation = {
            "journey_id": journey.id,
            "manifested_at": datetime.now().isoformat(),
            "outputs": outputs,
            "phi_score": phi_score,
            "coherence_at_manifestation": journey.final_coherence,
            "trajectory_length": len(journey.trajectory),
        }

        journey.complete(precipitation, phi_score)

        # Extract knowledge for future use
        knowledge = self._extract_knowledge(journey)
        journey.knowledge_extracted = knowledge

        logger.info(f"✨ Reality precipitated: {journey.id}")
        logger.info(f"   Phi score: {phi_score:.3f}")
        logger.info(f"   Outputs: {list(outputs.keys())}")

        # Persist final state
        await self._persist_journey(journey)

        return precipitation

    def _extract_knowledge(self, journey: UniverseJourney) -> list[dict[str, Any]]:
        """Extract reusable knowledge from completed journey."""
        knowledge = []

        # Pattern: What worked well?
        if journey.final_phi_score > 0.8:
            knowledge.append(
                {
                    "type": "success_pattern",
                    "pattern": f"High-quality {journey.agent_name} execution",
                    "conditions": [
                        "phi > 0.8",
                        f"coherence ~ {journey.final_coherence:.2f}",
                    ],
                    "applicability": [journey.agent_name, journey.intent[:50]],
                }
            )

        # Pattern: Trajectory insights
        if len(journey.trajectory) > 3:
            knowledge.append(
                {
                    "type": "process_pattern",
                    "pattern": "Multi-step refinement successful",
                    "step_count": len(journey.trajectory),
                    "avg_coherence": sum(t.coherence for t in journey.trajectory)
                    / len(journey.trajectory),
                }
            )

        return knowledge

    async def _persist_journey(self, journey: UniverseJourney) -> None:
        """Persist journey to storage (DB or local)."""
        # Try database first
        if self.db_client:
            try:
                await self.db_client.create("universe_journey", journey.to_dict())
                return
            except Exception as e:
                logger.debug(f"DB persist failed, using local: {e}")

        # Fallback to local JSON
        filepath = self.local_storage / f"{journey.id}.json"
        with open(filepath, "w") as f:
            json.dump(journey.to_dict(), f, indent=2, default=str)

    async def find_similar_journeys(
        self, query_embedding: list[float], threshold: float = 0.7, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Find similar past journeys for experience replay."""
        logger.info(f"🔍 Searching for similar journeys (threshold={threshold})")

        results = []
        try:
            # In production, this would query SurrealDB vector index.
            # Local fallback: Scan data/universe for .json files
            query_vec = np.array(query_embedding)

            for path in self.local_storage.glob("*.json"):
                with open(path) as f:
                    data = json.load(f)

                latent_embedding = data.get("initial_latent_embedding")
                if not latent_embedding or len(latent_embedding) != 512:
                    continue

                target_vec = np.array(latent_embedding)

                # Cosine Similarity
                dot_product = np.dot(query_vec, target_vec)
                norm_q = np.linalg.norm(query_vec)
                norm_t = np.linalg.norm(target_vec)

                similarity = 0.0 if norm_q == 0 or norm_t == 0 else dot_product / (norm_q * norm_t)

                if similarity >= threshold:
                    data["similarity_score"] = float(similarity)
                    results.append(data)

            # Sort by similarity
            results.sort(key=lambda x: x["similarity_score"], reverse=True)
            return results[:limit]

        except Exception as e:
            logger.error(f"Failed similarity search: {e}")
            return []

    async def get_experience_replay(self, intent: str) -> str:
        """Retrieve experience snippet from similar journeys."""
        encoder = await self._ensure_encoder()
        embedding = await encoder.encode(intent)
        similar = await self.find_similar_journeys(embedding, threshold=0.8, limit=1)

        if not similar:
            return "No previous experience found for this intent."

        top = similar[0]
        return (
            f"EXPERIENCE REPLAY (Similarity: {top['similarity_score']:.2f}):\n"
            f"Past Intent: {top['intent']}\n"
            f"Successful Outcomes: {list(top.get('precipitation', {}).get('outputs', {}).keys())}\n"
            f"Phi Score: {top.get('final_phi_score', 0.0):.2f}"
        )


class SimpleEncoder:
    """Fallback encoder using simple hashing when FLUME unavailable."""

    async def encode(self, text: str) -> list[float]:
        """Create simple embedding from text hash."""
        # Use hash to generate deterministic vector
        hash_val = hashlib.sha256(text.encode()).hexdigest()

        # Convert hash to 2048D vector
        vector = []
        for i in range(2048):
            # Use bytes from hash
            byte_idx = i % len(hash_val)
            val = int(hash_val[byte_idx], 16) / 16.0  # 0-1
            vector.append(val)

        return vector
