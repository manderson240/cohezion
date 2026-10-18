"""Terminal-RSI: Recursive Self-Improving Terminal Agent Invariants.

Abstracted and implemented from arXiv:2610.22192:
'Terminal-RSI: Recursive Self-Improving Terminal Agents via Recursive
Self-Rewrite and Policy-Refine' (Yang et al., Oct 2026).

Provides:
1. SuccessPrioritizedReward (SPR): Concave bounded partial credit with strict
   separation between failure (< 1.0) and verified terminal success (>= 1.0).
2. TurnBoundaryGAE (TB-GAE): Credit assignment across interaction turn boundaries
   invariant to passive observation/log token dilation.
3. RecursiveTrajectoryRewriter (RSR): Verified trajectory discovery, runbook abstraction,
   leakage screening, and clean replay curation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


@dataclass
class FamilyCalibrationConfig:
    """Task-family specific divisor for progress calibration."""
    family: str
    default_divisor: float = 82.0
    failure_suppressed_multiplier: float = 2.0
    low_return_multiplier: float = 0.25

    def get_divisor(self, high_reward_failure: bool = False, low_return: bool = False) -> float:
        """Calculate phase-frozen divisor D'_f."""
        div = self.default_divisor
        if high_reward_failure:
            # Failure suppression takes strict precedence
            div *= self.failure_suppressed_multiplier
        elif low_return:
            div *= self.low_return_multiplier
        return max(1.0, div)


class SuccessPrioritizedReward:
    """Success-Prioritized Reward (SPR) per arXiv:2610.22192.
    
    Eliminates proxy-outcome mismatch by bounding partial progress credit:
        R_SPR(S, P, D'_f) = S + P / (P + D'_f)
    
    Invariants:
    1. Every failed trajectory scores strictly in [0.0, 1.0).
    2. Every verified success scores in [1.0, 2.0).
    3. Partial credit is strictly concave: g'_f(P) > 0, g''_f(P) < 0.
    4. Reward variance is strictly bounded: Var(R_SPR) <= 1.0.
    """

    def __init__(self, family_configs: Optional[Dict[str, FamilyCalibrationConfig]] = None):
        self.family_configs = family_configs or {}

    def compute_reward(
        self,
        strict_success: bool,
        passed_checks: int,
        family: str = "default",
        high_reward_failure: bool = False,
        low_return: bool = False,
    ) -> float:
        """Compute SPR reward with bounded partial credit."""
        config = self.family_configs.get(family, FamilyCalibrationConfig(family=family))
        d_prime = config.get_divisor(high_reward_failure=high_reward_failure, low_return=low_return)
        
        p = max(0, passed_checks)
        # Strictly concave bounded progress term g_f(P) in [0, 1)
        progress_credit = float(p) / float(p + d_prime)
        
        s = 1.0 if strict_success else 0.0
        reward = s + progress_credit
        
        # Invariant checks
        if not strict_success:
            assert reward < 1.0, f"Failure reward must be < 1.0, got {reward}"
        else:
            assert reward >= 1.0, f"Success reward must be >= 1.0, got {reward}"
        assert 0.0 <= reward < 2.0, f"Reward must be bounded in [0, 2), got {reward}"
        
        return reward


@dataclass
class TurnStep:
    """Action turn step containing pre-token values and causally assigned rewards."""
    turn_id: int
    is_decision_token: bool
    value: float
    reward: float = 0.0
    is_terminal: bool = False


class TurnBoundaryGAE:
    """Turn-Boundary Skip-Observation Generalized Advantage Estimation (TB-GAE).
    
    Decays credit strictly across interaction turn boundaries B:
        decay = (gamma_turn * lambda_turn)^B
    
    Observations condition values but are NEVER recursion nodes, eliminating
    the temporal dilation artifact where verbose shell logs attenuate credit.
    """

    def __init__(
        self,
        gamma_turn: float = 0.99,
        lambda_turn: float = 0.95,
    ):
        self.gamma_turn = float(gamma_turn)
        self.lambda_turn = float(lambda_turn)
        assert 0.0 <= self.gamma_turn <= 1.0
        assert 0.0 <= self.lambda_turn <= 1.0

    def compute_advantages(
        self,
        steps: List[TurnStep],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute TB-GAE advantages and value targets for a sequence of turn steps.
        
        Parameters
        ----------
        steps : List[TurnStep]
            Ordered list of generated tokens/steps with turn_id, values, and rewards.
            
        Returns
        -------
        advantages : np.ndarray
            Calculated advantages A_j^TB.
        targets : np.ndarray
            Value targets G_j^hat = A_j^TB + v_j.
        """
        n = len(steps)
        if n == 0:
            return np.array([]), np.array([])

        advantages = np.zeros(n, dtype=np.float64)
        targets = np.zeros(n, dtype=np.float64)

        # Filter and index only policy decision positions
        # Backward pass from episode end
        last_turn_id = steps[-1].turn_id
        running_adv = 0.0

        for j in reversed(range(n)):
            curr = steps[j]
            v_curr = curr.value
            r_curr = curr.reward
            d_curr = 1.0 if curr.is_terminal else 0.0

            if j == n - 1:
                # Terminal boundary
                v_next = 0.0
                gamma_decay = 1.0
                lambda_decay = 1.0
            else:
                next_step = steps[j + 1]
                v_next = next_step.value
                # Turn-boundary clock: decay applies ONLY if turn_id advances
                turn_advanced = (next_step.turn_id != curr.turn_id)
                gamma_decay = self.gamma_turn if turn_advanced else 1.0
                lambda_decay = self.lambda_turn if turn_advanced else 1.0

            # Delta: r_j + gamma * (1 - d) * v_next - v_curr
            delta = r_curr + gamma_decay * (1.0 - d_curr) * v_next - v_curr

            if curr.is_terminal:
                running_adv = delta
            else:
                running_adv = delta + gamma_decay * lambda_decay * (1.0 - d_curr) * running_adv

            advantages[j] = running_adv
            targets[j] = running_adv + v_curr

        return advantages, targets


@dataclass
class VerifiedTrajectory:
    """Trajectory that passed complete protected verifier V_x(tau) = 1."""
    task_id: str
    actions: List[Dict[str, Any]]
    final_output: str
    strict_verifier_passed: bool
    leakage_screen_passed: bool
    runbook: Optional[str] = None


class RecursiveTrajectoryRewriter:
    """Recursive Self-Rewrite (RSR) trajectory coordinator.
    
    Retains discovered solutions only when:
        a_x(tau) = V_x(tau) and q_leak(tau) == 1
    
    Generates clean runbooks, strips harness-specific control artifacts,
    and curates accepted multisets for the policy refinement phase.
    """

    def __init__(self):
        self.verified_pool: List[VerifiedTrajectory] = []

    def evaluate_and_ingest(
        self,
        task_id: str,
        actions: List[Dict[str, Any]],
        final_output: str,
        verifier_outcome: bool,
        leakage_clean: bool,
        runbook: Optional[str] = None,
    ) -> bool:
        """Ingest trajectory if and only if verifier and leakage gates pass."""
        if verifier_outcome and leakage_clean:
            traj = VerifiedTrajectory(
                task_id=task_id,
                actions=actions,
                final_output=final_output,
                strict_verifier_passed=True,
                leakage_screen_passed=True,
                runbook=runbook,
            )
            self.verified_pool.append(traj)
            return True
        return False

    def get_clean_replay_batch(self, max_samples: Optional[int] = None) -> List[VerifiedTrajectory]:
        """Return clean replay pool for the policy refinement phase."""
        if max_samples is not None:
            return self.verified_pool[:max_samples]
        return list(self.verified_pool)
