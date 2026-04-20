"""
BlueQubit Strategy Selector
Automatically selects best strategy based on problem characteristics
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
import qiskit
from circuit_library import CircuitLibrary


class ChallengeType(Enum):
    """Types of quantum challenges."""

    UNKNOWN = "unknown"
    PEAKED_CIRCUIT = "peaked"  # Find heavy output
    QUANTUM_ADVANTAGE = "advantage"  # Demonstrate speedup
    VARIATIONAL_OPTIMIZATION = "vqa"  # Optimize parameters
    QAOA = "qaoa"  # Combinatorial optimization
    STATE_PREPARATION = "state_prep"  # Prepare specific state


@dataclass
class StrategyRecommendation:
    """Strategy recommendation with justification."""

    challenge_type: ChallengeType
    primary_strategy: str
    secondary_strategy: Optional[str]
    device: str
    shots: int
    bond_dimension: Optional[int]
    estimated_time: str
    estimated_cost: str
    confidence: float
    justification: List[str]


class StrategySelector:
    """
    Intelligent strategy selector for quantum challenges.

    Analyzes problem characteristics and recommends optimal approach.
    """

    def __init__(self):
        """Initialize strategy selector."""
        self.lib = CircuitLibrary()
        self.strategies = {
            "mps_heavy_output": self._mps_heavy_output_strategy,
            "mps_statevector": self._mps_statevector_strategy,
            "pauli_path": self._pauli_path_strategy,
            "vqa_gradient": self._vqa_gradient_strategy,
            "qaoa_mixer": self._qaoa_mixer_strategy,
        }

    def analyze_challenge(
        self,
        circuit: Optional[qiskit.QuantumCircuit] = None,
        n_qubits: Optional[int] = None,
        target: Optional[str] = None,
        objective: Optional[str] = None,
    ) -> ChallengeType:
        """
        Analyze challenge characteristics to determine type.

        Args:
            circuit: The quantum circuit (if available)
            n_qubits: Number of qubits
            target: Target description
            objective: Objective description

        Returns:
            ChallengeType classification
        """
        indicators = []

        # Check for peaked circuit indicators
        if target and any(
            word in target.lower() for word in ["heavy", "peak", "dimple", "probability"]
        ):
            indicators.append("peaked keywords in target")
            return ChallengeType.PEAKED_CIRCUIT

        # Check for VQA indicators
        if objective and any(
            word in objective.lower()
            for word in ["optimize", "minimize", "variational", "vqe", "vqa"]
        ):
            indicators.append("optimization keywords in objective")
            return ChallengeType.VARIATIONAL_OPTIMIZATION

        # Check for QAOA indicators
        if objective and any(
            word in objective.lower() for word in ["maxcut", "graph", "partition", "combinatorial"]
        ):
            indicators.append("combinatorial optimization keywords")
            return ChallengeType.QAOA

        # Check for state preparation
        if target and any(
            word in target.lower() for word in ["state", "ghz", "w-state", "bell", "prepare"]
        ):
            indicators.append("state preparation keywords")
            return ChallengeType.STATE_PREPARATION

        # Check circuit characteristics
        if circuit:
            depth = circuit.depth()
            n_gates = len(circuit.data)

            # High depth with many gates suggests variational
            if depth > 50 and n_gates > 100:
                indicators.append(f"deep circuit ({depth} depth, {n_gates} gates)")
                return ChallengeType.VARIATIONAL_OPTIMIZATION

            # Medium depth with entanglement suggests peaked
            if 10 < depth <= 50:
                indicators.append(f"medium depth circuit ({depth})")
                return ChallengeType.PEAKED_CIRCUIT

        # Default based on qubit count
        if n_qubits:
            if n_qubits <= 20:
                indicators.append(f"small circuit ({n_qubits} qubits)")
                return ChallengeType.PEAKED_CIRCUIT
            elif n_qubits <= 40:
                indicators.append(f"medium circuit ({n_qubits} qubits)")
                return ChallengeType.QUANTUM_ADVANTAGE
            else:
                indicators.append(f"large circuit ({n_qubits} qubits)")
                return ChallengeType.QUANTUM_ADVANTAGE

        return ChallengeType.UNKNOWN

    def recommend_strategy(
        self,
        challenge_type: ChallengeType,
        n_qubits: int,
        budget: str = "medium",
        time_constraint: str = "relaxed",
    ) -> StrategyRecommendation:
        """
        Recommend strategy based on challenge type and constraints.

        Args:
            challenge_type: Classified challenge type
            n_qubits: Number of qubits
            budget: Cost budget (low/medium/high)
            time_constraint: Time available (tight/relaxed)

        Returns:
            StrategyRecommendation
        """
        justification = []

        if challenge_type == ChallengeType.PEAKED_CIRCUIT:
            return self._recommend_peaked_strategy(n_qubits, budget, time_constraint)

        elif challenge_type == ChallengeType.VARIATIONAL_OPTIMIZATION:
            return self._recommend_vqa_strategy(n_qubits, budget, time_constraint)

        elif challenge_type == ChallengeType.QAOA:
            return self._recommend_qaoa_strategy(n_qubits, budget, time_constraint)

        elif challenge_type == ChallengeType.STATE_PREPARATION:
            return self._recommend_state_prep_strategy(n_qubits, budget, time_constraint)

        else:  # UNKNOWN or QUANTUM_ADVANTAGE
            # Conservative approach
            justification.append("Unknown challenge type - using conservative MPS strategy")
            return StrategyRecommendation(
                challenge_type=challenge_type,
                primary_strategy="mps_heavy_output",
                secondary_strategy="pauli_path",
                device="mps.cpu",
                shots=10000 if n_qubits > 17 else 0,
                bond_dimension=64,
                estimated_time="10-60 seconds",
                estimated_cost="$0.00",
                confidence=0.5,
                justification=justification,
            )

    def _recommend_peaked_strategy(
        self, n_qubits: int, budget: str, time_constraint: str
    ) -> StrategyRecommendation:
        """Recommend strategy for peaked circuit challenges."""
        justification = []

        # Device selection
        if n_qubits <= 17:
            device = "mps.cpu"
            shots = 0  # Can use probabilities
            bond_dim = 128
            justification.append(f"Small circuit ({n_qubits} qubits) - use probabilities")
        elif n_qubits <= 30:
            device = "mps.cpu"
            shots = 100000
            bond_dim = 128
            justification.append(f"Medium circuit ({n_qubits} qubits) - use high-shot sampling")
        else:
            device = "mps.cpu" if budget == "low" else "mps.gpu"
            shots = 100000
            bond_dim = 256
            justification.append(f"Large circuit ({n_qubits} qubits) - use {device}")

        # Time estimation
        if time_constraint == "tight":
            shots = min(shots, 10000) if shots > 0 else 0
            justification.append("Time constraint - reducing shots")

        confidence = 0.9 if n_qubits <= 30 else 0.75

        return StrategyRecommendation(
            challenge_type=ChallengeType.PEAKED_CIRCUIT,
            primary_strategy="mps_heavy_output",
            secondary_strategy="pauli_path" if n_qubits <= 20 else None,
            device=device,
            shots=shots,
            bond_dimension=bond_dim,
            estimated_time="30-120 seconds",
            estimated_cost="$0.00" if device == "mps.cpu" else "$0.20-0.50",
            confidence=confidence,
            justification=justification,
        )

    def _recommend_vqa_strategy(
        self, n_qubits: int, budget: str, time_constraint: str
    ) -> StrategyRecommendation:
        """Recommend strategy for variational optimization."""
        justification = [
            "Variational algorithm requires iterative optimization",
            "Use Pennylane for parameter optimization",
        ]

        device = "mps.cpu"
        shots = 1024  # Need shots for expectation values

        return StrategyRecommendation(
            challenge_type=ChallengeType.VARIATIONAL_OPTIMIZATION,
            primary_strategy="vqa_gradient",
            secondary_strategy="mps_heavy_output",
            device=device,
            shots=shots,
            bond_dimension=64,
            estimated_time="5-30 minutes (iterative)",
            estimated_cost="$0.00-1.00",
            confidence=0.85,
            justification=justification,
        )

    def _recommend_qaoa_strategy(
        self, n_qubits: int, budget: str, time_constraint: str
    ) -> StrategyRecommendation:
        """Recommend strategy for QAOA."""
        justification = [
            "QAOA requires classical-quantum hybrid loop",
            "Optimize gamma and beta parameters",
        ]

        return StrategyRecommendation(
            challenge_type=ChallengeType.QAOA,
            primary_strategy="qaoa_mixer",
            secondary_strategy="vqa_gradient",
            device="mps.cpu",
            shots=1024,
            bond_dimension=64,
            estimated_time="5-20 minutes",
            estimated_cost="$0.00-0.50",
            confidence=0.8,
            justification=justification,
        )

    def _recommend_state_prep_strategy(
        self, n_qubits: int, budget: str, time_constraint: str
    ) -> StrategyRecommendation:
        """Recommend strategy for state preparation."""
        justification = [
            "State preparation requires precise gate sequence",
        ]

        return StrategyRecommendation(
            challenge_type=ChallengeType.STATE_PREPARATION,
            primary_strategy="mps_statevector",
            secondary_strategy="mps_heavy_output",
            device="mps.cpu",
            shots=0,  # Get statevector
            bond_dimension=256,
            estimated_time="5-30 seconds",
            estimated_cost="$0.00",
            confidence=0.9,
            justification=justification,
        )

    def execute_strategy(
        self,
        recommendation: StrategyRecommendation,
        circuit: Optional[qiskit.QuantumCircuit] = None,
    ) -> Dict:
        """
        Execute the recommended strategy.

        Args:
            recommendation: Strategy recommendation
            circuit: Circuit to execute (optional)

        Returns:
            Execution results
        """
        strategy_fn = self.strategies.get(recommendation.primary_strategy)

        if not strategy_fn:
            return {"error": f"Unknown strategy: {recommendation.primary_strategy}"}

        return strategy_fn(circuit, recommendation)

    # Strategy implementations
    def _mps_heavy_output_strategy(self, circuit, recommendation):
        """Execute MPS heavy output strategy."""
        return {
            "strategy": "MPS Heavy Output",
            "device": recommendation.device,
            "shots": recommendation.shots,
            "bond_dimension": recommendation.bond_dimension,
            "steps": [
                "1. Submit circuit to MPS device",
                "2. Get measurement counts",
                "3. Calculate heavy output threshold",
                "4. Extract heavy outputs",
                "5. Calculate SNR",
            ],
        }

    def _mps_statevector_strategy(self, circuit, recommendation):
        """Execute MPS statevector strategy."""
        return {
            "strategy": "MPS Statevector",
            "device": recommendation.device,
            "shots": 0,
            "bond_dimension": recommendation.bond_dimension,
            "steps": [
                "1. Submit circuit without measurement",
                "2. Get statevector",
                "3. Analyze amplitudes",
                "4. Calculate probabilities",
            ],
        }

    def _pauli_path_strategy(self, circuit, recommendation):
        """Execute Pauli path strategy."""
        return {
            "strategy": "Pauli Path",
            "device": "pauli-path",
            "steps": [
                "1. Define Pauli observables",
                "2. Submit to pauli-path device",
                "3. Get expectation values",
                "4. Optimize observables",
            ],
        }

    def _vqa_gradient_strategy(self, circuit, recommendation):
        """Execute VQA gradient strategy."""
        return {
            "strategy": "VQA Gradient",
            "device": recommendation.device,
            "shots": recommendation.shots,
            "steps": [
                "1. Initialize random parameters",
                "2. Define cost function",
                "3. Execute quantum circuit",
                "4. Calculate gradients",
                "5. Update parameters",
                "6. Repeat until convergence",
            ],
        }

    def _qaoa_mixer_strategy(self, circuit, recommendation):
        """Execute QAOA mixer strategy."""
        return {
            "strategy": "QAOA Mixer",
            "device": recommendation.device,
            "shots": recommendation.shots,
            "steps": [
                "1. Define graph/problem",
                "2. Initialize gamma, beta",
                "3. Apply QAOA circuit",
                "4. Measure and calculate cost",
                "5. Optimize parameters",
                "6. Return best solution",
            ],
        }


def demo_strategy_selector():
    """Demonstrate strategy selector."""
    print("=" * 70)
    print("BlueQubit Strategy Selector Demo")
    print("=" * 70)

    selector = StrategySelector()

    # Test cases
    test_cases = [
        {
            "name": "Little Dimple (36 qubits)",
            "target": "Find heavy output from peaked circuit",
            "n_qubits": 36,
            "budget": "medium",
        },
        {
            "name": "Small peaked circuit (10 qubits)",
            "target": "Find peak probability",
            "n_qubits": 10,
            "budget": "low",
        },
        {
            "name": "VQE optimization",
            "target": "Minimize energy",
            "objective": "optimize variational parameters",
            "n_qubits": 8,
            "budget": "medium",
        },
        {
            "name": "MaxCut QAOA",
            "target": "Maximize cut",
            "objective": "solve combinatorial optimization",
            "n_qubits": 12,
            "budget": "medium",
        },
    ]

    for test in test_cases:
        print(f"\n{'=' * 70}")
        print(f"Test: {test['name']}")
        print(f"{'=' * 70}")

        # Analyze
        challenge_type = selector.analyze_challenge(
            n_qubits=test["n_qubits"], target=test.get("target"), objective=test.get("objective")
        )
        print(f"Detected Type: {challenge_type.value}")

        # Recommend
        recommendation = selector.recommend_strategy(
            challenge_type, test["n_qubits"], budget=test["budget"]
        )

        print(f"\nRecommendation:")
        print(f"  Primary Strategy: {recommendation.primary_strategy}")
        print(f"  Secondary Strategy: {recommendation.secondary_strategy}")
        print(f"  Device: {recommendation.device}")
        print(f"  Shots: {recommendation.shots}")
        print(f"  Bond Dimension: {recommendation.bond_dimension}")
        print(f"  Estimated Time: {recommendation.estimated_time}")
        print(f"  Estimated Cost: {recommendation.estimated_cost}")
        print(f"  Confidence: {recommendation.confidence:.1%}")

        print(f"\nJustification:")
        for j in recommendation.justification:
            print(f"  • {j}")

        # Execute
        result = selector.execute_strategy(recommendation)
        print(f"\nExecution Plan:")
        for step in result.get("steps", []):
            print(f"  {step}")

    print("\n" + "=" * 70)
    print("Demo Complete")
    print("=" * 70)


if __name__ == "__main__":
    demo_strategy_selector()
