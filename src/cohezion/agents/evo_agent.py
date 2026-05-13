import logging
from typing import Any

import torch

from cohezion.agents.base import BaseAgent
from cohezion.flume.vae import FlumeVAE, FlumeVAEConfig
from cohezion.persistence.obsidian_mcp import ObsidianMemoryMCP
from cohezion.persistence.surreal_logger import SurrealTrajectoryLogger
from cohezion.rewards.calculator import RewardCalculator
from cohezion.rewards.ratchet import RatchetMechanism
from cohezion.swarm.swarm_types import SwarmConfig
from cohezion.universe.triune_engine import TriuneSimulationEngine
from cohezion.universe.triune_manifold import TriuneState


logger = logging.getLogger(__name__)


class EVOAgent(BaseAgent):
    """
    Sovereign agent modeled as an Exotic Vacuum Object (EVO).

    Navigates the 12D/512D/2048D Triune Manifold using FLUME VAE
    for conceptual interpolation and the Triune Engine for state transitions.
    Governance is provided by the Reward & Ratchet system.
    """

    def __init__(
        self,
        model_name: str,
        config: SwarmConfig | None = None,
        surreal_logger: SurrealTrajectoryLogger | None = None,
        obsidian_mcp: ObsidianMemoryMCP | None = None,
        **kwargs,
    ):
        super().__init__(model_name, config, **kwargs)

        # Initialize internal manifold state (zero-initialized for scaffold)
        self.manifold_state = TriuneState(doer=torch.zeros(12), thinker=torch.zeros(512), knower=torch.zeros(2048))

        # Persistence Layer (DI)
        self._surreal_logger = surreal_logger or SurrealTrajectoryLogger()
        self._obsidian_mcp = obsidian_mcp or ObsidianMemoryMCP()

        # Simulation Engine
        self._triune_engine = TriuneSimulationEngine(
            state=self.manifold_state,
            surreal_logger=self._surreal_logger,
            obsidian_mcp=self._obsidian_mcp,
        )

        # FLUME VAE
        vae_config = FlumeVAEConfig(z_dim=256)
        self._flume_vae = FlumeVAE(vae_config)

        # Governance & Economy
        self._reward_calculator = RewardCalculator()
        self._ratchet = RatchetMechanism(obsidian_mcp=self._obsidian_mcp)

    async def act(self, prompt: str, trajectory_id: str) -> None:
        """
        Performs a sovereign agentic action.

        1. Encodes the prompt intent into a latent ThoughtVector.
        2. Projects the intent into the Triune Engine.
        3. Transitions the manifold state.
        4. Calculates reward and evaluates ratchet.

        Args:
            prompt: Human-provided idea or goal.
            trajectory_id: Unique identifier for the journey.
        """
        # Conceptual: Encode intent
        tokens = torch.zeros((1, 1), dtype=torch.long)  # Dummy
        mu, logvar = self._flume_vae.encode(tokens)
        intent_vec = self._flume_vae.reparameterize(mu, logvar)

        # Map intent vector to environment input (12D)
        env_input = torch.zeros(12)
        env_input[: min(12, intent_vec.shape[0])] = intent_vec[: min(12, intent_vec.shape[0])]

        # Step the engine
        await self._triune_engine.step(dt=0.1, environment=env_input, trajectory_id=trajectory_id)

        # Governance Loop
        # 1. Calculate coherence (from updated doer state vs intent)
        # Note: Triune Engine handles coherence calc internally during step,
        # but for reward we need the value.
        from cohezion.universe.triune_manifold import calculate_hiho_coherence

        coherence = calculate_hiho_coherence(self.manifold_state.doer, env_input)

        # 2. Reward Calculation (Dummy tokens for now)
        score = self._reward_calculator.calculate_score(coherence=coherence, tokens_used=100)

        # 3. Ratchet Evaluation
        await self._ratchet.evaluate_and_ratchet(
            trajectory_id=trajectory_id, state=self.manifold_state, score=score, coherence=coherence
        )

        logger.info(f"EVO Agent {self.__class__.__name__} performed action. Score: {score:.4f}")

    async def process(self, *args: Any, **kwargs: Any) -> Any:
        """
        Implementation of the required BaseAgent process method.
        """
        query = args[0] if args else kwargs.get("query", "")
        traj_id = kwargs.get("trajectory_id", f"auto_{int(torch.randint(0, 10000, (1,)).item())}")

        await self.act(query, traj_id)

        # Call the parent's Ollama execution for text response
        return await self._call_ollama(query)
