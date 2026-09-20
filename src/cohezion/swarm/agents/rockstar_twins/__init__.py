"""Council of Rockstar Scientist Digital Twins for Monolith Decomposition.

Digital Twins:
- ClaudeShannonTwin: Interface & Channel Architect (cz-gateway)
- LeslieLamportTwin: Distributed Consensus & Invariant Architect (cz-consensus)
- RichardFeynmanTwin: Silicon Compute & Hardware Kernel Architect (cz-inference)
- BarbaraMcClintockTwin: Autopoietic Self-Healing Architect (cz-autopoiesis)
- JohnVonNeumannTwin: Swarm Automata & Game-Theoretic Architect (cz-swarm)
- IlyaPrigogineTwin: Non-Equilibrium Persistence & Cache Architect (cz-persistence)
- RockstarCouncil: Multi-agent council orchestrator
"""

from __future__ import annotations

from cohezion.swarm.agents.rockstar_twins.base_twin import RockstarScientistTwin
from cohezion.swarm.agents.rockstar_twins.feynman_twin import RichardFeynmanTwin
from cohezion.swarm.agents.rockstar_twins.lamport_twin import LeslieLamportTwin
from cohezion.swarm.agents.rockstar_twins.mcclintock_twin import BarbaraMcClintockTwin
from cohezion.swarm.agents.rockstar_twins.prigogine_twin import IlyaPrigogineTwin
from cohezion.swarm.agents.rockstar_twins.shannon_twin import ClaudeShannonTwin
from cohezion.swarm.agents.rockstar_twins.twin_council import RockstarCouncil
from cohezion.swarm.agents.rockstar_twins.von_neumann_twin import JohnVonNeumannTwin


__all__ = [
    "BarbaraMcClintockTwin",
    "ClaudeShannonTwin",
    "IlyaPrigogineTwin",
    "JohnVonNeumannTwin",
    "LeslieLamportTwin",
    "RichardFeynmanTwin",
    "RockstarCouncil",
    "RockstarScientistTwin",
]
