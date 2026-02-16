"""Universe Repository - Abstract definitions for universe persistence.

Re-exports core types from surreal_client for convenience.

TODO: Implement full UniverseRepository abstract base class.
"""

from cohezion.core.persistence.surreal_client import PhysicsState, UniverseNode


__all__ = ["PhysicsState", "UniverseNode"]
