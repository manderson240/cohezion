"""Cohezion Gymnasium environments for RL agent training."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.environments.manifold_env import ManifoldEnv as ManifoldEnv

with contextlib.suppress(Exception):
    from cohezion.environments.swarm_env import SwarmEnv as SwarmEnv

with contextlib.suppress(Exception):
    from cohezion.environments.universe_agent_env import (
        UniverseAgentEnv as UniverseAgentEnv,
    )


__all__ = ["ManifoldEnv", "SwarmEnv", "UniverseAgentEnv"]

# Wiring-sweep 2026-06-06: auto_generator was a genuine production orphan — its
# EnvironmentGenerator / EnvironmentSpec / GeneratedEnvironment / GeneratedCodeValidator
# (specification-driven environment synthesis) had ZERO importers anywhere (src, tests,
# registry, entry-points). Guarded re-export puts it on the package surface and makes it
# statically reachable. SEPARATE suppress block (it imports torch + transformers at module
# scope) so a heavy-optional-dep absence can't take down the load-bearing ManifoldEnv/SwarmEnv
# imports above — failure-domain isolation, per the world_model/sigreg pattern.
with contextlib.suppress(Exception):
    from cohezion.environments.auto_generator import (
        EnvironmentGenerator as EnvironmentGenerator,
    )
    from cohezion.environments.auto_generator import (
        EnvironmentSpec as EnvironmentSpec,
    )
    from cohezion.environments.auto_generator import (
        GeneratedCodeValidator as GeneratedCodeValidator,
    )
    from cohezion.environments.auto_generator import (
        GeneratedEnvironment as GeneratedEnvironment,
    )

    __all__ += [
        "EnvironmentGenerator",
        "EnvironmentSpec",
        "GeneratedCodeValidator",
        "GeneratedEnvironment",
    ]

# Wiring-sweep 2026-06-22: arc_env was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.environments.arc_env import (
        ARCEnvironment as ARCEnvironment,
    )
