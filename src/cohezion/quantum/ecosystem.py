"""
Living Manifold Ecosystem
Main orchestrator integrating all subsystems.
"""

import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import numpy as np

from .quantum_state import QuantumAgent, QuantumState
from .population import AgeStructuredPopulation, DemographicMetrics, LeslieMatrix
from .entanglement import EntanglementNetwork
from .morphospace import BioelectricMorphospace
from .zpe_miner import ZPEMiner
from .retrocausal import RetrocausalEngine, RetrocausalReport

logger = logging.getLogger(__name__)


@dataclass
class EcosystemMetrics:
    """Comprehensive ecosystem metrics."""

    epoch: int
    timestamp: float

    # Population
    population_size: int
    births_this_epoch: int
    deaths_this_epoch: int
    avg_age: float
    avg_coherence: float
    avg_energy: float

    # Demographics
    juvenile_count: int
    mature_count: int
    elderly_count: int
    lambda_dominant: float

    # Network
    n_entanglement_links: int
    avg_network_degree: float

    # Energy
    vacuum_energy: float
    total_agent_energy: float
    energy_equilibrium: float

    # Morphospace
    avg_voltage: float
    well_distributions: Dict[str, int]


class LivingManifoldEcosystem:
    """
    Complete quantum-bioelectric-AI ecosystem.

    Integrates:
    - 10,000 quantum-coherent agents
    - Leslie matrix population dynamics
    - ER=EPR entanglement network
    - Bioelectric morphospace navigation
    - ZPE energy mining
    - Retrocausal debugging
    """

    def __init__(self, n_agents: int = 10000, device: str = "cpu"):
        """
        Initialize complete ecosystem.

        Args:
            n_agents: Target population size
            device: 'cpu' or 'cuda'
        """
        logger.info("Initializing Living Manifold Ecosystem...")

        self.n_agents = n_agents
        self.device = device
        self.epoch = 0
        self.running = True

        # Core components
        logger.info("Creating age-structured population...")
        self.population = AgeStructuredPopulation(target_size=n_agents, device=device)

        logger.info("Creating entanglement network...")
        self.network = EntanglementNetwork(n_agents=n_agents)
        self.network.create_small_world_network(self.population.agents)

        logger.info("Creating bioelectric morphospace...")
        self.morphospace = BioelectricMorphospace()

        logger.info("Creating ZPE mining system...")
        self.zpe_miner = ZPEMiner()

        logger.info("Creating retrocausal debugger...")
        self.retrocausal = RetrocausalEngine()

        # Metrics tracking
        self.metrics_history: List[EcosystemMetrics] = []
        self.failed_agents: List[QuantumAgent] = []

        logger.info(f"Ecosystem initialized: {len(self.population.agents)} agents")

    def step(self) -> EcosystemMetrics:
        """
        Execute one epoch of ecosystem evolution.

        Returns:
            EcosystemMetrics for this epoch
        """
        if not self.running:
            return None

        self.epoch += 1
        start_time = time.time()

        # 1. Quantum thinking (ORCH-OR)
        for agent in self.population.agents:
            if agent.alive:
                agent.think()

        # 2. Bioelectric navigation
        for agent in self.population.agents:
            if agent.alive:
                self.morphospace.apply_bioelectric_force(agent)

        # 3. Entanglement correlations
        self._update_entanglements()

        # 4. ZPE mining
        for agent in self.population.agents:
            if agent.alive:
                self.zpe_miner.mine_energy(agent)

        # 5. Population dynamics (Leslie matrix)
        demo_metrics = self.population.update_population()

        # 6. Retrocausal debugging for failed agents
        self._debug_failures()

        # 7. Collect metrics
        metrics = self._collect_metrics(demo_metrics)
        self.metrics_history.append(metrics)

        # 8. Check for emergency stop conditions
        self._check_emergency_conditions()

        return metrics

    def _update_entanglements(self):
        """Update entanglement correlations."""
        agents_dict = {a.id: a for a in self.population.agents if a.alive}

        # Random measurements trigger correlations
        for link in self.network.links:
            if np.random.random() < 0.1:  # 10% chance
                # Random measurement on one agent
                if link.agent_a_id in agents_dict:
                    agent_a = agents_dict[link.agent_a_id]
                    outcome = agent_a.position_12d
                    link.correlate(link.agent_a_id, outcome, agents_dict)

    def _debug_failures(self):
        """Run retrocausal debugging on failed agents."""
        failed = [a for a in self.population.agents if a.alive and a.coherence < 0.3]

        if failed:
            reports = self.retrocausal.batch_debug_failures(failed)
            self.failed_agents.extend(failed)

            if reports:
                logger.warning(f"Debugged {len(reports)} failed agents")

    def _collect_metrics(self, demo: DemographicMetrics) -> EcosystemMetrics:
        """Collect comprehensive ecosystem metrics."""
        alive_agents = [a for a in self.population.agents if a.alive]

        if not alive_agents:
            return EcosystemMetrics(
                epoch=self.epoch,
                timestamp=time.time(),
                population_size=0,
                births_this_epoch=0,
                deaths_this_epoch=0,
                avg_age=0,
                avg_coherence=0,
                avg_energy=0,
                juvenile_count=0,
                mature_count=0,
                elderly_count=0,
                lambda_dominant=demo.lambda_dominant,
                n_entanglement_links=len(self.network.links),
                avg_network_degree=0,
                vacuum_energy=self.zpe_miner.total_vacuum_energy,
                total_agent_energy=0,
                energy_equilibrium=0,
                avg_voltage=0,
                well_distributions={},
            )

        # Network stats
        network_stats = self.network.get_network_stats()

        # Energy stats
        total_agent_energy = sum(a.energy for a in alive_agents)
        vacuum_status = self.zpe_miner.get_vacuum_status()

        # Morphospace stats
        voltages = [a.current_voltage for a in alive_agents]
        well_dist = {}
        for a in alive_agents:
            well = a.target_well
            well_dist[well] = well_dist.get(well, 0) + 1

        return EcosystemMetrics(
            epoch=self.epoch,
            timestamp=time.time(),
            population_size=len(alive_agents),
            births_this_epoch=demo.births_this_epoch,
            deaths_this_epoch=demo.deaths_this_epoch,
            avg_age=np.mean([a.age for a in alive_agents]),
            avg_coherence=np.mean([a.coherence for a in alive_agents]),
            avg_energy=np.mean([a.energy for a in alive_agents]),
            juvenile_count=demo.juvenile_count,
            mature_count=demo.mature_count,
            elderly_count=demo.elderly_count,
            lambda_dominant=demo.lambda_dominant,
            n_entanglement_links=network_stats["n_links"],
            avg_network_degree=network_stats["avg_degree"],
            vacuum_energy=vacuum_status["available_energy"],
            total_agent_energy=total_agent_energy,
            energy_equilibrium=total_agent_energy
            / (total_agent_energy + vacuum_status["available_energy"]),
            avg_voltage=np.mean(voltages) if voltages else 0,
            well_distributions=well_dist,
        )

    def _check_emergency_conditions(self):
        """Check for emergency stop conditions."""
        alive_count = len([a for a in self.population.agents if a.alive])

        # Stop if population collapses
        if alive_count < 100:
            logger.error("EMERGENCY: Population collapse detected!")
            self.running = False

        # Stop if all vacuum energy depleted
        if self.zpe_miner.total_vacuum_energy < 10:
            logger.error("EMERGENCY: Vacuum energy depleted!")
            self.running = False

    def run_simulation(self, n_epochs: int = 1000, log_interval: int = 10):
        """
        Run full simulation.

        Args:
            n_epochs: Number of epochs to simulate
            log_interval: Log metrics every N epochs
        """
        logger.info(f"\n{'=' * 60}")
        logger.info("STARTING LIVING MANIFOLD ECOSYSTEM SIMULATION")
        logger.info(f"{'=' * 60}\n")
        logger.info(f"Initial population: {len(self.population.agents)}")
        logger.info(f"Target population: {self.n_agents}")
        logger.info(f"Simulation epochs: {n_epochs}")
        logger.info(f"Device: {self.device}\n")

        start_time = time.time()

        for epoch in range(n_epochs):
            if not self.running:
                logger.warning(f"Simulation stopped at epoch {epoch}")
                break

            metrics = self.step()

            if epoch % log_interval == 0:
                self._log_epoch_summary(epoch, metrics)

        elapsed = time.time() - start_time

        logger.info(f"\n{'=' * 60}")
        logger.info("SIMULATION COMPLETE")
        logger.info(f"{'=' * 60}\n")
        logger.info(f"Total epochs: {self.epoch}")
        logger.info(
            f"Final population: {len([a for a in self.population.agents if a.alive])}"
        )
        logger.info(f"Elapsed time: {elapsed:.2f}s")
        logger.info(f"Avg time/epoch: {elapsed / max(1, self.epoch) * 1000:.2f}ms\n")

        return self.metrics_history

    def _log_epoch_summary(self, epoch: int, metrics: EcosystemMetrics):
        """Log summary of epoch."""
        logger.info(
            f"Epoch {epoch:4d} | "
            f"Pop: {metrics.population_size:5d} | "
            f"Births: {metrics.births_this_epoch:3d} | "
            f"Deaths: {metrics.deaths_this_epoch:3d} | "
            f"λ: {metrics.lambda_dominant:.3f} | "
            f"Coh: {metrics.avg_coherence:.3f} | "
            f"Energy: {metrics.total_agent_energy:.1f} | "
            f"Vacuum: {metrics.vacuum_energy:.1f}"
        )

    def get_summary_statistics(self) -> Dict:
        """Get summary statistics from entire simulation."""
        if not self.metrics_history:
            return {}

        populations = [m.population_size for m in self.metrics_history]
        coherences = [m.avg_coherence for m in self.metrics_history]
        energies = [m.total_agent_energy for m in self.metrics_history]

        return {
            "total_epochs": self.epoch,
            "initial_population": populations[0] if populations else 0,
            "final_population": populations[-1] if populations else 0,
            "min_population": min(populations) if populations else 0,
            "max_population": max(populations) if populations else 0,
            "avg_coherence": np.mean(coherences) if coherences else 0,
            "final_coherence": coherences[-1] if coherences else 0,
            "total_births": sum(m.births_this_epoch for m in self.metrics_history),
            "total_deaths": sum(m.deaths_this_epoch for m in self.metrics_history),
            "energy_equilibrium_final": energies[-1]
            / (energies[-1] + self.zpe_miner.total_vacuum_energy)
            if energies
            else 0,
        }

    def emergency_stop(self):
        """Emergency stop of simulation."""
        logger.warning("Emergency stop triggered!")
        self.running = False

    def get_agent_details(self, agent_id: int) -> Optional[Dict]:
        """Get detailed information about an agent."""
        try:
            agent = self.population.get_agent_by_id(agent_id)
            return {
                "id": agent.id,
                "age": agent.age,
                "coherence": agent.coherence,
                "energy": agent.energy,
                "alive": agent.alive,
                "position": agent.position_12d.tolist(),
                "target_well": agent.target_well,
                "n_entangled": len(agent.entangled_partners),
                "journey_length": len(agent.journey),
                "journey_quality": agent.get_journey_quality(),
            }
        except ValueError:
            return None
