from collections import defaultdict
from typing import Dict, List, Set

from cohezion.inference.transition_controller import TransitionController
from cohezion.world_model.observer import Observer
from cohezion.inference.task_classifier import classify


class ObserverWorldModel:
    def __init__(self, observer: Observer, default_coherence: float = 0.7):
        self.observer = observer
        self._default_coherence = default_coherence
        self._state = "unknown"
        self._n_transitions = defaultdict(int)
        self._transition_counts = defaultdict(lambda: defaultdict(int))

    def set_task(self, task_description: str) -> None:
        try:
            self._state = classify(task_description).output_type
        except Exception:
            self._state = "unknown"

    def record(self, frm: str, to: str, quality: float) -> float:
        reward = 2.0 * quality - 1.0
        surprise = 1.0
        if self._n_transitions[frm] > 0:
            surprise = 1.0 - self._transition_counts[frm][to]/self._n_transitions[frm]
        try:
            self.observer.observe(surprise)
        except Exception:
            pass
        self.observer.state_matrix.record_transition(frm, to, reward)
        self._n_transitions[frm] += 1
        self._transition_counts[frm][to] += 1
        return surprise

    def transition_probability(self, frm: str, to: str) -> float:
        ranked = self.observer.state_matrix.ranked_next(frm)
        if not ranked:
            return 0.0
        total_weight = sum(w for _, w in ranked)
        if total_weight == 0.0:
            return 0.0
        for state, weight in ranked:
            if state == to:
                return weight / total_weight
        return 0.0

    def _expected_quality(self, frm: str) -> float:
        """Coherence = expected outcome quality under the EMPIRICAL transition distribution:
        sum over observed next-states of p̂(to|frm) * quality(frm,to), where p̂ comes from
        recorded counts (never from default weights of unexplored edges — those diluted the
        signal into penalizing states with many options) and quality is decoded from the
        learned edge weight (record_transition targets 1+reward = 2*quality, so w/2 ≈ EMA
        quality, clipped to [0,1])."""
        n = self._n_transitions[frm]
        if n < 3:
            return self._default_coherence
        weights = self.observer.state_matrix.weights
        coherence = 0.0
        for to, count in self._transition_counts[frm].items():
            quality = max(0.0, min(1.0, weights.get((frm, to), 1.0) / 2.0))
            coherence += (count / n) * quality
        return max(0.0, min(1.0, coherence))

    def _most_likely_next(self, frm: str) -> str | None:
        counts = self._transition_counts[frm]
        return max(counts, key=counts.get) if counts else None

    def predict_next_state(self, state, action) -> List[float]:
        return [self._expected_quality(self._state)]

    def simulate_trajectory(self, state, actions) -> List[List[float]]:
        current = self._state
        result = [[self._expected_quality(current)]]
        for _ in actions:
            nxt = self._most_likely_next(current)
            if nxt is None:
                result.append([self._default_coherence])
                continue
            current = nxt
            result.append([self._expected_quality(current)])
        return result

    def n_transitions(self, frm: str) -> int:
        return self._n_transitions[frm]


def trace_kernel(controller: TransitionController, subset: Set[str], max_hops: int = 50) -> Dict[str, Dict[str, float]]:
    """
    Compute the Markov kernel Q_A for a subset of states A.
    
    Implements the formula:
    Q_A = I_A Q Σ_{k=0..∞} (I_U Q)^k Q I_A
    
    where U is the complement of A, I_A and I_U are indicator matrices,
    and Q is the row-normalized transition matrix from controller.ranked_next.
    
    The result is a dict mapping each state in A to a dict of probabilities
    to states in A. Each row sums to at most 1 + 1e-9.
    """
    # Step 1: Build row-normalized transition matrix Q
    states = set(controller.matrix) | {t for lst in controller.matrix.values() for t in lst}
    Q = {}
    
    for s in states:
        valid = controller.ranked_next(s)
        if not valid:
            # Terminal self-loop
            Q[s] = {s: 1.0}
        else:
            total = sum(w for _, w in valid)
            if total == 0:
                # Fallback to uniform over valid
                Q[s] = {v: 1.0 / len(valid) for v, _ in valid}
            else:
                Q[s] = {v: w / total for v, w in valid}

    # Step 2: Compute R using first-return probabilities
    U = states - subset
    R = {}
    
    # Initialize R_prev[u] for all u in U
    R_prev = {}
    for u in U:
        R_prev[u] = {a: Q[u].get(a, 0.0) for a in subset}
    
    # Iterate max_hops times to compute R_next from R_prev
    for _ in range(max_hops):
        R_next = {}
        for u in U:
            R_next[u] = {}
            for a in subset:
                R_next[u][a] = Q[u].get(a, 0.0) + sum(Q[u].get(u2, 0.0) * R_prev[u2][a] for u2 in U)
        R_prev = R_next
    
    # Step 3: Compute Q_A
    Q_A = {}
    
    for a in subset:
        Q_A[a] = {}
        for a2 in subset:
            val = Q[a].get(a2, 0.0) + sum(Q[a].get(u, 0.0) * R_prev[u][a2] for u in U)
            if val > 0.0:
                Q_A[a][a2] = val
    
    return Q_A


# --- live tier-flow singleton (TRACE wiring 2026-07-15) -------------------------------
# States are engine tiers; a transition is (cascade entry tier -> engine that ran).
# Fed by cohezion.compound.local_inference.make_local_execute_fn on every execution;
# consumed by cohezion.compound.lemonade_world_model.build_live_jepa_gate once warm.
_TIER_MATRIX = {
    "npu": ["npu", "igpu", "cpu", "cloud"],
    "igpu": ["igpu", "cpu", "cloud"],
    "cpu": ["cpu", "cloud"],
    "cloud": ["cloud"],
}
_default_model = None


def get_default_observer_model() -> "ObserverWorldModel":
    global _default_model
    if _default_model is None:
        from cohezion.world_model.surprise_router import SurpriseRouter

        _default_model = ObserverWorldModel(
            Observer(
                name="tier-flow",
                state_matrix=TransitionController(matrix={k: list(v) for k, v in _TIER_MATRIX.items()}),
                router=SurpriseRouter(),
            )
        )
    return _default_model
