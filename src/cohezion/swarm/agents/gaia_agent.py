import logging
import random
import asyncio
import time
from cohezion.swarm.agents.base import BaseAgent, AgentResponse
from cohezion.swarm.agents.sovereign_agent import SovereignAgent
from cohezion.swarm.swarm_types import SwarmConfig
from cohezion.reliability.monitor import get_resource_monitor
from cohezion.gaia.interface import get_planetary_interface
from cohezion.bio.biophotonics import BioSignal, Wavelength
from cohezion.core.local_registry import get_local_registry

logger = logging.getLogger(__name__)

class GaiaAgent(SovereignAgent):
    """
    Gaia Agent (Phase 18).

    Gateway 29: Planetary Interface & Parthenogenesis.

    Role:
    - Immune System: Throttles system if overheating.
    - Creator: Spawns clones (Parthenogenesis) if resources allow.
    """
    MAX_CLONES = 5
    SPAWN_COOLDOWN_SECONDS = 60

    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(config=config)
        self.interface = get_planetary_interface()
        self.id = "GaiaAgent"
        self.last_spawn_time = 0.0
        self.clone_count = 0

    async def process(self, query: str) -> str:
        """
        Monitor system health and react.
        """
        # 1. Sense Constants
        constants = self.interface.get_cosmic_constants()
        temp = constants["CosmicTemperature"]
        energy = constants["VacuumEnergy"]
        entropy = constants["UniversalEntropy"]

        report = f"\n\n### 🌍 Gaia Report (Vital Signs)\n"
        report += f"**Cosmic Temperature**: {temp:.1f} (Activity/min)\n"
        report += f"**Vacuum Energy**: {energy:.2f} (ZPE Availability)\n"
        report += f"**Universal Entropy**: {entropy:.4f}\n"

        # 2. Immunity Response (Overheating)
        if temp > 100: # Arbitrary threshold for simulation
            self._emit(Wavelength.RED, 0.9, "CRITICAL: System Overheating")
            report += "⚠️ **Immune Response**: Emitted RED signal (Throttling).\n"
            # In a real loop, other agents would subscribe to this signal and sleep()
            await asyncio.sleep(5.0) # Gaia forces a pause

        elif temp > 80:
             self._emit(Wavelength.BLUE, 0.7, "WARN: High Load")
             report += "⚠️ **Immune Response**: Emitted BLUE signal (Warning). Throttling active.\n"
             await asyncio.sleep(2.0)

        # 3. Parthenogenesis (Asexual Reproduction)
        # "If Vacuum Energy is high (>0.8) and Entropy is efficient"
        if energy > 0.8 and entropy < 0.2:
            now = time.time()
            cooldown_ok = (now - self.last_spawn_time) > self.SPAWN_COOLDOWN_SECONDS
            capacity_ok = self.clone_count < self.MAX_CLONES

            if cooldown_ok and capacity_ok:
                # Check if we can afford to spawn
                registry = get_local_registry()
                if registry.check_capacity(min_gb=10.0):
                    # Simulate spawning a clone
                    spawn_name = f"Mistral-Clone-{random.randint(100,999)}"
                    report += f"🌱 **Parthenogenesis Triggered**: Spawning {spawn_name} to expand universe simulation.\n"
                    logger.info(f"Gaia spawned new agent: {spawn_name}")
                    self.last_spawn_time = now
                    self.clone_count += 1
                else:
                     report += "🌱 **Parthenogenesis Inhibited**: Insufficient Storage.\n"
            elif not capacity_ok:
                report += "🌱 **Parthenogenesis Inhibited**: Maximum Clones Reached.\n"
            else:
                report += "🌱 **Parthenogenesis Inhibited**: Cooldown Active.\n"

        base_resp = await super().process(query)
        return AgentResponse(
            base_resp + report,
            embedding=getattr(base_resp, 'embedding', None),
            persistence_id=getattr(base_resp, 'persistence_id', None),
            frequency=getattr(base_resp, 'frequency', 1),
            phi_score=getattr(base_resp, 'phi_score', 0.0),
            confidence=getattr(base_resp, 'confidence', 1.0),
            security_level=getattr(base_resp, 'security_level', "safe"),
            narration=getattr(base_resp, 'narration', None),
            alignment_score=getattr(base_resp, 'alignment_score', 1.0)
        )

    async def close(self):
        await super().close()
