"""Hyperparameter search via democratic debate.

Uses the DemocraticDebate orchestrator to have multiple agent personas
discuss and converge on REINFORCE hyperparameters for the FlumeNav-v0
environment.
"""

import json
import logging
import math
from pathlib import Path
from typing import Any

from cohezion.swarm.democratic_debate import DemocraticDebate


logger = logging.getLogger(__name__)

# Sensible defaults and bounds for each hyperparameter
_PARAM_SPEC: dict[str, dict[str, float]] = {
    "learning_rate": {"min": 1e-5, "max": 1e-2, "default": 3e-4},
    "lr": {"min": 1e-5, "max": 1e-2, "default": 3e-4},
    "hidden_dim": {"min": 64, "max": 512, "default": 128},
    "hidden": {"min": 64, "max": 512, "default": 128},
    "gamma": {"min": 0.9, "max": 0.999, "default": 0.99},
    "discount": {"min": 0.9, "max": 0.999, "default": 0.99},
    "action_scale": {"min": 0.001, "max": 0.1, "default": 0.01},
    "kl_weight": {"min": 1e-4, "max": 0.015, "default": 0.01},  # collapse at ~0.02 (empirical)
}

# Canonical name mapping (aliases -> canonical)
_CANONICAL: dict[str, str] = {
    "lr": "learning_rate",
    "hidden": "hidden_dim",
    "discount": "gamma",
}


def _nearest_power_of_2(x: float) -> int:
    """Round to nearest power of 2."""
    if x <= 0:
        return 64
    log2 = math.log2(x)
    return int(2 ** round(log2))


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _apply_bounds(raw_params: dict[str, float]) -> dict[str, Any]:
    """Clamp extracted params to sensible ranges and apply defaults."""
    result: dict[str, Any] = {}

    for name, value in raw_params.items():
        spec = _PARAM_SPEC.get(name)
        if spec is None:
            continue
        canonical = _CANONICAL.get(name, name)
        clamped = _clamp(value, spec["min"], spec["max"])
        if canonical == "hidden_dim":
            clamped = float(_nearest_power_of_2(clamped))
        result[canonical] = clamped

    # Fill defaults for anything not extracted
    defaults = {
        "learning_rate": 3e-4,
        "hidden_dim": 128,
        "gamma": 0.99,
        "action_scale": 0.01,
    }
    for key, default in defaults.items():
        if key not in result:
            result[key] = default

    # Ensure hidden_dim is int in output
    result["hidden_dim"] = int(result["hidden_dim"])
    return result


class HyperparameterDebate:
    """Use democratic debate to search for RL hyperparameters."""

    def __init__(self, ollama_host: str = "http://localhost:11434"):
        self.ollama_host = ollama_host

    async def search_rl_params(
        self,
        baseline_metrics: dict | None = None,
        output_path: str = "data/rl/hyperparameter_debate.json",
    ) -> dict:
        """Run debate on RL hyperparameters, return suggested params.

        Parameters
        ----------
        baseline_metrics
            Optional dict of current training metrics to inform the debate.
        output_path
            Where to save the full debate session JSON.

        Returns
        -------
        dict
            Bounded hyperparameter dict with keys: learning_rate, hidden_dim,
            gamma, action_scale.
        """
        topic = (
            "Optimal REINFORCE hyperparameters for 256D FlumeNav-v0 environment, "
            "CPU-only training, Hamiltonian dynamics. "
            "Parameters to decide: learning_rate, hidden_dim, gamma "
            "(discount factor), action_scale, reward weights."
        )
        if baseline_metrics:
            summary = ", ".join(f"{k}={v}" for k, v in baseline_metrics.items())
            topic += f" Current baseline: {summary}"

        debate = DemocraticDebate(ollama_host=self.ollama_host)
        try:
            session = await debate.run_debate(
                topic=topic,
                max_rounds=3,
                min_rounds=3,
            )
        finally:
            await debate.close()

        # Extract params from the consensus
        raw_params: dict[str, float] = {}
        if session.final_consensus:
            raw_params = session.final_consensus.get("extracted_params", {})

        params = _apply_bounds(raw_params)

        # Save full session
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump(
                {
                    "params": params,
                    "session": session.to_dict(),
                },
                f,
                indent=2,
                default=str,
            )
        logger.info("Hyperparameter debate saved to %s", out)

        return params


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    params = asyncio.run(HyperparameterDebate().search_rl_params())
    print(f"Suggested params: {json.dumps(params, indent=2)}")
