"""Journey Analyzer - Comprehensive analysis of agent trajectories in 12D HIHO manifold.

Analyzes captured journeys for patterns, clusters, anomalies, and behavioral modes.
Provides thermodynamic analysis, topological features, and archetype identification.

Architecture:
    JourneyAnalyzer
        ├── cluster_journeys() → ClusteringResult (k-means, DBSCAN, GMM)
        ├── detect_anomalies() → AnomalyReport (Isolation Forest, LOF)
        ├── mine_patterns() → PatternLibrary (sequential patterns, motifs)
        ├── compute_archetypes() → ArchetypeModel (Explorer, Stabilizer, Innovator)
        ├── analyze_thermodynamics() → ThermoAnalysis (entropy, free energy)
        ├── analyze_topology() → TopoAnalysis (Betti numbers, persistence)
        └── generate_report() → JourneyReport (comprehensive analysis)

References:
    - Smith's HIHO: coherence clustering around 0.5
    - Thermodynamics: entropy production, free energy minima
    - Topology: persistent homology for behavioral modes
    - Archetypes: Percival's Triune Self (Knower/Thinker/Doer)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)


class ArchetypeType(Enum):
    """Agent behavioral archetypes identified through journey analysis."""

    EXPLORER = "explorer"  # High novelty, low smoothness, high entropy production
    STABILIZER = "stabilizer"  # High coherence, low variance, near HIHO
    INNOVATOR = "innovator"  # High phi score, high thermodynamic activity
    OSCILLATOR = "oscillator"  # Periodic coherence oscillation, cyclic behavior
    DRIFTER = "drifter"  # Low coherence, high variance, no clear attractor


@dataclass
class ClusteringResult:
    """Result of journey clustering analysis."""

    n_clusters: int
    labels: list[int]
    cluster_centers: list[list[float]]
    silhouette_score: float
    inertia: float
    cluster_sizes: list[int]
    algorithm: str  # "kmeans", "dbscan", "gmm"


@dataclass
class AnomalyReport:
    """Anomaly detection report for a journey."""

    journey_id: str
    anomaly_score: float
    is_anomaly: bool
    anomaly_type: str | None  # "coherence_collapse", "thermodynamic_violation", "topological_void"
    contributing_factors: list[str]
    severity: str  # "low", "medium", "high", "critical"


@dataclass
class PatternLibrary:
    """Library of recurring journey patterns."""

    motifs: list[dict[str, Any]]  # Recurring trajectory motifs
    sequences: list[dict[str, Any]]  # Sequential patterns
    cycles: list[dict[str, Any]]  # Cyclic/periodic patterns
    support: float  # Pattern support (frequency)
    confidence: float  # Pattern confidence


@dataclass
class ArchetypeModel:
    """Agent archetype classification model."""

    archetype: ArchetypeType
    confidence: float
    characteristics: dict[str, float]
    matching_journeys: list[str]
    population_fraction: float


@dataclass
class ThermoAnalysis:
    """Thermodynamic analysis of a journey."""

    entropy_production_rate: float
    free_energy: float
    effective_temperature: float
    susceptibility: float
    heat_capacity: float
    is_attractor: bool
    well_depth: float
    basin_width: float
    phase_transition_detected: bool
    critical_temperature: float | None


@dataclass
class TopoAnalysis:
    """Topological persistence analysis of a journey."""

    n_clusters: int  # Betti number β₀ (connected components)
    n_loops: int  # Betti number β₁ (cycles)
    persistence_entropy_h0: float
    persistence_entropy_h1: float
    topological_complexity: float
    dominant_features: list[dict[str, Any]]


@dataclass
class JourneyReport:
    """Comprehensive journey analysis report."""

    report_id: str
    generated_at: datetime
    n_journeys_analyzed: int
    clustering: ClusteringResult
    archetypes: list[ArchetypeModel]
    anomalies: list[AnomalyReport]
    thermodynamic_summary: dict[str, float]
    topological_summary: dict[str, float]
    patterns: PatternLibrary
    key_findings: list[str]
    recommendations: list[str]


class JourneyAnalyzer:
    """Analyze agent journeys for patterns, clusters, and anomalies.

    Provides comprehensive analysis of journey trajectories including:
    - Behavioral clustering (k-means, DBSCAN, GMM)
    - Anomaly detection (Isolation Forest, LOF)
    - Pattern mining (sequential motifs, cycles)
    - Archetype identification (Explorer, Stabilizer, Innovator, etc.)
    - Thermodynamic analysis (entropy, free energy, phase transitions)
    - Topological analysis (persistent homology, Betti numbers)

    Example:
        ```python
        analyzer = JourneyAnalyzer()

        # Load journeys from data directory
        journeys = analyzer.load_journeys("data/universe")

        # Cluster by behavioral similarity
        clusters = analyzer.cluster_journeys(journeys)

        # Identify archetypes
        archetypes = analyzer.compute_archetypes(journeys)

        # Detect anomalies
        anomalies = [analyzer.detect_anomalies(j) for j in journeys]

        # Generate comprehensive report
        report = analyzer.generate_report(journeys)
        ```
    """

    # Archetype thresholds
    EXPLORER_NOVELTY_THRESHOLD: float = 0.7
    STABILIZER_COHERENCE_THRESHOLD: float = 0.8
    INNOVATOR_PHI_THRESHOLD: float = 0.75
    OSCILLATOR_VARIANCE_THRESHOLD: float = 0.3
    DRIFTER_COHERENCE_LOWER: float = 0.4

    def __init__(self, random_state: int = 42):
        """Initialize Journey Analyzer.

        Args:
            random_state: Random seed for reproducibility
        """
        self.random_state = random_state
        self.rng = np.random.RandomState(random_state)

        # Cache for loaded journeys
        self._journey_cache: dict[str, dict[str, Any]] = {}

        logger.debug("Initialized JourneyAnalyzer with seed=%d", random_state)

    def load_journeys(self, journey_dir: str | Path) -> list[dict[str, Any]]:
        """Load journeys from JSON files.

        Args:
            journey_dir: Directory containing journey_*.json files

        Returns:
            List of journey dictionaries
        """
        journey_path = Path(journey_dir)
        if not journey_path.exists():
            logger.warning("Journey directory does not exist: %s", journey_path)
            return []

        journeys = []
        for json_file in journey_path.glob("journey_*.json"):
            try:
                with open(json_file) as f:
                    journey = json.load(f)
                    journeys.append(journey)
                    self._journey_cache[journey["id"]] = journey
            except Exception as e:
                logger.error("Failed to load journey %s: %s", json_file.name, e)

        logger.info("Loaded %d journeys from %s", len(journeys), journey_path)
        return journeys

    def extract_features(self, journey: dict[str, Any]) -> np.ndarray:
        """Extract feature vector from journey for analysis.

        Features:
        - Mean coherence, std coherence, min coherence, max coherence
        - Mean phi score, std phi score
        - Mean efficiency, std efficiency
        - Smoothness, convergence
        - Thermodynamic: entropy production, free energy
        - Topological: n_clusters, n_loops

        Args:
            journey: Journey dictionary

        Returns:
            Feature vector (16D)
        """
        trajectory = journey.get("trajectory", [])
        if not trajectory:
            return np.zeros(16)

        # Extract coherence and phi scores
        coherences = [t.get("coherence", 0.5) for t in trajectory]
        phi_scores = [t.get("phi_score", 0.5) for t in trajectory]
        efficiencies = [t.get("efficiency", 0.5) for t in trajectory]

        # Basic statistics
        features = [
            np.mean(coherences),
            np.std(coherences),
            np.min(coherences),
            np.max(coherences),
            np.mean(phi_scores),
            np.std(phi_scores),
            np.mean(efficiencies),
            np.std(efficiencies),
        ]

        # Smoothness (variance of consecutive differences)
        if len(coherences) > 1:
            diffs = np.diff(coherences)
            smoothness = 1.0 - np.mean(np.abs(diffs))
            features.append(smoothness)
        else:
            features.append(1.0)

        # Convergence (std of last 3 points)
        if len(coherences) > 2:
            convergence = 1.0 - np.std(coherences[-3:])
            features.append(convergence)
        else:
            features.append(1.0)

        # 12D trajectory statistics
        dims = [t.get("dimensions", [0.5] * 12) for t in trajectory]
        dim_means = np.mean(dims, axis=0)
        dim_stds = np.std(dims, axis=0)
        features.extend(dim_means[:2])  # First 2 dim means
        features.extend(dim_stds[:2])  # First 2 dim stds

        return np.array(features)

    def cluster_journeys(
        self,
        journeys: list[dict[str, Any]],
        n_clusters: int = 4,
        algorithm: str = "kmeans",
    ) -> ClusteringResult:
        """Cluster journeys by behavioral similarity.

        Args:
            journeys: List of journey dictionaries
            n_clusters: Number of clusters (for k-means, GMM)
            algorithm: Clustering algorithm ("kmeans", "dbscan", "gmm")

        Returns:
            ClusteringResult with labels, centers, scores
        """
        if not journeys:
            return ClusteringResult(
                n_clusters=0,
                labels=[],
                cluster_centers=[],
                silhouette_score=0.0,
                inertia=0.0,
                cluster_sizes=[],
                algorithm=algorithm,
            )

        # Extract features
        feature_matrix = np.array([self.extract_features(j) for j in journeys])

        if algorithm == "kmeans":
            return self._kmeans_cluster(feature_matrix, n_clusters)
        elif algorithm == "dbscan":
            return self._dbscan_cluster(feature_matrix)
        elif algorithm == "gmm":
            return self._gmm_cluster(feature_matrix, n_clusters)
        else:
            logger.warning("Unknown algorithm: %s, defaulting to kmeans", algorithm)
            return self._kmeans_cluster(feature_matrix, n_clusters)

    def _kmeans_cluster(
        self,
        features: np.ndarray,
        n_clusters: int,
    ) -> ClusteringResult:
        """K-means clustering with silhouette score."""
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score

        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=self.random_state,
            n_init=10,
        )
        labels = kmeans.fit_predict(features)
        centers = kmeans.cluster_centers_.tolist()
        inertia = float(kmeans.inertia_)

        # Silhouette score (requires >= 2 clusters)
        if n_clusters >= 2 and len(np.unique(labels)) >= 2:
            sil_score = float(silhouette_score(features, labels))
        else:
            sil_score = 0.0

        cluster_sizes = [int(np.sum(labels == i)) for i in range(n_clusters)]

        return ClusteringResult(
            n_clusters=n_clusters,
            labels=labels.tolist(),
            cluster_centers=centers,
            silhouette_score=sil_score,
            inertia=inertia,
            cluster_sizes=cluster_sizes,
            algorithm="kmeans",
        )

    def _dbscan_cluster(self, features: np.ndarray) -> ClusteringResult:
        """DBSCAN clustering (density-based)."""
        from sklearn.cluster import DBSCAN
        from sklearn.metrics import silhouette_score

        # Auto-tune eps based on k-distance graph
        from sklearn.neighbors import NearestNeighbors

        neighbors = NearestNeighbors(n_neighbors=5)
        neighbors_fit = neighbors.fit(features)
        distances, _ = neighbors_fit.kneighbors(features)
        k_distances = np.sort(distances[:, -1])

        # Elbow method for eps selection
        eps = float(np.percentile(k_distances, 90))

        dbscan = DBSCAN(eps=eps, min_samples=3)
        labels = dbscan.fit_predict(features)

        # Handle noise points (label = -1)
        len([label for label in labels if label >= 0])
        unique_labels = set(labels) - {-1}

        centers = []
        cluster_sizes = []
        for label in unique_labels:
            mask = labels == label
            centers.append(features[mask].mean(axis=0).tolist())
            cluster_sizes.append(int(np.sum(mask)))

        # Silhouette score (excluding noise)
        non_noise_mask = labels != -1
        if np.sum(non_noise_mask) >= 2 and len(unique_labels) >= 2:
            sil_score = float(silhouette_score(features[non_noise_mask], labels[non_noise_mask]))
        else:
            sil_score = 0.0

        return ClusteringResult(
            n_clusters=len(unique_labels),
            labels=labels.tolist(),
            cluster_centers=centers,
            silhouette_score=sil_score,
            inertia=0.0,  # DBSCAN doesn't have inertia
            cluster_sizes=cluster_sizes,
            algorithm="dbscan",
        )

    def _gmm_cluster(
        self,
        features: np.ndarray,
        n_clusters: int,
    ) -> ClusteringResult:
        """Gaussian Mixture Model clustering."""
        from sklearn.metrics import silhouette_score
        from sklearn.mixture import GaussianMixture

        gmm = GaussianMixture(
            n_components=n_clusters,
            random_state=self.random_state,
            n_init=5,
        )
        labels = gmm.fit_predict(features)
        centers = gmm.means_.tolist()
        inertia = float(gmm.lower_bound_)

        sil_score = float(silhouette_score(features, labels)) if n_clusters >= 2 else 0.0

        cluster_sizes = [int(np.sum(labels == i)) for i in range(n_clusters)]

        return ClusteringResult(
            n_clusters=n_clusters,
            labels=labels.tolist(),
            cluster_centers=centers,
            silhouette_score=sil_score,
            inertia=inertia,
            cluster_sizes=cluster_sizes,
            algorithm="gmm",
        )

    def detect_anomalies(
        self,
        journey: dict[str, Any],
        method: str = "isolation_forest",
    ) -> AnomalyReport:
        """Detect anomalous journey patterns.

        Args:
            journey: Journey dictionary
            method: Anomaly detection method ("isolation_forest", "lof")

        Returns:
            AnomalyReport with score, type, severity
        """
        features = self.extract_features(journey).reshape(1, -1)

        # Need reference data for anomaly detection
        if not self._journey_cache:
            return AnomalyReport(
                journey_id=journey.get("id", "unknown"),
                anomaly_score=0.5,
                is_anomaly=False,
                anomaly_type=None,
                contributing_factors=[],
                severity="low",
            )

        # Build reference feature matrix
        ref_features = np.array([self.extract_features(j) for j in self._journey_cache.values()])

        if method == "isolation_forest":
            from sklearn.ensemble import IsolationForest

            iso = IsolationForest(
                contamination=0.1,
                random_state=self.random_state,
                n_estimators=100,
            )
            iso.fit(ref_features)
            score = -float(iso.score_samples(features)[0])  # Higher = more anomalous
            is_anomaly = score > 0.6

        elif method == "lof":
            from sklearn.neighbors import LocalOutlierFactor

            lof = LocalOutlierFactor(n_neighbors=5, novelty=True)
            lof.fit(ref_features)
            score = -float(lof.score_samples(features))
            is_anomaly = score > 1.5

        else:
            score = 0.5
            is_anomaly = False

        # Determine anomaly type
        coherence = journey.get("final_coherence", 0.5)
        if coherence < 0.3:
            anomaly_type = "coherence_collapse"
        elif score > 1.0:
            anomaly_type = "thermodynamic_violation"
        else:
            anomaly_type = None

        # Contributing factors
        factors = []
        if coherence < 0.4:
            factors.append(f"Low coherence ({coherence:.2f})")
        if len(journey.get("trajectory", [])) < 5:
            factors.append("Short trajectory")
        if features[0, 1] > 0.3:  # High coherence std
            factors.append("High coherence variance")

        # Severity
        if score > 1.0 or coherence < 0.3:
            severity = "critical"
        elif score > 0.7 or coherence < 0.4:
            severity = "high"
        elif score > 0.6 or coherence < 0.5:
            severity = "medium"
        else:
            severity = "low"

        return AnomalyReport(
            journey_id=journey.get("id", "unknown"),
            anomaly_score=score,
            is_anomaly=is_anomaly,
            anomaly_type=anomaly_type,
            contributing_factors=factors,
            severity=severity,
        )

    def mine_patterns(
        self,
        journeys: list[dict[str, Any]],
        min_support: float = 0.1,
    ) -> PatternLibrary:
        """Mine recurring journey patterns.

        Args:
            journeys: List of journey dictionaries
            min_support: Minimum pattern support threshold

        Returns:
            PatternLibrary with motifs, sequences, cycles
        """
        if not journeys:
            return PatternLibrary(
                motifs=[],
                sequences=[],
                cycles=[],
                support=0.0,
                confidence=0.0,
            )

        # Extract coherence sequences
        sequences = []
        for j in journeys:
            traj = j.get("trajectory", [])
            coherences = [t.get("coherence", 0.5) for t in traj]
            sequences.append(coherences)

        # Find motifs (recurring subsequences)
        motifs = self._find_motifs(sequences, min_support)

        # Find cycles (periodic patterns)
        cycles = self._find_cycles(sequences)

        # Compute support
        n_patterns = len(motifs) + len(cycles)
        support = n_patterns / max(len(journeys), 1)

        return PatternLibrary(
            motifs=motifs,
            sequences=[],
            cycles=cycles,
            support=support,
            confidence=0.7,  # Placeholder
        )

    def _find_motifs(
        self,
        sequences: list[list[float]],
        min_support: float,
    ) -> list[dict[str, Any]]:
        """Find recurring motifs in coherence sequences."""
        motifs = []

        # Simple motif: coherence stays in HIHO band (0.4-0.6) for N steps
        for i, seq in enumerate(sequences):
            hiho_streak = 0
            for c in seq:
                if 0.4 <= c <= 0.6:
                    hiho_streak += 1
                else:
                    if hiho_streak >= 3:
                        motifs.append(
                            {
                                "type": "hiho_streak",
                                "length": hiho_streak,
                                "journey_idx": i,
                            }
                        )
                    hiho_streak = 0

        return motifs[:10]  # Cap at 10 motifs

    def _find_cycles(self, sequences: list[list[float]]) -> list[dict[str, Any]]:
        """Find cyclic/periodic patterns."""
        cycles = []

        for i, seq in enumerate(sequences):
            if len(seq) < 6:
                continue

            # Simple cycle detection: coherence oscillates
            diffs = np.diff(seq)
            sign_changes = np.sum(np.diff(np.sign(diffs)) != 0)

            if sign_changes >= 3:
                cycles.append(
                    {
                        "type": "oscillation",
                        "n_turns": sign_changes,
                        "journey_idx": i,
                    }
                )

        return cycles[:10]  # Cap at 10 cycles

    def compute_archetypes(
        self,
        journeys: list[dict[str, Any]],
    ) -> list[ArchetypeModel]:
        """Identify agent behavioral archetypes.

        Args:
            journeys: List of journey dictionaries

        Returns:
            List of ArchetypeModel for each journey
        """
        archetypes = []

        for journey in journeys:
            features = self.extract_features(journey)

            mean_coherence = features[0]
            std_coherence = features[1]
            mean_phi = features[4]
            smoothness = features[8]

            # Classify archetype
            if mean_coherence < self.DRIFTER_COHERENCE_LOWER:
                archetype = ArchetypeType.DRIFTER
                confidence = 0.8
            elif std_coherence > self.OSCILLATOR_VARIANCE_THRESHOLD:
                archetype = ArchetypeType.OSCILLATOR
                confidence = 0.75
            elif mean_phi > self.INNOVATOR_PHI_THRESHOLD:
                archetype = ArchetypeType.INNOVATOR
                confidence = 0.85
            elif mean_coherence > self.STABILIZER_COHERENCE_THRESHOLD:
                archetype = ArchetypeType.STABILIZER
                confidence = 0.9
            else:
                archetype = ArchetypeType.EXPLORER
                confidence = 0.7

            characteristics = {
                "mean_coherence": float(mean_coherence),
                "std_coherence": float(std_coherence),
                "mean_phi": float(mean_phi),
                "smoothness": float(smoothness),
            }

            archetypes.append(
                ArchetypeModel(
                    archetype=archetype,
                    confidence=confidence,
                    characteristics=characteristics,
                    matching_journeys=[journey["id"]],
                    population_fraction=0.0,  # Computed later
                )
            )

        # Compute population fractions
        total = len(archetypes)
        archetype_counts = {}
        for a in archetypes:
            archetype_counts[a.archetype] = archetype_counts.get(a.archetype, 0) + 1

        for a in archetypes:
            a.population_fraction = archetype_counts[a.archetype] / max(total, 1)

        return archetypes

    def analyze_thermodynamics(self, journey: dict[str, Any]) -> ThermoAnalysis:
        """Deep thermodynamic analysis of single journey.

        Args:
            journey: Journey dictionary

        Returns:
            ThermoAnalysis with entropy, free energy, etc.
        """
        trajectory = journey.get("trajectory", [])
        if not trajectory:
            return ThermoAnalysis(
                entropy_production_rate=0.0,
                free_energy=0.0,
                effective_temperature=0.0,
                susceptibility=0.0,
                heat_capacity=0.0,
                is_attractor=False,
                well_depth=0.0,
                basin_width=0.0,
                phase_transition_detected=False,
                critical_temperature=None,
            )

        # Extract coherence history
        coherences = [t.get("coherence", 0.5) for t in trajectory]

        # Use ThermodynamicMetrics if available
        try:
            from cohezion.compound.thermodynamic_metrics import ThermodynamicMetrics

            thermo = ThermodynamicMetrics(window_size=len(coherences), min_samples=3)
            for c in coherences:
                thermo.record(c)

            state = thermo.compute_state()
            hiho_analysis = thermo.get_hiho_free_energy_analysis()

            return ThermoAnalysis(
                entropy_production_rate=state.entropy_production_rate if state else 0.0,
                free_energy=state.free_energy if state else 0.0,
                effective_temperature=state.temperature if state else 1.0,
                susceptibility=state.susceptibility if state else 0.0,
                heat_capacity=state.heat_capacity if state else 0.0,
                is_attractor=hiho_analysis.get("is_attractor", False),
                well_depth=hiho_analysis.get("well_depth", 0.0),
                basin_width=hiho_analysis.get("basin_width", 0.0),
                phase_transition_detected=False,
                critical_temperature=None,
            )
        except Exception as e:
            logger.warning("Thermodynamic analysis failed: %s", e)
            return ThermoAnalysis(
                entropy_production_rate=0.0,
                free_energy=0.0,
                effective_temperature=1.0,
                susceptibility=0.0,
                heat_capacity=0.0,
                is_attractor=False,
                well_depth=0.0,
                basin_width=0.0,
                phase_transition_detected=False,
                critical_temperature=None,
            )

    def analyze_topology(self, journey: dict[str, Any]) -> TopoAnalysis:
        """Topological persistence analysis of journey shape.

        Args:
            journey: Journey dictionary

        Returns:
            TopoAnalysis with Betti numbers, persistence entropy
        """
        trajectory = journey.get("trajectory", [])
        if not trajectory:
            return TopoAnalysis(
                n_clusters=0,
                n_loops=0,
                persistence_entropy_h0=0.0,
                persistence_entropy_h1=0.0,
                topological_complexity=0.0,
                dominant_features=[],
            )

        # Extract 12D trajectory
        dims = [t.get("dimensions", [0.5] * 12) for t in trajectory]

        # Use topological_persistence if available
        try:
            from cohezion.compound.topological_persistence import trajectory_persistence_summary

            summary = trajectory_persistence_summary(np.array(dims))

            return TopoAnalysis(
                n_clusters=summary.get("n_clusters", 0),
                n_loans=summary.get("n_loops", 0),
                persistence_entropy_h0=summary.get("persistence_entropy_h0", 0.0),
                persistence_entropy_h1=summary.get("persistence_entropy_h1", 0.0),
                topological_complexity=summary.get("topological_complexity", 0.0),
                dominant_features=[],
            )
        except Exception as e:
            logger.warning("Topological analysis failed: %s", e)
            return TopoAnalysis(
                n_clusters=0,
                n_loans=0,
                persistence_entropy_h0=0.0,
                persistence_entropy_h1=0.0,
                topological_complexity=0.0,
                dominant_features=[],
            )

    def generate_report(
        self,
        journeys: list[dict[str, Any]],
        report_title: str = "Journey Analysis Report",
    ) -> JourneyReport:
        """Generate comprehensive analysis report.

        Args:
            journeys: List of journey dictionaries
            report_title: Report title

        Returns:
            JourneyReport with all analysis results
        """
        logger.info("Generating journey analysis report for %d journeys", len(journeys))

        # 1. Clustering
        clustering = self.cluster_journeys(journeys, n_clusters=4, algorithm="kmeans")

        # 2. Archetypes
        archetypes = self.compute_archetypes(journeys)

        # 3. Anomalies
        anomalies = [self.detect_anomalies(j) for j in journeys]

        # 4. Thermodynamic summary
        thermo_results = [self.analyze_thermodynamics(j) for j in journeys]
        thermo_summary = {
            "mean_entropy_production": float(
                np.mean([t.entropy_production_rate for t in thermo_results])
            ),
            "mean_free_energy": float(np.mean([t.free_energy for t in thermo_results])),
            "n_attractors": sum(1 for t in thermo_results if t.is_attractor),
            "mean_well_depth": float(np.mean([t.well_depth for t in thermo_results])),
        }

        # 5. Topological summary
        topo_results = [self.analyze_topology(j) for j in journeys]
        topo_summary = {
            "mean_n_clusters": float(np.mean([t.n_clusters for t in topo_results])),
            "mean_n_loans": float(np.mean([t.n_loans for t in topo_results])),
            "mean_persistence_entropy": float(
                np.mean([t.persistence_entropy_h0 for t in topo_results])
            ),
        }

        # 6. Pattern mining
        patterns = self.mine_patterns(journeys)

        # 7. Key findings
        findings = []
        if clustering.silhouette_score > 0.5:
            findings.append(
                f"Strong behavioral clustering (silhouette={clustering.silhouette_score:.2f})"
            )
        if thermo_summary["n_attractors"] > len(journeys) // 2:
            findings.append(
                f"HIHO attractor confirmed ({thermo_summary['n_attractors']}/{len(journeys)} journeys)"
            )
        if sum(1 for a in anomalies if a.is_anomaly) > 0:
            findings.append(
                f"Anomalies detected in {sum(1 for a in anomalies if a.is_anomaly)} journeys"
            )

        # 8. Recommendations
        recommendations = []
        if thermo_summary["mean_free_energy"] > 1.0:
            recommendations.append("Consider thermodynamic regularization for training")
        if topo_summary["mean_persistence_entropy"] > 2.0:
            recommendations.append("High topological complexity suggests diverse training needed")

        report = JourneyReport(
            report_id=f"report_{int(datetime.now().timestamp())}",
            generated_at=datetime.now(),
            n_journeys_analyzed=len(journeys),
            clustering=clustering,
            archetypes=archetypes,
            anomalies=anomalies,
            thermodynamic_summary=thermo_summary,
            topological_summary=topo_summary,
            patterns=patterns,
            key_findings=findings,
            recommendations=recommendations,
        )

        logger.info("Generated report: %s", report.report_id)
        return report

    def save_report(self, report: JourneyReport, output_dir: str | Path) -> Path:
        """Save report to markdown file.

        Args:
            report: JourneyReport
            output_dir: Output directory

        Returns:
            Path to saved report
        """
        output_path = Path(output_dir) / f"{report.report_id}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write(f"# {report.report_id}\n\n")
            f.write(f"Generated: {report.generated_at.isoformat()}\n\n")
            f.write(f"Journeys analyzed: {report.n_journeys_analyzed}\n\n")

            f.write("## Clustering Results\n\n")
            f.write(f"- Algorithm: {report.clustering.algorithm}\n")
            f.write(f"- Clusters: {report.clustering.n_clusters}\n")
            f.write(f"- Silhouette score: {report.clustering.silhouette_score:.3f}\n\n")

            f.write("## Archetypes\n\n")
            for archetype in report.archetypes:
                f.write(
                    f"- {archetype.archetype.value}: {archetype.population_fraction * 100:.1f}% "
                )
                f.write(f"(confidence={archetype.confidence:.2f})\n")
            f.write("\n")

            f.write("## Thermodynamic Summary\n\n")
            for k, v in report.thermodynamic_summary.items():
                f.write(f"- {k}: {v:.3f}\n")
            f.write("\n")

            f.write("## Topological Summary\n\n")
            for k, v in report.topological_summary.items():
                f.write(f"- {k}: {v:.3f}\n")
            f.write("\n")

            f.write("## Key Findings\n\n")
            for finding in report.key_findings:
                f.write(f"- {finding}\n")
            f.write("\n")

            f.write("## Recommendations\n\n")
            for rec in report.recommendations:
                f.write(f"- {rec}\n")

        logger.info("Saved report to %s", output_path)
        return output_path
