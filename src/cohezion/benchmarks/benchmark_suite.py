"""Cohezion Benchmark Suite - Multi-dimensional evaluation of novel universe physics.

Implements four benchmark strategies:
A. Intrinsic Metrics - HIHO stability, thermodynamic efficiency, topological robustness
B. Comparative Baseline - Ablation studies (HIHO vs random)
C. Predictive Metrics - Coherence-reward correlation
D. External Validation - Human expert review (requires public dataset)

Architecture:
    CohezionBenchmark
        ├── compute_intrinsic_metrics() → IntrinsicResults
        ├── run_ablation_study() → ComparativeResults
        ├── compute_predictive_metrics() → PredictiveResults
        ├── prepare_human_evaluation() → HumanEvalPackage
        └── generate_report() → BenchmarkReport

Publication:
    - Hugging Face dataset upload
    - Public-facing documentation
    - Interactive demo notebook
    - Expert review workflow
"""

from __future__ import annotations

import json
import logging
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats


logger = logging.getLogger(__name__)


@dataclass
class IntrinsicResults:
    """Intrinsic metrics (what makes Cohezion novel)."""

    hiho_stability: float  # % time in [0.4, 0.6] coherence
    thermodynamic_efficiency: float  # task_reward / entropy_production
    topological_robustness: float  # Δβ₀ / perturbation_magnitude
    archetype_balance: float  # std(population_fraction)
    journey_smoothness: float  # 1 - mean(|Δcoherence|)
    phase_transition_rate: float  # n_critical_points / trajectory_length
    composite_score: float  # Weighted average


@dataclass
class ComparativeResults:
    """Comparative metrics (ablation study)."""

    baseline_mean: float
    hiho_mean: float
    cohen_d: float  # Effect size
    improvement_ratio: float  # (hiho - baseline) / baseline
    p_value: float  # Statistical significance
    confidence_interval: tuple[float, float]  # 95% CI
    sample_size: int


@dataclass
class PredictiveResults:
    """Predictive metrics (does HIHO predict success?)."""

    coherence_reward_correlation: float  # Pearson r
    p_value: float
    r_squared: float  # Variance explained
    rmse: float  # Root mean squared error
    calibration_slope: float  # Ideal = 1.0
    discrimination_auc: float  # Area under ROC curve


@dataclass
class HumanEvalPackage:
    """Package for human expert evaluation."""

    trajectory_pairs: list[dict[str, Any]]  # (HIHO, random) pairs
    evaluation_form: dict[str, Any]  # Questions for experts
    instructions: str  # How to evaluate
    expected_pattern: str  # What experts should recognize
    n_pairs: int
    estimated_time_minutes: float


@dataclass
class BenchmarkReport:
    """Comprehensive benchmark report."""

    report_id: str
    generated_at: datetime
    n_journeys: int
    intrinsic: IntrinsicResults
    comparative: ComparativeResults | None
    predictive: PredictiveResults | None
    human_eval: HumanEvalPackage | None
    key_findings: list[str]
    recommendations: list[str]
    hugging_face_ready: bool


class CohezionBenchmark:
    """Multi-dimensional benchmark suite for novel universe physics.

    Implements four strategies:
    A. Intrinsic Metrics - Measure what makes Cohezion novel
    B. Comparative Baseline - Ablation studies (HIHO vs random)
    C. Predictive Metrics - Test if HIHO predicts task success
    D. External Validation - Human expert review (public dataset)

    Example:
        ```python
        benchmark = CohezionBenchmark()

        # Load journeys
        journeys = benchmark.load_journeys("data/universe")

        # Compute intrinsic metrics
        intrinsic = benchmark.compute_intrinsic_metrics(journeys)
        print(f"HIHO stability: {intrinsic.hiho_stability:.2%}")

        # Run ablation study
        comparative = benchmark.run_ablation_study(journeys)
        print(f"Cohen's d: {comparative.cohen_d:.2f}")

        # Generate report
        report = benchmark.generate_report(journeys)
        ```
    """

    # Intrinsic metric weights
    HIHO_WEIGHT: float = 0.3
    THERMO_WEIGHT: float = 0.2
    TOPO_WEIGHT: float = 0.15
    ARCHETYPE_WEIGHT: float = 0.15
    SMOOTHNESS_WEIGHT: float = 0.1
    PHASE_WEIGHT: float = 0.1

    # HIHO band
    HIHO_LOWER: float = 0.4
    HIHO_UPPER: float = 0.6

    def __init__(self, random_state: int = 42):
        """Initialize benchmark suite.

        Args:
            random_state: Random seed for reproducibility
        """
        self.random_state = random_state
        self.rng = np.random.RandomState(random_state)

        # Cache for loaded data
        self._journey_cache: list[dict[str, Any]] = []
        self._baseline_cache: list[dict[str, Any]] = []

        logger.debug("Initialized CohezionBenchmark with seed=%d", random_state)

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
            except Exception as e:
                logger.error("Failed to load journey %s: %s", json_file.name, e)

        self._journey_cache = journeys
        logger.info("Loaded %d journeys from %s", len(journeys), journey_path)
        return journeys

    def compute_intrinsic_metrics(
        self,
        journeys: list[dict[str, Any]],
    ) -> IntrinsicResults:
        """Compute intrinsic metrics (Strategy A).

        Metrics:
        - HIHO Stability: % time in [0.4, 0.6] coherence
        - Thermodynamic Efficiency: reward / entropy_production
        - Topological Robustness: shape persistence under perturbation
        - Archetype Balance: behavioral diversity
        - Journey Smoothness: trajectory quality
        - Phase Transition Rate: adaptive flexibility

        Args:
            journeys: List of journey dictionaries

        Returns:
            IntrinsicResults with all metrics
        """
        if not journeys:
            return IntrinsicResults(
                hiho_stability=0.0,
                thermodynamic_efficiency=0.0,
                topological_robustness=0.0,
                archetype_balance=0.0,
                journey_smoothness=0.0,
                phase_transition_rate=0.0,
                composite_score=0.0,
            )

        # 1. HIHO Stability
        hiho_times = []
        for j in journeys:
            traj = j.get("trajectory", [])
            coherences = [t.get("coherence", 0.5) for t in traj]
            hiho_count = sum(1 for c in coherences if self.HIHO_LOWER <= c <= self.HIHO_UPPER)
            hiho_times.append(hiho_count / max(len(coherences), 1))
        hiho_stability = float(np.mean(hiho_times))

        # 2. Thermodynamic Efficiency
        efficiencies = []
        for j in journeys:
            traj = j.get("trajectory", [])
            rewards = [t.get("phi_score", 0.5) for t in traj]
            # Approximate entropy production from coherence variance
            entropy_prod = np.std([t.get("coherence", 0.5) for t in traj])
            if entropy_prod > 0.01:
                eff = np.mean(rewards) / entropy_prod
                efficiencies.append(eff)
        thermodynamic_efficiency = float(np.mean(efficiencies)) if efficiencies else 0.0

        # 3. Topological Robustness (simplified)
        # Use coherence variance as proxy for topological change
        topo_scores = []
        for j in journeys:
            traj = j.get("trajectory", [])
            coherences = [t.get("coherence", 0.5) for t in traj]
            # Low variance = high robustness
            variance = np.var(coherences)
            robustness = 1.0 / (1.0 + variance * 10)
            topo_scores.append(robustness)
        topological_robustness = float(np.mean(topo_scores))

        # 4. Archetype Balance
        try:
            from cohezion.compound.journey_analyzer import JourneyAnalyzer

            analyzer = JourneyAnalyzer(random_state=self.random_state)
            archetypes = analyzer.compute_archetypes(journeys)
            fractions = [a.population_fraction for a in archetypes]
            # Ideal balance: equal distribution (std = 0.2 for 5 archetypes)
            archetype_balance = 1.0 - min(statistics.stdev(fractions) / 0.2, 1.0)
        except Exception:
            archetype_balance = 0.5

        # 5. Journey Smoothness
        smoothness_scores = []
        for j in journeys:
            traj = j.get("trajectory", [])
            coherences = [t.get("coherence", 0.5) for t in traj]
            if len(coherences) > 1:
                diffs = np.diff(coherences)
                smoothness = 1.0 - np.mean(np.abs(diffs))
                smoothness_scores.append(smoothness)
        journey_smoothness = float(np.mean(smoothness_scores)) if smoothness_scores else 0.5

        # 6. Phase Transition Rate
        phase_rates = []
        for j in journeys:
            traj = j.get("trajectory", [])
            coherences = [t.get("coherence", 0.5) for t in traj]
            # Detect critical points (large coherence changes)
            if len(coherences) > 1:
                diffs = np.abs(np.diff(coherences))
                critical_points = sum(1 for d in diffs if d > 0.2)
                rate = critical_points / len(coherences)
                phase_rates.append(rate)
        phase_transition_rate = float(np.mean(phase_rates)) if phase_rates else 0.0

        # 7. Composite Score (weighted average)
        composite = (
            self.HIHO_WEIGHT * hiho_stability
            + self.THERMO_WEIGHT * thermodynamic_efficiency
            + self.TOPO_WEIGHT * topological_robustness
            + self.ARCHETYPE_WEIGHT * archetype_balance
            + self.SMOOTHNESS_WEIGHT * journey_smoothness
            + self.PHASE_WEIGHT * phase_transition_rate
        )

        # Normalize composite to [0, 1]
        composite = min(1.0, max(0.0, composite))

        return IntrinsicResults(
            hiho_stability=hiho_stability,
            thermodynamic_efficiency=thermodynamic_efficiency,
            topological_robustness=topological_robustness,
            archetype_balance=archetype_balance,
            journey_smoothness=journey_smoothness,
            phase_transition_rate=phase_transition_rate,
            composite_score=composite,
        )

    def run_ablation_study(
        self,
        journeys: list[dict[str, Any]],
        baseline_journeys: list[dict[str, Any]] | None = None,
    ) -> ComparativeResults:
        """Run ablation study (Strategy B).

        Compares HIHO physics vs baseline (random/randomized):
        - Effect size (Cohen's d)
        - Improvement ratio
        - Statistical significance (t-test)
        - 95% confidence interval

        Args:
            journeys: HIHO journeys
            baseline_journeys: Baseline journeys (or generate random)

        Returns:
            ComparativeResults with effect sizes
        """
        if not journeys:
            return ComparativeResults(
                baseline_mean=0.0,
                hiho_mean=0.0,
                cohen_d=0.0,
                improvement_ratio=0.0,
                p_value=1.0,
                confidence_interval=(0.0, 0.0),
                sample_size=0,
            )

        # Extract HIHO scores
        hiho_scores = [j.get("final_phi_score", 0.5) for j in journeys]

        # Generate or use baseline
        if baseline_journeys:
            baseline_scores = [j.get("final_phi_score", 0.5) for j in baseline_journeys]
        else:
            # Generate random baseline (uniform [0, 1])
            baseline_scores = list(self.rng.uniform(0.0, 1.0, len(hiho_scores)))

        # Compute statistics
        hiho_mean = float(np.mean(hiho_scores))
        baseline_mean = float(np.mean(baseline_scores))
        hiho_std = float(np.std(hiho_scores))
        baseline_std = float(np.std(baseline_scores))

        # Pooled standard deviation
        pooled_std = np.sqrt((hiho_std**2 + baseline_std**2) / 2)

        # Cohen's d (effect size)
        cohen_d = (hiho_mean - baseline_mean) / pooled_std if pooled_std > 0 else 0.0

        # Improvement ratio
        if baseline_mean > 0:
            improvement_ratio = (hiho_mean - baseline_mean) / baseline_mean
        else:
            improvement_ratio = 0.0

        # Two-sample t-test
        _, p_value = stats.ttest_ind(hiho_scores, baseline_scores)

        # 95% confidence interval for difference
        diff = hiho_mean - baseline_mean
        n = len(hiho_scores) + len(baseline_scores) - 2
        t_crit = stats.t.ppf(0.975, df=n)
        se = np.sqrt(hiho_std**2 / len(hiho_scores) + baseline_std**2 / len(baseline_scores))
        ci = (diff - t_crit * se, diff + t_crit * se)

        return ComparativeResults(
            baseline_mean=baseline_mean,
            hiho_mean=hiho_mean,
            cohen_d=cohen_d,
            improvement_ratio=improvement_ratio,
            p_value=float(p_value),
            confidence_interval=(float(ci[0]), float(ci[1])),
            sample_size=len(hiho_scores),
        )

    def compute_predictive_metrics(
        self,
        journeys: list[dict[str, Any]],
    ) -> PredictiveResults:
        """Compute predictive metrics (Strategy C).

        Tests if HIHO coherence predicts task success:
        - Coherence-reward correlation (Pearson r)
        - R-squared (variance explained)
        - RMSE (prediction error)
        - Calibration (ideal slope = 1.0)
        - Discrimination (AUC)

        Args:
            journeys: List of journey dictionaries

        Returns:
            PredictiveResults with correlation stats
        """
        if not journeys or len(journeys) < 3:
            return PredictiveResults(
                coherence_reward_correlation=0.0,
                p_value=1.0,
                r_squared=0.0,
                rmse=0.0,
                calibration_slope=0.0,
                discrimination_auc=0.5,
            )

        # Extract coherence and rewards
        coherences = [j.get("final_coherence", 0.5) for j in journeys]
        rewards = [j.get("final_phi_score", 0.5) for j in journeys]

        # Pearson correlation
        r, p_value = stats.pearsonr(coherences, rewards)
        r_squared = r**2

        # RMSE (predict reward from coherence)
        # Simple linear regression: reward = a * coherence + b
        slope, intercept, _, _, _ = stats.linregress(coherences, rewards)
        predictions = [slope * c + intercept for c in coherences]
        residuals = [r - p for r, p in zip(rewards, predictions, strict=False)]
        rmse = float(np.sqrt(np.mean([e**2 for e in residuals])))

        # Calibration slope (ideal = 1.0)
        calibration_slope = float(slope)

        # Discrimination AUC (can we distinguish high vs low reward?)
        # Split into high/low reward groups
        median_reward = np.median(rewards)
        high_coherences = [c for c, r in zip(coherences, rewards, strict=False) if r > median_reward]
        low_coherences = [c for c, r in zip(coherences, rewards, strict=False) if r <= median_reward]

        # Mann-Whitney U test (equivalent to AUC)
        if len(high_coherences) > 0 and len(low_coherences) > 0:
            u_stat, _ = stats.mannwhitneyu(high_coherences, low_coherences, alternative="greater")
            auc = float(u_stat / (len(high_coherences) * len(low_coherences)))
        else:
            auc = 0.5

        return PredictiveResults(
            coherence_reward_correlation=float(r),
            p_value=float(p_value),
            r_squared=float(r_squared),
            rmse=rmse,
            calibration_slope=calibration_slope,
            discrimination_auc=auc,
        )

    def prepare_human_evaluation(
        self,
        journeys: list[dict[str, Any]],
        n_pairs: int = 10,
    ) -> HumanEvalPackage:
        """Prepare human evaluation package (Strategy D).

        Creates trajectory pairs for expert review:
        - (HIHO, random) pairs
        - Evaluation form
        - Instructions
        - Expected pattern description

        Args:
            journeys: List of journey dictionaries
            n_pairs: Number of pairs to create

        Returns:
            HumanEvalPackage for expert review
        """
        if not journeys or len(journeys) < n_pairs:
            return HumanEvalPackage(
                trajectory_pairs=[],
                evaluation_form={},
                instructions="",
                expected_pattern="",
                n_pairs=0,
                estimated_time_minutes=0.0,
            )

        # Create pairs (HIHO journey + random baseline)
        pairs = []
        for i in range(min(n_pairs, len(journeys))):
            hiho_journey = journeys[i]
            # Generate random baseline trajectory
            baseline_traj = {
                "id": f"baseline_{i}",
                "trajectory": [
                    {
                        "coherence": float(self.rng.uniform(0.0, 1.0)),
                        "phi_score": float(self.rng.uniform(0.0, 1.0)),
                    }
                    for _ in range(len(hiho_journey.get("trajectory", [])))
                ],
                "final_coherence": float(self.rng.uniform(0.0, 1.0)),
                "final_phi_score": float(self.rng.uniform(0.0, 1.0)),
            }

            pairs.append(
                {
                    "hiho": hiho_journey,
                    "baseline": baseline_traj,
                    "pair_id": f"pair_{i}",
                }
            )

        # Evaluation form
        evaluation_form = {
            "questions": [
                {
                    "id": "stability",
                    "question": "Which trajectory appears more stable?",
                    "options": ["Trajectory A", "Trajectory B", "Unclear"],
                },
                {
                    "id": "coherence",
                    "question": "Which trajectory maintains better coherence?",
                    "options": ["Trajectory A", "Trajectory B", "Unclear"],
                },
                {
                    "id": "confidence",
                    "question": "How confident are you in your assessment?",
                    "options": ["Low", "Medium", "High"],
                },
            ],
        }

        # Instructions
        instructions = """
        Expert Evaluation Instructions:

        1. You will see pairs of agent trajectories through a 12D manifold.
        2. One trajectory uses HIHO physics (coherence attractor at 0.5).
        3. The other uses random movement (no physics).
        4. For each pair, indicate which appears more stable and coherent.
        5. Rate your confidence in each assessment.

        Expected Pattern:
        HIHO trajectories should show:
        - Stability around 0.5 coherence (attractor behavior)
        - Smooth transitions (low variance)
        - Clear purpose (directed movement)

        Random trajectories should show:
        - Unpredictable coherence (high variance)
        - No clear attractor
        - Erratic movement
        """

        # Expected pattern
        expected_pattern = "HIHO trajectories cluster around 0.5 coherence with low variance"

        # Estimated time
        estimated_time = n_pairs * 2.0  # 2 minutes per pair

        return HumanEvalPackage(
            trajectory_pairs=pairs,
            evaluation_form=evaluation_form,
            instructions=instructions,
            expected_pattern=expected_pattern,
            n_pairs=n_pairs,
            estimated_time_minutes=estimated_time,
        )

    def generate_report(
        self,
        journeys: list[dict[str, Any]],
        include_comparative: bool = True,
        include_predictive: bool = True,
        include_human_eval: bool = True,
    ) -> BenchmarkReport:
        """Generate comprehensive benchmark report.

        Args:
            journeys: List of journey dictionaries
            include_comparative: Whether to run ablation study
            include_predictive: Whether to compute predictive metrics
            include_human_eval: Whether to prepare human evaluation

        Returns:
            BenchmarkReport with all results
        """
        logger.info("Generating benchmark report for %d journeys", len(journeys))

        # 1. Intrinsic metrics (always)
        intrinsic = self.compute_intrinsic_metrics(journeys)

        # 2. Comparative metrics (optional)
        comparative = None
        if include_comparative:
            comparative = self.run_ablation_study(journeys)

        # 3. Predictive metrics (optional)
        predictive = None
        if include_predictive:
            predictive = self.compute_predictive_metrics(journeys)

        # 4. Human evaluation (optional)
        human_eval = None
        if include_human_eval:
            human_eval = self.prepare_human_evaluation(journeys)

        # 5. Key findings
        findings = []
        if intrinsic.hiho_stability > 0.7:
            findings.append(f"Strong HIHO stability ({intrinsic.hiho_stability:.1%})")
        if comparative and comparative.cohen_d > 0.8:
            findings.append(f"Large effect size (Cohen's d = {comparative.cohen_d:.2f})")
        if predictive and abs(predictive.coherence_reward_correlation) > 0.5:
            findings.append(f"Strong coherence-reward correlation (r = {predictive.coherence_reward_correlation:.2f})")

        # 6. Recommendations
        recommendations = []
        if intrinsic.hiho_stability < 0.5:
            recommendations.append("Improve HIHO attractor strength")
        if comparative and comparative.p_value > 0.05:
            recommendations.append("Increase sample size for statistical significance")
        if predictive and predictive.r_squared < 0.25:
            recommendations.append("HIHO coherence has limited predictive power")

        # 7. Hugging Face readiness
        hf_ready = (
            intrinsic.composite_score > 0.5 and (not comparative or comparative.cohen_d > 0.5) and len(journeys) >= 20
        )

        report = BenchmarkReport(
            report_id=f"benchmark_{int(datetime.now().timestamp())}",
            generated_at=datetime.now(),
            n_journeys=len(journeys),
            intrinsic=intrinsic,
            comparative=comparative,
            predictive=predictive,
            human_eval=human_eval,
            key_findings=findings,
            recommendations=recommendations,
            hugging_face_ready=hf_ready,
        )

        logger.info("Generated benchmark report: %s", report.report_id)
        return report

    def save_report(self, report: BenchmarkReport, output_dir: str | Path) -> Path:
        """Save report to markdown file.

        Args:
            report: BenchmarkReport
            output_dir: Output directory

        Returns:
            Path to saved report
        """
        output_path = Path(output_dir) / f"{report.report_id}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write("# Cohezion Benchmark Report\n\n")
            f.write(f"Generated: {report.generated_at.isoformat()}\n\n")
            f.write(f"Journeys analyzed: {report.n_journeys}\n\n")

            f.write("## Intrinsic Metrics\n\n")
            f.write(f"- HIHO Stability: {report.intrinsic.hiho_stability:.1%}\n")
            f.write(f"- Thermodynamic Efficiency: {report.intrinsic.thermodynamic_efficiency:.2f}\n")
            f.write(f"- Topological Robustness: {report.intrinsic.topological_robustness:.2f}\n")
            f.write(f"- Archetype Balance: {report.intrinsic.archetype_balance:.2f}\n")
            f.write(f"- Journey Smoothness: {report.intrinsic.journey_smoothness:.2f}\n")
            f.write(f"- Phase Transition Rate: {report.intrinsic.phase_transition_rate:.2f}\n")
            f.write(f"- **Composite Score: {report.intrinsic.composite_score:.2f}**\n\n")

            if report.comparative:
                f.write("## Comparative Metrics (Ablation Study)\n\n")
                f.write(f"- Baseline Mean: {report.comparative.baseline_mean:.3f}\n")
                f.write(f"- HIHO Mean: {report.comparative.hiho_mean:.3f}\n")
                f.write(f"- **Cohen's d: {report.comparative.cohen_d:.2f}**\n")
                f.write(f"- Improvement Ratio: {report.comparative.improvement_ratio:.1%}\n")
                f.write(f"- p-value: {report.comparative.p_value:.4f}\n")
                ci = report.comparative.confidence_interval
                f.write("- 95% CI:\n")
                f.write(f"    ({ci[0]:.3f}, {ci[1]:.3f})\n\n")

            if report.predictive:
                f.write("## Predictive Metrics\n\n")
                corr = report.predictive.coherence_reward_correlation
                f.write(f"- Coherence-Reward Correlation: {corr:.3f}\n")
                f.write(f"- p-value: {report.predictive.p_value:.4f}\n")
                f.write(f"- R-squared: {report.predictive.r_squared:.3f}\n")
                f.write(f"- RMSE: {report.predictive.rmse:.3f}\n")
                f.write(f"- Calibration Slope: {report.predictive.calibration_slope:.2f}\n")
                f.write(f"- Discrimination AUC: {report.predictive.discrimination_auc:.3f}\n\n")

            if report.human_eval:
                f.write("## Human Evaluation Package\n\n")
                f.write(f"- Trajectory Pairs: {report.human_eval.n_pairs}\n")
                f.write(f"- Estimated Time: {report.human_eval.estimated_time_minutes:.1f} minutes\n")
                f.write(f"- Hugging Face Ready: {report.hugging_face_ready}\n\n")

            f.write("## Key Findings\n\n")
            for finding in report.key_findings:
                f.write(f"- {finding}\n")
            f.write("\n")

            f.write("## Recommendations\n\n")
            for rec in report.recommendations:
                f.write(f"- {rec}\n")

        logger.info("Saved benchmark report to %s", output_path)
        return output_path

    def export_for_huggingface(
        self,
        journeys: list[dict[str, Any]],
        output_dir: str | Path,
        dataset_name: str = "cohezion-benchmark",
    ) -> Path:
        """Export benchmark dataset for Hugging Face upload.

        Creates:
        - dataset.json (all journeys)
        - README.md (dataset card)
        - evaluation_form.json (human eval questions)
        - metadata.json (benchmark stats)

        Args:
            journeys: List of journey dictionaries
            output_dir: Output directory
            dataset_name: Hugging Face dataset name

        Returns:
            Path to export directory
        """
        export_path = Path(output_dir) / f"{dataset_name}"
        export_path.mkdir(parents=True, exist_ok=True)

        # 1. Save dataset
        dataset_file = export_path / "dataset.json"
        with open(dataset_file, "w") as f:
            json.dump(journeys, f, indent=2)

        # 2. Generate README (dataset card)
        readme_content = self._generate_dataset_card(dataset_name, len(journeys))
        readme_file = export_path / "README.md"
        with open(readme_file, "w") as f:
            f.write(readme_content)

        # 3. Save evaluation form
        human_eval = self.prepare_human_evaluation(journeys)
        eval_file = export_path / "evaluation_form.json"
        with open(eval_file, "w") as f:
            json.dump(
                {
                    "form": human_eval.evaluation_form,
                    "instructions": human_eval.instructions,
                    "expected_pattern": human_eval.expected_pattern,
                },
                f,
                indent=2,
            )

        # 4. Save metadata
        intrinsic = self.compute_intrinsic_metrics(journeys)
        metadata = {
            "dataset_name": dataset_name,
            "n_journeys": len(journeys),
            "generated_at": datetime.now().isoformat(),
            "intrinsic_metrics": {
                "hiho_stability": intrinsic.hiho_stability,
                "composite_score": intrinsic.composite_score,
            },
            "license": "MIT",
            "contact": "manderson240@github.com",
        }
        metadata_file = export_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info("Exported Hugging Face dataset to %s", export_path)
        return export_path

    def _generate_dataset_card(self, dataset_name: str, n_journeys: int) -> str:
        """Generate Hugging Face dataset card (README.md)."""
        return f"""---
dataset_info:
  features:
    - id: string
    - agent_name: string
    - intent: string
    - trajectory: list[dict]
    - final_coherence: float
    - final_phi_score: float
  splits:
    - name: train
      num_examples: {n_journeys}
---

# {dataset_name}

## Dataset Description

This dataset contains agent trajectories through the 12D HIHO manifold
from the Cohezion universe simulation framework.

## Key Features

- **12D State Space**: Smith's 4 fabrics (Space, Field, Control, Precipitation)
- **HIHO Attractor**: Coherence clusters around 0.5 (thermodynamic stability point)
- **Thermodynamic Metrics**: Entropy production, free energy, phase transitions
- **Topological Features**: Behavioral modes, cycles, persistence entropy

## Benchmark Strategies

1. **Intrinsic Metrics**: HIHO stability, thermodynamic efficiency, topological robustness
2. **Comparative Baseline**: Ablation study (HIHO vs random)
3. **Predictive Metrics**: Coherence-reward correlation
4. **Human Evaluation**: Expert review of trajectory pairs

## Usage

```python
from datasets import load_dataset

dataset = load_dataset("manderson240/{dataset_name}")
journey = dataset["train"][0]
print(journey["trajectory"])
```

## Citation

```bibtex
@dataset{{cohezion-benchmark,
  author = {{Anderson, Mike}},
  title = {{{dataset_name}: Agent Trajectories in 12D HIHO Manifold}},
  year = {{2026}},
  publisher = {{Hugging Face}},
  url = {{https://huggingface.co/datasets/manderson240/{dataset_name}}}
}}
```

## License

MIT License
"""
