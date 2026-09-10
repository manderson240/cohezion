"""Cohezion Neuro & Connectomics Subsystem.

Integrates biological connectome architectures (e.g. Drosophila melanogaster CNS)
into Cohezion's FLUME neural mesh and SurrealDB substrate.
"""

from cohezion.neuro.drosophila_cns import (
    DrosophilaCircuitTier,
    DrosophilaCNSConnectome,
    DrosophilaNeuronType,
    DrosophilaSensoryMotorCircuit,
)


__all__ = [
    "DrosophilaCNSConnectome",
    "DrosophilaCircuitTier",
    "DrosophilaNeuronType",
    "DrosophilaSensoryMotorCircuit",
]
